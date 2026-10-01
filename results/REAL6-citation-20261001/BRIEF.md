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

## Result [ran] — FALSIFIED: the citation is unchanged (and why)

T on an A100 (363 rows, span-masked); S1 on an L4 after one refused card (Colab had no L4; retried 10 min later), G1 applied,
0 errors. `real6_real5.json`. **S2 (the REAL4 guard) was stopped before it booted: a flat verdict makes the guard moot.**

| on REAL5 (40 CFR 112) | headline (25) | value-right | cited another statement holding the value | refusals (5) | all (40) |
|---|---|---|---|---|---|
| `real-none-s0` (previous) | 15 | 19 | 2 | 5 | 28 |
| `real-cite-s0` | 15 | 21 | 3 | 4 | 25 |

Paired on the headline a tie, 1 : 1. **CITATION FIXED fails on every clause** (15 < 18; wrong same-value citations 3, not
fewer; refusals 4/5 holds).

**Read where it happens — the corpus trained the wrong shape.** Of the same-value miscitations (both members), most are
**multi-hop rows cited at the wrong end of the chain**: the question leads from one page through a link to another, both
pages hold the number, and the member cites the statement on the page it is already on (the middle of the walk) instead of
the one the chain ends on (112.6 ↔ 112.3, 112.4 ↔ 112.1, 112.3 ↔ 112.5). The 50 repeated-value walks were all **one-hop**
— the choice among same-value statements on one page or the next search — not the choice of which end of a link to cite.
**One row is an instrument limit:** 112.7§d-1 and 112.9§d-3-i are the same sentence word for word ("An oil spill
contingency plan following the provisions of part 109 of this chapter"); no reading separates them, so the strict
citation measures the path there, not the statement.

**What it points to, not bought here:** repeated values placed **across a link** in two-hop training walks — the answer at
the chain's end, a decoy with the same number at its start — and a gate that drops evaluation rows whose supporting
statement has a word-for-word twin elsewhere in the library.
