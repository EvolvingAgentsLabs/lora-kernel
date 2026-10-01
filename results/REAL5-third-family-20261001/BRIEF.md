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

### As frozen (2026-10-01, before any model answered) — and its limits

40 rows (`make_questions.py`): 10 one-hop, 19 two-hop, 6 three-hop, 5 unanswerable (2 adjacent: a state UST registration
fee, a tank-truck placard); **headline 25, all 25 (statement, question) pairs and support statements distinct**; support
spread over 11 pages (112.20 eight headline rows, 112.3 and 112.8 three or four each). Oracle 40/40 verified, 0 refused
(`zero_gpu.json`); no digit in any question; every hop a real link; no token in an earlier opened statement; the search of
every plan ranks its start page strictly first. One `famous` row (1,320 gallons), one-hop — outside the headline.
**Limits, stated now:** comma-formatted values are checked as the regulation writes them (`2,100`) — a model writing
`2100` is graded wrong, both arms alike; one row's link can be skipped (the search also shows the target page); values
repeat across statements (60 days ×6) — only the strict citation separates them; two plan searches name a section number
(plans only, never a question); thin pages push support toward 112.20 and 112.1.

## Verdict (fixed here), on the headline

- **VOID** — `nolib` value-right on > 10 % of the headline.
- **TRANSFERS** — `real-none-s0` ≥ 70 % of the headline **and** an improvement over `base-walks+page` (exact sign test,
  $p \lt 0.05$) **and** refusals ≥ 4/5.
- **PARTIAL** — an improvement under 70 %, or refusals under 4/5.
- **DOES NOT TRANSFER** — no improvement over the base.
- Beside: one-hop; the `famous` rows apart.

## Result

*(written after S)*
