# P51 — session 1 of 4: let the models say where the difficulty is

**Pre-registered 2026-09-16, before the run. No training.**

## Why this first

`training/suite_gates.py` has seven gates and **four need a model**. Those four are
the ones that voided runs: P42's base already at 0.815, P45's floor of six steps,
P49's saturated `team`, P46's information ceiling. No amount of reading a generator
answers them.

And it is the answer to the report's deepest finding, which no gate can check:

> *A generated suite cannot contain a difficulty its author did not think of.*

The fix is not another check — it is to **stop choosing the difficulty**. The suite is
generated wide over the full 4 × 4 region × depth grid, and what gets kept is the band
where the **base** is neither on the floor nor at the ceiling.

## Arms

| # | arm | model | why |
|---|---|---|---|
| 1 | **base** | `Qwen/Qwen2.5-3B-Instruct` | it decides the band |
| 2 | **target** | `Qwen/Qwen2.5-32B-Instruct-AWQ` | acceptance will be measured against it; a cell it also fails teaches nothing about ranking |

**The base first**, sequentially, one model on the card at a time. 240 cases, 15 per
grid cell, seed 424242, four tools, up to 8 turns. **Nothing is trained.**

## The stopping rule, and it is the point of writing this down

**The band is `0.15 ≤ base ≤ 0.70`, and a cell the target scores below `0.40` is
dropped as broken rather than hard.** Chosen **once**, from this run, and **never
revisited whatever a later treatment scores.**

Choosing it twice would be the instrument looking for a result. This repository counts
redesigns and stops at three; this is the rule that keeps the count honest.

## What it has to produce to be worth anything

**A surviving grid, not a surviving row.** If the band keeps cells from fewer than two
regions, or fewer than two depths, the grid has collapsed back into the diagonal every
previous suite had — arriving through the back door, because the generator produced a
grid and the band threw all but one row of it away. `band()` reports `usable: false`
and the next three sessions do not run on it.

## What would end the whole line

- **The base above 0.70 everywhere.** The suite is too easy and no expert can show
  anything on it.
- **The base below 0.15 everywhere.** Too hard, and every arm will fail in a way that
  reads as the architecture failing.
- **The target below 0.40 on most cells.** Then there is no reference worth accepting
  against and the ranking experiment has no ruler.

Each of those is a real outcome and each ends this line of work for one session's
cost, which is the point of spending the first of four here.

## What it cannot conclude

- **Nothing about acceptance**, which is session 3.
- **Nothing about any adapter** — none exists for this suite yet.
- **Nothing about the frontier.** It is not in this run.
