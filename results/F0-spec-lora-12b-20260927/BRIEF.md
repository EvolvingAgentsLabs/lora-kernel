# F0 — a LoRA expert on Gemma 4 12B with speculative decoding: what vLLM does today (pre-registered 2026-09-27)

**Why.** The user's brief of 2026-09-27 (*expertos LoRA + speculative decoding en Gemma 4 12B*): one 12B server, N
domain experts as LoRAs, each with a drafter, hot-swappable per request, speculative decoding on for all. Its phase F0
asks the cheap questions first. Milestone 4 here measured the pair's *acceptance* offline (B4) and never ran speculative
decoding for real, so there is no wall-clock number yet.

**What was verified before writing this [read, 2026-09-27].** LoRA + speculative decoding in vLLM V1 landed in PR #21068
(merged 2025-11-08) and `tests/v1/e2e/spec_decode/draft_model/test_lora.py` checks **EAGLE-3 + LoRA on Qwen3-1.7B**
(equal outputs with and without spec decode, batch-invariant mode) — not Gemma 4. PR #55628, which the brief cites as
the verification, was **closed unmerged**; the docs' feature matrix still marks LoRA × SD ❌. Google ships an MTP drafter
for the 12B, `google/gemma-4-12B-it-assistant` (`Gemma4UnifiedAssistantForCausalLM`, 4 layers reading the target's
activations and KV); vLLM serves it as `method: mtp`. A public EAGLE-3 exists, `BCCard/MoAI-gemma-4-12B-it-speculator.eagle3`
(Apache-2.0, trained on-policy against the **FP8** 12B on ~450k general prompts). vLLM here: 0.30.0.

**The one change of order against the user's brief, and why.** The brief makes the native MTP drafter a baseline only.
It reads the target's activations exactly as EAGLE-3 does, so it too *sees* the active LoRA — it is strategy A with no
training at all. If it holds its speed with a LoRA on, most of F2–F6 is not needed; so it is measured first, beside EAGLE-3.

**What (one A100, `training/harness/spec_lora_spike.py`).** `gemma-4-12B-it` bf16 + the expert LoRA already trained here,
`wiki12b-walks-s0` (B3, W9's corpus), served three ways: no spec decode · + MTP assistant (k = 4) · + BCCard EAGLE-3
(k = 4). In each: G1; 16 of the expert's own prompts (W9 + hard band, the member's prompt) and 8 general ones, as the
base and as the LoRA; vLLM's own counters for acceptance (α, mean accepted length, per position); tokens/s at batch 1
and 8; outputs at temperature 0 against `nospec`'s; a LoRA loaded and unloaded at runtime with the drafter running.

**Readings, written first.**

| question | answered by |
|---|---|
| does vLLM serve a LoRA on the 12B with the MTP drafter / with EAGLE-3 at all? | the server starts, G1 applied — or the error, recorded |
| is the output unchanged? (the brief's mandatory test) | identical texts at temperature 0, batch 1 — a mismatch is read where it happens: vLLM is not batch-invariant by default, so a mismatch in `nospec` vs spec at batch 1 is a finding, not noise, only if it recurs |
| does the LoRA cost acceptance? | α and mean accepted length, LoRA vs base, same drafter, same prompts |
| is it worth it? | speed-up in tokens/s vs `nospec`, batch 1 and 8 — the brief's bar is ≥ 1.8× |
| hot swap with the drafter on? | runtime load/unload of a LoRA, seconds, same text as the preloaded one |

Not in F0, said: training any drafter (A, B, C), speculators' hidden-state extraction with a LoRA (needs a speculators
install and a training run — F3), the 31B distillation, new domains. One seed, one adapter, 24 prompts: a spike, not a bench.
