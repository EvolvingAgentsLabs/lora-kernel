# P22 — a boundary guard made of dimensional algebra

**The problem, measured.** A specialist scores **30/30 on its formulas inside its
region and 1/20 outside**, with nothing in its prose marking the difference
**[ran]** `results/P14-held-out-20260910/`. The cheap behavioural signal was
falsified: outside the region the tool layer refuses calls at 0.18 against 0.15
inside, and the guard scored 0.62 where chance was 0.60 **[ran]**
`results/P18-confirm-20260910/`.

**The hypothesis.** Outside its region the specialist does not fail quietly — it
**invents relations**. An invented relation is unlikely to be dimensionally
consistent, and dimensional consistency is checkable by a program that consults
nothing:

    6. Drag force F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)
       kg/m^3 · (m/s)^2 / [dimensionless]  =  kg/(m·s^2)  =  a PRESSURE
       the problem asked for a FORCE

The real drag law, `0.5 rho v^2 C_d A`, comes out in newtons. The invented one does
not. **The chain declares its own error in a currency the model never thinks
about.**

## Why this one and not the other candidates

Three routes were on the table. This is the only one that is pure code with a
runtime cost near zero.

| route | why not now |
|---|---|
| two specialists, disagreement as the signal | needs a second trained adapter, doubles the cost of every guarded request, and only sees an edge where some *other* expert happens to be competent |
| sample the expensive model after withdrawal | works, and costs money forever on the guarded path — the cost withdrawal exists to remove |
| **dimensional consistency** | **a few hundred lines, no model consulted, no threshold to fit** |

## It satisfies the six constraints, and that is why it was chosen

1. **Consults no expensive model.** It reads the chain and the units in the problem.
2. **Ignores the specialist's self-report.** It never asks the model anything.
3. **Needs no correct answer.** Units are checkable without knowing the number.
4. **It must still be shown to separate "outside" from "inside and difficult"** —
   that is the measurement, not an assumption.
5. **No threshold to fix.** The verdict is binary: the units close or they do not.
6. **Cheap enough for every request.** It is arithmetic over exponents.

## The rule, fixed before it is scored

A chain is flagged **out of region** when the dimension its final step produces
does not match the unit the problem asked for. Nothing else. No tuning, no
per-family exceptions, no second signal folded in if the first disappoints.

Dimensions are assigned only where they are **known rather than guessed**: from the
units printed in the statement, from the handbook the tool holds, from the SI target
of each conversion, and from `g = 9.80665 m/s^2`. A literal that matches nothing
known is treated as dimensionless, which is the honest reading of `2`, `pi` and
`1/3` — and a source of misses that will be reported rather than patched around.

## Falsification, written before the run

**If it does not separate in-region from out-of-region material well above the 0.60
chance line, dimensional consistency is not the signal either**, and the third
cheap idea in a row has failed — which would be worth knowing, because it would say
the edge is not visible in the artefact at all and only a second model or a paid
audit can find it.

**And a second number decides whether it is usable at all**: how often it fires on
in-region work. A guard that flags correct chains costs the deployment throughput
and will be switched off, whatever its headline accuracy. Both are reported.

## What it is measured on

Transcripts already on disk, correctness already known: **P13's two arms in region
(60 chains) and P14's two arms outside it (40 chains)**. No GPU, no new training,
no new material. If it works, the confirmation on families it was not developed
against is the next run and is cheap.

**Redesign count: 0.**
