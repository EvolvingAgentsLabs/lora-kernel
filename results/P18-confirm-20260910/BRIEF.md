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
