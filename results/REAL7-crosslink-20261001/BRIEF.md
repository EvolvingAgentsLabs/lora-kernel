# REAL7 — cite the end of the link, not the decoy at its start

**Written 2026-10-01, before training.** REAL6 **[ran]** read where REAL5's citations fail: on multi-hop rows the member
cites a statement at the **start** of a link that holds the same number as the answer at its **end**. REAL6's corpus
taught one-hop choices and changed nothing (15/25 against 15/25).

## The change (one): cross-link decoy walks

`train_real_link.jsonl` = REAL4's corpus (unchanged; it regenerates byte-identical) **+ 98 two-hop walks whose answer sits
at the end of a link while the same number sits on the page the walk starts from** (`real_corpus.build_crosslink`):
Claude Haiku ($0.46) is shown the linking statement, the decoy statement(s) on the first page and the target statement(s)
on the second, and writes a question only the target answers; a row is kept only if the value is in the target, in a
decoy, and not in the question. "Number" is any two-digit-or-more value (days, dates, amounts) — never a section
reference, part number, link or paragraph label (`decoy_numbers`). To find enough such links within the trainer's window
the training family gains **49 CFR 390/392/393/397** (`knowledge/regs-train2`, FMCSA, 225 pages, ingested verbatim;
sources committed) — the evaluation libraries are untouched. Gate G1–G6 passed: 418 rows, 212 two-hop. Same span-masked
recipe (results are long), seed 0: **`real-link-s0`**.

## Arms and sets (one L4 each, `+page`, `--max-model-len 16384`)

- **REAL5's set (verdict):** `real-link-s0` vs `real-none-s0` (our previous version).
- **REAL4's set (guard) — bought only if REAL5 shows an effect** (a flat verdict makes the guard moot).

**The twin gate, fixed now:** 4 of REAL5's headline rows rest on a statement with a word-for-word twin elsewhere in the
library (`general-onshore-17`, `onshore-general-18`, `qualified-onshore-26`, `qualified-onshore-27`) — the strict citation
cannot separate twins by reading. **The verdict is read on the twin-free headline (21 rows)**; the full 25 beside.
`real-none-s0` on it: **13/21** (REAL6's session).

## Verdict (fixed here)

- **PASSED** — twin-free headline ≥ 15/21 (≈ 70 %) **and** paired against `real-none-s0` not a regression **and** refusals
  ≥ 4/5; then the REAL4 guard: headline loses ≤ 2 against `real-none-s0`, refusals ≥ 13/16.
- **FALSIFIED** — otherwise, the failing clause named. **Caveat said now:** REAL5's failures have been read twice; the
  corpus is built on training documents only, by a model that never saw REAL5.

## Result [ran] — FALSIFIED: the citation is unchanged; the corpus line on this question stops here

T on an A100 (418 rows, span-masked, 81 steps); S1 on one L4, G1 applied for both, 0 errors. `real7_real5.json`. **The REAL4
guard was not bought** (no effect on REAL5, as the brief set it).

| on REAL5 | twin-free headline (21) | headline (25) | value-right | same-value miscitations | refusals (5) | all (40) |
|---|---|---|---|---|---|---|
| `real-none-s0` (previous) | **13** | 15 | 20 | 2 | 5 | 28 |
| `real-link-s0` | **13** | 16 | 22 | 2 | 5 | 30 |

Paired on the twin-free headline a tie, **4 : 4**, $p = 1.0$ — under the 15/21 bar. The baseline reproduced REAL5 exactly
(28/40, 15/25). The value is right more often (22 against 20) and the citation is not.

**Two corpus changes aimed at this citation have now changed nothing** (REAL6: one-hop repeated values; REAL7: decoys across
a link). By the rule on counting redesigns, a third corpus redesign on the same question set would be looking for the
result; this line stops. What stands: `real-none-s0` with the runtime cites the supporting statement on 13/21 twin-free
multi-hop rows of a third family (value right 20/25), refuses 5/5 — the measured level. What might move it is not another
corpus on these rows: a different mechanism (a citation check in the runtime that rejects a citation whose page the walk
did not end on), measured on a **fresh** set.
