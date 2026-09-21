# M7 · W5d — the answer policy: the adapter walks, and who writes the last line depends on the kind of task (pre-registered 2026-09-20)

Step 1 of [`docs/FRAMEWORK.md`](../../docs/FRAMEWORK.md) §7, *decide who reads*. No training.

**Question (one unknown: who writes which final line).** W5, W5b and W5c **[ran]** say one thing three
ways: the adapter **navigates** a procedure it never trained on (42 : 0 against the untrained base made
to walk, 0 retrieval misses) and carries it; it does **not read** a value stated under a condition in a
note it never saw (0/11; 4/15 after a corpus that showed the shape over eight notes), where the
untrained base reads 15/15. Letting the base write *every* final line is not a serving design — it
gives back 19 control cases (W5b). **Does a split by kind of task — the adapter carries procedures and
computes rates, the bare base reads values from the pages the adapter's walk opened — beat the adapter
alone on a held-out procedure, without giving the trained band back?**

## The policy, frozen before any set below was written

`training/nursing/answer_policy.py`. The adapter **walks, always**. The final line:

| kind of task | who writes | why |
|---|---|---|
| **carry** — report the last step carried out; or say it is not in the library | the **adapter** | navigation and procedure are what training bought: shared-line 22/22 against the base's 8/22, mid-procedure 14/22 against 5/22 **[ran]** W5c |
| **rate** — a rate computed from an order | the **adapter** | a rate is computed, not read, and the adapter computes through `<calc>`. Decided **from the trained band only**: on the CONTROL sets the adapter is 15/15 (W5) and 12/12 (W5c), the base handed the same notes 7/15 and 5/12, composition 7/15 (W5b). The held-out procedure has no rate step, so no held-out number exists to have been used |
| **value** — a quantity read off a note, plain or under a condition | the **bare base**, given the pages the adapter's walk opened, served exactly as `base-reads` is | 15/15 and 16/16 where the adapter is 4/15 and 13/16 **[ran]** W5c |

**Decided without the grader's labels.** A row's `family` does not exist at serving time. `kind()`
reads the **statement** and nothing else — the form of answer the request itself asks for. Agreement
with the generator's `family`, on rows nobody evaluates (zero GPU **[ran]**): **600/600** on
`data_walks_v2/train.jsonl`, **600/600** on `data_walks/train.jsonl` (563 and 559 statements name a
form; the rest name none and default to the adapter, which is today's behaviour). The bar fixed for
this number was 0.98: under it, stop and report, do not tune against an evaluation set.

**What that 1.0 is worth, said before it is quoted anywhere.** The statements are written by a generator
whose closing sentence names the answer form, so a rule over that sentence recovers it exactly. It
shows the rule is wired to the corpus's wording; it does **not** show that a live request can be
classified. *A model of a generated corpus learns the generator* holds for a regex too. In a role pack
the answer form belongs in the task schema, or a classifier is paid for and measured on real asks. This
run does neither, and prices only the split.

The freeze is a commit of its own; its hash is cited under *Sets* below, which was written after it.

## Two stages — only one is the claim

| stage | on what | what it is |
|---|---|---|
| **claim** | NEW held-out and control sets, `training/nursing/data_walks_w5d/`, written **after** the freeze; never W5's 80, never W5c's 88/80 | **the only stage the verdict reads** |
| **attribution** | the policy over W5c's **recorded** `withlib` walks on the v2 sets (whole walks and opened ids are stored since W5b's fix; 168/168 replay exactly **[ran]**, zero GPU) | those sets are new to the policy's *design* — its 47/56 came from W5's first set — and **not new to us**: a first out-of-sample look, labelled as that, never the claim |

## Arms, in the order bought — one L4 session

| # | arm | why now |
|---|---|---|
| 0 | zero GPU: `kind()` agreement, the floor on the new sets, the attribution ceiling | before anything is paid for |
| 1 | **`base-reads`** on the new sets — the untrained base, the oracle's notes open | **headroom first**, and W5's bar. If it has credit on ≥ n − 5 of the headline, no arm can *beat* it by a sign test: `no_headroom_for_the_bar` is reported. **The session continues either way** — the pair that can falsify the policy is the next one, its headroom is `withlib`'s failures, and the session is already bought |
| 2 | **`withlib`** walks the new sets — W5c's v2 adapter (`adapters/nursing-walks-v2-q35`, sha256 `0f7d872d…`), **carried in, not retrained** | the policy's walks have to exist on the new set; G1 identity first |
| 3 | **`policy`** on the new sets — `withlib`'s record where the adapter writes; its replayed walk plus the base's line where the base does | the claim |
| 4 | **`policy`** on the v2 sets, from W5c's recorded walks | attribution; last, because a session lives sixty minutes and this is the stage that does not count |

**Not bought:** `nolib` and `base-walks` on the new sets (W5 and W5c settled both: 35 : 2, 39 : 0, 42 : 0);
a policy that sends only values from *untrained* notes to the base (decidable at serving time — the
release knows which notes its corpus opened — and a redesign of this one); any training.

## Verdict — written first (`walks_policy.verdict`)

On the NEW **headline** (held-out, depth ≤ 9, final line no other procedure states), by **credit**
(`right` or `format`, the untouched `grade_walks`), paired by case id, exact two-sided sign test on
discordant pairs (FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, different at
$p<0.05$:

| pair | required | reading if not |
|---|---|---|
| **policy vs withlib**, headline | **improvement** | **FALSIFIED** — on a set written after the freeze the split buys nothing over the adapter alone; the 47/56 was the set |
| **policy vs withlib**, control | **not a REGRESSION** | **NOT A SERVING DESIGN** — what composition did (W5b, 0 : 19) |
| **policy vs base-reads**, headline | W5's bar; the spec says ***beats*** | a **tie is reported as a tie**, with totals. What a tie would mean here: *learned* navigation plus the base's reading reaches what the *oracle's* navigation plus the base's reading reaches — the adapter paid for the walk `base-reads` is handed for free — while on control the policy is far ahead of `base-reads`, printed beside. It is still a tie, and W5's bar is not cleared by it |

`passed` = all three. `right` alone — the contract: right **and** in the taught form — is paired and
printed beside credit for both headline pairs. Void, not failed: G1 not applied; any headline record
missing or lost to transport. A walk that cannot be replayed leaves every slice for every arm and is
counted (zero are expected: records keep their whole walk now).

**W5's verdict stands whatever this says.** A policy that passes is a candidate serving design with one
held-out set under it — an entry for the role pack's *answer policy* — not a second reading of W5.

Beside the headline, never folded in: shared-line rows; quantity by layer and by which value was asked;
control with and without `rate`; `policy` credit by writer; `format`, `unread`, `context`; transport
errors; `prompt_identical_to_base_reads`.

## Suite, models, parameters

**Suite.** See *Sets* below. **Models and provider.** `Qwen/Qwen3.5-4B` (Hugging Face weights, bf16)
served by **vLLM on Colab**, with one LoRA module, `withlib`; no API provider is called. Thinking off
in every render. **Parameters.** Temperature 0; walking arm 160 tokens a step, stop at the closing tag,
64 calls; arms with no verbs 320 tokens, no stop strings; window 8192 — a prompt that outgrows it is
`context`, not an error; concurrency 8; searcher lexical (R0 did not pass W3), as the corpus was
generated.

## Cost, abort, redesigns

**Cost.** One L4 session expected: ≈ 170 `base-reads` replies, ≈ 170 walks, ≈ 130 single replies —
W5c's scoring session did more in 24 minutes. **Ceiling: 2 sessions**, on this arm's own budget. No
dollars to a provider. **Abort rule.** No `[arm]` progress line for 8 minutes once the base is up →
stop the session; the runner persists every record and resumes. Never `colab exec` by hand into the
session the chain is polling. **Redesign count: 0** for this arm; the instrument's count stays **2**
(the grader is untouched; a third ends the step). Changing `WRITER` or `kind()` after the freeze
commit is a redesign and is counted.

## Sets and zero-GPU numbers — written AFTER the freeze

**The freeze is commit `d3e5056`** on `w5d-answer-policy`: `answer_policy.py` (the table and `kind()`),
the runner, its verdict and everything above this heading. The sets below did not exist at that commit.
Changing `WRITER` or `kind()` from here on is a redesign, and is counted.
Since the freeze `answer_policy.py` is byte-identical; `walks_policy.py` changed in one place — *where* the
zero-GPU numbers are written (their own small file, so the chain does not carry 1 MB of copied records in) —
and its arms, its analysis and its verdict are untouched (`git diff d3e5056 -- training/nursing/walks_policy.py`).

**The new sets [ran, zero GPU]** — `training/nursing/generate_walks_w5d.py`, seed 20260921, gate
PASSED (`gate.json`). Nothing is trained on them; the adapter that walks them is W5c's.

| | held-out (`discontinue-iv`, never opened in training) | control (the trained band) |
|---|--:|--:|
| rows | **89** | **78** |
| by the frozen rule | carry 57 · value 32 | carry 32 · value 36 · rate 10 |
| **headline** (depth ≤ 9, final line not shared) | **67** = 35 carry + 32 value | — |
| shared-line | 22 | — |
| value asked: conditional / plain | 16 / 16, stated explicitly 16, implicitly 16 | 18 / 18 |
| by layer | site or case 26 · textbook 6 | — |
| *copy the first number on the page* is worth | 0.50 | 0.50 |

What makes a case new: every opening sentence (all three procedures), every ask (the six conditional
quantities, both values, both phrasings), the held-out note's value pools — (1, 2, 17, 19) and
(21, 23, 24, 26, 27, 28, 35), in neither W5's pools nor W5c's — the not-in-library topics, the seed.
Gate clauses, each shown able to fail (`tests/test_walks_w5d.py`): G1 no value in a statement 0 · G2 no
evaluated walk or world in the v2 corpus 0 · G4 every row accepted by the referee in `strict` 0 · **G5
no case W5 or W5c evaluated 0** (dropped while building, and counted: 0 held-out rows, 6 control rows — rate orders with no opening sentence, whose numbers an earlier set or corpus had already drawn) · G6 balance · G8 no opening an earlier set
used 0 · **G9 `kind()` agrees with the generator's family on every row 0** · G10 no held-out value from
an earlier pool. No depth-15 rows are drawn: walk length stays a separate unknown.

**The floor on the new sets** — *open result #1, answer the last page*, through the real runtime and
the real grader (`zero_gpu.json`): headline **5/67**, shared-line 5/22, every value slice **0**,
control **8/78** (rate 0/10).

**The attribution ceiling** (v2 sets, from W5c's recorded walks; all 168 replay exactly): if the base
reads the walk's pages as well as it read the oracle's, the policy reaches **56/66** on that headline
(`withlib` 42, `base-reads` 46) and **75/80** on control (`withlib` 78) — the base is sent 31 and 36
rows, its prompt byte-identical to `base-reads`' on 23 and 27 of them. **So on control the policy is
expected to give a few cases back** (the base misreads 3 of 36 trained-note values where the adapter
misreads 1): a paired tie, not a regression — and if it *is* a regression, the verdict says NOT A
SERVING DESIGN. No ceiling exists for the claim: `withlib` has not walked the new sets.

**Power, said in advance.** The policy changes only the 32 value rows of the 67; the 35 carry rows are
`withlib`'s own records and are concordant by construction. If `withlib` fails the conditional value at
W5c's rate (11 of 15) and the base reads them, the first pair is about 12 : 0. Five gained and none
lost is $p = 0.0625$ — a tie, and it would be reported as one.

## Launch

`adapters.tgz` is **on disk** (157 MB, both W5c adapters, `withlib` sha256 `0f7d872d…`) at
`…/scratchpad/lk-w5c-run/results/M7-W5c-conditional-corpus-20260919/adapters.tgz`. It is git-ignored,
so it reaches the new run directory by hand; the chain uploads `$RUN_DIR/adapters.tgz` in chunks and
unpacks it on the VM. If it were gone, `withlib` would have to be retrained — one A100 session more.

```bash
R=results/M7-W5d-answer-policy-20260920
cp <lk-w5c-run>/results/M7-W5c-conditional-corpus-20260919/adapters.tgz $R/adapters.tgz
tar tzf $R/adapters.tgz | grep nursing-walks-v2-q35/adapter_model.safetensors     # must print one line

GPU=L4 BRANCH=w5d-answer-policy RUN_DIR=$R MODULE=training.nursing.walks_policy \
  MARGS="--concurrency 8" RESULTS_NAME=walks_policy.json BASE=Qwen/Qwen3.5-4B SESSIONS=1 \
  training/harness/chain_serve.sh
```

`BRANCH=main` once this is merged. No `SKIP_ADAPTERS` (the adapter is carried in), no `TRAINDEPS`
(nothing trains). If the log shows `cannot score: adapters/nursing-walks-v2-q35 is not on disk` the
carry-in failed: stop, do not retrain inside this run. A second session resumes every record from
`walks_policy.json`, which says `"finished"` only when the run is decided. Read the pairs from the
JSON, not from the chain's clipped peek (W5 **[ran]**).

## Result **[ran]** 2026-09-20 · FALSIFIED as written — 5 : 0 is a tie, and the eleven that are left are the adapter's own query

One L4 session of the two allowed, ~21 min, scoring 11 min. The first attempt never started: the
account had no premium quota (`chain_attempt0_no_quota.log`). Nothing frozen changed between the freeze
and the run (`git diff bb694a7 origin/main` over the policy, the runner, the sets and this brief: empty).
G1 `applied` 3/3. 0 transport errors, 0 `context`, 0 unreplayable. Read off `walks_policy.json`; the
chain's clipped peek skipped two arms entirely, which is why.

**The claim — the sets written after the freeze.** Headline n = 67 (35 carry + 32 value).

| arm | right | format | unread | wrong | **credit** | value rows (32) | carry rows (35) |
|---|--:|--:|--:|--:|--:|--:|--:|
| `base-reads` — untrained, oracle's notes | 31 | 21 | 0 | 15 | **52** | 31 | 21 |
| `withlib` — the adapter alone | 33 | 4 | 0 | 30 | **37** | 16 | 21 |
| **`policy`** — adapter walks; base writes values | 38 | 4 | 0 | 25 | **42** | 21 | 21 |

Paired, exact two-sided sign test on discordant pairs, $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:

| pair | credit | right-only |
|---|---|---|
| **`policy vs withlib`** — the pair that decides | **5 : 0, $p = 0.0625$ — tie** | 5 : 0, tie |
| `policy vs base-reads` — W5's bar | 6 : 16, $p = 0.052$ — tie | 17 : 10, $p = 0.25$ — tie |
| `withlib vs base-reads` | 6 : 21, $p = 0.006$ — REGRESSION | 17 : 15 — tie |
| control (78): `policy vs withlib` — the no-regression gate | 75 vs 73, 2 : 0 — **holds** | |
| control: `policy vs base-reads` | 75 vs 58, 17 : 0 | |

`passed = false`, `policy_buys_something = false`. **The brief's own power line named this case before
the run — five gained and none lost is $p = 0.0625$, a tie, and it is reported as one.** The verdict is
not softened: on a set written after the freeze the policy does not beat the adapter alone.

Slices: conditional value asked (16) — base-reads 16, withlib 7, **policy 12**; plain value asked (16) —
15, 9, **9**; shared-line (22) — 7, 17, 17; control rate (10) — 3, 10, 10. The policy sent 32 of the 67
headline tasks to the base and kept 35 on the adapter.

**Read where it happens (zero GPU).** The policy changes only the 32 value rows. On the **21 where the
walk opened the supplying note, the base reads it right 21 of 21** (the adapter alone: 16 of 21). The
other **11 are all retrieval misses — and the searcher did what it was asked.** All 11 are `wiki` /
`wiki-parent` rows (11 of the 16 that need a search; the 16 `step` rows need none). Faced with a new
wording — *"how many minutes of pressure does the site get when…"* — the adapter did not search for
that: in 9 of the 11 it wrote, word for word, **a query that occurs 68 times in its training corpus and
belongs to another topic** — `turning an order into a number to set on a pump or a clamp` — walked the
rates shelf, and computed a drip rate (`2 drops per minute`, `67 minutes`). The base, handed those
notes, answered `Not in my library.` — correctly. Replayed with no model: **the same lexical searcher,
given the request's own statement as the query on the wiki shelf, returns the needed note in the top 3
on 16 of 16 of those rows — 11 of 11 of the missed ones** (without the shelf argument: 8 of 16). None of
the 11 was reachable by a link from a note the walk had open (0 of 11): the wanted note is `uses`-linked
only from the held-out step.

So on this set **the reading problem is solved by the policy wherever there is a note to read, and the
binding constraint is the query the adapter writes** — the same disease as the reading failure, one
step earlier: *a model of a generated corpus learns the generator*; here it learned the generator's
queries. The oracle's queries in W4/W5c's corpora were close to the notes' own wording, and the first
two held-out sets kept that wording, which is why they showed 0 retrieval misses.

**The attribution stage — W5c's sets, a first out-of-sample look, not the claim.** With 0 retrieval
misses there, the policy lands exactly on its zero-GPU ceilings: headline **56/66** (withlib 42,
base-reads 46) — `policy vs withlib` 14 : 0, $p = 0.0001$; `policy vs base-reads` 12 : 2, $p = 0.013$;
conditional value 15/15 (withlib 4/15). Control **75/80** against withlib's 78 — 0 : 3, a tie. The
asymmetry between the two stages is the point of writing a set after the freeze: the new wording is
what exposed the query.

**Redesign count of this arm: 0. The instrument's stays 2. W5's verdict stands.**

**What follows — not run; the user's decision.** Each with its prediction and what would falsify it.

1. **The query is the unknown — not the searcher.** Same adapter, same policy, same sets; the runtime
   issues the *first* search of a conversation from the request's own statement (scoped to the shelf the
   adapter names), and the adapter takes over from the listing. One L4 session, no training. *Prediction:*
   retrieval misses on the value rows fall from 11 to ≤ 2 (the zero-GPU replay says the note is listed
   in 16 of 16) and `policy vs withlib` becomes an improvement. *Falsified if* the adapter, shown the
   right note in the listing, still opens another one on ≥ 6 of the 11 — then listing is not enough
   and the walk itself is memorised. Caveat stated now: these sets are seen by us for the policy; a
   pass is attribution, and the claim needs a fresh set. The adapter trained on listings produced by
   *its oracle's* queries; a statement-query listing is a different distribution (the target less often
   first) — report walk mechanics beside credit.
2. **The radar (R0) behind the same interface** answers a different question than the one this run
   raised — it cannot repair a query about the wrong topic — and is worth buying only after 1, on the
   misses 1 leaves. The encoder (0.6B) would be hosted in the runner's process beside vLLM's 4B on one
   24 GB card, not inside vLLM.
3. **The library's own links** as the path to a wiki value: 0 of these 11 were reachable from what the
   walk had open, so links alone would not have helped here; they help when the walk is on the right
   procedure, which these walks were not.
4. **Option E's many-note library regardless** — queries, like conditionals, have to be taught over many
   notes and many phrasings, or left to something that is not the adapter.
