# B1 — Gemma 4 E4B against Qwen3.5-4B as the wiki member's base (pre-registered 2026-09-25)

The user asked for a comparison. The family is decided (Qwen 3.x, `CLAUDE.md` §0), and the rule for a
candidate base is *run the gate against it, don't shop*: so the comparison is bought as a sequence in
which each stage can stop it, and **switching needs a win — a tie keeps Qwen.**

**Why now.** Two blockers were recorded against Gemma 4 and both may have moved. P29 **[ran]** 2026-09-14:
peft refused `Gemma4ClippableLinear`. Since then the cause is documented **[read]** — the class wraps
only the vision and audio towers' projections, the language model's are plain `nn.Linear`, and a LoRA
scoped away from the towers is the known fix ([peft#3129](https://github.com/huggingface/peft/issues/3129)).
And Gemma 4 ships its own multi-token-prediction drafter, which vllm-metal v0.28.0 (2026-09-22) serves
as a speculative method **[read]** ([vLLM blog](https://vllm.ai/blog/2026-09-22-vllm-metal-v0-28-0)) —
relevant to milestones 3–4 and to a Mac target, not measured here.

**What changed in code, zero GPU [ran].** `training/s4_train.py::towers_to_exclude`: when — and only when —
a model contains `Gemma4ClippableLinear`, the LoRA excludes the vision/audio towers and projector; every
other base's targets are unchanged (Qwen's included). `training/harness/tiny_adapter.py` skips `audio` and
`multi_modal` modules beside the `vision` ones it already skipped.

## Stages, in the order bought

| # | stage | session | stops the comparison if |
|---|---|---|---|
| 1 | **substrate gate** — `lora_matrix --control Qwen/Qwen3.5-4B --subject google/gemma-4-E4B-it`: a tiny adapter trained in process (G1: `lora_B` moved and the output changed), then served by vLLM (G2: served text differs from the base) | one A100 | the control is not applied → **VOID**; Gemma's adapter is not applied when served → **Qwen stays** (P29 still holds, now for a known reason) |
| 2 | **headroom on W9** — the bare Gemma 4 E4B on W9's evaluation set, `nolib` · `base-reads` · `base-walks`, paired by row with Qwen's stage-1 records (0 · 29 · 0 of 40) | one L4 | `nolib` > 10 % → **VOID** for this base (it knows the answers); `base-walks` ≥ 85 % → **the base alone walks it — no adapter needed on Gemma**, reported as the finding |
| 3 | **the wiki member on Gemma** — W9's corpus and recipe unchanged, one seed | one A100 | training fails, or G1 on the served adapter fails |
| 4 | **scoring** — `withlib-gemma` on the same 67 rows | one L4 | — |

## Verdict — written first

Headline = W9's (40 rows, two hops or more), credit = W9's grader (value right **and** citation verified),
exact two-sided sign test on discordant pairs, $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:

- **GEMMA IS PREFERRED** only if `withlib-gemma` beats **each** Qwen seed (`withlib-s0`, `withlib-s1`),
  paired, an improvement against both.
- **A TIE KEEPS QWEN.** The family is decided; a switch would re-release every member and re-open every
  number measured on Qwen — it has to buy something measurable.
- **GEMMA LOSES** if either Qwen seed beats it.

Beside, never folded in: stage 2's three arms against Qwen's; value-right beside credit; calls, refusals,
the continued-listing failure W9 stage 1 found on Qwen (does Gemma's base write a verb after a result?);
one Gemma seed against two Qwen seeds, said as such (W5e: two draws of one recipe can disagree on 25 of 67).

## Models, provider, cost

`google/gemma-4-E4B-it` and `Qwen/Qwen3.5-4B` (Hugging Face weights, bf16) on vLLM 0.30 on Colab; no API
provider. Thinking off in every render. **Ceiling: 2 A100 + 2 L4**, each stage only if the one before it did
not stop the comparison. **Not measured:** the MTP drafter (stage 1 serves no speculative method), a Mac
runtime (vllm-metal's tested configurations are 32 GB and up; this Mac has 16 GB), Gemma 4's other sizes.

## Launch — stage 1

```bash
R=results/B1-gemma4-vs-qwen35-20260925
GPU=A100 BRANCH=w9-atomic-statements-20260924 RUN_DIR=$R MODULE=training.harness.lora_matrix \
  MARGS="--control Qwen/Qwen3.5-4B --subject google/gemma-4-E4B-it" RESULTS_NAME=lora_matrix.json \
  BASE=google/gemma-4-E4B-it TRAINDEPS=1 SKIP_ADAPTERS=1 SESSIONS=1 training/harness/chain_serve.sh
```
