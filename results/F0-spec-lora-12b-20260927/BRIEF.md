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

**Hardware, as it came (2026-09-27):** the A100 and the H100 were refused over quota (`attempt1_*`, `attempt2_*`). The 12B in
bf16 does not fit an L4, so F0 runs the target in **FP8** (`--quantization fp8`, vLLM's dynamic FP8) on an L4 — the
precision BCCard's EAGLE-3 was trained against. A second unknown, said: the LoRA was trained on bf16 weights and is
served over FP8 ones; G1 says whether it is applied, and every comparison is FP8 against FP8.

## Result **[ran]** 2026-09-27 (session 1) — the combination runs; the native MTP drafter keeps 1.7–2.1× with a LoRA on; the output is NOT yet shown identical

vLLM 0.30.0, `gemma-4-12B-it` **FP8** on one L4, the expert LoRA `wiki12b` (B3), k = 4, temperature 0, 16 expert prompts
and 8 general, `max_tokens` 160 (`spike.json`).

**What works [ran]:** vLLM serves the 12B + a LoRA **with the MTP drafter and with EAGLE-3** — both start, G1 applied in
both (3/3); a LoRA **loads at runtime in 0.23–0.28 s with the drafter running**, no restart.

| | set | tok/s b1 | **speed-up b1** | speed-up b8 | α | mean accepted len | acceptance at position 0 · 1 · 2 · 3 | identical to no-SD |
|---|---|--:|--:|--:|--:|--:|---|--:|
| no SD | base / domain | 16.5 | — | — | — | — | — | — |
| **MTP** | base / domain | 45.2 | **2.73×** | 2.95× | 0.790 | 4.16 | .98 · .88 · .83 · .46 | 8/16 |
| **MTP** | base / general | 41.2 | **2.41×** | 1.86× | 0.530 | 3.12 | .79 · .58 · .43 · .32 | 0/8 |
| **MTP** | **LoRA / domain** | 27.6 | **1.74×** | 1.48× | 0.313 | 2.25 | .58 · .34 · .20 · .13 | 4/16 |
| **MTP** | LoRA / general | 34.3 | **2.13×** | 1.90× | 0.429 | 2.72 | .71 · .47 · .32 · .21 | 1/8 |
| EAGLE-3 (BCCard) | base / domain | 19.4 | 1.17× | 1.01× | 0.136 | 1.55 | | |
| EAGLE-3 (BCCard) | base / general | 27.3 | 1.59× | 1.40× | 0.245 | 1.98 | | |

**Readings.**
1. **The native MTP drafter is the one to build on**, not the public EAGLE-3: on the same prompts it accepts 5.8× as
   much on the domain (α 0.79 against 0.14) — the brief's choice of EAGLE-3 as the main drafter is contradicted here.
2. **The LoRA costs the drafter, and most on the expert's own ground:** position-0 acceptance on the domain falls from
   0.98 to 0.58, the speed-up from 2.73× to **1.74×** — just under the brief's 1.8× bar; on general text 2.41× → 2.13×. A
   drafter that reads the target's activations *sees* the LoRA, and still does not predict what the LoRA makes the target
   write. That is exactly the gap the brief's strategies B, C, D exist to close — now measured, not assumed.
3. **The mandatory test does not pass as run, and is not yet read:** at temperature 0, spec decode's text equals no-SD's
   in 8/16, 0/8, 4/16, 1/8 cases, diverging at near-ties ("booking time" / "booking"). vLLM without batch-invariant mode
   is not deterministic across batch shapes — the **same** LoRA reloaded at runtime, no drafter, also wrote a different
   text — so this run cannot tell a spec-decode fault from ordinary numeric drift. Next: the same comparison under
   `VLLM_BATCH_INVARIANT=1` (as vLLM's own LoRA × SD test runs), with a no-SD-vs-no-SD control. Until then *identical
   output* is **not established**.
