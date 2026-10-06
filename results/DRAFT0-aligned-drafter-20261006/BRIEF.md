# DRAFT0 — a LoRA on Gemma 4's MTP drafter, aligned to the 12B with its expert's LoRA on (pre-registered 2026-10-06)

**Why.** The user, 2026-10-06 ("empezá con el drafter alineado"): a 12B with per-expert LoRAs in MLX on their Mac, the
expert's LoRA and a drafter aligned to it switched together. HOTL0 **[ran]** set the numbers: the stock MTP drafter gives
1.47× on the bare 12B and 1.23× with the wiki LoRA on (acceptance 0.76 → 0.67 on general text; 0.60 on the LoRA's own
domain, MLXK0). At $k = 1$ a round costs $C(1) = 1.755/1.40 \approx 1.25$ plain steps on that Mac, so
speed-up $= (1+\alpha)/C(1)$ and the question is $\alpha$ alone: **can a small LoRA on the drafter make it predict what the
LoRA'd target writes?** DistillSpec-style alignment **[read]** (Zhou et al. 2023) says acceptance moves; no one, as far as
we found, has done it per LoRA expert.

**What.** `training/harness/drafter_align.py` (mechanism, formula and gates in its docstring). The drafter
(`google/gemma-4-12B-it-assistant`, 4 layers, every layer reading the target's KV) gets a LoRA (r 16, α 32, on
`q_proj, o_proj, gate_proj, up_proj, down_proj, pre_projection`; fp32 adapter over the bf16 drafter), trained by cross-entropy
to the target's argmax $y_i$ at every position of the model's turns, the target being `google/gemma-4-12B-it` + B3's
`wiki12b-walks-s0` (bf16, frozen). Corpus: the expert's own training corpus (`training/wiki/data/train.jsonl`, W9's, 600
rows, 1,536-token window); 2 epochs, AdamW 2e-4, accumulation 8, seed 0. **Held out:** the 12B+LoRA's own greedy
continuations (160 tokens) of 40 wiki prompts — `eval` and `eval_hard`, 20 each, the first 3 of each being MLXK0's — and of the
4 general prompts; $\alpha$ = the fraction of those positions where the drafter's argmax equals the target's. **Model and
provider:** Colab, one G4 (96 GB) through `chain_serve.sh`, transformers ≥ 5.18 + peft installed by the runner; nothing
on the user's Mac, no API.

**Gates before training — the run stops on any:**
- **GL** — the expert's LoRA acts on the target: the last-position logits of a wiki prompt differ from the bare 12B's by more than 0.5 (B3's adapter is named for the ForConditionalGeneration layout; a text-only class would load it unmatched and silently).

- **G0** — the masked parallel forward used for training equals the drafter called exactly as generation calls it, at 5
  positions including one past the sliding window: same argmax, $\max|\Delta\text{logit}| \le 0.5$.
- **G1** — the stock drafter's offline $\alpha$ on the domain prompts lies in [0.45, 0.75], around the 0.60 the Mac measured.
  Outside it, this instrument does not measure what MLX serves.

**Verdict, written first** (domain $\alpha$, held-out):
- **ALIGNED** — aligned $\alpha \ge 0.85$ **and** ≥ 0.15 over stock → the Mac test is bought next: the drafter's LoRA applied
  in MLX, the expert's and the drafter's switched together, tokens/s against HOTL0's 1.23×.
- **PARTLY ALIGNED** — +0.05 or more, short of that → reported with its projected speed-up; the user decides.
- **NOT ALIGNED** — less than +0.05.
- **VOID** — G0 or G1 failed.
- Beside: general-text $\alpha$ before and after (the drafter's LoRA is meant to be on only with its expert, but a collapse
  there would say it overfit), the loss curve, the projected $k = 1$ speed-ups $(1+\alpha)/C(1)$.

**What it does not answer:** speed on the Mac (the projection uses HOTL0's $C(1)$, and an adapter on the drafter adds its own
cost per round), $k > 1$ (the chained drafts read the drafter's own `post_projection`, trained here only through
`pre_projection` of the next step — not at all), and identity of output in MLX (MLXK0: it does not hold there).

**Stopping condition.** One G4 session; nothing in the corpus, prompts, gates or bars moves after this brief. Redesign
count: 0.
