# C0 — does a drafter ALIGNED to the expert give back the speed the LoRA took? (pre-registered 2026-09-27)

**Why.** F0 **[ran]**: with the expert LoRA on, Gemma 4's native MTP drafter accepts far less on the expert's own ground
(position 0: 0.98 → 0.58; 2.73× → 1.74×) — it reads the target's activations but does not predict what the LoRA makes the
target write. The user's brief proposes aligning a drafter to the LoRA'd target (strategies A–D, most needing training).
**The cheapest test of that hypothesis needs no training:** a drafter aligned to this expert already exists — the E4B
member trained on the same W9 corpus (B1 `wiki-walks-s1`), whose drafts the 12B + LoRA accepted at **α 0.898 offline**
(B4 **[ran]**). vLLM puts no LoRA on a drafter, so the member is **merged into its weights** (`training/harness/merge_lora.py`,
$W' = W + \tfrac{\alpha}{r}BA$) and served as a plain draft model (`method: draft_model`, FP8). This is strategy C built
from what exists.

**What.** `spec_lora_spike --quantization fp8 --configs nospec,mtp,draft_e4b` on one L4 — the same 12B + `wiki12b`, the
same prompts as F0, batch 1 and 8.

**Readings, written first.**

| check | reading |
|---|---|
| the merged E4B does not fit beside the 12B on an L4, or vLLM refuses a Gemma 4 draft model | recorded with its error; the test moves to an A100 |
| `draft_e4b` on `lora/domain`: acceptance **above MTP's** (α 0.31 in F0) | alignment buys acceptance, as the brief assumes |
| …and speed-up **above MTP's 1.74×** | an aligned drafter pays even at the E4B's cost per draft → strategy C holds for this expert |
| acceptance up, speed-up not | the E4B is too expensive a drafter here (FOUNDATIONS §6.4: $c$ too high) → align a *cheap* drafter (A/B/D) |
| acceptance not up | alignment by corpus is not what the drafter lacks — rethink before training anything |

Beside: the same on `base/*` and `lora/general` (the aligned drafter should lose there — it was trained on the wiki).
Output identity is F0b's question, not this run's.

## Attempts **[ran]** 2026-09-27 — hardware, not the question

- **L4, FP8** (`spike_l4.json`): `nospec` and `mtp` ran and reproduce F0 (MTP with the LoRA on its domain **1.74×**,
  α 0.32); the merge worked (258/258 projections); **`draft_e4b` did not fit** — the 12B in FP8 takes ~14 GB and the merged
  E4B, carrying its per-layer embedding tables and its vision/audio towers, OOMs beside it on 22 GB (`vllm_l4.log`).
- **A100, FP8** (`spike_a100_fp8_failed.json`): **vLLM's online FP8 does not run on Ampere** — every server failed in
  `cutlass_scaled_mm_sm80` (`vllm_a100.log`). In bf16 the 12B (~24 GB) and the E4B (~16 GB) do not fit 40 GB together.
- **H100**: refused over quota.
- **Next, A100 with the 12B in bf16 and the drafter in 4-bit (`--draft-quantization bitsandbytes`)**, all three configs on
  the same card and precision so the speed-ups stay comparable with each other (not with the L4's numbers).

## A100, 12B in bf16 **[ran]** 2026-09-27 — MTP clears the brief's bar with the LoRA on; the aligned drafter is still blocked by hardware

`spike_a100_bf16.json`. All three configs on the same card and precision (speed-ups comparable with each other only).

| MTP vs no SD | speed-up b1 | b8 | α | mean accepted len | identical to no SD |
|---|--:|--:|--:|--:|--:|
| base / domain | **2.80×** | 3.18× | 0.785 | 4.14 | 13/16 |
| base / general | 2.60× | 2.02× | 0.537 | 3.15 | 4/8 |
| **LoRA / domain** | **1.92×** | 1.73× | 0.336 | 2.34 | 11/16 |
| LoRA / general | **2.40×** | 1.86× | 0.445 | 2.78 | 5/8 |

(no SD, batch 1: base 46.6 / 48.4 tok/s, LoRA 40.6 / 41.1 tok/s; hot LoRA load 0.23–0.25 s, and **the reloaded LoRA now
writes the same text** — bf16 is steadier than FP8 was on the L4.)

**Reading.** In bf16 on an A100 the native MTP drafter with the LoRA on reaches **1.92× on the expert's domain and 2.40×
on general text** — above the brief's 1.8× bar at batch 1 (1.73× at batch 8). The LoRA still costs acceptance (α 0.79 →
0.34 on the domain), so an aligned drafter has room to add; it does not have to rescue the pair.

**`draft_e4b` did not start:** vLLM's speculative config accepts only pre-quantised formats for a drafter (awq, gptq,
fp8, …), not bitsandbytes. The four routes so far: L4 FP8 → OOM; A100 FP8 → no kernel on sm80; A100 bf16 + 4-bit drafter →
not a drafter format; H100 → quota. Open routes: an H100 (FP8, 80 GB); or an A100 with the drafter pre-quantised to AWQ/GPTQ
(llm-compressor, one calibration pass); or the 12B in a pre-quantised INT4 with the E4B in bf16.
