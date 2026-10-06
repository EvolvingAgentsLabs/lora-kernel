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
