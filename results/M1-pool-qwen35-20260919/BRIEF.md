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

## Attempt 1 **[ran]** 2026-09-19 — no verdict; the harness ended it (`attempt1_session_given_up/`)

What it did establish, read off the partial file: `email-full` **trains** on `Qwen3.5-4B` under the
unchanged recipe, and `train_one` renamed **256 tensors** for `Qwen3_5ForConditionalGeneration`
(8 full-attention layers × 4 projections + 32 MLPs × 3, × A and B). No gate was reached.

What ended it: **training one member took ~50 minutes on an L4** (≈6 on the 3B — the hybrid stack
trains through the slow path), all of it silent to the chain's progress filter; after six silent
polls the chain sent one liveness probe, it went unanswered, and the chain gave up **and stopped
the session** as the second training began. *An expired `colab exec` is not a failed command* was
already a rule; the chain did not follow it. The trained adapter was on the card.

Three fixes, all to the harness, none to the question — gates, recipe, cases and verdict table are
unchanged, so the redesign counter stays at 0:

- three unanswered probes a minute apart, not one, before a card is given up;
- the trainer's `loss` lines pass the progress filter, so fifty minutes of training show a position;
- `pool_base` packs `adapters_out.tgz` the moment each adapter exists and says so in the results
  file (`"packed": n`); the chain fetches it **while the session still answers**, and a relaunch
  that carries it in skips what is already trained.

Attempt 2 runs on an **A100** for the same reason: two fifty-minute trainings should not need one
two-hour session to survive.

## Attempt 2 **[ran]** 2026-09-19 — no verdict; killed by the fix (`attempt2_chain_killed_by_my_patch/`)

The line added to fetch adapters early — `PACKS=$(grep … | grep … | tail -1)` — exits 1 under the
chain's `set -euo pipefail` whenever the results file has no `"packed"` key yet, which is the first
poll of every run. The chain died there and its EXIT trap stopped an A100 that had just begun to
train. About fifteen minutes of boot, nothing measured. `grep` printing nothing and exiting 1 is a
rule this repository already had written down; `bash -n` cannot see an exit status. Fixed with
`|| true`, and `tests/test_chain_scripts.py` now lifts that line out of the script and runs it
under the script's own shell options against a missing file, a file without the key and a file
with it. Redesign counter still 0: nothing about the question moved.

## Attempt 3 **[ran]** 2026-09-19 — no verdict, and the cause of attempt 1 corrected (`attempt3_session_ttl_60min/`)

`email-full` trained on `Qwen3.5-4B` (A100, ~45 min — no faster than the L4: the hybrid stack's
slow path is the bottleneck, not the card), 256 tensors renamed, **and the adapter came home while
the session was alive** (`adapters home: 1 packed`, sha `9e83817a…`) — the early fetch did its job.
Then, during the second training, three probes a minute apart went unanswered and the chain gave up,
correctly this time.

**What actually ends these runs — read off `colab log`, not inferred:**

| session | created | terminated |
|---|---|---|
| `srv074513` (attempt 1, L4) | 10:45:28 | 11:45:43 |
| `srv085922` (attempt 3, A100) | 11:59:34 | 12:59:34 |

**A session lives sixty minutes.** Every earlier run here finished inside that (P64 25 min, D2 25
min), so it had never been met. **My diagnosis of attempt 1 was wrong**: I wrote that one unanswered
probe made the chain stop a healthy session. The session had been terminated by Colab at its hour;
the probe was unanswered because nothing was there. The three-probe rule is still the right rule and
was not the cause. `colab new` has no lifetime option and already runs its own keep-alive.

**So the unit of work is a session, not a run.** Nothing about the question changes — gates, recipe,
cases, verdict table — and the redesign counter stays 0. What changes is the harness:

- `pool_base --stop-after-training` ends a session cleanly once the adapters are packed and home;
- the chain uploads the partial results file into a new session, so arms resume instead of restart;
- M1 runs as **three sessions under an hour each**: `email-full` trained (done, home) · `desk-commitment`
  trained · both carried in, gates and the four arms.

## Result **[ran]** 2026-09-19 · MOVED — both members hold their recorded runs on `Qwen3.5-4B`

Four sessions in all, each under the hour: **A** trained `email-full` (adapter home, the session
ended at its sixty minutes) · **B** trained `desk-commitment` with `--only … --stop-after-training`,
52 minutes · **C** carried both in, passed every gate, scored the base on email and **450 of 475** of
`email-full`, and then the VM stopped answering at ~22 minutes — not the lifetime limit; nothing on
disk says why · **D** carried in the adapters *and the partial results*, resumed at case 450, and
finished. Read off `pool_base.json`.

| gate | outcome |
|---|---|
| G1 identity on a **full-recipe** adapter | `applied`, 3/3, **both** members — the arm that could kill this first; D2's had been a 60-step toy |
| G2 tools reachable · G2′ `auto` | both · each probe served by its own member |

| member | on `Qwen3.5-4B` | recorded on `Qwen2.5-3B` | paired | the new base alone |
|---|--:|--:|---|--:|
| `email-full` | **471 / 475** · human 347/351 = 0.989 · 1053 calls, 0 refused | 471 / 475 | **tie**, 1 : 1, $p = 1$ | 346 / 475 · human 222/351 = 0.632 · 15 calls |
| `desk-commitment` | **240 / 240** · 240 calls, 0 refused | 240 / 240 | **tie**, 0 : 0 | 0 / 240 |

`moved` = every gate, each member `tie` or better against its recorded run and `improvement` against
the new base: **true**. Manifests: `releases/email-full@v2.json`, `releases/desk-commitment@v2.json`;
the `@v1` releases on Qwen 2.5 stay as the control arm.

**What each number is worth — said, because two of them look better than they are.**

- **The ties are the result.** Same corpora, unchanged recipe, another base and another family: both
  members land where they were. The recipe's seven projection names reach only 8 of the 32 attention
  layers of the hybrid stack (the other 24 are linear attention) and all 32 MLPs — and that was enough.
- **`desk-commitment` beats the base "240 : 0" and that says almost nothing.** Read where it happens:
  in 236 of 240 cases the bare 4B writes `<thread_history>...</thread_history>` — *the tool block's
  own placeholder, dots included* — seven times, is refused seven times, and runs out of turns. It is
  P59's behaviour again: an untrained model copies tags off the block. That arm measures whether a
  base understands this tag protocol, not what it knows about the task. The gate is passed; the
  margin is not a finding.
- **On email the new base is far stronger than the old one: human 0.632 against 0.345**, asking for a
  tool only 15 times. The adapter still adds 125 : 0 — but the headroom an adapter has to fill is
  smaller on this base, and that is worth knowing before the next region is trained on it.
- **Both bands are at the ceiling**, as they were on 2.5. Nothing here ranks anything.

**Not measured:** `knowledge_arm` on the 4B — whether a base this size follows a written procedure
(P61 was a fact about a 3B; M5 since showed the 4B *answers about* a note it reads); the deep desk
band; why session C's VM stopped answering.

**Redesign counter: 0.** Five relaunches, every one a fix to the harness — a session's lifetime, a
pipeline's exit status, one member a session, resuming arms — and none to the question.
