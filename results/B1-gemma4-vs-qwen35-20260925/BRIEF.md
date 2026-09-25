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
- ~~**A TIE KEEPS QWEN.** The family is decided; a switch would re-release every member and re-open every
  number measured on Qwen — it has to buy something measurable.~~
- **A TIE CHOOSES GEMMA — the user's decision, 2026-09-25, before any stage ran:** the user's whole
  development stack targets Gemma 4, so parity is enough; the cost of re-releasing the Qwen members is
  accepted. A tie = neither `withlib-gemma vs withlib-s<k>` pair is a regression.
- **GEMMA LOSES** if either Qwen seed beats it (a REGRESSION on either pair) — then Qwen stays and the
  user decides whether stack alignment is worth a measured loss.

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

## Stage 1, attempt 1 **[ran]** 2026-09-25 · VOID — the harness, not a model

The control was chosen wrong: `Qwen3.5-4B`'s adapters are applied by vLLM only after `rekey` (D2), which
`lora_matrix` applies to the subject, not the control — so the control's G2 read "identical to the base" and
the run is void as the instrument says. And Gemma's in-process G1 failed in 67 s for a reason that stayed on the
VM: the chain did not fetch `run.log` (now it does). Attempt 2: the instrument's own control
(`Qwen/Qwen2.5-3B-Instruct`, applied without rekey **[ran]** P26/P33). Redesign count of this stage: 0 — the
gates and their reading are unchanged; the control is the instrument's default.

## Stage 1, attempt 2 **[ran]** 2026-09-25 · the control valid, Gemma's G1 lost to my omission

Control `Qwen2.5-3B-Instruct` valid (G1 and G2 applied). Gemma's in-process G1 raised peft's
`ValueError: Target module Gemma4ClippableLinear(...)` (`run_attempt2_tiny_no_exclude.log`): `tiny_adapter`
targets modules BY NAME, and the towers reuse `q_proj`/`k_proj`/…; the tower exclusion had been added to
`s4_train` and not to `tiny_adapter`. That is a harness omission, not a fact about Gemma — the reading
"cannot be trained this way" is not taken as the answer. Attempt 3: the same exclusion in `tiny_adapter`
(`tests/test_gemma_towers.py` holds the rule). Redesign count of the stage: 0.

## Stage 1, attempt 3 **[ran]** 2026-09-25 · PASSED — Gemma 4 E4B trains a LoRA and vLLM serves it applied

Control `Qwen2.5-3B-Instruct`: G1 and G2 applied — the procedure is valid. Subject `google/gemma-4-E4B-it`: G1
in process passed (`lora_B` moved, the output changed) with the vision/audio towers excluded; G2 passed — vLLM 0.30
serves the adapter and its text differs from the base's. **P29's block is lifted**, for the reason
[peft#3129](https://github.com/huggingface/peft/issues/3129) documents. Stage 2 is bought.

## Stage 2 result **[ran]** 2026-09-25 · the untrained Gemma already walks — NAVIGATION IS STILL THE GAP

One L4, W9's evaluation set, W9's arms and verdict code, `gemma_wiki_stage1.json`. Headline (40), verified:

| | Gemma 4 E4B, untrained | Qwen3.5-4B, untrained (W9 stage 1) | Qwen + trajectory LoRA (s0 · s1) |
|---|--:|--:|--:|
| `nolib` | 0 | 0 | — |
| `base-reads` | **40** | 29 | — |
| `base-walks` | **19** | 0 | 35 · 35 |

Paired on the same rows: Gemma's `base-walks` against Qwen's **19 : 0**; against Qwen's trained seeds 0 : 16 and 2 : 18
(it loses). By hops, Gemma walking untrained: 1-hop 7/21, 2-hop 9/24, 3-hop 10/16. Its misses: 28 answers with no
citation, 7 citing a statement that does not hold the value — typically stopping one hop early (the supplier's
page cited for the supplier's town). By W9's verdict as written: **NAVIGATION IS THE GAP → stage 3 bought**, the wiki
member trained on Gemma, W9's corpus and recipe, `train_one --seed 0`.
