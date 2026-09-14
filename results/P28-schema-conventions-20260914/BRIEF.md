# P28 — two schema conventions, and the prediction that one should do nothing

**Pre-registered 2026-09-14, before either convention was written.**

## The two open numbers are one problem

| | |
|---|---|
| P27 arm 3 | the OpenAI schema costs **0.188**, and **33 of its 93 refusals** are `<calc>expression=…</calc>` against the trained `<calc>1.2 * 3</calc>` |
| P25 | on a subject it never saw the adapter reaches **27/63**, and **56% of its refusals are names** — `expansion_coefficient` for `expansion` |

**Both are the adapter not knowing what shape or what names the tool expects, and
nobody telling it.** A JSON tool schema already has fields for exactly those two
things. This step uses them.

## The conventions, and why neither is domain knowledge

**A — arity.** A function with **exactly one required parameter** renders
positionally: `<calc>…</calc>` rather than `<calc>expression=…</calc>`. This is a
rule about *schemas*, keyed on a count. A converter that counts parameters still does
not know what a fluid is.

**B — enums.** A parameter carrying `enum` renders its allowed values:
`property=modulus|expansion|resistivity|heat_capacity`. **The names are schema; the
handbook's values remain data** — the adapter still has to call the tool to learn what
a modulus *is*.

**The voiding condition, and it is the first one:** if implementing either convention
requires a single line naming a tool or a domain, the proposal fails. The serializer
scored **0 of 38** domain lines in P27 and must still score 0.

## What is being measured, said without flattery

Convention B **gives the adapter information it did not have**. That is what a tool
schema is for — the tool's author declares its own vocabulary — but it means arm C is
not a test of generalisation. **It measures whether telling the adapter the names
helps**, which is a fair question and a different one.

## The sharp prediction

On **fluids**, the properties are `density` and `viscosity`, which the adapter was
trained on. So:

- **A should close most of the 0.188 gap**, because 33 of the 93 refusals are the
  `calc` shape.
- **B should do almost nothing on fluids.** If enums help here, they are a generic
  boost rather than a vocabulary fix, and the reading of P25's 56% was wrong.

**A convention that helps everywhere is a convention that is not doing what it
claims.** That is the check this arm exists to run.

## The arms, on the fluid suite, killing arm first

| arm | tool surface |
|---|---|
| trained instruction | the ceiling — 0.615 in P27 arm 3 |
| OpenAI schema, plain | the floor — 0.427 in P27 arm 3 |
| **+ arity** | convention A alone |
| **+ arity + enums** | both |

Materials is the second purchase and only if A and B behave as predicted here.

## Falsification

- **The conventions work** if arity closes most of the gap while enums move nothing
  on fluids.
- **The reading of P27 was wrong** if arity changes little — the `calc` refusals were
  a symptom rather than the cause.
- **The reading of P25 was wrong** if enums help on fluids, where there is no
  vocabulary to supply.
