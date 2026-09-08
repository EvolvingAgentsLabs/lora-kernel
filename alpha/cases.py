"""The task suite, borrowed rather than built.

`../verified-runtime` already owns a sealed `clinical_learning` benchmark with an
**exact** verifier: 50 held-out referral-completeness cases whose truth is a set
of missing document types. Reusing it costs an afternoon; building an equivalent
suite costs a milestone, and the numbers would not be comparable to the ladder
this workspace already ran on it.

Two things are frozen here on purpose:

  * THE PROMPT. Phase I of `verified-runtime` measured a **30-point** swing from
    changing only the wording of a message. The template below is hashed into
    every run record, and changing it is a redesign that gets counted.
  * THE REGIONS. Withdrawal happens per region, so a case carries its region
    label from the start. The clinic is the region: each publishes a different
    required-document protocol, which is exactly the axis an expert specialises on.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = Path(
    os.environ.get("VERIFIED_RUNTIME", Path(__file__).resolve().parents[2] / "verified-runtime")
)

PROMPT_VERSION = "2.0.0"   # 1.0.0 was our own template; see `canonical_prompt`

SYSTEM = (
    "You complete administrative referral checks for a dental clinic network. "
    "You never diagnose and you never recommend treatment."
)

# Kept only as the system turn. The task prompt itself is the canonical one:
# our own template scored `gemma4:12b` at 3/12 where the canonical scores 4/12
# and the published ladder scores 38-41/50, because ours omitted the rule that a
# document attached but no longer valid still counts as missing [ran]. Two prompt
# paths is one variable too many, so there is now one.
_RETIRED_TEMPLATE = """OBJECTIVE
{instruction}

CURRENT OBSERVATION
clinic: {clinic}
published required documents: {published}
attachments on the referral: {attachments}
patient: {patient}
imaging: {imaging}

CONSTRAINTS
Administrative task. Do not diagnose and do not recommend treatment.

ANSWER FORMAT
Reply with one JSON object and nothing else:
{{"kind": "submit_missing_documents", "arguments": {{"missing": ["..."]}}}}"""


def prompt_hash(prompt: str = "canonical") -> str:
    """Hash what the other repository will actually render, so a change there
    shows up here as a changed run rather than as an unexplained number."""
    return hashlib.sha256(canonical_prompt("held_out-000").encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Case:
    case_id: str
    region: str          # the clinic — the unit of withdrawal
    prompt: str
    truth: frozenset[str]


def _bench_root(root: Path) -> Path:
    return root / "benchmarks" / "clinical_learning"


def canonical_prompt(case_id: str, root: Path = DEFAULT_ROOT,
                     data_root: Path | None = None) -> str:
    """The prompt `../verified-runtime` actually used to produce its ladder.

    The frozen template above scored `gemma4:12b` at 3/12 where that repository
    published 38–41/50 for the same model on the same split [ran]
    results/S0b-payload-20260907. Rather than tune a prompt of our own until the
    numbers look familiar — which is how an instrument starts looking for a
    result — the context compiler that produced the published number is imported
    and called directly. Our prompt stops being a variable.
    """
    import contextlib
    import os
    import sys
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    @contextlib.contextmanager
    def _in(d):
        # That repository resolves its benchmark root relative to the working
        # directory, so borrowing its prompt means standing where it stands.
        # `data_root` separates the two: its CODE renders the prompt, our
        # generated cases supply the data, which is what lets a training corpus
        # be rendered by exactly the compiler that renders the sealed one.
        prev = os.getcwd()
        os.chdir(d)
        try:
            yield
        finally:
            os.chdir(prev)

    with _in(data_root or root):
        from domains.clinical_learning import ClinicalLearningDomain
        from domains.clinical_learning import objective as make_objective

        domain = ClinicalLearningDomain()
        obj = make_objective(case_id)
        return domain.compile_context(obj, domain.observe(obj), [])


def load(split: str = "held_out", n: int | None = None,
         root: Path = DEFAULT_ROOT, prompt: str = "canonical") -> list[Case]:
    d = _bench_root(root) / split
    if not d.is_dir():
        raise FileNotFoundError(
            f"{d} not found. Set VERIFIED_RUNTIME to the checkout that owns the "
            "clinical_learning benchmark; this repository deliberately does not "
            "copy a sealed held-out set."
        )
    if prompt != "canonical":
        raise ValueError(
            "the frozen template was retired — one prompt, or the prompt is a "
            "variable in every comparison. See `canonical_prompt`.")
    cases: list[Case] = []
    for case_dir in sorted(p for p in d.iterdir() if p.is_dir()):
        v = case_dir / "visible"
        task = json.loads((v / "task.json").read_text())
        ref = json.loads((v / "referral.json").read_text())
        patient = json.loads((v / "patient.json").read_text())
        imaging = json.loads((v / "imaging.json").read_text())
        truth = json.loads((case_dir / "truth.json").read_text())
        cases.append(Case(
            case_id=task["case_id"],
            region=task["clinic"],
            prompt=canonical_prompt(task["case_id"], DEFAULT_ROOT, root),
            truth=frozenset(truth["missing_documents"]),
        ))
    return cases[:n] if n else cases


# -- the verifier ---------------------------------------------------------------
# EXACT, and it belongs to the benchmark rather than to any model's opinion of
# itself. An unparseable answer is a failure: a system that cannot be read cannot
# be acted on.

def parse_answer(text: str) -> set[str] | None:
    start, depth, chunk = text.find("{"), 0, ""
    if start < 0:
        return None
    for ch in text[start:]:
        chunk += ch
        depth += (ch == "{") - (ch == "}")
        if depth == 0:
            break
    try:
        obj = json.loads(chunk)
    except json.JSONDecodeError:
        return None
    args = obj.get("arguments", obj)
    missing = args.get("missing")
    if not isinstance(missing, list):
        return None
    return {str(x) for x in missing}


def verify(text: str, truth: frozenset[str]) -> dict:
    got = parse_answer(text)
    if got is None:
        return {"passed": False, "parsed": False, "f1": 0.0,
                "extra": [], "missed": sorted(truth)}
    tp = len(got & truth)
    precision = tp / len(got) if got else (1.0 if not truth else 0.0)
    recall = tp / len(truth) if truth else 1.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {"passed": got == set(truth), "parsed": True, "f1": round(f1, 3),
            "extra": sorted(got - truth), "missed": sorted(truth - got)}


# -- where the answer stops being format and starts being an answer --------------
# The first S0 run measured α = 1.00 between three models that all produced the
# same WRONG answer, and α = 0.00 between two identical answers because one was
# wrapped in a markdown fence [ran] results/S0-instrument-20260907. Both numbers
# were about formatting. A metric that can move while the capability does not is
# deleted, not loosened — so acceptance is measured over the payload: the part of
# the stream the answer format does not determine.

PAYLOAD_MARKER = '"missing"'


def content_offset(answer: str) -> int | None:
    """Index of the first character of the payload, or None if the format is absent.

    None is a finding, not a fallback: a model that did not produce the declared
    shape has nothing comparable to a payload, and scoring it against one would
    invent an agreement that does not exist.
    """
    i = answer.find(PAYLOAD_MARKER)
    if i < 0:
        return None
    j = answer.find("[", i + len(PAYLOAD_MARKER))
    return j + 1 if j >= 0 else None


def payload(answer: str) -> str | None:
    """The list contents themselves — from after `[` to its closing `]`.

    Bounded at both ends on purpose. Left open, a trailing markdown fence would
    reappear as a disagreement at the tail, which is the same formatting artefact
    the payload exists to remove.
    """
    o = content_offset(answer)
    if o is None:
        return None
    end = answer.find("]", o)
    return answer[o:end] if end >= 0 else answer[o:]
