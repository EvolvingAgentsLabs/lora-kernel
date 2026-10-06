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

## Result [ran] 2026-10-06 — NOT THE WRAPPERS; MLXK0's numbers were the sitting, and are superseded

One sitting, 81 % / 75 % of memory free before H0 / H1, swap unchanged; peak 8.0 GB. `h0_bare.json`, `h1_wrapped.json`,
`run.log`. H1 ended on a `KeyError` *after* every row was saved: the swap check reads `base/domain/off`, which `--sets general`
does not run — its summary was computed from the saved rows (`"note"` in the file), and the runner now skips the swap check
when the domain set did not run.

| arm | no spec | $k=1$ | $k=2$ | acceptance |
|---|--:|--:|--:|---|
| H0 base, no wrappers | 14.23 | 1.40× | **1.47×** | 0.76 / 0.58 |
| H1 base, 328 wrappers inactive | 14.16 | 1.41× | **1.43×** | 0.76 / 0.58 |
| H1 **LoRA active** (beside) | 13.72 | **1.23×** | 1.22× | 0.67 / 0.54 |
| *MLXK0, LoRA active, general (yesterday)* | *12.6* | *1.08×* | *1.04×* | *0.67 / 0.54* |

**By the table written first: NOT THE WRAPPERS** — $s_0 - s_1 = 1.47 - 1.43 = 0.04 < 0.08$; plain decoding costs the same
with them (14.23 / 14.16).

**Reading.**
1. **MLXK0's whole sitting was slow**, not its wrappers: every row there — base and LoRA alike — sits ~0.15–0.25× under
   today's at identical acceptance, and its no-speculation rates were lower too (13.7 / 12.6 against 14.2 / 13.7). That
   sitting's memory pressure was never checked; this morning's first OMLX0 sitting was caught swapping 7 GB. **MLXK0's
   numbers are superseded by these** (its round-cost reading — MLX's round far cheaper than llama.cpp's — stands, and is
   stronger).
2. **The active LoRA itself costs** ~3.5 % of plain decoding and its speculation 1.23× — the drafter's misalignment
   (0.67 against 0.76), not the wrappers.
3. **For the user's design** (12B + LoRA expert + aligned drafter in MLX): the base's 1.47× at $k = 2$ is the ceiling an
   aligned drafter would approach on general text — above MLXK0's WORTH-ALIGNING bar (1.4×). On the LoRA's own domain, in a
   clean sitting, the misaligned number is not yet measured (MLXK0's 1.08× there was the slow sitting).
4. **Instrument rule, from this and OMLX0:** a Mac speed number carries the sitting's memory state in its record, or it is
   not compared with another.
