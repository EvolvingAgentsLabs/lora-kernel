# M1 — the pool on Qwen 3.x small (pre-registered 2026-09-19)

**Question (one unknown: the base).** Do `email-full` and `desk-commitment`, retrained on
`Qwen/Qwen3.5-4B` from their released corpora under the unchanged recipe, tie or beat their
own `Qwen2.5-3B-Instruct` releases — served as a pool, each routed by its question?

**Why.** [`docs/PLAN.md`](../../docs/PLAN.md) milestone 1: the family is Qwen 3.x small and
large, and everything released is on 2.5. D2 **[ran]** removed the obstacle (tensor names).

**Set-up.** Colab **L4**, one session, `MODULE=training.harness.pool_base`. No API provider,
no frontier call. Both members trained in a subprocess each (`train_one`, `release_gate.RECIPE`:
r 16, α 32, 3 epochs, lr 2e-4, the seven projection names), renamed for the class vLLM serves
(`rekey.json` beside the weights), served together in one vLLM behind the proxy with
`--prune --member-prompt --auto`. Suites and cases are the recorded runs' own: email 475
(seed 717171, P57), desk 240 of 960 (seed 424242, P64), paired by case id.

**Preflight, zero GPU, done before this was written [read].** Rendered from the published
`chat_template.jinja` of `Qwen3.5-4B`: a training example's assistant turn is written behind an
**empty** `<think>\n\n</think>\n\n` block; the default generation prompt ends `<think>\n`, open.
A bare base served that way thinks until its 160 tokens run out and scores as a floor, and any
adapter "wins". Every generation render and the proxy's member request now pass
`enable_thinking=False`, whose prompt is an exact prefix of the trained text. Qwen 2.5's template
has no such switch and ignores it, so nothing frozen moved.

**The order is the kill order.**

| step | stops the run if |
|---|---|
| G1 identity on each **full-recipe** adapter | not `applied` — D2's was a 60-step toy; nothing is scored |
| G2 tools reachable · G2′ `auto` routes each probe to its member | reported, scored anyway |
| base arm per suite, **on the new base** | — (the headroom arm is never inherited from 2.5) |
| member arm per suite, paired vs the recorded 2.5 run | — |

**Verdict, written first (`pool_base.verdict`).** `moved` iff G1, G2, G2′ hold and each member is
`tie` or `improvement` against its recorded run **and** `improvement` against the new base —
exact two-sided sign test on discordant pairs, $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$.

| outcome | reading | what we do |
|---|---|---|
| `moved` | the pool lives on Qwen 3.x small | release `@v2` manifests on the new base; 2.5 stays the control |
| STOPPED AT G1 | a real adapter is not applied though a toy was | read the activation log; the pool stays on 2.5 |
| a member `REGRESSION` vs its release | the family move costs quality in that region | pool stays on 2.5 **for that region**; one arm allowed: the linear-attention projections added to the targets |
| a member ties the new base | the 4B already does the region; the adapter buys nothing there | read the base arm — that is a finding about headroom, not a failure of training |

**Known and accepted before the run.** The recipe's seven projection names exist on all 32 MLPs
but only on the 8 full-attention layers of the hybrid 3.5 stack; the 24 linear-attention layers
(`in_proj_qkv`, `in_proj_z`, `out_proj`) get no delta. That is "unchanged recipe", deliberately:
one unknown per run. Desk's shallow band is at the ceiling (240/240), so a tie there says little;
email (471/475) has a little room below and a lot above the base.

**Not measured:** the deep band; `knowledge_arm` on the 4B (whether a larger base follows a
written procedure) — one arm, after this; anything about the 27B.

**Redesign counter: 0.**
