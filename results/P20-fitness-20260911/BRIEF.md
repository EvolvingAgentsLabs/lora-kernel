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
