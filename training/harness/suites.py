"""What `accept_rank.py` needs to know about a suite, and nothing else.

WHY A RECORD. The runner was written against the triage inbox with its three tags,
its `IMPORTANT / NOT IMPORTANT` verdict and its human-message bar baked into the
module. P55 A then showed the ordering test unbuyable on that suite and P51 showed
where it is buyable — the desk's `commitment` region — so the suite became a
parameter. Everything a suite decides is listed here; everything else the runner does
(corpus-mode loop, forced scoring, gates, persistence) is the same for both, which is
what makes the two runs comparable.

THE EMAIL SUITE REPRODUCES THE RUNNER'S FIRST BEHAVIOUR BYTE FOR BYTE: same system
prompt, same listing, same block, same tags, same verdict rule, same human bar.
`tests/test_accept_rank.py` still passes unchanged against it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from training.harness.tool_calls import tools_to_instruction


def _positional(schema: list[dict]) -> dict[str, str]:
    """P28's arity convention on the way in: the one parameter of a one-parameter tool."""
    out = {}
    for t in schema:
        fn = t["function"]
        req = fn["parameters"].get("required") or sorted(fn["parameters"]["properties"])
        if len(req) == 1:
            out[fn["name"]] = req[0]
    return out


@dataclass
class Case:
    id: str
    user: str                      # the user turn WITHOUT the tool block
    ctx: dict                      # what the tools answer from (an inbox, a desk)
    truth: object                  # for the record
    verify: Callable[[str | None], bool]
    human: bool = True
    meta: dict = field(default_factory=dict)


@dataclass
class Suite:
    name: str
    system: str
    block: str                     # the tool block, byte for byte what the corpus taught
    tags: tuple[str, ...]
    answer: Callable[[dict, str, str], str]
    positional: dict[str, str]
    parse: Callable[[str], object]         # the final span's text -> an answer or None
    cases: Callable[[int, int], list[Case]]
    bar: Callable[[list[Case]], float]     # the floor a target must clear on its own
    eval_seed: int
    eval_n: int

    @property
    def close(self) -> tuple[str, ...]:
        return tuple(f"</{t}>" for t in self.tags)

    @property
    def tag(self) -> re.Pattern:
        return re.compile(rf"<({'|'.join(self.tags)})>([^<]*)</\1>")

    def user_text(self, case: Case) -> str:
        return f"{case.user}\n\n{self.block}"


# --- triage: the inbox, three tags, IMPORTANT / NOT IMPORTANT ------------------

def _email() -> Suite:
    from training.email.inbox import generate
    from training.email.tools import SCHEMA, answer
    from training.harness.agent_sim import SYSTEM
    from training.harness.generate_email_full import listing
    from training.harness.generate_email_protocol import INSTRUCTION

    def parse(text: str):
        t = text.upper()
        return False if "NOT IMPORTANT" in t else True if "IMPORTANT" in t else None

    def cases(n: int, seed: int) -> list[Case]:
        inbox = generate(n, seed)
        return [Case(id=m["id"], user=listing(m), ctx=inbox, truth=m["_truth"],
                     verify=(lambda said, t=m["_truth"]: said == t),
                     human=not m["_facts"]["automated"])
                for m in inbox["messages"]]

    def bar(cs: list[Case]) -> float:
        ht = [c.truth for c in cs if c.human]
        return max(sum(ht), len(ht) - sum(ht)) / len(ht) if ht else 0.0

    return Suite(name="email", system=SYSTEM, block=INSTRUCTION,
                 tags=("thread_history", "sender_stats", "message"), answer=answer,
                 positional=_positional(SCHEMA), parse=parse, cases=cases, bar=bar,
                 eval_seed=717171, eval_n=475)


# --- the desk: four tags, a free-text answer verified by substring ---------------

def _all_regions():
    from training.email.desk import REGIONS
    return REGIONS


def _desk(region: str = "commitment") -> Suite:
    from training.email.desk import correct, generate
    from training.email.desk_tools import SCHEMA, answer
    from training.harness.desk_sim import SYSTEM

    block = tools_to_instruction(SCHEMA, arity=True, enums=False)

    def cases(n: int, seed: int) -> list[Case]:
        # THE FIRST 240 OF `generate(960, 424242)` ARE P51'S CASES EXACTLY — the draw is
        # a deterministic prefix — so the target's 1.000 on `commitment` was measured on
        # a subset of what is scored here.
        return [Case(id=c["case_id"], user=c["prompt"], ctx=c["desk"], truth=c["answer"],
                     verify=(lambda said, cc=c: correct(cc, said)), human=True,
                     meta={"region": c["region"], "depth": c["depth"]})
                for c in generate(n, seed, regions=(region,) if region == "commitment_deep"
                                  else None or _all_regions())["cases"]
                if c["region"] == region]

    # A DATE HAS NO MAJORITY CLASS. The floor a target must clear on its own is 0 here
    # and the gate reduces to the paired test against the best expert — which is the
    # part of it that ever decided anything.
    return Suite(name=f"desk:{region}", system=SYSTEM, block=block,
                 tags=("inbox", "thread_history", "sender_stats", "message"), answer=answer,
                 positional=_positional(SCHEMA),
                 parse=lambda text: text.strip() or None,
                 # THE DEEP BAND IS ITS OWN GRID: generate(n, seed, regions=(deep,)) spreads
                 # n over four depths, so 240 cases is 60 per depth — the shallow band's
                 # size, and the power `bar.resolvable` priced at 0.92 for +0.10.
                 cases=cases, bar=lambda cs: 0.0, eval_seed=424242,
                 eval_n=240 if region == "commitment_deep" else 960)


def load(name: str) -> Suite:
    if name == "email":
        return _email()
    if name.startswith("desk"):
        return _desk(name.split(":", 1)[1] if ":" in name else "commitment")
    raise ValueError(f"no suite named {name!r}")
