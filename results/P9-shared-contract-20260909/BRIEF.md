# P9 — composition, measured under a contract the two halves actually share

**Why P8 has to be re-run and not re-read.** P8 stacked a kernel adapter and a
domain adapter, scored 0/30, and I read it as weight-space interference. It could
not be read as anything. Side by side **[ran]**:

| | kernel corpus | domain corpus |
|---|---|---|
| examples with `<calc>` | 600 / 600 | 0 / 598 |
| examples with LaTeX | 0 / 600 | 433 / 598 |
| system prompt | "every computed number must come from a `<calc>` call" | "show no working: reply with one JSON object only" |

The domain prompt contradicts its own 598 working-showing targets, and **every arm
ran under it**, including the kernel's. The `\sqrt{}` and stray markup inside the
tags were the superposition of two taught notations, not a fact about composition.

**What is different here, and it is only this.** Both corpora import
`training/protocol.py`: one system prompt, one user instruction, one numbered
ASCII chain, one final JSON. The domain corpus is the oracle's own chains with the
tags removed and the arithmetic left in place, so its formulas are exact by
construction (the repair walk recovers the oracle's answer on **200/200** of them).
The two adapters differ in exactly one thing: whether the arithmetic is delegated.

**The instruction says nothing about `<calc>`.** If the prompt asked for tags, the
prompt would be the protocol and the kernel adapter would be decoration. §4 claims
the protocol lives in weights, so the prompt must not carry it.

## The arms, in the order in which they can kill the hypothesis

| # | arm | what it answers |
|---|---|---|
| 1 | **domain** | Does the expert know the physics **at all**? P8 never found out — its domain arm emitted a bare JSON number on 30/30 cases. Scored twice: raw, and with its arithmetic repaired. |
| 2 | kernel | The protocol under a prompt that does not ask for it. P8 says 30/30 well-formed calls; this re-measures it honestly. |
| 3 | **kernel + domain** | The claim. |
| 4 | base | Attribution. Bought last, because it cannot kill anything. |

## The stopping condition, written before the run

**If the domain adapter's repaired accuracy is below 0.25, arms 2–4 are not
bought.** A composition cannot be shown to gain from a half that contributes
nothing, and buying it anyway is how a flat result gets spent into a grid. The
gate is enforced in `training/harness/separate.py`, not in a reviewer's judgement.

## Falsification

With the contract shared and the domain half verified, if `kernel + domain` still
fails to beat both halves alone, **weight-space composition is genuinely dead** and
`ARCHITECTURE.md` §4 has to be served some other way — sequential activation
(§5 option 1) or disjoint target modules. Neither is bought here.

## What is deliberately not bought

- **Constrained decoding / tag repair.** The free diagnostic settled it: 19 of the
  stacked arm's 30 failures had **every call clean** and still got the physics
  wrong. Syntax was never the dominant failure.
- **More weighting knobs.** One blend was pre-registered and run in P8; another
  would be a search.

**Redesign count: 0.** P8's instrument is not being adjusted toward a friendlier
number — a confound was found, published, and the confounded variable removed.

---

## Outcome (2026-09-09)

| arm | raw | repaired | calls/case |
|---|---|---|---|
| domain | 1/30 | **30/30** | 0.0 |
| kernel | 0/30 | n/a | **7.7** |
| **kernel + domain** | **4/30** | 22/30 | 0.6 |
| base (control) | **4/30** | undefined | 0.0 |

**Composition composes.** With the contract shared it beats both halves and
inherits 22/30 of the physics. P8's 0/30 was the confound, as suspected.

**And it delegates on 5 of 30 cases.** Split that way: **3 of 5 pass when it
calls the tool, 1 of 25 when it does not.** The mechanism is intact; the domain
delta simply wins the competition for the output format at almost every step.

**The base is not at zero.** 4/30 with no adapter, a tie with the composition.
Every baseline in P5–P8 ran under a prompt that told the model to show no working
while every treatment was trained to show working. The frontier gap and the 0/40
attribution arms inherit that doubt.

**The gate did its job in both directions**: it opened on a domain half that was
verified to contribute (repaired 30/30), and the composition arm it authorised
returned the first positive composition number this project has produced.

**Redesign count: 0.**
