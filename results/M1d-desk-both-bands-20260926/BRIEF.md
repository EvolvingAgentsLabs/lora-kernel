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

## Result **[ran]** 2026-09-26 · PASSED — `desk-commitment@v3` on Gemma, one member for both bands

One A100 trained `desk-commitment-g4b` (`dd8e2ba0…`, 1,200 rows, 225 steps); two L4 scored it (`shallow.json`, `deep.json`),
G1 applied in both.

| deep band (240) | depth 1 | 2 | 3 | 4 | total |
|---|--:|--:|--:|--:|--:|
| bare Gemma 4 E4B | 60 | 0 | 0 | 23 | 83 |
| shallow-only member on Gemma (M1c) | 60 | 0 | 0 | 0 | 60 |
| `@v2` on Qwen (M1c) | 60 | 0 | 0 | 4 | 64 |
| **both-bands member on Gemma** | **60** | **59** | **60** | **60** | **239** |

**Shallow:** 240/240, a tie with `@v2` (0 : 0) — the deep corpus cost the shallow band nothing. **Deep:** 239/240 — **156 : 0**
against the bare Gemma, 175 : 0 against `@v2`. Read where it happens: every deep walk makes one `thread_history` call and
picks MY latest promise among the sender's proposals (depth 4: five dates in play, "June 17" right). **PASSED as written:
`releases/desk-commitment@v3.json` on Gemma**, `@v2` stays the control. One seed, said as such.
