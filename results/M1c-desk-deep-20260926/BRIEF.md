# M1c — desk-commitment on a band with room: does it move to Gemma? (pre-registered 2026-09-26)

**Why.** M1b **[ran]**: on the shallow `commitment` band the bare Gemma 4 E4B already scores 240/240, so the Gemma
member tied it and the verdict could not release it; `desk-commitment@v2` stayed on Qwen. The user asked for a suite
with room. It exists and was built for exactly this: **`desk:commitment_deep`** (P60 **[ran]**, 240 cases, 60 per depth
1–4) — from depth 2 the last message is the sender's, so the promise has to be read out of the thread and told apart
from the sender's proposed dates; the verifier accepts exactly one named date.

**Question (one unknown: the base, on the band that has room).** On `commitment_deep`, does the member retrained on
Gemma (`desk-commitment-g4`, M1b, `f8dc47d7…`) tie or beat the released one (`desk-commitment@v2`, Qwen3.5-4B, M1
`adapters.tgz`) — and does each beat its own bare base? Both members were trained on the SHALLOW corpus; this measures
them where they were not trained to the ceiling, which is the point.

**Sessions.** Two L4, `pool_base --members desk-commitment --suite-for desk-commitment=desk:commitment_deep --against none`:
**G** on `google/gemma-4-E4B-it` (`--tag g4`), **Q** on `Qwen/Qwen3.5-4B` (`--tag q35`). Each: G1, G2, the bare base and
the member on the same 240 cases (`eval_seed 424242`). The two sessions are paired offline by case id.

**Verdict — written first.** Exact two-sided sign test on discordant pairs, $p<0.05$:

| check | required | reading if not |
|---|---|---|
| headroom — the bare Gemma on the deep band | < 216/240 (90 %) | **NO ROOM EVEN HERE** — desk needs no adapter on Gemma; the region is served by the bare Gemma, stated as such |
| `desk-commitment-g4 vs bare Gemma` | improvement | **NOT A MEMBER ON GEMMA** — the adapter buys nothing on this base |
| `desk-commitment-g4 vs desk-commitment@v2` | tie or improvement (the user's rule: parity chooses Gemma) | **STAYS ON QWEN** — a measured loss; the user decides whether stack alignment is worth it |

All three hold → **`desk-commitment@v3` on Gemma**, `@v2` stays the control. Beside: by depth; the bare Qwen on the band.
**Ceiling: 2 L4.** No training. **Redesign counter: 0.**
