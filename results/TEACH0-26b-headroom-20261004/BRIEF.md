# TEACH0 — is there a teacher? `gemma-4-26B-A4B-it`, untrained, against the E4B member on real documents

**Written 2026-10-04, before anything runs.** Step 4 of `docs/review/moe-distillation-and-spotlight.md`.

## What and why

Two proposals rest on a stronger model: distilling specialists from the 26B MoE into E4B adapters, and the 26B as the base
for every member ([read: a design note pasted by the user]). Distillation transfers what the teacher knows and the student
does not. In this project's regions no larger model has yet beaten the E4B member: B3 and PAIR1 **[ran]** (a trained 12B
member ties), PAIR0 **[ran]** (the untrained 12B loses, 2 : 12). The 26B is a different model — an MoE, 128 experts per layer,
8 active — and has never run here. **One headroom run decides whether a teacher exists.**

## The arm

`base-walks+page+top8` — `google/gemma-4-26B-A4B-it`, untrained, vLLM **FP8** on one Colab A100 (bf16 does not fit 40 GB:
a second unknown, named), `--empty-thought` (Gemma 4's larger models open their thought channel with thinking off — PAIR0
**[ran]**), PAGE0's 52 rows on `knowledge/hazwaste-regs`, the served runtime (full-text entry, pages with their statements,
`page_top = 8`), the strict grader, `--max-model-len 16384`.

Compared, paired per row, with records already on disk under the same runtime and rows:
- `real-none-s0` (E4B + LoRA) — PAGE0 **[ran]**, 34/44 answerable (FMT0's record 33/44, the spread);
- the bare E4B — PAIR0 **[ran]**, 21/44.

## Verdict (fixed here)

- **A TEACHER EXISTS** — the 26B beats `real-none-s0` on the answerable rows, paired, exact sign test $p \lt 0.05$ →
  distillation gets a pilot under its own brief (on-policy, one region's corpus), and the 26B as a base goes to the user
  as a decision with this run.
- **SIZE HELPS ONLY UNTRAINED** — the 26B beats the bare E4B ($p \lt 0.05$) but not `real-none-s0` → training already
  closes the gap; no distillation, no base change.
- **NO TEACHER** — the 26B beats neither → the line closes, as PAIR0/PAIR1 did for the 12B.
- Beside: refusals, multi-hop and one-hop, format failures, thought lines (should be ~0 with the prefill).

## Stopping condition

One A100 session. If the 26B does not start under vLLM in FP8 (a recorded error), one retry in bitsandbytes 4-bit is the
only change allowed, and it is said. The rows, runtime and bars do not move.

## Result

*(written after the run)*
