# P18 — the tripwire, with the threshold fixed and the families unseen

**What P16 found and why it does not stand.** The tool layer's rejection rate runs
**0.15 inside a region and 0.63 outside**, classifying 86% of cases with one cut
**[ran]**. Three things make that a hypothesis rather than a detector, and all
three were written into P16's own brief:

1. the six signals were chosen with the answers already visible;
2. the cut was fitted on the same fifty problems that scored it;
3. the two out-of-region families used are the only held-out families the suite
   had, so "outside the region" and "these two families" are the same set.

**What this run changes, and it changes exactly one thing.** Two families no
earlier run has touched — `weir_flow` and `jet_reaction` — and **P16's cut applied
unchanged**: `rejection_rate > 0.50` means outside. The number is written into
`training/harness/tripwire.py` as a constant so it cannot quietly be refitted.

**Falsification, written before the run.**

- **Near 0.86 with the cut fixed** and the guard is real: the rejection rate is a
  property of a region's edge, not of `drag_force` and `orifice_discharge`.
- **Well below it** and P16 measured two families rather than a boundary. That
  would close the only candidate guard this project has, and Problem 3 of
  `OPEN-PROBLEMS.md` would go back to having none.

**What it still will not settle.** A detector that fires is not a policy. Deciding
what the system *does* when it fires — decline, defer upward, ask the frontier — is
a separate question, and this run does not touch it.

**Redesign count: 0.**

---

## Outcome (2026-09-11) [ran]

With P16's cut applied unchanged at `rejection_rate > 0.50`, on `weir_flow` and
`jet_reaction` — families no run that fitted anything has seen:

| arm | in region | new families | guard accuracy |
|---|---|---|---|
| sequential · domain plans, kernel executes | 0.15 | **0.18** | **0.62** |
| control · domain alone, harness repairs | 0.15 | **0.14** | **0.58** |

**The guard is falsified.** Outside its region the tool layer refuses calls at very
nearly the rate it refuses them inside — 0.18 and 0.14 against 0.15. And 0.62 is
what chance looks like here: with 30 cases in and 20 out, answering "in region"
every time scores 0.60.

**So P16 measured `drag_force` and `orifice_discharge`, not a boundary.** Its 0.86
came from six signals chosen with the answers visible and a cut fitted on the same
fifty problems that scored it, exactly as its own brief warned. The warning was
right and the number was not.

**One nuance, because the two figures differ and both are real.** Pooled over the
arm, 23 of 66 calls were refused — 0.348. Averaged per case, the rate is 0.18. A
detector thresholds a *case*, so the per-case mean is the one that matters; the
pooled figure is higher because a few cases fail badly and most do not. Quoting
0.348 as "the rejection rate outside the region" would have been true and
misleading.

## What this costs

**Problem 3 of `OPEN-PROBLEMS.md` goes back to having no candidate.** The expert's
formulas still fall from 30/30 inside its region to 1/20 outside it, nothing in its
prose marks the difference, and now nothing in the tool layer's behaviour does
either. Per-region promotion — the mechanism that lets the frontier be withdrawn —
still has no guard.

**And the cheap direction is exhausted.** Reading the process instead of the model
was the idea, and the process does not know. What is left is more expensive: a
second expert whose disagreement flags the edge, or sampling the frontier after
withdrawal, which is the cost withdrawal exists to avoid.

**Redesign count: 0.** The cut was fixed in code before the run and not touched.
