# REAL6 — cite the statement the question asks about, not the first one holding the number

**Written 2026-10-01, before training.** REAL5 **[ran]**: on a third, link-dense family (EPA 40 CFR 112) `real-none-s0`
had the value right on 20/25 multi-hop rows but the strict citation on 15/25 — of 5 lost, 3 cited **another statement
holding the same number** (the library repeats values; "60 days" sits on six statements). That is the whole distance to
the 70 % bar.

## The change (one): repeated-value questions in the corpus

`train_real_cite.jsonl` = REAL4's corpus (unchanged) **+ 50 walks whose value occurs in several statements of the
training library** (`real_corpus.build_repeated`): for each value a regulation repeats ("3 years" on 13 statements, "15
days" on 9, …), Claude Haiku is shown every statement holding it and writes one question per statement that only that
statement answers; a row is kept only if the value is in the named statement and not in the question **and** in at least
one other statement (it must exercise the choice). Strict-citation oracle walks through the served runtime, gate G1–G6
passed (363 rows; 50 repeated-value rows, 14 % — fewer than asked for: validation drops most of the model's drafts). Same
span-masked recipe (results here are long): **`real-cite-s0`**.

**A caveat said before the number:** REAL5's failures have been read (that is what motivated this). The corpus is built
on the training family only, by a model that never saw REAL5's questions; the fix targets a general failure (a repeated
value), not those rows. A fresh set would be the cleaner verdict; REAL5's is used for comparability, REAL4's as the guard.

## Arms (one L4 each, `+page`, `--max-model-len 16384`)

| set | arms |
|---|---|
| **REAL5** (40 CFR 112, 40 rows) — the verdict | `real-cite-s0` vs `real-none-s0` (our previous version) |
| REAL4 (logistics-regs, 52 rows) — the guard | the same pair |

## Verdict (fixed here)

- **CITATION FIXED** — on REAL5's headline `real-cite-s0` ≥ 18/25 (70 %) **and** its rows that cite a wrong statement
  holding the right value drop (fewer than `real-none-s0`'s 3) **and** refusals ≥ 4/5.
- **NO COST** — on REAL4's set, paired against `real-none-s0`: headline loses ≤ 2, refusals ≥ 13/16.
- **PASSED** = both; else FALSIFIED with the part that failed named.

## Result

*(written after S)*
