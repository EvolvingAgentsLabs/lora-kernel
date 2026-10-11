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

## Run log

- **Attempt 1 — the server did not start, nothing scored** (`attempt1_vllm.log`): vLLM 0.30's engine failed compiling the
  26B MoE in FP8 on the A100 — `torch._inductor ... AssertionError: auto_functionalized was not removed`. Not memory, not
  an unsupported model: the compile step. **Fix, an engine flag, not the quantisation:** `wiki_arm --enforce-eager`
  (no compile, no CUDA graphs; slower, the same arithmetic). The rows, runtime, FP8 and bars do not move.
- **Attempt 2 — the server did not start either** (`attempt2_vllm.log`): with eager mode the engine reaches the FP8 matmul
  and fails in `cutlass_scaled_mm_sm80_epilogue` — vLLM's W8A8 FP8 kernel does not run on the A100 (sm80, Ampere); FP8
  wants an H100, which Colab refuses this account (quota, PAIR1). **By the stopping condition written first: one retry in
  bitsandbytes 4-bit**, the only change allowed (`--quantization bitsandbytes`), eager kept. If it does not start, the run
  is recorded as blocked by the serving engine, not as a result.
- **Attempt 3 (bitsandbytes 4-bit, eager) — not run: Colab refused the A100 three times (quota, 2026-10-04 11:15–11:45),
  after a day of A100 sessions** (`S_attempt*_rejected.log`). TEACH0 has **no result**; the retry runs when the quota
  returns, unchanged.
- **Attempt 4 — the same bitsandbytes 4-bit run, on an L4 (2026-10-05):** the A100 was refused again the next morning
  (quota spent on the previous day's A100 sessions). A provider change, declared: the 26B in 4 bits is ~15 GB and fits the
  L4's 24 GB with room for the KV cache; FP8 (~26 GB) would not fit it. Rows, runtime, quantisation and bars unchanged.

## Result [ran] — BLOCKED BY THE SERVING ENGINE: no score, as the stopping condition wrote

- **Attempt 4 (L4, 2026-10-05)** got a card and the server refused the configuration: vLLM 0.30 has **no `bitsandbytes`
  quantisation method** (`Unknown quantization method: bitsandbytes`; `attempt4/vllm.log`). With FP8 failing on the A100's
  sm80 (attempt 2) and 4-bit bitsandbytes absent from this vLLM, the brief's one allowed retry is spent: **TEACH0 is
  recorded as blocked by the serving engine, not as a result.** Whether the 26B is a teacher stays unanswered.
- **What vLLM 0.30 does list, for a new brief if one is wanted:** `experts_int8` — the MoE's experts quantised to int8 at
  load (~23 GB for the experts plus ~6 GB dense: an A100 40 GB, not an L4), or a pre-quantised AWQ/GPTQ checkpoint of
  the 26B if one exists. Either is a new instrument under its own brief — not a fifth attempt of this one.
- **Context [read]:** Google's model card reports τ²-bench (average over 3) at 68.2 % for the 26B-A4B, 69.0 % for the 12B
  and 76.9 % for the 31B (`docs/tau2/TEACHER-TERMS.md` on branch `tau2-t0-20261005`) — on that card's own harness, the
  26B is not ahead of the 12B, which PAIR0/PAIR1 already showed buys no accuracy here.
