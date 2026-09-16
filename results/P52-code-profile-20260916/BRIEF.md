# P52 — where does the completion difficulty sit? Session 2 of the remaining 3

**Pre-registered 2026-09-16, before the run. No training.**

## Why the predicate changed

Everything this architecture does rests on a small model's continuation aligning with
a larger one's, and C9 measured what breaks that: **identical answers scored 0.00
across formats** while different answers scored 0.44 within one **[ran]**. Layout
dominated.

**A code prefix has already fixed the layout.** The indentation, the names and the
brace style are in the prompt, so what is left to predict is the algorithm rather than
a convention. And the difficulty is **where the implementation is cut**, which comes
from the algorithm's own length — the answer to the report's finding that a generated
suite cannot hold a difficulty its author did not think of.

**The verifier is execution.** Not a definition, not a floor, not a judge. All 15
references print identical output in Python, JavaScript and C; `base32` reproduces the
published RFC 4648 vectors; all 60 oracle completions reconstruct their reference.

## The suite

**5 algorithms × 3 languages × 4 depths = 60 cases.** `crc32`, `xorshift128`,
`base32`, `levenshtein`, `dft`. Depth removes 20/40/60/80% of the body from the end.

- **`levenshtein` is a deliberate ceiling control** — the most canonical of the five.
  If it does not come back at the ceiling, the instrument is not detecting ceilings.
- **`dft` is the candidate to measure rather than assume.** It scores two of four on
  the criteria (floats need a tolerance; it is among the most reproduced snippets in
  existence), and the prediction on record is that it lands at the ceiling or needs a
  tolerance nobody chose. **The profile decides, not the argument.**

## Arms

| # | arm | model |
|---|---|---|
| 1 | **base** | `Qwen/Qwen2.5-3B-Instruct` — decides the band |
| 2 | **target** | `Qwen/Qwen2.5-32B-Instruct-AWQ` — a cell it also fails is broken, not hard |

Sequentially, one model on the card. ~700 completion tokens, 4096 context.

## The band — P51's, unchanged

`0.15 ≤ base ≤ 0.70`; a cell the target scores under `0.40` is dropped as broken.
**Chosen once, on 2026-09-16, and not revisited.**

**And P51's flaw is reported rather than fixed.** That run found `commitment@4` at base
**0.000** against target **1.000** — dropped for being on the floor by a clause written
for *"every arm fails"*, when the target had just proved it doable. Changing the rule
now is indistinguishable from moving the band to fit a result, so every such cell is
**counted under `floor_but_target_clears`** and still dropped. The evidence is visible;
the decision stays open.

## What it must produce

A grid, not a row: kept cells spanning **≥2 algorithms and ≥2 depths**. Otherwise the
next sessions do not run on it.

## What ends this line

- Base above 0.70 everywhere — the completion task is too easy.
- Base below 0.15 everywhere — too hard at 3B.
- Target below 0.40 on most cells — no reference worth accepting against.

## Budget, honestly

Four sessions were granted. **P51 spent one and returned `usable: false`.** This is the
second. If it comes back usable, one remains for training the experts and one does not
exist — the ranking measurement would need a fifth. That is worth knowing before this
runs rather than after.

## What it cannot conclude

Nothing about acceptance, nothing about any adapter, nothing about ranking. It decides
**where** those may be measured.

## Safety

Model-written code is executed. That happens on a disposable rented VM, with a timeout
and no shell — there is no sandbox, and saying otherwise would be worse than saying so.
