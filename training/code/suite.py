"""Complete the tail of a known algorithm, in a known language. The predicate.

WHY THIS SHAPE. Everything this architecture does rests on a small model's
continuation aligning with a larger one's, and C9 measured what breaks that:
identical answers scored **0.00** across formats while different answers scored 0.44
within one **[ran]**. **Layout dominated.** A code prefix has already fixed the
layout — the indentation, the names, the brace style are all in the prompt — so what
is left to predict is the algorithm rather than a convention.

THE DIFFICULTY IS NOT INVENTED. `docs/REPORT.md`'s deepest finding was that *a
generated suite cannot contain a difficulty its author did not think of*. Here the
difficulty is **where the implementation is cut**, which comes from the algorithm's
own length. Nobody chose it.

AND THE VERIFIER IS EXECUTION — the strongest this project has had. Not a definition
(triage), not a floor (drafting), not a judge. The completion is concatenated onto the
prefix, run, and its stdout compared to the reference's, **character for character**.
All fifteen references agree across all three languages, which is what makes that
comparison exact rather than a tolerance; `base32` reproduces the published RFC 4648
vectors, so at least one of them is checked against something outside this repository.

REGION IS THE LANGUAGE, AND IT IS VISIBLE. `region_not_in_the_prompt` will fail and is
waived by name: ranking was chosen over routing, and nobody would build a router to
detect the language of code they are already holding. What the experts differ in is
the **tail they write**, which is the thing acceptance has to be able to rank.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

from training.code.reference import ALGORITHMS, LANGUAGES, REFERENCE, SPEC

#: Fraction of the body removed at each depth. A fraction rather than a line count,
#: because the programs differ in length and a count would make depth mean something
#: different in each language — which is the confound every previous suite had.
DEPTHS = {1: 0.20, 2: 0.40, 3: 0.60, 4: 0.80}

EXT = {"python": "py", "javascript": "js", "c": "c"}
TIMEOUT = 20


class RunError(RuntimeError):
    pass


def run_source(source: str, language: str, timeout: int = TIMEOUT) -> str:
    """Execute a program and return its stdout, stripped.

    SAFETY IS A PROPERTY OF WHERE THIS RUNS, NOT OF THIS FUNCTION. Model-written code
    is executed, which is only acceptable on a disposable rented VM. There is a
    timeout and no shell; there is no sandbox, and pretending otherwise in a docstring
    would be worse than saying so.
    """
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / f"prog.{EXT[language]}"
        src.write_text(source)
        if language == "python":
            cmd = [sys.executable, str(src)]
        elif language == "javascript":
            cmd = ["node", str(src)]
        else:
            binary = Path(d) / "prog"
            built = subprocess.run(["gcc", "-O1", "-o", str(binary), str(src), "-lm"],
                                   capture_output=True, text=True, timeout=timeout)
            if built.returncode:
                raise RunError(f"compile: {built.stderr.strip()[:200]}")
            cmd = [str(binary)]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RunError(f"timed out after {timeout}s") from None
        if r.returncode:
            raise RunError(f"exit {r.returncode}: {r.stderr.strip()[:200]}")
        return r.stdout.strip()


_EXPECTED: dict[tuple[str, str], str] = {}


def expected(algorithm: str, language: str) -> str:
    """What the reference prints — computed by running it, never hardcoded.

    A cached constant can drift from the source beside it; running cannot. This is the
    same rule that made `generate_fluids_full` *call* `render_tools` instead of
    copying what it printed, after a copy drifted and voided a whole run **[ran]** P38.
    """
    key = (algorithm, language)
    if key not in _EXPECTED:
        _EXPECTED[key] = run_source(REFERENCE[key][0], language)
    return _EXPECTED[key]


def _body_lines(source: str) -> tuple[list[str], int]:
    """The lines that may be cut, and where they start.

    The header comment and the first constant stay: they say what the program is, and
    cutting them would change the *question* rather than the difficulty.
    """
    lines = source.splitlines()
    start = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not s.startswith(("#", "//", "/*", "*", "import ", "#include",
                                   "const ALPHABET", "from ")):
            start = i
            break
    return lines, max(start, 1)


def truncate(source: str, depth: int) -> tuple[str, int]:
    """Keep the head, remove `DEPTHS[depth]` of the body from the end."""
    lines, start = _body_lines(source)
    body = len(lines) - start
    cut = max(1, round(body * DEPTHS[depth]))
    keep = len(lines) - cut
    return "\n".join(lines[:keep]) + "\n", cut


INSTRUCTION = (
    "Complete this program. Write only the remaining code, continuing exactly where "
    "the text stops — no explanation, no fences, no repetition of what is already "
    "there. The finished program must compile and run and print the correct result."
)


def prompt_for(algorithm: str, language: str, prefix: str) -> str:
    return (f"Language: {language}\n"
            f"Task: implement {SPEC[algorithm]}.\n\n"
            f"{INSTRUCTION}\n\n"
            f"```{language}\n{prefix}```")


def generate(languages=LANGUAGES, algorithms=ALGORITHMS,
             depths=tuple(DEPTHS)) -> list[dict]:
    """The full algorithm x language x depth grid. No diagonal."""
    cases = []
    for algorithm in sorted(algorithms):
        for language in sorted(languages):
            source = REFERENCE[(algorithm, language)][0]
            for depth in sorted(depths):
                prefix, cut = truncate(source, depth)
                cases.append({
                    "case_id": f"{algorithm}-{language}-d{depth}",
                    "region": language, "algorithm": algorithm, "depth": depth,
                    "lines_removed": cut, "prefix": prefix,
                    "prompt": prompt_for(algorithm, language, prefix),
                    "reference_sha": hashlib.sha256(source.encode()).hexdigest()[:12],
                })
    return cases


def strip_fences(text: str) -> str:
    """Models wrap completions in fences however they are asked not to.

    Removing them is not loosening the check — the check is what the program PRINTS,
    and a fence is a formatting habit rather than a wrong answer. Refusing it would be
    measuring phrasing, which this repository's rule says to delete rather than loosen.
    """
    out, skipping = [], False
    for line in (text or "").splitlines():
        if line.strip().startswith("```"):
            skipping = not skipping and not out
            continue
        out.append(line)
    return "\n".join(out)


def verify(case: dict, completion: str) -> dict:
    """Concatenate, run, compare to what the reference prints."""
    whole = case["prefix"] + strip_fences(completion)
    want = expected(case["algorithm"], case["region"])
    try:
        got = run_source(whole, case["region"])
    except RunError as e:
        return {"correct": False, "why": str(e)[:200], "got": None, "want": want}
    return {"correct": got == want, "got": got[:200], "want": want,
            "why": "" if got == want else "output differs"}
