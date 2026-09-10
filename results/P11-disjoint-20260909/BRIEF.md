# P11 (F3+F2) — the two weight-space fixes for delegation, and both fail

**The problem, measured in P9.** The composition delegates on **5 of 30** cases
where the kernel alone delegates on all 30 at 7.7 calls each, and it passes **3 of
those 5** against **1 of the other 25** **[ran]**. The mechanism is intact and
rarely fires: at every step the kernel's *"write a call"* and the domain's *"write
the number here"* compete, and the domain wins.

**Two interventions, both pure adapter-space, no runtime change.**

- **F3 — disjoint modules.** Kernel on `q,k,v,o`, domain on the MLP. The two
  deltas then share no matrix, so they cannot compete by summing.
- **F2 — asymmetric weights.** `add_weighted_adapter` at kernel 1.0, domain 0.5.

**The metric that decides is calls per case**, not accuracy: accuracy moved by
three cases in P9 and could move by three again for reasons unrelated to the
mechanism.

## Outcome (2026-09-09) [ran]

| arm | raw | repaired | calls/case |
|---|---|---|---|
| domain (MLP only) | 1/30 | **30/30** | 0.0 |
| kernel (attention only) | 0/30 | 0/30 | **6.0** |
| **F3 · kernel + domain, disjoint** | 0/30 | 5/30 | **0.2** |
| **F2 · kernel 1.0 + domain 0.5** | 0/30 | 0/30 | **3.5** |
| *(P9 · kernel + domain, shared matrices)* | *4/30* | *22/30* | *0.6* |

**F3 is falsified, and it is the informative half.** Disjoint parameters made
delegation **worse** — 0.2 against P9's 0.6 — and cost most of the physics, 5/30
repaired against 22/30. Two adapters with **no parameter in common** still fight.
So the competition is not a collision in weight space at all: both deltas shape the
same output distribution, and separating the matrices they live in changes nothing
about that. **This closes the whole "linear algebra" family of fixes.**

**F2 moves the metric and destroys the thing being composed.** Weighting the kernel
up restores delegation seventeen-fold, 0.2 → 3.5 — so delegation *is* controllable.
But the expert vanishes with it: repaired 0/30 against the domain's own 30/30. The
two halves do not coexist under a weighting; one wins outright and the other is
gone.

**What survives, and what it points at.** Each half is separately healthy on its
own projections — the kernel still calls 6.0 times per case trained on attention
alone, the domain's physics is still exact on the MLP alone. The failure is
*behavioural competition at the token*, which is why a knob on magnitude trades one
half for the other instead of combining them. Two directions remain, and they are
of different kinds: change what the expert was taught to produce so there is
nothing to compete with (**F1**), or make the losing behaviour impossible at decode
time rather than merely less likely (**a logit mask on digits outside `<calc>`**).
The second is the only intervention measured so far that a competing delta cannot
out-vote.

**Redesign count: 0.**
