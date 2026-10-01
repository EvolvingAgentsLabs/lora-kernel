# REAL4 — teach the real-document member to refuse, without losing what it answers

**Written 2026-09-30, before training.** REAL3 **[ran]**: `real-spans-s0` (walks over real documents, span-masked loss)
answers 18/23 of a fresh multi-hop set on an unseen document family — and refuses **0/4** questions the library cannot
answer, where the untrained base refuses 3/4. Its corpus held no unanswerable question. A member that never says
`Not in my library.` invents; it is not served until this is fixed.

## The change (one): unanswerable questions in the corpus

`training/wiki/data/train_real_none.jsonl` = REAL3's corpus (unchanged, 284 walks after the gate) **plus 27 unanswerable
walks** (`real_corpus.build_none`): questions a carrier, plant or warehouse would ask on topics none of the training
library holds (customs, insurance, payroll, placards, …), kept only if none of their topic keywords occurs in the training
library; the oracle searches, **opens the best page the entry shows, finds nothing, and answers `Not in my library.`** —
a refusal after reading, not a reflex. Gate G1–G6 passed (315 rows; 27 refusals, 8.6 %). Same recipe as `real-spans-s0`
(span-masked loss, seed 0, window 4,096): **`real-none-s0`**.

## The evaluation — REAL3's fresh 40 rows + 12 new unanswerable questions (`questions.jsonl`, 52 rows)

The 12 are written before training, on `knowledge/logistics-regs`: **6 adjacent** — on topics that ARE in the training
family but NOT in this library (hours of service, the medical certificate, periodic inspection, daily logs, exit routes,
a food safety plan's review) — and 6 unrelated (insurance, import duty, payroll tax, placards, instructor hours, rail
demurrage). Checked: none is answered by any statement of the library (three keyword hits were common words —
"physical", "log", "flammable liquids" in a forklift rule — none holds an answer).

## Arms (one L4, `+page` runtime, `--max-model-len 16384`)

| arm | member |
|---|---|
| `withlib-s1+page` | **`real-none-s0`** — the treatment |
| `withlib-s0+page` | `real-spans-s0` — our previous version, the baseline |
| `base-walks+page` | the untrained base |

(The two adapters are packed as `adapters/real4-s0` = `real-spans-s0` and `adapters/real4-s1` = `real-none-s0`, so
one session serves both; their sha256 are recorded in REAL3's and this run's training records.)

## Verdict (fixed here)

- **REFUSAL FIXED** — `real-none-s0` refuses ≥ 13 of the 16 unanswerable rows (≥ 80 %) **and** ≥ 4 of the 6 adjacent ones.
- **AT NO COST** — on REAL3's 23-row headline, paired against `real-spans-s0`, it loses ≤ 2 rows it answered, and stays ≥ 70 %.
- **PASSED** = both. **A refusal bought with answers** (fixed, but the headline cost exceeds the bar) is FALSIFIED as a
  recipe, and said so.

## Result

*(written after S)*
