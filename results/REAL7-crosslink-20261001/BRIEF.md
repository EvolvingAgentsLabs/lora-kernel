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

## Result

*(written after S)*
