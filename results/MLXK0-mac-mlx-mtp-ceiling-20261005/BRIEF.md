# MLXK0 — the MTP drafter's ceiling in MLX on the Mac: is a round cheap enough for an aligned drafter to pay? (pre-registered 2026-10-05)

**Why.** The user, 2026-10-05, wants a 12B with an **aligned drafter** in MLX, switching the expert's LoRA and the
drafter's together, without running tight on 16 GB. The design that fits is Gemma's MTP drafter (8.4 GB peak with the 12B,
MAC **[ran]**) with a per-expert LoRA on the drafter. Before training that LoRA: SPECK0 **[ran]** showed llama.cpp's round
costs ≈ 2.2 decode steps even at 97 % acceptance, so no drafter could pay there. This run asks the same of MLX. With
acceptance $\alpha$ and $k$ drafted tokens a round yields $E(\alpha,k) = (1-\alpha^{k+1})/(1-\alpha)$ tokens and costs
$C(k)$ plain steps; speed-up $= E/C$. **An aligned drafter can at most restore the base's acceptance on the expert's
domain**, so the base's speed-up at its own acceptance is the ceiling of what aligning buys.

**What.** `examples.mac.mlx_spec_lora` (MAC's runner) with a block-size sweep: `draft_block_size` ∈ {2, 3, 4} → $k$ = 1, 2,
3 drafted tokens (`MTPDrafterBase.prefer_requested_block_size = True` **[read]**, so the size is honoured), plus no
speculation. Experts: the 12B base and `wiki12b-walks-s0` (B3's adapter, the wiki corpus); sets: 6 wiki prompts (MAC's)
and 4 general ones; greedy, 160 tokens. Acceptance read from mlx-vlm's lifetime counters diffed per request (exact at
batch 1) — the column MAC could not report. **Model and provider:** local, the user's MacBook Air M4 16 GB, mlx-vlm 0.7.3,
`mlx-community/gemma-4-12B-it-4bit`, `google/gemma-4-12B-it-assistant` — approved by the user 2026-10-05, ~20 min.

**Known before running:** MAC's base/domain row degenerated into a `<|channel>thought` loop in MLX (void); it is reported,
not read. The ceiling is read on **base/general**; LoRA/domain gives today's misaligned number.

**Verdict, written first** (best $k$ per row):
- **WORTH ALIGNING** — base/general reaches ≥ **1.4×**: an aligned drafter that restores base-level acceptance on the domain
  would pay a useful margin → train the drafter's LoRA (Colab), then the switching test.
- **MARGINAL** — base/general 1.15–1.4×: aligning would buy at most that; reported, the user decides.
- **NOT WORTH IT ON THIS MAC** — base/general < 1.15×: even a perfectly aligned drafter could not pay enough here.
- Beside: implied $C(k) = E(\hat\alpha,k)/\text{speed-up}$, LoRA/domain today, identical outputs, peak memory.

**Stopping condition.** One sitting, these configs. Redesign count: 0.
