# P46 — most of P44's room was the suite. The listing-only typed arm is cancelled

**[ran]** 2026-09-16. **No GPU, no training, nothing served.** P44's own 475 cases
re-read, the inbox regenerated from its seed (475, 717171) with **ids and truth
verified to match** before any join. Numbers: [`ceiling.txt`](ceiling.txt).

## The question P44 did not ask

P44 measured the confidence `email-full` attaches to its own answers, found an AURC
gap of **0.400** above the oracle floor, and read it — per its pre-registered brief —
as *the confidence does not order the errors, so the typed arm is bought* **[ran]**.

The brief asked whether the gap was **large**. It never asked **how much of it is
claimable**, and that turns out to be most of the answer.

## The ceiling

Group the cases by what a predictor can actually *see*. Inside a group every case
looks identical, so the best any model can output is the group's base rate — and the
AURC of that predictor is the floor of what is **achievable**, not of what was
achieved.

In this suite the listing carries exactly one bit: automated messages announce
themselves. For a human message the `Re:` is random, the preview is generic and
carries no ask, and the two decisive facts live behind the tools **by construction** —
`tests/test_email.py::test_the_listing_alone_cannot_beat_the_majority_class` has
asserted this since the suite was built.

| subset | n | groups | ceiling gap | rankable |
|---|---:|---:|---:|---|
| all | 475 | 2 | **0.098** | yes |
| human | 351 | **1** | **0.277** | **no** |

## Against what was measured

| subset · arm | measured gap | 95% CI | ceiling | room | share that is the suite |
|---|---:|---|---:|---:|---:|
| all · email-full | 0.128 | [0.105, 0.155] | 0.098 | **+0.030** | **77%** |
| all · base | 0.105 | [0.084, 0.127] | 0.098 | **+0.007** | **94%** |
| human · email-full | 0.400 | [0.346, 0.449] | 0.277 | +0.123 | **69%** |
| human · base | 0.338 | [0.288, 0.388] | 0.277 | +0.062 | **82%** |

**On the full inbox both arms are already at the ceiling.** There is nothing for a
better model to take: 0.030 and 0.007.

**On the human subset the ceiling predictor is a constant** — one group, `rankable:
false`. The 0.123 of "room" is not room to rank better; it is room to **stop being
worse than a constant**. A model cannot order cases that look identical to it.

## The consequence, stated plainly

> **A typed head answering from the listing alone cannot produce a routing signal,
> because a constant confidence routes nothing.**

That is the signal P41 went looking for and did not find: per-case escalation
delivered **less** than routing by region, 0.378 and 0.689 against 0.775, because the
available rules cannot see a coherent wrong answer **[ran]**. A typed listing-only
head would inherit the same blindness — and now we know that before paying for it
rather than after.

**The arm is cancelled.** Not because the idea is wrong, but because the
configuration P44 scoped has no room in it.

## Where the room actually is

With the tools, every fact the definition needs is recoverable — `thread_history`
gives *did I write in this thread*, `sender_stats` gives *is this a frequent
counterpart*. The truth becomes **decidable**, the ceiling collapses to the oracle
floor, and the whole of a measured gap is claimable.

So the re-aimed arm is a **typed final answer on top of the existing tool chain**,
not instead of it. `email-full` already reaches **0.741** with tools **[ran]** P43;
what nobody has measured is the confidence attached to *that* answer, because P44
deliberately measured the tool-free configuration as the like-for-like baseline for
a one-forward-pass head.

**That measurement needs serving but no training**, and it is the next headroom check
rather than the next treatment.

## What this does not say

- **Not that P44 was wrong.** Its numbers reproduce exactly. What it lacked was a
  ceiling for *ranking*; `CLAUDE.md` had the rule for accuracy and no way to state it
  for ordering. That rule now exists.
- **Not that typed adapters are a bad idea.** The single-token invariant holds, the
  contract is in `POOL`, and the post-tool configuration is untested and promising.
- **Not that the base beats the expert.** `all · base` has a smaller gap than
  `all · email-full`, but both sit at a ceiling — a difference under a ceiling is not
  a ranking of models.

## One instrument bug, caught by running it

`room()`'s first reading had the sign backwards: it called a model that came in
*below* the ceiling "worse than knowing nothing". Lower is better for an AURC gap. A
model cannot beat the best predictor of what it can see, so a negative room indicts
the **grouping** — something visible was left out of it — and not the model. Fixed,
and the test now says which.
