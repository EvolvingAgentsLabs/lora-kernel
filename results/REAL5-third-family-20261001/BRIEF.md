# REAL5 — does the real-document member transfer to a third family, one with dense links?

**Written 2026-10-01, before the questions exist and before anything runs.**

## What and why

REAL3 **[ran]** showed a trajectory member trained on real documents of one family (FMCSA driver/HOS/inspection rules,
FDA manufacturing practices, OSHA exits) walking another family (FDA food transportation, OSHA forklifts) — 18/23 and
17/23 with two seeds. That evaluation library was **link-poor** (22 links over 20 pages): its multi-hop rows repeated
paths. REAL5 asks the same question on a **third** family chosen for the opposite property: **40 CFR Part 112** (EPA,
oil spill prevention, control and countermeasure plans — fuel storage at terminals, warehouses, small facilities),
`knowledge/spcc-regs`, ingested verbatim (`memory/ingest.py`, source committed): 15 pages, 462 statements, **146 links —
9.7 per page**, so the multi-hop rows can be genuine distinct chains. A different agency, a different subject from the
training and the first evaluation family. One reserved section has no paragraphs (lint `body-empty`).

## The member and the arms (one L4, `+page` runtime, `--max-model-len 16384`)

| arm | what |
|---|---|
| `withlib-s0+page` with `adapters/real-none-s` | **`real-none-s0`** — the member the user accepted after REAL4 (unchanged) |
| `base-walks+page` | the untrained base, same runtime |
| `nolib` | closed book — the gate: is Part 112 in the weights? |

## The questions — written blind (`questions.jsonl`), frozen before any model answers

40 rows: ≥ 25 multi-hop on distinct (statement, question) pairs, ~10 one-hop, 5 the library cannot answer (2 adjacent);
oracle 40/40 before freezing; at most 2 rows whose answer is one of SPCC's famous thresholds (marked `famous`).

## Verdict (fixed here), on the headline

- **VOID** — `nolib` value-right on > 10 % of the headline.
- **TRANSFERS** — `real-none-s0` ≥ 70 % of the headline **and** an improvement over `base-walks+page` (exact sign test,
  $p \lt 0.05$) **and** refusals ≥ 4/5.
- **PARTIAL** — an improvement under 70 %, or refusals under 4/5.
- **DOES NOT TRANSFER** — no improvement over the base.
- Beside: one-hop; the `famous` rows apart.

## Result

*(written after S)*
