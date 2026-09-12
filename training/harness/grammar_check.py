"""Does the mask forbid anything the oracle writes? It must not.

A grammar that blocks a legal call is worse than no grammar: it converts the
adapter's correct intention into an impossible one, and the run that follows
measures the mask rather than the protocol. So before any of it reaches a GPU,
every call in both corpora and in the evaluation is replayed through the mask one
character at a time, and each character must have been permitted.

    python3 -m training.harness.grammar_check
"""

from __future__ import annotations

import json
import pathlib
import re

from training.harness.grammar import CallGrammar
from training.physics.multitool import FAMILIES, generate
from training.physics.tools import CALL

CORPORA = ["training/harness/data_mt/train.jsonl",
           "training/physics/data_mt/train.jsonl"]


def calls_in(text: str):
    for m in CALL.finditer(text):
        yield m.group(0)


def replay(call: str, g: CallGrammar) -> str | None:
    """The first character the mask would have forbidden, or None."""
    for i in range(1, len(call)):
        allowed = g.allowed(call[:i])
        if allowed is not None and call[i] not in allowed:
            return f"{call!r} blocked at {i}: {call[i]!r} not in {sorted(allowed)}"
    return None


def main() -> int:
    g = CallGrammar()
    seen = blocked = 0
    problems = []
    for path in CORPORA:
        p = pathlib.Path(path)
        if not p.exists():
            print(f"[missing] {path}")
            continue
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            for m in json.loads(line)["messages"]:
                for call in calls_in(m["content"]):
                    seen += 1
                    bad = replay(call, g)
                    if bad:
                        blocked += 1
                        if len(problems) < 5:
                            problems.append(f"{path}: {bad}")

    # And the evaluation's own oracle chains, which no corpus contains.
    for row in generate(60, 616161, FAMILIES):
        for _, tool, body in row["chain"]:
            call = f"<{tool}>{body}</{tool}>"
            seen += 1
            bad = replay(call, g)
            if bad:
                blocked += 1
                if len(problems) < 5:
                    problems.append(f"eval: {bad}")

    print(f"calls replayed through the mask: {seen}")
    print(f"calls the mask would have blocked: {blocked}")
    for p in problems:
        print(f"  {p}")
    if blocked:
        print("\nA mask that blocks a legal call measures itself. Fix it before "
              "buying a GPU.")
        return 1
    print("\nThe mask forbids nothing the oracle writes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
