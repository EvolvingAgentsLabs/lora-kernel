# M1b — the pool re-released on Gemma 4 E4B (pre-registered 2026-09-25)

**Question (one unknown: the base).** Do `email-full` and `desk-commitment`, retrained on `google/gemma-4-E4B-it` from
their released corpora under the unchanged recipe, tie or beat their **`@v2` releases on `Qwen3.5-4B`** (M1 **[ran]**) —
served as a pool, each routed by its question?

**Why.** The user's decision, 2026-09-25: everything moves to Gemma 4 after B1's measured tie on W9. A decision about a
family is not a measurement of every member on it: each released member moves only through the release gate, paired
against the release it would replace. This is milestone 1's procedure run again, one base later.

**Set-up — M1's, unchanged except the base and the reference.** `training.harness.pool_base`: both members trained in a
subprocess each (`train_one`, `release_gate.RECIPE`), adapters `adapters/<member>-g4`, served together behind the proxy
(`--prune --member-prompt --auto`); the Gemma LoRA excludes the vision/audio towers (`s4_train.towers_to_exclude`,
B1); thinking off in every render. Suites and cases are M1's own: email 475, desk 240, paired by case id **against M1's
member records** (`--against results/M1-pool-qwen35-20260919/pool_base.json`), and against the new bare base.

**Sessions.** T: one A100, both members trained and packed (`--stop-after-training`; Gemma trains a 600-row corpus in
~13 min, B1 **[ran]**). S: one L4, both carried in — G1 identity per member, G2 tools reachable, G2′ `auto` routes each
probe to its member, then the base arm and the member arm per suite.

**Verdict — `pool_base.verdict`, written first, unchanged.** `moved` iff G1, G2, G2′ hold and each member is `tie` or
`improvement` against its `@v2` record **and** `improvement` against the new bare base, exact two-sided sign test on
discordant pairs. `moved` → `@v3` manifests on Gemma; `@v2` stays the control. A member `REGRESSION` against `@v2` → that
member stays on Qwen and the user decides whether stack alignment is worth a measured loss (B1's rule covers a tie, not a
loss). A member tying the new base → the region needs no adapter on Gemma, reported as headroom.

**Not measured:** the deep band; the 31B; the MTP drafter. **Redesign counter: 0.**

## Result **[ran]** 2026-09-25 · NOT MOVED as a pool — email-full moves, desk-commitment needs no adapter on Gemma

One A100 trained both members (`email-full-g4` `725ad8dd…`, `desk-commitment-g4` `f8dc47d7…`); one L4 carried both in:
G1 applied on both, G2 reachable, G2′ `auto` routed each probe to its member, 0 transport errors (`pool_base.json`).

| member on Gemma 4 E4B | vs its `@v2` (Qwen3.5-4B) | vs the bare Gemma |
|---|---|---|
| **email-full** | 469 vs 471 of 475 — **tie** (1 : 3, $p = 0.625$) | 469 vs 350 — **improvement** (119 : 0) |
| **desk-commitment** | 240 vs 240 — **tie** | 240 vs 240 — **tie**: the bare Gemma is already at the ceiling |

`pool_base.verdict`, as written, requires every member to beat the new base: **NOT MOVED**. Read by the brief's own
table, row by row: **email-full moves** — `releases/email-full@v3.json` on Gemma, `@v2` stays the control;
**desk-commitment ties the new base — the region needs no adapter on Gemma**, reported as headroom, not a failure.
M1 had said it before this ran: desk's shallow band sits at the ceiling (240/240), so a tie there says little. The
desk member stays released on Qwen (`@v2`) until a suite with room above the base decides it — the verdict is not
rewritten to release it.
