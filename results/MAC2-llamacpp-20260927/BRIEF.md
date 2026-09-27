# MAC2 — the same Mac, llama.cpp instead of MLX: the E4B loads? the LoRA applies? which drafter pays with the LoRA on? (pre-registered 2026-09-27)

**Why.** The user asked whether to run the Mac track on vLLM or llama.cpp. vLLM is CUDA-first; on the Mac the
measured alternative is MLX (MAC **[ran]**): the hot swap works in 2.9 µs, but **the MTP drafter gains nothing with the
LoRA on (0.92–1.04×)**. llama.cpp offers what MLX does not **[read]** `llama-server --help`, build 11146:
- a separate draft model (`--spec-type draft-simple`, `-md`). That is our pair: an E4B draft for the 12B, with byte-identical
  vocabularies (B2).
- Gemma 4's MTP heads (`--spec-type draft-mtp`, `mtp-*.gguf` in the GGUF repos).
- LoRA hot-swap through `POST /lora-adapters`.

The user extended the local-inference exception to llama.cpp for this test (2026-09-27, "si"). Nothing is trained here.

**Model and provider.** Local, MacBook Air M4 16 GB, llama.cpp 0.5.0 (build 11146, Homebrew, Metal). Models:
- `unsloth/gemma-4-12b-it-GGUF` Q4_0 and its `mtp-gemma-4-12b-it.gguf`;
- `ggml-org/gemma-4-E4B-it-GGUF` Q4_0.

Adapters, all from the wiki corpus, the same ones as MAC and C0, converted with `convert_lora_to_gguf.py`:
- `wiki12b-walks-s0` (B3) on the 12B;
- `wiki-walks-s1` (B1) merged into the E4B's weights (`merge_lora.py`) and quantized to Q4_0, as the draft, because
  llama.cpp puts no LoRA on a draft model **[read]**.

**Prompts.** MAC's exact sets: 6 of the expert's prompts (3 `eval`, 3 `eval_hard`, wiki system prompt) and 4 general
ones, rendered with the same chat template. Greedy, 160 tokens.

**Arms, in order. Each step can stop the rest.**

| step | question | reading | stops the test if |
|---|---|---|---|
| 1 | does the E4B GGUF load on this build? | load, one completion | it does not load: the pair is off llama.cpp; steps 2 and 4 still run on the 12B |
| 2 | does the 12B LoRA GGUF act? | G1 analogue: the expert's text ≠ the base's on 6 domain prompts (≥ 4 of 6) | fewer than 4 differ: the conversion is wrong; steps 3–4 on the LoRA are void |
| 3 | which drafter pays with the LoRA on? | tok/s with speculation ÷ tok/s without, per {base, LoRA} × {domain, general}; draft acceptance from the server's `timings` | — |
| 3a | MTP (`draft-mtp`) | directly comparable to MAC's MLX row | |
| 3b | the pair (`draft-simple`, E4B+wiki merged, Q4_0) | the aligned draft vLLM could not serve (C0) | Metal out of memory: E4B at Q3_K_M instead, said so; if that fails too, the answer is "not on 16 GB" (the Mac mini question) |
| 4 | is the swap hot? | `POST /lora-adapters` scale 0 ↔ 1: time, and base text restored exactly | |

**Verdict, written first.** llama.cpp becomes the `edge` engine if the LoRA acts (step 2), the swap is hot and exact
(step 4), and **some drafter gives ≥ 1.3× with the LoRA on, on the expert's domain**. MLX's best there was 0.92×; 1.3× is
the least a laptop user would notice. Otherwise MLX stays the `edge` engine and llama.cpp is recorded with the reason.

**Not comparable, said.**
- llama.cpp Q4_0 is not MLX 4-bit, and neither is vLLM bf16. Only ratios within an engine are read.
- One adapter pair and 10 prompts: a spike, not a suite.
- Output identity under speculation is reported, not gated (F0b: not testable without batch-invariance).

## Result **[ran]** 2026-09-27 — the LoRA and the swap work; no drafter pays on 16 GB; **MLX stays the `edge` engine**

MacBook Air M4 16 GB, llama.cpp build 11146 (Metal). Files: `mac2.json`, `run.log`, `server_*.log`.

| step | result |
|---|---|
| 1. does the E4B GGUF load? | **yes**: it answers coherently at 28.4 tok/s. The July failure (capability-kernel) is fixed in this build |
| 2. does the 12B LoRA GGUF act? | **yes: 6/6** domain texts differ from the base's. The expert walks the wiki as trained; the base writes one search call and stops |
| 4. is the swap hot? | **yes**: `POST /lora-adapters` in 3.0 ms on, 1.65 ms off; base text restored exactly; the global switch gives the same text as the per-request `lora` field |

**Step 3: speculative decoding, tok/s with ÷ without.**

| drafter | expert / prompts | tok/s without | tok/s with | speed-up | acceptance | output identical |
|---|---|--:|--:|--:|--:|--:|
| MTP | base / domain | 12.6 | 11.0 | 0.87× | 0.77 | 6/6 |
| MTP | base / general | 12.8 | 8.4 | 0.66× | 0.53 | 4/4 |
| MTP | **LoRA / domain** | 12.1 | 6.3 | **0.52×** | 0.37 | 6/6 |
| MTP | LoRA / general | 11.2 | 7.8 | 0.70× | 0.46 | 4/4 |
| the pair (E4B + wiki, merged) | — | | | **did not run** | | |

The pair ran out of Metal memory (`kIOGPUCommandBufferCallbackErrorOutOfMemory`) on its first prompt, in three
configurations:
- the draft at Q4_0 (5.2 GB), as registered — the traceback is in `run.log`;
- the draft at Q3_K_M (4.9 GB), the registered fallback — `server_pair.log`;
- REDESIGN 1, after the verdict: the draft's `per_layer_token_embd` (2.31 of its 4.83 GB, a lookup table) on the CPU —
  `server_pair_ple_cpu.log`.

**By the table written first: MLX stays the `edge` engine.** The LoRA acts and the swap is hot and exact, but the best
drafter with the LoRA on its domain gives 0.52×, below the 1.3× bar.

**Reading.**
1. **On this Mac, llama.cpp's MTP costs more than it saves**, even without the LoRA: 0.66× on general text, where MLX gave
   1.25× (MAC). With the LoRA on, the acceptance, 0.37, is vLLM's (0.34, C0): MTP does not predict what the LoRA makes
   the target write, in any engine.
2. **Output identity holds under speculation in llama.cpp**: 20 of 20 texts are identical with and without MTP. That is
   what vLLM on FP8 could not establish (F0b).
3. **The aligned pair does not fit in 16 GB with the 12B.** That question moves to a Mac mini with 24 GB or more, or to a
   smaller target. Whether a draft aligned with the expert pays on a Mac stays **unmeasured**.
4. Redesign count: 1. The stopping condition was the registered fallback; the extra arm was run once and recorded.

**What this changes.** vLLM stays `server` and MLX stays `edge` (the pointer swap in 2.9 µs; access to the graph from
Python). llama.cpp is recorded as ready to serve a hot-swapped LoRA expert on the Mac: it loads the E4B, the swap is in
milliseconds, and spec decode's output is exact. It is also the only engine here that runs the separate-draft pair. That
arm is the one to run first on a larger Mac. PR-2 of the brief (a LoRA in the draft context) waits on it: an aligned
draft has not yet been shown to pay.
