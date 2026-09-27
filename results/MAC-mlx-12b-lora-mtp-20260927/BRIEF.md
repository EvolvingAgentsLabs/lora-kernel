# MAC — Gemma 4 12B on a MacBook Air M4 (16 GB) with MLX: a hot-swapped LoRA expert and the MTP drafter (pre-registered 2026-09-27)

**Why.** The user, 2026-09-27: `gemma4:12b-mlx` runs very well on their MacBook Air M4 16 GB — can the same machine run the
base, **a LoRA switched per request** and **speculative decoding** together, as F0 showed vLLM can on an L4? **Inference on
the user's machine by the user's explicit exception** to the Colab-only rule (confirmed 2026-09-27); nothing is trained here.

**What [read] before building.** `mlx_lm.server` reloads the whole model when a request names another adapter, and mlx-lm
cannot load the 12B (`gemma4_unified`); **mlx-vlm 0.7.3** loads it and ships Gemma 4's MTP drafter
(`gemma4_unified_assistant`). So `examples/mac/mlx_spec_lora.py` loads the base once (`mlx-community/gemma-4-12B-it-4bit`,
already in the user's cache), wraps every projection the adapter targets in `HotLoRA` (all adapters resident, one active,
$y = Wx + s\,B(Ax)$), and switches experts by pointer.

**The run.** Base 4-bit + the expert LoRA `wiki12b` (B3, trained on the bf16 12B, applied here over 4-bit weights) + the
drafter `google/gemma-4-12B-it-assistant`. 6 of the expert's prompts, 4 general; greedy; 160 tokens; each of
{base, wiki12b} × {no SD, MTP}.

**Readings, written first.**

| question | answered by |
|---|---|
| does the LoRA act over 4-bit MLX weights? | G1 analogue: the expert's text differs from the base's on its own prompts |
| does the MTP drafter speed the 12B up on this Mac, with and without the LoRA? | generation tokens/s, SD vs no SD; accepted tokens per round |
| is the output unchanged? | identical texts, SD vs no SD, same expert — read as in F0: a mismatch is a finding only once numeric drift is ruled out |
| is the swap hot? | switch time; base → expert → base returns the base's exact text |
| does it fit? | peak memory against 16 GB |

Not comparable, said: MLX 4-bit against vLLM FP8/bf16 is another experiment; one adapter; 10 prompts — a spike.

## Result **[ran]** 2026-09-27 — the hot swap works and fits; on this Mac the MTP drafter does not pay with the LoRA on

MacBook Air M4 16 GB, mlx-vlm 0.7.3, `mlx-community/gemma-4-12B-it-4bit`, `google/gemma-4-12B-it-assistant`
(`mac.json`, `run.log`). Loads: base 5.9 s, the LoRA attached to 328 projections in 1.0 s, the drafter 23 s (download).

**What works [ran]:**
- **The LoRA acts over 4-bit MLX weights**: 6/6 of the expert's texts differ from the base's; it walks the wiki as trained.
- **The swap is hot**: switching experts takes **2.9 µs** (a pointer), and base → expert → base returns the base's exact text.
- **It fits**: peak memory **8.4 GB** of 16. The LoRA costs ~7 % of speed (13.8 → 12.9 tok/s).

| expert / prompts | tok/s, no SD | tok/s, MTP | speed-up | identical |
|---|--:|--:|--:|--:|
| base / domain | 13.8 | 27.0 | ~~1.96×~~ **void** | 3/6 |
| base / general | 14.1 | 17.6 | **1.25×** | 1/4 |
| LoRA / domain | 12.9 | 11.8 | **0.92×** — slower | 2/6 |
| LoRA / general | 13.0 | 13.5 | **1.04×** | 2/4 |

**Read where it happens — two instrument faults, both said:**
1. **The base/domain row is void.** Given the wiki's system prompt, the *base* model in MLX degenerates into a loop of
   `<|channel>thought` tokens on all 6 prompts, with and without the drafter; a loop is trivial to draft, so its 1.96× is
   the loop's, not a speed-up. (vLLM's base on the same prompts writes a real walk — F0 — so this is the MLX rendering
   of Gemma 4's template with a system turn, to be found; the LoRA expert, trained on that prompt, walks it correctly.)
2. **The accepted-per-round column is not reported**: mlx-vlm resets the drafter's counters on each generation and the
   runner sliced them as if cumulative — only the first prompt was read. Fixed for the next run (`mlx_spec_lora.run`).

**Reading.** On this Mac, today: base + hot-swapped LoRA experts, yes — fast, exact, in half the memory. Speculative
decoding with the native MTP drafter: a modest 1.25× on the base on clean text, and **no gain with the LoRA on (0.92–
1.04×)** — the same misalignment F0 measured on vLLM (the drafter does not predict what the LoRA makes the target write),
worse here because a failed draft costs relatively more on a laptop's memory bandwidth. What would change it: a drafter
aligned to the LoRA'd target (the user's strategies A–D), measured first where it is cheapest to train (Colab).
