# P21 — a suite where a tool call cannot be remembered

**What P15 proved about itself.** A learned protocol beat a hand-written rule
94.8% to 91.7% where the call is not a copy — and a control with **no tool layer at
all** beat both at **27/30 while asking nothing** **[ran]**. The domain corpus shows
the property table, seven fluids times two properties is fourteen numbers, and 600
examples is far more than enough to memorise them. **A suite whose tool calls can
be recalled cannot price a tool layer**, whoever writes the calls.

**The fix is one line of the material's design.** Each problem carries **its own
handbook**, with the properties drawn per case and printed nowhere the model has
seen before:

    Handbook entry — fluid XJ-7: density 1043.9 kg/m^3, viscosity 2.71e-3 Pa s.

    A gate 47 cm wide and 179 cm tall is submerged in XJ-7, its top edge 1.78 m
    below the surface. Compute the resultant force.

The fluid has a made-up name and values that exist only in this problem. An expert
can still learn **which** property a step needs — that is the physics, and it is
what an expert is for — but it cannot learn **what the value is**, because the
value did not exist during training. Memory is removed by construction rather than
by hoping the table is large.

**The tool changes with it**: `lookup` reads the handbook supplied with the case
rather than a fixed table, and refuses a fluid the handbook does not name.

## The arms, and the killing one is bought first

`CLAUDE.md` says to buy the arm that can kill the experiment first, and P15 is what
ignoring that costs: two arms paid for before learning the material could not
support them.

| # | arm | why it is first |
|---|---|---|
| 1 | **no tool layer at all** | **if this still scores well, the material is still memorisable and the other two are not bought** |
| 2 | hand-written rule writes the calls | the competitor |
| 3 | kernel adapter writes the calls | the claim |

## Falsification, written before the run

**If arm 1 scores anywhere near P15's 27/30, the redesign failed** and the problem
is deeper than a fixed table — the expert would be reconstructing values some other
way, and this whole line of measurement needs rethinking rather than another arm.

**If arm 1 collapses**, the material finally makes tools necessary, and arms 2 and
3 measure what P15 could not: whether a learned protocol is worth its weights when
the answer genuinely is not in the weights.

**Redesign count: 0.** This is a new experiment on new material, not P15 retuned —
P15's numbers stand as published.

---

**Built and verified before any GPU was bought (2026-09-11) [ran].**

| check | result |
|---|---|
| the oracle's chains still reach their answers | **400/400** |
| statements containing a value from their own handbook | **0/400** |
| the hand-written bar, repaired for the new phrasings | **94.0%** |

**Two faults of my own, caught before the run rather than by it.** The first draft
**printed the handbook in the statement**, which repeats P15's fault with a new
face: a density in the prompt is copied, and the call is decoration again. And the
rule had fluid names hard-coded, so it could not query at all on invented codes —
leaving it that way would have handed the kernel a win by default. Both fixed; the
bar came out *higher* than on the old material, 94.0% against 92.9%.

**The kernel's own corpus uses invented fluids too**, or it would learn the fixed
table and stop querying — the behaviour this material exists to remove.

**The gate is in the runner**: if the no-tool arm reaches 0.35, the material is
still answerable from memory and arms 2 and 3 are not bought.

---

## Addendum — why each case failed, and what is left to win (2026-09-12) [ran]

`training/harness/failure_mode.py` classifies a failed case by asking the oracle,
not by catching an exception. A malformed call the tool happens to accept is not a
protocol success, and a well-formed `lookup` of the wrong fluid is not a physics
failure — so the verdict is **did this arm obtain the values the oracle obtained**:

    rejected > 0        malformed    the tool refused the call
    accepted < wanted   missing      it did not ask where the oracle asked
    matched  < wanted   wrong args   it asked, and got a different value
    otherwise           physics      it held every value and still answered wrong

It is computed from what the runner already stores, so it applies to the two arms
that reported before it existed. **No GPU was bought for this.**

| arm | passes | fails | protocol | physics |
|---|--:|--:|--:|--:|
| no tool layer at all | 6/30 | 24 | **24** (all *missing*) | 0 |
| hand-written rule | 5/30 | 25 | 3 (*wrong args*) | **22** |

The no-tool arm failing 24 of 24 by never asking is the classifier's own sanity
check: an arm with no tool layer must fail that way, and it does.

### The finding, and it is about headroom

**On this material the tool layer is no longer the bottleneck — the physics is.**
Of the rule's 25 failures, 22 are cases where it obtained every value the oracle
obtained and the expert still answered wrong. Per family: hydrostatic 6, Manning 7,
head loss 4, venturi 5 — the physics fails everywhere, not in one corner.

That bounds what the third arm can possibly show:

- **On the final answer, a perfect tool layer takes the rule from 5/30 to 8/30.**
  Three cases. A treatment cannot move more than that, whatever it is.
- **On the pre-registered axis — the oracle's tool steps — the rule reproduces
  93 of 96, or 0.969**, above its own published bar of 0.929. **Three tool values
  are available to win.**

This is CLAUDE.md §3's headroom rule arriving before the arm rather than after it.
The instrument has almost no room left in the direction the treatment would move.

### What is bought anyway, and what would not count

The kernel arm **is** run, at the same `--n-eval 30`, because the outcome it can
still resolve is the one that matters: P13 measured a learned protocol at 9/30
against a rule's 23/30, and a defeat of that size is visible at any n. **A narrow
win is not.**

Pre-registered before the run: **a kernel result within 3 tool values of the rule
is a tie, not a win**, and will be reported as one. Separating them would need a
larger evaluation, and that is a purchase to argue for on its own once there is a
reason to.
