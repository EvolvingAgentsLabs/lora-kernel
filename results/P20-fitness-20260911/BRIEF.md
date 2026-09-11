# P20 — a fitness that does not select for failing quietly

**What P19 found.** A fitness built on a transcript-reading judge ordered the P15
pair backwards, and the mechanism is precise **[ran]**:

| among chains that are… | showing no error | showing an error |
|---|---|---|
| actually correct | judged correct 98% | 89% |
| actually wrong | judged correct **41%** | 7% |

The judge's weakness is one cell: it **accepts 41% of wrong work that looks
clean**. The hand-written rule cannot malform a call, so 0 of its 26 chains show an
error, it sits entirely in that cell, and its grade is inflated by false
acceptance.

**And the obvious correction is backwards.** Subtracting the tool layer's
rejections would penalise the kernel arm — 14 of 30 chains show an error — and push
the pair further the wrong way. Visible errors are a *signal*, not a fault: they
cost correct work almost nothing and let the judge reject wrong work.

**What is actually needed** is something that separates "clean because correct"
from "clean because it never tried". The procedural check is exactly that: it
re-evaluates a chain's own arithmetic and asks whether the answer follows from it,
and it does not care how the chain looks. P17 measured it at **0.94 recall on
correct work** and 0.52 on wrong — permissive, and blind in a different direction
from the model judge.

## The four combinations, fixed before any is scored

Two judges give four ways to combine them and there is no fifth, so all four are
listed here and all four are reported. Searching a space of combinations for the
one that orders the pairs correctly would be the same failure this run exists to
fix.

| # | `w₁` is | what it should do |
|---|---|---|
| 1 | the model judge alone | P19's baseline: 1 of 3 pairs |
| 2 | the procedural check alone | permissive; should over-accept everywhere |
| 3 | **both must accept** | should close the 41% cell: a clean chain whose arithmetic does not support its answer is refused |
| 4 | either may accept | should be worse than 1, and is included so the choice is not made by omission |

**No oracle appears in any of them.** The verdicts are already cached, the
procedural check needs no model, and the fitness a loop would actually use can see
neither the answer nor the true accuracy.

## Falsification, written before the run

**If no combination orders more pairs than the judge alone, the fitness function
cannot be repaired this way** — and the honest conclusion would be that a
tournament needs a grader with access to something neither of these judges has,
which is a much harder problem than the one this run is trying to solve.

**And three pairs remain three pairs.** One of them differs by a single problem in
twenty and should not count. Getting 2 of 3 instead of 1 of 3 is a mechanism
working, not a result about tournaments.

**Redesign count: 0.**

---

## Outcome (2026-09-11) [ran]

| candidate | true | model | procedural | **both** | either |
|---|---|---|---|---|---|
| P13 · control | 0.767 | 1.000 | 0.767 | **0.767** | 1.000 |
| P13 · sequential | 0.300 | 0.567 | 0.300 | **0.267** | 0.600 |
| P15 · kernel adapter | **0.333** | 0.300 | 0.267 | **0.267** | 0.300 |
| P15 · hand-written rule | 0.231 | **0.538** | 0.346 | **0.231** | 0.654 |

| fitness | pairs with a real gap ordered right |
|---|---|
| model judge alone | 1/2 |
| procedural alone | 1/2 |
| **both must accept** | **2/2** |
| either may accept | 1/2 |

**Requiring both judges to accept is the only combination that orders both pairs
the way the oracle does**, and the cell it closes is exactly the one P19 named:

| | wrong work that looks clean | correct work |
|---|---|---|
| model judge alone | accepts **41%** | accepts 96% |
| **both must accept** | accepts **2%** | accepts 90% |

**False acceptance falls from 41% to 2% and costs six points of correct work.**
That is the mechanism closing, not a combination found by search: the model judge
reads a transcript and cannot tell clean-because-correct from
clean-because-it-never-tried; the procedural check re-executes the chain and does
not care how it looks. Neither is sufficient and the conjunction is.

**It is also nearly calibrated, which nobody asked for.** P13's control scores
0.767 against a true 0.767, and P15's rule scores 0.231 against a true 0.231.

## Limits, and they are severe

**Two pairs.** A fitness that orders two pairs correctly is a mechanism with
evidence, not a tournament. The third pair was excluded before the run for a gap of
one problem in twenty.

**The candidates were not bred by a loop.** Nothing here shows that repeated
selection converges anywhere, or that a loop optimising this fitness would not find
a way to satisfy both judges while being wrong.

**And the procedural judge had to be repaired twice to get here**, both times
because it was undefined on an input class rather than wrong about one: it knew
only `<calc>` and found nothing in a multi-tool chain, then it compared the final
answer against the last *lookup* because a chain is mixed — tagged query steps and
untagged arithmetic. Both fixes are recorded in the code with what they cost.

**Redesign count: 0 for the experiment.** Four combinations listed before scoring,
four reported. The two changes were to an instrument that could not read the data.
