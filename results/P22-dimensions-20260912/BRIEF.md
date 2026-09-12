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

---

## Outcome (2026-09-12) [ran]

**First, against material that cannot be wrong.** On 120 oracle chains, correct by
construction, the guard flags **2**. Every earlier version flagged more and each
number is kept below, because they are the record of an instrument learning to read
its own input.

**Then the measurement, on the 100 transcripts P13 and P14 banked:**

| group | n | flagged | rate |
|---|---|---|---|
| in region | 60 | 19 | 0.32 |
| **outside the region** | 40 | **31** | **0.78** |
| in region **and correct** | 32 | 7 | **0.22** |

| | |
|---|---|
| separation | **0.72** against a chance line of **0.60** |
| on the 80 chains it had an opinion about (coverage 0.80) | **0.75** |
| false alarm on correct in-region work | **0.22** |

**And then the confirmation, which is the part that matters.** `weir_flow` and
`jet_reaction`, produced by P18 **before this guard existed** and never opened while
it was being built:

| | out-of-region work flagged | coverage |
|---|---|---|
| development set (P14) | 0.78 | 0.80 |
| **confirmation set (P18)** | **0.80** | 0.82 |

**It does not drop.** The behavioural guard fell from 0.63 to 0.18 at exactly this
question; this one holds. **Four out of five out-of-region chains are caught, on
families the guard was never shown.**

## What it is, and what it is not

**It is the first confirmed signal this project has for the region's edge.** No
model is consulted, no threshold was fitted, the rule is the one written down before
anything was scored, and it survives unseen material.

**It is not deployable.** One correct in-region chain in five is flagged. A system
that escalates one good answer in five has spent a large part of what withdrawal was
supposed to save, and the pre-registration said this number counts equally.

**And it is not domain-free.** Two limitations are real and neither was engineered
around:

- **Empirical constants carry units.** Manning's `n` is s·m^(-1/3), so that family
  only types if the statement names the constant. A new domain costs a table of its
  own constants.
- **Numbers are matched by value.** An intermediate that happens to equal a quantity
  printed in the statement inherits its dimension. Symbolic tracking would fix it
  and is a much larger instrument.

## The instrument changed seven times, and that is the number to be suspicious of

Every one was the checker failing to read its input, and **the rule never moved**.
They are listed so the count is visible rather than buried:

1. the verdict was read off the last step that *typed*, not the last step — Manning's
   untypeable ending had it comparing a length against a flow rate
2. `Pa.s` matched the `Pa` prefix, typing a viscosity as a pressure
3. integer exponents could not express `R**(2/3)`
4. `**(2/3)` is a division, which `literal_eval` refuses — the guard had been
   abstaining on a whole family *by accident*
5. empirical constants had no dimensions at all
6. the constant matcher took the first unit-less number and found `1.9` inside `1.96`
7. its boundary check rejected `0.015` because a full stop follows it

False alarm on correct in-region work across those: **0.56 → 0.19 → 0.22**.

**Seven is past the point where this project's own rule says a measurement is
looking for its result.** The defence is not that each fix was justified — it is
that **the confirmation set was scored once, after all seven, on material never
opened during development, and it held at 0.80**. Without that, this would be a
number to distrust.

**Redesign count: 7 on the instrument, 0 on the rule.**

## What to do next

- **The 22% false alarm is the blocker**, and seven chains is few enough to read by
  hand. If they are correct answers the checker mistypes, that is more instrument;
  if they are correct answers that genuinely produce an inconsistent intermediate,
  the rule needs rethinking.
- **Coverage of 0.80 is a hole with a shape**, concentrated where constants are
  empirical. It bounds how much of a deployment this can guard.
- **Combining it with the judge conjunction from P20** is the obvious next question
  and has not been asked: they fail differently, and P20 showed that two weak checks
  with opposite error profiles beat either alone.

---

## Addendum — composing the guard with the mechanical check (2026-09-12) [ran]

An external proposal suggested a cascade: run the dimensional guard first as a cheap
structural filter and escalate whatever it flags. That keeps its 22% false alarm
intact, because escalation happens on the dimensional verdict alone. The measurement
says the opposite composition is the right one.

**All 7 of the dimensional false alarms are accepted by the mechanical check — 7 of
7.** The two fail independently, and in the useful direction.

| escalation rule | detects out of region | false alarm on correct in-region work |
|---|---|---|
| dimensional alone | 0.78 dev · **0.80 conf** | **0.22** |
| **dimensional AND mechanical both fail** | 0.50 dev · **0.47 conf** | **0.00** |
| dimensional OR mechanical fails | 0.93 | 0.28 |

**The conjunction removes the false alarm entirely and keeps half the detection**,
and it holds on the confirmation families at 0.47. For a guard whose job is to decide
when to escalate, a false alarm of zero is the property that lets it be switched on
at all: **half of out-of-region work caught, and not one correct answer stopped.**

The proposal's compounding warning was right in magnitude — a blind triple `AND` of
three acceptance tests would reject about 30% of correct work — but the fix is not
to order the checks by cost. It is to require **two independent failures before
escalating**, which is the same shape as P20's conjunction and works for the same
reason: the two checks are blind in different places.

**This is one sample of 7 false alarms and 40 out-of-region chains.** The zero is a
zero on small numbers, and the detection halving is the price. Neither is settled.
