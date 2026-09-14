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

---

## Outcome (2026-09-14) [ran]

| arm | oracle's tool values | calls | refused |
|---|--:|--:|--:|
| trained instruction | 59/96 = **0.615** | 182 | 17 |
| OpenAI schema, plain | 41/96 = **0.427** | 173 | **88** |
| **schema + arity** | 51/96 = **0.531** | 173 | **17** |
| schema + arity + enums | 48/96 = **0.500** | 188 | 37 |

### Arity is confirmed, and precisely

**Refusals fall from 88 to 17 — the trained arm's number exactly.** The `calc` shape
was not *a* cause of the schema's refusals; it was the whole excess. And the gap to
the trained arm closes by **55%**: 0.188 down to 0.084.

A convention that keys on a parameter count, with **0 of 48 lines of code naming any
tool or domain**, recovers over half of what speaking OpenAI's dialect cost.

### Enums are falsified, and not in the direction predicted

The brief predicted enums would **do almost nothing** on fluids, because `density` and
`viscosity` are what the adapter was trained on. They did something: **they made it
worse**, 0.531 down to 0.500, with refusals rising 17 → 37.

**And they did fix what they were aimed at.** Without enums the adapter writes
`property=D` seven times; with them, never:

| | `density` | `viscosity` | `D` | other |
|---|--:|--:|--:|--:|
| + arity | 13 | 9 | **7** | `Density` ×1 |
| + arity + enums | 22 | 13 | **0** | `viscosity\|T=25`, `roughness\|T=25` |

**The damage is somewhere else.** Handbook misses — a lookup for a substance or
temperature this problem does not carry — go from **3 to 17**, and total calls rise
from 173 to 188. Supplying part of the vocabulary made the adapter query more
confidently and miss on a *different argument*. Only **one** call leaked the renderer's
`|` into its body, so the separator is not the cause.

### What this changes

**The reading of P27 was right**: the schema's cost was mostly a shape mismatch, and
naming the convention that fixes it costs no domain knowledge.

**The reading of P25 does not transfer the way this brief assumed.** "56% of
out-of-domain refusals are names" remains true; **"so tell it the names" does not
follow.** Telling it the names moved the failure rather than removing it, on a suite
where the names were not the problem to begin with. Whether enums help where the
vocabulary *is* genuinely unknown — the materials suite — is now a different and more
interesting question, and it is **not** the one this run answers.

**Bought next, if anything**: arity alone on materials, where the shape mismatch and a
real vocabulary gap coexist. Enums are **not** carried forward as a default.
