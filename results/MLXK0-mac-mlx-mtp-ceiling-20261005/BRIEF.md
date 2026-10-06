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

## Result [ran] 2026-10-05 — MARGINAL: base/general 1.21× at best; a round in MLX costs about half of llama.cpp's

One sitting, ~20 min, `mlxk0.json`, `run.log`. Peak memory **8.37 GB** of 16; the expert swap 10 µs, base text restored
exactly; G1 6/6. No speculation: base 13.7 tok/s, base + LoRA 12.8 (domain) / 12.6 (general).

| expert / set | $k$ | speed-up | acceptance | accepted / round | $E$ | implied $C(k)$ | identical |
|---|--:|--:|--:|--:|--:|--:|--:|
| base / general | 1 | **1.21×** | 0.76 | 0.76 | 1.76 | 1.45 | 1/4 |
| base / general | 2 | 1.15× | 0.58 | 1.16 | 2.16 | 1.88 | 1/4 |
| base / general | 3 | 1.02× | 0.49 | 1.48 | 2.48 | 2.43 | 1/4 |
| LoRA / domain | 1 | 1.08× | 0.60 | 0.60 | 1.60 | 1.48 | 3/6 |
| LoRA / domain | 2 | 1.04× | 0.48 | 0.95 | 1.95 | 1.88 | 3/6 |
| LoRA / domain | 3 | 0.88× | 0.36 | 1.07 | 2.07 | 2.35 | 2/6 |
| LoRA / general | 1 | 1.08× | 0.67 | 0.67 | 1.67 | 1.55 | 0/4 |
| LoRA / general | 2 | 1.04× | 0.54 | 1.07 | 2.07 | 1.99 | 1/4 |
| LoRA / general | 3 | 0.94× | 0.45 | 1.35 | 2.35 | 2.50 | 2/4 |
| *base / domain (void: a thought-token loop)* | 1 | *1.53×* | *0.94* | *0.94* | *1.94* | *1.27* | *1/6* |
| *base / domain (void)* | 2 | *1.64×* | *0.87* | *1.74* | *2.74* | *1.67* | *1/6* |
| *base / domain (void)* | 3 | *1.63×* | *0.96* | *2.87* | *3.87* | *2.37* | *3/6* |

$E = 1 +$ accepted per round (measured, not modelled); $C = E / \text{speed-up}$.

**By the table written first: MARGINAL** — base/general reaches 1.21× (k = 1), inside 1.15–1.4×.

**Reading.**
1. **In MLX a round is cheap enough for a drafter to pay**, unlike llama.cpp: a one-token round costs **1.3–1.5** plain steps
   (SPECK0: 2.2–2.4), and each extra drafted token ≈ 0.45 more. The best $k$ is 1 everywhere.
2. **What an aligned drafter could buy, from these numbers:** at $k = 1$, speed-up $= (1 + \alpha)/C(1)$ with
   $C(1) \approx 1.3$–$1.5$. Today's misaligned drafter on the LoRA's domain, $\alpha = 0.60$ → 1.08×. A drafter aligned to
   base-level acceptance on general text (0.76) → ≈ 1.2×; to the 0.94 the drafter reaches on the void row's repetitive text
   → ≈ 1.3–1.5×. The wiki walks are formulaic, so the upper end is plausible but **not measured** — it is exactly what
   training the drafter's LoRA would establish.
3. **Output identity does not hold in MLX's MTP path**: 1/4 to 3/6 texts identical to greedy decoding without speculation,
   with and without the LoRA (MAC showed the same, 1/4 and 2/6). Greedy speculative decoding is exact in principle; here the
   verification forward (batch $k+1$, 4-bit) differs numerically from the single-token one, so near-ties flip and the texts
   diverge from there. vLLM (F0c) and llama.cpp (SPECK0, 46/48) kept identity. **Whether the divergent texts are worse is
   not measured** — before serving a member this way, its gate runs with speculation on.
4. The base/domain rows are MAC's known MLX rendering fault (the base loops on `<|channel>thought` under the wiki system
   prompt); void as a speed-up, still informative for $C$ because the engine's cost does not depend on the text.

**What this changes.** The memory side of the user's design holds (8.4 GB, swap in µs). The speed side is a bet worth at
most ≈ 1.3–1.5× on formulaic domains at $k = 1$ — paid for by one A100 session to train the drafter's LoRA and the MLX
work to put a LoRA on the drafter — and it comes with the identity question above. The user decides.
