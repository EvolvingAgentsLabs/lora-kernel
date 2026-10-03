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

## Run log

- **T attempt 1 — out of memory, nothing trained** (`attempt1_T_chain_oom.log`): the 4.00 GiB logits tensor (262k
  vocabulary × 4,096 positions, fp32) failed on the A100's 39.5 GiB with 2.3 GiB free and 3.7 GiB reserved but
  unallocated — fragmentation, with gradient checkpointing already on. **Fix, not a window cut:** the trainer sets
  `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` (unless the caller set it). The corpus, recipe, window and bars do not
  move. If attempt 2 runs out of memory too, one H100 attempt, then stop and record.
- **T attempt 2 — out of memory again, by a hair** (`attempt2_T_chain_oom.log`): fragmentation gone (159 MiB reserved
  unallocated), the same 4.00 GiB request against exactly 4.00 GiB free — the 12B at window 4,096 does not fit a 40 GB
  A100. **Attempt 3: the one H100 (80 GB) attempt**, same everything.
- **T attempt 3 — the H100 refused three times (quota), nothing ran.** The stop the brief wrote is reached for the
  hardware route. **What does not change the recipe:** the loss only needs logits where it is taken (~3 % of positions);
  `s4_train.span_logits_loss` computes them through the model's own `logits_to_keep` (final softcapping included) and is
  the same quantity as the model's shifted cross-entropy — **[ran] equal to HuggingFace's loss on a tiny random causal LM,
  with and without accumulation** (`tests/test_span_logits.py`). Attempt 4, when the user's machine is back: the A100 with
  `wiki_arm --span-logits`, everything else as written.

- **T attempt 4 [ran]:** the A100, `--span-logits`: trained without running out of memory (315 rows, 19,454 trained tokens
  of 594,798); adapter home.

## Result [ran] — TIE: trained on the same corpus, the 12B member does what the E4B member does

One A100, vLLM bf16, G1 applied, 0 errors (`pair1.json`).

| member, served runtime (top-8) | answerable (44) | multi-hop (30) | one-hop (14) | refusals (8) |
|---|---|---|---|---|
| **`real-none-12b`** (12B + LoRA) | **33** | 23 | 10 | 7 |
| `real-none-s0` (E4B + LoRA), PAGE0's record | 34 | 24 | 10 | 7 |
| `real-none-s0`, FMT0's record (the spread) | 33 | 23 | 10 | 7 |

- **Verdict: TIE** — paired against PAGE0's record **5 : 6** ($p = 1.0$), against FMT0's 6 : 6. With B3 (W9, generated
  wiki), **two regions where a large member buys no accuracy**: the speculative pair stays a measured speed result (B4,
  F0, C0, F0c) without a region in this project that needs its large half.
- **What the 12B member fixed and did not:** trained, it walks like the E4B member — no thought lines (0, against the
  bare 12B's hundreds in PAIR0), no missing line, 3 citations without `§section`. The protocol PAIR0's bare 12B failed was
  the training, not the size.
- **One observation beside the verdict, not a claim:** the two members tie on totals but **err on different rows** (11
  discordant of 44 — 5 the 12B alone gets right, 6 the E4B alone); rows right by either: 39/44 against 33–34 for each.
  Whether anything can *choose* between them per request (the citation gate does not see which is right when both
  verify) is untested.
- **Training note:** the 12B at window 4,096 needs `span_logits_loss` on a 40 GB A100 — the same loss, a 30× smaller
  vocabulary projection.

## Beside the verdict, zero GPU, post-hoc — a hypothesis, not a finding (2026-10-03)

Read on this one 52-row set, already seen, so it is not evidence until measured on a fresh set under a brief.
- **Choosing the member that is right is not possible from the runtime:** of the 11 discordant rows the citation gate
  decides 4 (one member fails it); in the other 7 both verify with different answers — sometimes citing the same
  statement and reading a different number off it. Gate, then E4B: 35/44; gate, then 12B: 36/44; the oracle union 39.
- **Disagreement detects wrong answers.** Delivering only when both members pass the gate and agree: 37 delivered, 34
  right, **3 wrong** (precision 0.92), against today's served E4B with the gate — 50 delivered, 41 right, **9 wrong**
  (0.82). It forwards 7 right answers to catch 6 wrong ones — GATE0's kind of trade, on top of it.
- **Cost and the cheaper rival, both untested:** two members per request, one a 12B; two samples of the same E4B
  (self-consistency) might carry the same signal without the large model.
