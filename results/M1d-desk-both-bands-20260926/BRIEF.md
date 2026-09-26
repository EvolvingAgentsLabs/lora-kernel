# M1d — desk-commitment trained on both bands, on Gemma 4 E4B (pre-registered 2026-09-26)

**Why.** M1c **[ran]**: on `commitment_deep` both released-style members — trained on the shallow band only — copy the last
message's date and fail from depth 2 (Gemma 60/240, 0 : 22 against its own base; Qwen `@v2` 64/240), while the bare Gemma
scores 82/240. The corpus that teaches the deep chain exists (`data_desk_deep`, 600 rows, P60: `thread_history`, then the
latest date that is MINE). **One unknown: the corpus — both bands instead of the shallow one.**

**Corpus [ran, zero GPU].** `training/harness/data_desk_both/train.jsonl` = `data_desk` (600) + `data_desk_deep` (600),
shuffled (seed 20260926); **0** evaluation prompts of either band in it.

**Sessions.** T (A100): `pool_base --members desk-commitment --corpus-for desk-commitment=training/harness/data_desk_both/train.jsonl
--tag g4b --stop-after-training`, the unchanged recipe. S1 (L4): the shallow band, paired against M1's `@v2` records
(`--against results/M1-pool-qwen35-20260919/pool_base.json`). S2 (L4): the deep band, `--against none`, paired against the
bare Gemma of the same session.

**Verdict — written first.** Exact two-sided sign test on discordant pairs:

| check | required | reading if not |
|---|---|---|
| shallow: `g4b vs @v2` | tie or improvement | the deep corpus costs the shallow band — not released |
| deep: `g4b vs bare Gemma` | improvement | the deep corpus does not teach the chain on Gemma — not released |

Both → **`desk-commitment@v3` on Gemma** (one member for both bands), `@v2` stays the control. Beside: by depth; against M1c's
shallow-only `g4` on the deep band. One seed, said as such. **Ceiling:** 1 A100 + 2 L4. **Redesign counter: 0.**
