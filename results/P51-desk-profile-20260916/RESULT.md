# P51 — the band fired, the grid collapsed, and the rule found its own flaw

**[ran]** 2026-09-16, one A100, two arms, 240 cases, seed 424242, **no training**.
Brief: [`BRIEF.md`](BRIEF.md). Session stopped cleanly.

## The grid

| cell | base | target |
|---|---:|---:|
| `commitment@1` | 1.000 | 1.000 |
| `commitment@2` | 0.800 | 1.000 |
| **`commitment@3`** | **0.133** | **1.000** |
| **`commitment@4`** | **0.000** | **1.000** |
| `counterpart@1..4` | 0.000 | 0.000–0.133 |
| `importance@1` | 0.800 | 0.733 |
| **`importance@2`** | **0.533** | 0.600 |
| **`importance@3`** | **0.667** | 0.467 |
| **`importance@4`** | **0.667** | 0.733 |
| `owed@1..4` | 0.000 | **0.000** |
| **totals** | **69/240 = 0.288** | **101/240 = 0.421** |

## The verdict, as the pre-registered rule fired

**`usable: false`.** Three cells survive the band and all three are one region —
`importance` at depths 2, 3, 4. The grid collapsed back into a row, which is the
outcome the brief said would stop the next three sessions.

**The band is not being moved.** It was chosen once, before the run, and revisiting it
now is what the stopping rule exists to prevent.

## Two findings, and the second is about the rule rather than the suite

### 1. Two regions of four are unanswerable for both models

`owed` scores **0.000 for the target as well**, across all four depths, and
`counterpart` reaches 0.133 at best. Those questions ask about the **whole inbox** —
enumerate 24 threads with `inbox`, then call `message` or `sender_stats` per
candidate, then compare — and neither a 3B nor a 32B completes that in 8 turns.

**By this project's own rule those cells are broken, not hard.** A cell the reference
cannot do teaches nothing about ranking. Half the suite is unanswerable.

### 2. The band rule excludes the most informative cell there is

`commitment@4`: **base 0.000, target 1.000.** The band drops it because the base is
on the floor — and the clause that drops it was written for *"every arm fails and it
reads as the approach not working"*.

**But the target proves the task is doable.** A cell where the base cannot and a
larger model of the same family always can is not *nothing works*; it is the exact
shape a small expert exists to close, with the whole distance visible.

`commitment` degrades **1.000 → 0.800 → 0.133 → 0.000** across depth while the target
holds **1.000 throughout**. That is the cleanest difficulty gradient this project has
ever produced, and the rule threw away its bottom half.

**This is a flaw in how the intent was encoded, and noticing it after the numbers is
exactly when it must not be fixed unilaterally.** The floor clause needs a companion —
*unless the target clears the cell* — but making that change now, with the result in
hand, is indistinguishable from moving the band to fit it. It is written down and left
for a decision.

## What this costs and what it does not

**It does not cost the suite.** Three of four structural gates still pass: the
region × depth grid is real, four depths exist, four tools with genuine choice. What
failed is *where the difficulty landed*, which is what a profile is for.

**It does not cost the architecture.** Nothing here is about adapters, acceptance or
ranking — none of that was measured.

**It costs one of four sessions**, which is what the session was for.

## What the data says the next move is

Two of four regions need to become answerable — a smaller inbox, more turns, or a
candidate list handed over at low depths — and `commitment`'s gradient needs to land
inside the band rather than stepping across it. **Both are suite changes with the band
held fixed**, which is a different act from moving the band, and it would be the
**first post-result redesign** of this suite. The counter starts at one.
