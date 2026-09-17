"""The desk's `commitment` corpus, rendered the way the drafter will be served.

WHY THIS REGION, AND WHY THE CHAIN IS THE TARGET'S. P55 A measured the ordering test
unbuyable on triage: the best expert sits at 0.989 and the untrained 32B at 0.746, so
$Q(T) \\ge \\max Q(E)$ fails and acceptance against that target would reward agreeing
with its errors **[ran]** `results/P55-graded-ranking-20260916/`. P51 measured the
same 32B at **1.000 on every depth** of the desk's `commitment` region, solving all 60
cases with exactly one call — `message` — and reading the date off its body
**[ran]** `results/P51-desk-profile-20260916/`. So this corpus teaches that chain and
no other: `REPORT.md` §6 says a drafter's corpus should be written by the target, and
here the target's chain is known to the call.

WHAT IT TEACHES IN ONE ASSISTANT TURN, as `generate_email_full` does:

    <message>id=msg-007</message>= {"from": …, "body": "I will have it to you by June 12.", …}
    June 12

That is the shape `accept_rank.py` serves in corpus mode — stop at `</message>`,
inject the real result, continue — and the shape the target scores.

THE RISK, NAMED BEFORE A GRADE IS TRAINED. The task is one call and a copy. P51's base
gradient (1.000 → 0.000 over depth) was an *untrained* model losing its way between
`thread_history` and `inbox`; a trained expert may saturate every depth, and then the
grades are not grades and M1 fails on the ceiling. `graded.py` widens the grades to
25 / 75 / 598 for this reason, and the brief pre-registers that outcome.

THE EVALUATION'S PROMPTS ARE EXCLUDED BY CONTENT. The suite is `desk.generate(n, 424242)`;
a corpus drawn with another seed can still reproduce a listing by chance, so every
evaluation prompt is removed here rather than assumed away **[ran]** 2026-09-15 for
the triage corpus, 2 of 150 recurred.

    python3 -m training.harness.generate_desk
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random

from training.email.desk import build, correct, generate, listing, _desk
from training.email.desk_tools import SCHEMA, answer
from training.harness.desk_sim import SYSTEM
from training.harness.tool_calls import tools_to_instruction

EVAL_SEED = 424242
EVAL_N = 960           # the first 240 are P51's cases exactly; the rest extend the grid
REGION = "commitment"
DEPTHS = (1, 2, 3, 4)
OUT = pathlib.Path("training/harness/data_desk/train.jsonl")

# THE SAME BLOCK THE RUNNER RENDERS. `tools_to_instruction(SCHEMA, arity=True)` is what
# the proxy puts in front of an adapter and what `tests/test_prune.py` proved byte-equal
# to the triage corpus; the desk corpus uses the identical function on the desk surface.
INSTRUCTION = tools_to_instruction(SCHEMA, arity=True, enums=False)


def chain_for(case: dict) -> list[tuple[str, str]]:
    """The target's chain: one `message` call, then the date **[ran]** P51, 60 of 60."""
    return [("message", f"id={case['msg']['id']}")]


def render(case: dict) -> dict:
    lines = []
    for tool, body in chain_for(case):
        lines.append(f"<{tool}>{body}</{tool}>= {answer(case['desk'], tool, body)}")
    lines.append(case["answer"])
    assert correct(case, lines[-1]), "the oracle answer does not verify"
    return {"case_id": case["case_id"], "region": case["region"], "depth": case["depth"],
            "answer": case["answer"], "calls": len(lines) - 1,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"{case['prompt']}\n\n{INSTRUCTION}"},
                         {"role": "assistant", "content": "\n".join(lines)}]}


def eval_prompts() -> set[str]:
    return {c["prompt"] for c in generate(EVAL_N, EVAL_SEED)["cases"]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=515151)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    assert args.seed != EVAL_SEED, "the corpus would draw the evaluation's desks"

    held_out = eval_prompts()
    rng = random.Random(args.seed)
    rows, skipped, i = [], 0, 0
    desk = _desk(rng, 24, "me@ownmail.com")
    while len(rows) < args.n:
        depth = DEPTHS[i % len(DEPTHS)]
        i += 1
        if i % 40 == 0:
            desk = _desk(rng, 24, "me@ownmail.com")
        c = build(rng, REGION, depth, desk)
        if c is None:
            continue
        c |= {"case_id": f"dc-{len(rows):04d}", "desk": desk}
        c["prompt"] = listing(c)
        if c["prompt"] in held_out:
            skipped += 1
            continue
        rows.append(render(c))

    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    by_depth = {d: sum(r["depth"] == d for r in rows) for d in DEPTHS}
    print(json.dumps({"written": len(rows), "path": str(p), "skipped_eval_prompts": skipped,
                      "by_depth": by_depth, "eval_prompts_excluded": len(held_out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
