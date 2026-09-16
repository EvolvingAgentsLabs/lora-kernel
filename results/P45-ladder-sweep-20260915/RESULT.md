# P45 — the result: FALSIFIED, and the reason is not difficulty

**[ran]** 2026-09-15, one L4, two arms, 140 cases each, seed 454545.
Brief: [`BRIEF.md`](BRIEF.md). Session stopped cleanly; nothing left running.

## The curve

| oracle depth | base | expert | n |
|---:|---:|---:|---:|
| 1 | 0.111 | 0.278 | 18 |
| 2 | 0.000 | **0.000** | 18 |
| 3 | **0.167** | **0.000** | 18 |
| 4 | 0.000 | **0.000** | 18 |
| 6 | 0.000 | 0.382 | 34 |
| 7 | 0.000 | 0.000 | 17 |
| 9 | 0.000 | 0.000 | 17 |
| **total** | **5/140** | **18/140** | |

**The pre-registered falsification fired.** Easy end 0.069, hard end 0.191 — the
easy end is not merely within 0.15 of the hard end, it is **below** it.
`verdict_of` printed `FALSIFIED` without anyone reading the table.

So the claim that bought this run — *depth is the axis that will reveal a
sufficiency band in this expert* — is **wrong**, and it is wrong in the direction
nobody proposed. The expert is worse on easy problems than on hard ones.

## Why, measured rather than guessed

| rung | oracle steps | expert's median calls | over-solves | base | expert |
|---|---:|---:|---:|---:|---:|
| L1_property | 1 | 3 | 14/18 | 0.111 | 0.278 |
| L2_pressure | 2 | 5 | **18/18** | 0.000 | 0.000 |
| L3_pressure_converted | 3 | 5 | 17/18 | 0.167 | 0.000 |
| L4_force_on_base | 4 | 5 | **18/18** | 0.000 | 0.000 |
| hydrostatic_force | 6 | 6 | **0/17** | 0.000 | 0.118 |
| manning_channel | 6 | 6 | **0/17** | 0.000 | 0.647 |
| venturi_flow | 7 | 7 | **0/17** | 0.000 | 0.000 |
| pipe_head_loss | 9 | 8 | 0/17 | 0.000 | 0.000 |

**Below its training depth the expert over-solves on essentially every case. At or
above it, never.** Its median chain length floors at about five calls and will not
go under, whatever the question is.

Asked *"How much gauge pressure acts at 2.5 m depth in RW-38 held at 80 C?"* — two
steps, `lookup` then `ρ g h` — it produced:

    <convert>value=70; from=C; to=K</convert>
    <lookup>fluid=RW-38; property=density; T=80</lookup>
    <convert>value=2.5; from=m; to=m</convert>
    <convert>value=100; from=mm^2; to=m^2</convert>
    <calc>1169.7 * 9.80665 * 2.5 * 0.0001</calc>
    ...
    5. Resultant force F = rho g h A: = 0.29999

It converted metres to metres, **invented an area of 100 mm²**, and answered a
question about force that nobody asked. On another it fabricated a velocity, a
cross-section and a formula — `F = rho v A sqrt(1 - v^2/r)^2` — that does not exist.

## What this means

**It is not a capability failure and not an instrument failure.** The tools
answered: 810 calls, and the oracle chains were verified against the real tools
before the run. The expert knows how to call things. What it cannot do is **stop
early**.

> **A corpus with one difficulty teaches a floor, not just a skill.** Every example
> this expert saw was a 6-to-9-step multi-tool chain, so it emits one regardless of
> what was asked. It does not simplify; it pads.

The clearest single number is depth 3, where **the bare base beats the expert,
0.167 to 0.000**. Fine-tuning made the model *worse* at easy problems in its own
domain — the measured price of specialising on one band.

## What survives, and what does not

- **Dead: that this expert has a sufficiency band waiting to be found.** It does
  not. The band was never in its training data, so it is not in the adapter.
- **Alive: that a small expert can be sufficient at a known, acceptable level.**
  Nothing here tests that, because no expert in this repository has ever been
  trained on an easy problem. The suite's missing easy end became the *expert's*
  missing easy end, since the corpus is generated from the suite.
- **New and general:** train on the difficulty band you intend to serve. That is a
  claim about training data, testable for the price of one corpus and one adapter,
  and it is much better specified than what this run set out to check.

## Not done, deliberately

The obvious next move — train an expert on the full ladder and see whether the
floor disappears — was **not** launched. The brief said a flat curve stops the GPU,
and inventing a new hypothesis and buying it in the same night is how an instrument
starts looking for a result instead of measuring one. It is specified and waiting.

## Caveats

- **The base arm measures disposition, not difficulty.** 140 calls for 140 cases,
  85 refused, against the expert's 810 and 75. A model that will not operate the
  protocol scores zero whether or not it knows the physics, so *"the base gets 0.111
  at one step"* must not be quoted as *"one-step problems are hard"*.
- **`manning_channel` scored 0.647 here against 0.304 in P41** on a different seed.
  Family-level numbers from a single seed move a lot; the depth curve is the claim,
  not any one cell.
- Every number is a lower bound: Qwen 2.5 is forced by C18/P33, not chosen.
