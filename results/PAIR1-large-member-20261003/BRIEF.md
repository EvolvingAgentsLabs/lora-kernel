# PAIR1 — the large half as the pair defines it: a 12B member on the same real-document corpus

**Written 2026-10-03, before the member trains or anything is scored.**

## What and why

A speculative pair is worth serving only where its large half buys accuracy. B3 **[ran]**: on W9's generated wiki a 12B
member tied the E4B member. PAIR0 **[ran]**: on real documents, *untrained*, the 12B lost to the E4B 2 : 12 — but read
where it happened, the bare 12B followed the walking protocol worse (plain-text answers, section numbers opened as ids,
its thought channel), which conflates size with protocol. The pair's own definition removes that: **both sizes trained on
the same corpus.** If the 12B member does not beat the E4B member here either, no region the project has needs the large
half, and the pair stays a speed result.

## The member — `real-none-12b`

`google/gemma-4-12B-it` + LoRA, the same corpus and recipe as `real-none-s0` (`training/wiki/data/train_real_none.jsonl`:
REAL4's walks over real documents of another family, unanswerable walks, span-masked loss), seed 0, window 4,096,
`wiki_arm --train-seed 0 --corpus train_real_none --member-prefix adapters/real-none12b-s --max-seq 4096`, one Colab
A100. **Risk, named now:** the 12B at window 4,096 may not fit the A100's memory; an OOM is recorded and the window is
not cut silently.

## Arms (one A100 session, vLLM bf16, `--max-model-len 16384`), PAGE0's 52 rows on `knowledge/hazwaste-regs`

| arm | what |
|---|---|
| `withlib-s0+page+top8` on `gemma-4-12B-it` | `real-none-12b`, the served runtime |

The E4B member's arm is **not re-run**: `real-none-s0` under the same runtime on the same rows **[ran]** twice — PAGE0
34/44, FMT0 33/44 (refusals 7/8 both) — and the pair is read against the PAGE0 record, paired per row, with FMT0's
beside it as the run-to-run spread.

## Verdict (fixed here), on the answerable rows

- **LARGE MEMBER WINS** — `real-none-12b` beats `real-none-s0` (PAGE0's record), paired, exact sign test $p \lt 0.05$,
  **and** against FMT0's record it is not worse → the large half has a region; next, the speed of the pair on it.
- **TIE** — no significant difference → no region the project has needs the large half (with B3, two regions).
- **LARGE MEMBER LOSES** — significantly worse.
- Beside: refusals, multi-hop and one-hop; the 12B member's format failures (no line, `[id]` without `§`), thought lines.

## Stopping condition

One training (A100), one scoring (A100). No change to the corpus, recipe, set or bars after training starts.

## Result

*(written after the run)*
