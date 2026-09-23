# M7 · W5e — the referee writes the first query (pre-registered 2026-09-23)

The first item of W5d's *What follows* ([`BRIEF`](../M7-W5d-answer-policy-20260920/BRIEF.md)). No new training
recipe — but W5c's adapter has to be retrained, see *The adapter* below.

**Question (one unknown: the text of the walk's first search).** W5d **[ran]** falsified the answer policy
as written — `policy vs withlib` 5 : 0, $p = 0.0625$, a tie — and read the failure where it happens:
where the adapter's walk opened the supplying note, the bare base read it right **21 of 21**; the other
**11** value rows of the headline are retrieval misses. They are not a shelf problem: in all 11 the adapter's
first search is on the right shelf (`wiki`), and every one is a training query for the rates topic — 9
`turning an order into a number to set on a pump or a clamp` (68 times in its corpus), 2 `… to measure or
administer` **[ran]**, read off W5d's records. **If the runtime runs the conversation's first search on the
request's own statement, on the shelf the adapter named, does the walk reach the note — and does the
policy then beat the adapter alone without costing the trained band?**

## The treatment, frozen before the sessions

`memory.runtime.Conversation.first_query` — off (`None`) by default, which leaves every earlier run
byte-identical. Set to the statement, the conversation's **first** `<search>` runs on that text, on the
shelf the adapter wrote; the adapter's own words are logged (`substituted`, `written`), not searched;
every later search is the adapter's. The text of the walk is left as the adapter generated it — the
listing that follows it is the statement's. Applied to **every** row: the referee does not know a task's
kind, so carry rows are re-walked under it too, and the control set is where that is paid for, if it is.

A walk made under it replays result by result (`walks_composed._run` reads `first_query` off the record),
so the policy's base reads the pages the walk really opened. `tests/test_walks_first_search.py` holds that,
and shows the mechanism can fail: a scripted walker that writes W5d's memorised query reaches the
supplying note on ≤ 2 of the 11 without the referee and on 11 of 11 with it.

## The adapter — retrained, so the baseline is re-run

W5c's `withlib` (sha256 `0f7d872d…`) was kept only as a git-ignored tarball in a scratchpad that no longer
exists; it is on no disk of this machine **[ran]** (whole-disk search, 2026-09-23). It is **retrained** from
the same corpus with the same recipe — `walks_arm --data training/nursing/data_walks_v2 --tag v2 --train
withlib`, one A100 session, W5c's SA exactly. That is a session of its own: training and measuring are never
one session. A retrained adapter is not W5c's bit for bit, so **W5d's recorded `withlib` and `policy` do not
pair with it: both are re-run here, in the same scoring session as the treatment.** That also takes vLLM's
session-to-session spread (84, 81, 82 on one adapter **[ran]**) out of the pair that decides. Only
`base-reads`, which has no adapter in it, is copied from W5d — and it is read beside, never in the verdict.

The retrained adapter may not reproduce W5d's failure. **That is the headroom check, and it is bought
first:** `withlib` walks before `withlib-fs`, and the mechanism is read on *its own* misses.

## Stage — attribution, and only attribution

The sets are **W5d's own** (`training/nursing/data_walks_w5d/`, held-out 89 · headline 67 · control 78).
They were written after W5d's freeze and are **seen** now: the 11 misses are why this arm exists. So
nothing here is a claim about fresh cases. A pass buys exactly one thing — writing a set after **this**
freeze (new openings, asks and wordings, W5d's generator discipline) and running the claim on it. A fail
ends the idea on the cheapest set there is.

## Arms, in the order bought

| # | arm | session | why |
|---|---|---|---|
| 0 | zero GPU: what the statement lists, on the oracle's first shelf | none | before anything is paid for — below |
| T | retrain `withlib` on corpus v2 (`adapters/nursing-walks-v2-q35`) | **A100**, ~50 min | W5c's adapter is gone; its recipe is not |
| 1 | **`withlib`** — the retrained adapter walks both sets with its own queries | **L4**, G1 identity first | **headroom**: does it still lose value rows to its own query? |
| 2 | **`withlib-fs`** — the same adapter under the referee's first query | same L4 | the treatment |
| 3 | **`policy`** — W5d's frozen policy (`answer_policy.py`, untouched) over `withlib`'s walks | same L4 | the baseline the pair decides against |
| 4 | **`policy-fs`** — the same policy over `withlib-fs`' walks | same L4 | the pair that decides |
| — | `base-reads` | copied from W5d | beside only: W5's bar; no adapter in it |

**Not bought:** a fresh set (only after a pass); the radar behind the same interface (W5d's item 2, after
this); W5c's v2 sets (their walks had 0 retrieval misses: nothing for this treatment to repair); `nolib`.

## Verdict — written first (`walks_first_search.verdict`)

By **credit** (`right` or `format`, `grade_walks` untouched), paired by case id, exact two-sided sign test
on discordant pairs (FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, $p<0.05$:

| check | required | reading if not |
|---|---|---|
| **headroom** — headline value rows `withlib` (this session) loses to a retrieval miss | **≥ 4** | **NO HEADROOM** — the retrained adapter does not show the failure; nothing is left to repair, and the arm says so instead of reporting a tie |
| **mechanism** — of those rows, `withlib-fs`' walk still does not open the supplying note | **fewer than half, rounded up** (6 of 11 is W5d's own falsifier) | **FALSIFIED** — shown a listing that holds the note, the walk still goes elsewhere: the walk itself is memorised, not only its query |
| **`policy-fs vs policy`**, headline | **improvement** | **NOT BOUGHT** |
| **`policy-fs vs policy`**, control | **not a REGRESSION** | **NOT A SERVING DESIGN** — the referee's query costs the trained band |

`passed` = all four, read as *attribution on a seen set*. Beside, never folded in: `policy-fs vs base-reads`
(W5's bar — a tie is a tie), `withlib-fs vs withlib`, `policy vs withlib` (W5d's pair, re-run on the
retrained adapter), right-only pairs, retrieval misses on the 32 headline value rows for both walking arms
(**predicted ≤ 2** under the referee), W5d's own 11 walked with and without the referee, credit by writer,
the adapter's sha256. Void, not failed: G1 not applied; any headline record, or any row the mechanism
reads, lost to transport.

**Power, said now.** If the misses are repaired and the base reads them as it read W5d's other 21 (21/21),
eleven repaired is about 11 : 0, $p = 0.001$. Six gained and none lost is $p = 0.031$; five is $0.0625$, a tie.

## The zero-GPU numbers **[ran]** — `zero_gpu.json`

The lexical searcher, the statement as the query, on the shelf of the oracle's first search:

| slice | rows that need a search | a walk note listed (top 3) | the supplying note listed |
|---|--:|--:|--:|
| W5d's 11 missed | 11 | **11** | **11** |
| headline | 39 | 39 | 18 |
| control | 20 | 20 | 16 |

On the carry rows the statement lists the *procedure* (a walk note), not the step the answer sits on —
that is reached by walking, as trained. On the training corpus (v2, 600 rows) the statement lists a walk
note on 268 of the 274 rows that need one, against the oracle query's 258 (conditional 53 vs 56, carry
105 vs 92): on the distribution the adapter was trained on, the statement's listing is not poorer than
the one it learned to use. **What it does change:** the oracle's first open is first in the statement's
listing less often (30 vs 47 on W5d's held-out) — a listing the adapter never saw in training. Walk
mechanics — opens, searches, violations — are reported beside credit.

## Suite, models, parameters

W5d's, unchanged: `Qwen/Qwen3.5-4B` (Hugging Face weights, bf16) served by **vLLM on Colab**, one LoRA
module (`withlib`); no API provider is called. Thinking off in every render. Temperature 0; the walking arm
160 tokens a step, stop at the closing tag, 64 calls; the base's line 320 tokens; window 8192; concurrency 8;
searcher lexical. Training: W5c's recipe through `walks_arm --train`, unchanged.

## Cost, abort, redesigns

**Cost.** One A100 session to retrain (W5c's SA ran 56 of its 60 minutes; the trainer packs the adapter
before expiry, and a session that dies first is relaunched once), then one L4 session: ≈ 334 walks and
≈ 140 single replies — about twice W5d's scoring (11 min). **Ceiling: 1 A100 + 2 L4**; the second L4 only
resumes records a dead session lost. No dollars to a provider. **Abort.** No `[arm]` line for 8 minutes
once the base is up → stop; the runner persists every 20 records and resumes. Never `colab exec` by hand
into the session the chain polls. **Redesign count: 1** before any number — the baseline moved from W5d's
records to a same-session re-run once the adapter was found lost, before either session ran. The
instrument's stays **2** (grader untouched). Changing `first_query`'s scope (which search, which shelf)
after this commit is a redesign, and is counted.

## Launch

`R=results/M7-W5e-first-search-20260923`, `D="--data training/nursing/data_walks_v2 --tag v2"`, every line
through `training/harness/chain_serve.sh` (`BRANCH=arbiter-first-search-20260923` until merged, then `main`):

```bash
# T — retrain W5c's withlib, same corpus and recipe          (then: cp $R/adapters_out.tgz $R/adapters.tgz)
GPU=A100 BRANCH=arbiter-first-search-20260923 RUN_DIR=$R MODULE=training.nursing.walks_arm \
  MARGS="$D --train withlib --stop-after-training" RESULTS_NAME=train_withlib.json BASE=Qwen/Qwen3.5-4B \
  TRAINDEPS=1 SKIP_ADAPTERS=1 SESSIONS=1 training/harness/chain_serve.sh
tar tzf $R/adapters.tgz | grep nursing-walks-v2-q35/adapter_model.safetensors     # must print one line

# S — score: the adapter carried in, four arms, the baseline first
GPU=L4 BRANCH=arbiter-first-search-20260923 RUN_DIR=$R MODULE=training.nursing.walks_first_search \
  MARGS="--concurrency 8" RESULTS_NAME=walks_first_search.json BASE=Qwen/Qwen3.5-4B SESSIONS=1 \
  training/harness/chain_serve.sh
```

`cannot score: … not on disk` means the carry-in failed: stop, do not retrain inside the scoring run. Read
the verdict from `walks_first_search.json`, not from the chain's peek. **The adapter tarball is copied to
`~/lora-kernel-adapters/` as soon as it is home** — W5c's was lost by living only in a scratchpad.
