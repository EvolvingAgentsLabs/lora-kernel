# HOTL0 — do the `HotLoRA` wrappers make MTP verification expensive? (pre-registered 2026-10-06)

**Why.** OMLX0 **[ran]**: the base 12B with Gemma's MTP drafter runs at 1.40× ($k = 1$) / 1.47× ($k = 2$) with nothing
attached; MLXK0 **[ran]** measured 1.21× / 1.15× at the **same acceptance** (0.76 / 0.58) with 328 `HotLoRA` wrappers attached
and inactive. The round got cheaper by ~20 % with no change in what the drafter predicts. The members serve only through the
wrappers, so if they are the cost, the speculative design is judged on the wrong number. The user approved ~10 min of their
Mac, 2026-10-06 ("sigamos con 2").

**What.** One sitting, MLXK0's runner, mlx-vlm 0.7.3, `mlx-community/gemma-4-12B-it-4bit` + `google/gemma-4-12B-it-assistant`,
the 4 general prompts, greedy, 160 tokens, no speculation and `draft_block_size` 2, 3:
- **H0** — no adapter attached (OMLX0's A0, repeated in this sitting).
- **H1** — `wiki12b-walks-s0` attached (328 wrappers), rows read: `base/general/*` (wrappers inactive) and, beside,
  `wiki12b/general/*` (active).
Memory checked before each arm (the user closed Docker and the browser; 81 % free at start).

**Verdict, written first.** Let $s_0$, $s_1$ be the base's best speed-up in H0 and H1 (inactive).
- **THE WRAPPERS COST IT** — $s_0 - s_1 \ge 0.15$: the wrappers explain MLXK0's gap; the next step is a wrapper that costs
  nothing (fuse $s\,B A$ into the active projection, or call the base module directly when no adapter is active), measured
  the same way.
- **NOT THE WRAPPERS** — $|s_0 - s_1| < 0.08$: MLXK0's gap was the sitting (thermal state or memory); its numbers are
  superseded by a rerun with the wrappers in a clean sitting.
- In between: **PARTLY**, with the numbers.
- Beside: the no-speculation tokens/s in each arm (whether the wrappers cost plain decoding too), and the active-LoRA rows.

**Stopping condition.** One sitting, these two arms. Redesign count: 0.
