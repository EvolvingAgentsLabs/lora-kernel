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
