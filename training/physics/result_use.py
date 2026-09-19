"""Milestone 7, arm 0 — where a fluids chain breaks: the relation, or the reading?

WHY. "The expert that reasons fails" was read off a final score: 11 of 90 **[ran]** P41. Before
a knowledge base is built to repair that, the failure is measured where it happens. Every
recorded chain is replayed against the case's own handbook and two things are counted per call:
whether the value the tool returned is **used** by any later step, and whether a `<calc>` uses a
number that **came from nowhere** — not the statement, not a constant, not an earlier result.

WHAT IT FOUND (zero GPU, `results/M7-knowledge-base-20260919/arm0.json`): of 79 failures, **74**
contain a number from nowhere and **75** leave at least one tool result unused; 217 of 456
non-final results are ignored. The expert looks the density up — 882.3 — and multiplies by
1359.7. It does not mainly get the physics wrong: **it calls the tool and then writes a number
of its own.**

WHAT THAT DOES NOT SAY YET. That run served the expert through `tool_calls` / `role: "tool"`;
its corpus taught the result inline, `<calc>…</calc>= 4.2305`. The same path costs `email-full`
0.992 → 0.808 **[ran]** P55, and fluids was never re-served in corpus mode. So "a 3B does not
use what it reads" and "the harness did not show it the way it was taught" are both live, and
one re-serve separates them (docs/PLAN.md, milestone 7, arm 0b). Either answer decides how a
knowledge base has to deliver what it retrieves.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

TAG = re.compile(r"<(calc|lookup|convert)>(.*?)</\1>", re.S)
NUM = re.compile(r"(?<![\w.])\d+\.?\d*(?:[eE][-+]?\d+)?")
CONST = [9.80665, 9.81, 2, 0.5, 4, math.pi, 3.14159, 64, 0.25, 1, 3, 8, 5.74, 3.7, 0.9,
         1000, 10, 100, 60, 0]


def close(a: float, b: float, rtol: float = 2e-3) -> bool:
    return abs(a - b) <= rtol * max(abs(a), abs(b), 1e-12)


def read_chain(chain: str, statement: str, handbook, answer) -> dict:
    """One chain: results used, results ignored, steps with a number from nowhere."""
    calls = TAG.findall(chain or "")
    given = [float(x) for x in NUM.findall(statement)] + CONST
    results, used, ignored, invented, errors = [], 0, 0, 0, 0
    for i, (name, body) in enumerate(calls):
        if name == "calc":
            lits = [float(x) for x in NUM.findall(body)]
            invented += any(not any(close(x, a) for a in given + results) for x in lits)
        try:
            val = float(answer(name, body, handbook))
        except Exception:
            # COUNTED, NEVER SWALLOWED. The first version of this file passed the handbook
            # in its JSON shape, every `<lookup>` raised inside this `except`, and a chain
            # that used the looked-up density CORRECTLY was scored as holding "a number
            # from nowhere" — 74 of 79, published, and wrong [ran] 2026-09-19.
            errors += 1
            continue
        if i < len(calls) - 1:
            later = [float(x) for _, b in calls[i + 1:] for x in NUM.findall(b)]
            if any(close(val, x) for x in later):
                used += 1
            else:
                ignored += 1
        results.append(val)
    return {"calls": len(calls), "used": used, "ignored": ignored, "invented_steps": invented,
            "tool_errors": errors}


def main(records: str = "results/P41-routing-20260915/pool_results.json", arm: str = "fluids-full",
         n: int = 90, seed: int = 616161,
         out: str = "results/M7-knowledge-base-20260919/arm0.json") -> int:
    from training.physics import multitool, tools

    recs = json.loads(Path(records).read_text())["arms"][arm]["records"]
    recs = recs if isinstance(recs, list) else list(recs.values())
    cases = {c["case_id"]: c for c in multitool.generate(n, seed)}
    s, fam = Counter(), Counter()
    for r in recs:
        c = cases[r["id"]]
        assert r["statement"].startswith(c["prompt"][:80]), "the regenerated case is not the recorded one"
        if r["passed"]:
            s["passed"] += 1
            continue
        book = {tuple(k): v for k, v in c["handbook"]}      # JSON shape -> what `lookup` reads
        got = read_chain(r["chain"], c["prompt"].split("Solve the problem")[0], book, tools.answer)
        s["tool_errors_while_replaying"] += got["tool_errors"]
        s["failed"] += 1
        s["failed_with_a_result_never_used"] += got["ignored"] > 0
        s["failed_with_a_number_from_nowhere"] += got["invented_steps"] > 0
        s["results_used"] += got["used"]; s["results_ignored"] += got["ignored"]
        fam[r["family"]] += got["invented_steps"] > 0
    rec = {"source": records, "arm": arm, "n": len(recs), **s, "by_family_number_from_nowhere": dict(fam)}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rec, indent=1))
    print(f"[m7] failed {s['failed']} · a result never used {s['failed_with_a_result_never_used']} · "
          f"a number from nowhere {s['failed_with_a_number_from_nowhere']} · "
          f"results used {s['results_used']} ignored {s['results_ignored']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
