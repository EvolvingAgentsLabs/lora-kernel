"""The escalation rule, and the correction to which one it should be.

WHAT THIS IS FOR. A withdrawn frontier leaves a small expert answering alone, and
P19 falsified every *behavioural* signal that it had left its region — hedging,
length and tool use all read at chance on unseen families. P22 found a *structural*
one: dimensional algebra flags 0.80 of out-of-region work on families sealed before
the checker existed **[ran]** `results/P22-dimensions-20260912/`.

THE TWO CHECKS. The dimensional one asks whether the final step produces the unit
the question asked for. The mechanical one re-evaluates every step exactly and
carries corrected values forward, so it fires when the chain does not compute what
it claims to compute. Neither runs a model; together they are about 250 lines.

## The correction

P22's addendum recommended escalating only when **both** checks fail, on the
grounds that this drops the dimensional false alarm from 0.22 to 0.00. That was
measured against the wrong alternative. The conjunction is a **subset** of the
mechanical check, and the mechanical check fires on **0 of 33** correct chains — so
on the question "is this answer wrong", the conjunction is strictly dominated by
its own half: 14 wrong answers stopped against 31, at the same price of zero
**[ran]**. Not a sampling accident; a set inclusion.

What rescues the conjunction is that this was never the question. Pooling in-region
and out-of-region chains and counting wrong answers asks the guard to detect *every
error*, including the expert being wrong inside a region it has not left. Split the
two, and the rules stop being comparable on one axis:

                  IN REGION (60)            OUT OF REGION (40)
                  escalates  good lost      escalates
    mechanical      0.18         0            0.50
    dimensional     0.32         7            0.78
    either          0.50         7            0.93
    both            0.00         0            0.35

**The conjunction never fires in region at all** — 0 of 60 — and still fires on a
third of the work outside it. That is a region tripwire that costs nothing while
the expert is working normally, which is the only version an operator switches on
and leaves on.

**`either` is the better rule if escalation means asking a bigger model**, because
a false alarm then costs tokens rather than quality: delivered accuracy goes 0.53
to 0.83 in region and 0.03 to 0.33 outside. Its price is that half the in-region
work leaves, which is most of what withdrawal was for.

So there is no single winner and this module does not crown one. `SHOULD_ESCALATE`
is the tripwire, because that is the job P19 left open; `is_probably_wrong` is the
other rule, named for what it actually detects.

ABSTENTION IS NOT ACQUITTAL — but here it is treated as one. A chain the checker
cannot type produces no dimensional failure and is not escalated, which is the
conservative direction for a guard whose value is that it never fires in region.
"""

from __future__ import annotations

from training.physics.dimensions import check
from training.physics.headroom import parse_answer
from training.physics.repair import repair

MECHANICAL_RTOL = 1e-3


def mechanical_fails(chain: str) -> bool:
    """Does the chain compute what it says it computes?

    `repair` walks the steps, evaluates each one exactly and carries the corrected
    value forward, so a chain whose arithmetic drifts ends somewhere other than the
    answer it printed. Disagreement is the failure; an unparseable chain is not
    judged here and is left to the dimensional side.
    """
    claimed = parse_answer(chain)
    value, _, _ = repair(chain)
    if claimed is None or value is None:
        return False
    scale = max(abs(claimed), abs(value), 1e-12)
    return abs(claimed - value) > MECHANICAL_RTOL * scale


def dimensional_fails(chain: str, unit: str, statement: str = "") -> bool:
    return check(chain, unit, statement).consistent is False


def has_left_its_region(chain: str, unit: str, statement: str = "") -> bool:
    """The tripwire: free in region (0 of 60), fires on 0.35 of work outside it."""
    return dimensional_fails(chain, unit, statement) and mechanical_fails(chain)


def is_probably_wrong(chain: str, unit: str, statement: str = "") -> bool:
    """The quality gate: stops 60 of 67 wrong answers, sends away 7 of 33 good."""
    return dimensional_fails(chain, unit, statement) or mechanical_fails(chain)


#: What the runtime calls. The tripwire, because a guard that fires on half the
#: in-region work is a guard that gets switched off.
should_escalate = has_left_its_region
