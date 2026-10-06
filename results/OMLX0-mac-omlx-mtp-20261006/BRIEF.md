# OMLX0 — does a newer MLX stack (mlx-vlm 0.7.6, oMLX) make the MTP drafter pay on the Mac? (pre-registered 2026-10-06)

**Why.** The user, 2026-10-06, pasted a forum report and asked whether it is real and reproducible, and whether to switch
to oMLX (`jundot/omlx`, Apache 2.0, an OpenAI-compatible MLX server on mlx-lm + mlx-vlm 0.7.4 + its own kernels): *"the
gemma-4-12b-it-4bit (mlx-community) runs around 18 tok/s without MTP but up to 28 tok/s with the assist model; acceptance
55–75 %; best around 3 token draft block size"* — on a MacBook Pro M4, oMLX 0.4.2.dev2. That is ≈ 1.55×; MLXK0 **[ran]** on
the user's MacBook Air M4 with mlx-vlm 0.7.3 measured **1.21×** at best (base/general, block 2) and 1.15× at block 3, with
acceptance 0.58–0.76 — the same acceptance, so the claimed gain would be a cheaper round:
speed-up $= E/C$, $E = 1 + $ accepted per round.

**Arms, one sitting, the user's Mac** (approved 2026-10-06, ~25–30 min), base 12B only (`mlx-community/gemma-4-12B-it-4bit`,
`google/gemma-4-12B-it-assistant`), MLXK0's 4 general prompts, greedy, 160 tokens, no speculation and `draft_block_size`
2, 3, 4:
- **A0** — mlx-vlm 0.7.3, MLXK0's runner (the same-sitting control: the Air's thermal state is part of the number).
- **A1** — mlx-vlm 0.7.6, the same runner (attribution: the library's MTP path).
- **B** — oMLX, served, MTP off and on at the block sizes it exposes, the same prompts through its OpenAI endpoint; tokens/s
  from the server's own counts where reported, else completion tokens over wall time of the decode (said which).
- **C (zero GPU)** — read oMLX's source: does it load a LoRA adapter, and can it switch one per request without reloading
  the model? (`mlx_lm.server` reloads, which is why `HotLoRA` exists.)

**Verdict, written first.**
- **REPRODUCED** — B (or A1) reaches ≥ 1.4× on base/general at its best block, with A0 in the same sitting at ≤ 1.25×: the
  gain is real on this Mac and attributable to the stack that shows it.
- **NOT REPRODUCED ON THIS MAC** — every arm < 1.3×: the report's gain does not carry to the Air (or to these prompts).
- In between: **PARTIAL**, with the numbers.
- **Switching** is recommended only if REPRODUCED **and** C finds per-request LoRA without a reload — the members are LoRAs;
  an engine that cannot hot-swap one does not serve them, however fast. Otherwise the gain is ported, not the engine.

**Stopping condition.** One sitting; if oMLX does not install or serve within ~10 minutes, B is reported as not run and
A0/A1/C stand. Redesign count: 0.

## Attempt 1 — aborted, no result (2026-10-06)

A0 stalled after its no-speculation pass (13.6 tok/s) — the Mac was swapping: 7.0 of 8 GB of swap in use and 14 % of memory
free with the 12B resident beside a Docker VM and a browser (`sysctl vm.swapusage`, `memory_pressure`). A speed measured
while swapping measures the disk; both runners were stopped and their partial records deleted. Nothing is read from it.

## C [read] — oMLX does not serve LoRA adapters, and its MTP gain is a portable attention kernel

- `omlx/model_discovery.py:1822` (commit `79f4488`, 2026-10-06): adapter directories are skipped with *"oMLX does not
  support LoRA/PEFT adapters"*. **Switching to oMLX as the members' engine is ruled out by the brief's own rule**, whatever B
  would show.
- The Gemma 4 MTP speed-up is plausibly `omlx/patches/gemma4_verify_attention.py` + `gemma4_verify_kernel.py` (Apache 2.0):
  Gemma 4's global layers have head_dim 512, which MLX fuses only at one query row, so every verify forward of $k+1 \ge 2$
  rows falls to an unfused pass whose cost grows with context — *"what makes MTP verify cycles lose to plain decoding on
  low-accept content"*. The patch wraps `mlx_vlm.models.gemma4.language.Attention.__call__` with a multi-row vector kernel
  built at runtime through `mx.fast.metal_kernel` (no native build), gated to backbones without KV sharing — the 12B
  qualifies (`num_kv_shared_layers = 0`, `global_head_dim = 512`); the E4B does not. It touches attention only, so it
  composes with `HotLoRA` (projections). Its own note: near-tie verify rows can flip, as MLXK0 already saw.

**Re-planned before the rerun (redesign 1, said):** arm B (the oMLX server) is dropped — C already decides the switch; in
its place **A2 = mlx-vlm 0.7.3 + oMLX's two patch files applied in-process**, the same runner. Arms A0, A1, A2, verdict
table unchanged (REPRODUCED now reads "A1 or A2"). The rerun waits for the Mac to have memory free.
