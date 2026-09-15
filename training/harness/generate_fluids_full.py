"""The second pool member: one adapter for fluid mechanics, tools and physics together.

WHY THIS EXISTS. P36 measured a self-contained QLoRA clearing its gate on email
triage — 84/113 against a bar of 0.655, exact p = 0.028 **[ran]**. **One member is
not a pool.** The thesis says the whole agentic system is a pool of QLoRAs over one
resident base, and that only becomes a word this project has earned when a **second
expert, on a genuinely different subdomain, clears its own gate on the same base and
is selected by the `model` field of a request.**

Fluid mechanics was chosen over a calendar suite precisely because the distance
between the domains is what the thesis claims does not matter. It also needs no new
scaffolding: the suite, its per-case handbooks and its mechanical oracle already
exist and were built for a different question.

WHAT IT LEARNS. The oracle's own chain, rendered with every call answered — the
protocol and the physics in one target, exactly as `email-full` learned the tools
and the judgement together.

WHAT MAKES IT NOT A MEMORY TEST. Each case draws **its own handbook**: the fluid is
invented and its density and viscosity are drawn per case, so the fourteen numbers
that let P15's expert score 27/30 while asking nothing do not exist here **[ran]**.
The training seed is disjoint from the evaluation's 616161, and any prompt that
would appear in the evaluation is dropped **by content**, because a different draw
can reproduce one by chance — measured at 2 of 150 on the email suite, and removed
there the same way.

    python3 -m training.harness.generate_fluids_full --out training/physics/data_ff/train.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
from collections import Counter

from training.harness.generate_multitool import render
from training.physics.headroom import correct
from training.physics import multitool as mod
from training.protocol import SYSTEM

# `multitool_run` scores this seed. A corpus holding it would be scored on problems
# it had already been shown.
EVAL_SEED = 616161
EVAL_N = 200          # generous: the run may be widened without reopening this hole
SCORER_RTOL = 0.02    # `multitool_run --rtol`, and the only tolerance that matters


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=727272)
    ap.add_argument("--out", default="training/physics/data_ff/train.jsonl")
    args = ap.parse_args()

    assert args.seed != EVAL_SEED, "the corpus would be drawn from the evaluation seed"
    held_out = {c["prompt"] for c in mod.generate(EVAL_N, EVAL_SEED, mod.FAMILIES)}

    rows, skipped = [], 0
    for case in mod.generate(args.n, args.seed, mod.FAMILIES):
        if case["prompt"] in held_out:
            skipped += 1
            continue
        book = {tuple(k): v for k, v in case["handbook"]}
        body, last = render(case["chain"], book)
        # THE RENDERED CHAIN HAS TO END ON AN ANSWER THE SCORER ACCEPTS, and the
        # tolerance is **the scorer's own** rather than an epsilon chosen here.
        # `render` prints each intermediate at 6 significant figures and feeds it
        # forward, so the chain drifts from the suite's full-precision answer —
        # measured at 2.8e-6 relative on the first case, four orders of magnitude
        # inside `multitool_run`'s rtol of 0.02 [ran] 2026-09-15. A tighter
        # assertion here would refuse a corpus the scorer is perfectly happy with;
        # a looser one would let a real drift through. Tying it to SCORER_RTOL is
        # the only version that tests the thing that matters.
        assert correct(last, case["answer"], SCORER_RTOL), (
            f"{case['case_id']}: rendered {last}, suite expects {case['answer']} — "
            f"outside the scorer's own rtol of {SCORER_RTOL}")
        rows.append({"case_id": case["case_id"], "family": case["family"],
                     "calls": len(case["chain"]),
                     "tools": case["tools_needed"],
                     "messages": [{"role": "system", "content": SYSTEM},
                                  {"role": "user", "content": case["prompt"]},
                                  {"role": "assistant", "content": body}]})

    # EVERY FAMILY, OR THE EXPERT IS AN EXPERT IN SOME OF THEM. The suite scores all
    # four and a corpus missing one would fail those cases for a reason that has
    # nothing to do with the architecture.
    seen = Counter(r["family"] for r in rows)
    missing = set(mod.FAMILIES) - set(seen)
    assert not missing, f"the corpus never shows {sorted(missing)}"

    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(json.dumps({
        "written": len(rows), "path": str(p),
        "by_family": dict(seen),
        "calls_per_example": round(sum(r["calls"] for r in rows) / len(rows), 2),
        "prompts_skipped_because_the_run_will_be_scored_on_them": skipped,
        "drew_the_evaluation_seed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
