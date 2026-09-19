# M7 · W5 — the kill arm: does a library extend an expert to a procedure it never trained on? (pre-registered 2026-09-19)

**Question (one unknown: the library).** Two adapters on `Qwen/Qwen3.5-4B`, same 600 cases, same
recipe — one trained on walks through the note library (`train.jsonl`), one on the same cases with no
verbs and no notes (`train_nolib.jsonl`). Served on **`discontinue-iv`**, the procedure no training
row ever opened (0 of 600, W4 G3), *as walks through the referee*: **does the library arm beat the arm
without one — and beat the untrained base reading the very notes an oracle walk opens?**
([`docs/MEMORY.md`](../../docs/MEMORY.md) W5.)

**Falsification — the memory stops at this model size if, on the headline subset, either pair is not
an improvement:** `withlib vs nolib`, `withlib vs base-reads`. Also void, not failed: an adapter not
applied (G1), or any headline record lost to transport. Paired by case id, exact two-sided sign test
on discordant pairs (FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, different
at $p<0.05$; success of a record is **credit** = `right` or `format`
(`training/nursing/grade_walks.py`).

**A structural fact about the second pair, said before the run.** `base-reads` is handed the oracle's
navigation for free; `withlib` has to navigate by itself and then read. So a *tie* on that pair means
learned navigation reached what oracle navigation reaches, and only a *loss* means training cost
something. The spec says *beats*, and the verdict is coded as the spec says. If the pair ties, this
brief does not soften it: the verdict reads NOT PASSED, the `base-walks` arm (the same untrained base,
made to navigate by itself) is printed beside it as the price of navigation, and the decision is the
user's.

**Arms, in the order bought.**

| # | arm | session | why now |
|---|---|---|---|
| 0 | **`base-reads`** — untrained base, oracle's notes open (rendered by the runtime executing the oracle's plan), no verbs · **`base-walks`** — untrained base under the member's prompt and verbs | S0, L4, no training, ~15 min | **headroom first.** If `base-reads` already has credit on **≥ 51 of 56** headline rows, at most 5 pairs can be discordant and 5 : 0 is $p=0.0625$: no trained arm can *beat* it. The run stops there, before any training is paid for, and the decision goes to the user |
| 1 | **`withlib`** — train only | SA, A100, ~45 min | the treatment |
| 2 | **`nolib`** — train only | SB, A100 (rows are one line: minutes) | the control that isolates the library |
| 3 | score `nolib`, `withlib` (S0's records resumed from the results file) | SC, L4, ~25 min | the verdict |

**Suite.** `training/nursing/data_walks/eval_heldout.jsonl` (80) and `eval_control.jsonl` (60), written
after the generator was frozen (W4 G2: 0 evaluated cases in the corpus). **Headline = held-out rows at
depth ≤ 9 — the deepest walk in training — whose final line no other procedure states: n = 56.**
Reported beside it and never folded in: the **2** depth-15 rows (walk-length generalisation is a second
unknown); the **22** rows ending on a shared line; held-out quantity by layer — **17** site/case
against **6** textbook (a textbook value is common clinical knowledge); control **with and without its
15 `rate` rows** (the two rate formulas are nursing-school arithmetic a base may know); **retrieval
misses**, counted apart from the expert's score — the searcher is the **lexical** one the corpus was
generated with, because radar R0 did not pass W3 (recall@3 0.638 < 0.80), so an expert is not blamed
for a note it was never shown; a **`context`** bucket (the prompt outgrew the window) distinct from
wrong; a **`format`** bucket (right content, untaught final line — fluids on the 4B lost 10/90 that
way); **`unread`** — a right answer whose supplying note the walk never opened, which earns the
library arm no credit; transport errors, never a score.

**The floor, zero GPU [ran]** (`python -m training.nursing.walks_arm --floor`, `floor.json`): the
trivial policy *open result #1 (or the carried page's `next`), follow a skeleton to its first step,
answer the last page*, through the real runtime and the real grader —
**headline 3 / 56 · held-out shared-line 6 / 22 · control 11 / 60 (0 / 15 on `rate`)**. An arm at the
floor has learned nothing. The oracle, through the same function the model goes through, is 140 / 140
`right` with its walk read (`tests/test_walks_arm.py`).

**Models.** Base `Qwen/Qwen3.5-4B`, Hugging Face weights, bf16, served by **vLLM on Colab** with both
adapters resident (`--enable-lora --max-loras 2`); **no API provider is called**. Adapters: QLoRA,
`release_gate.RECIPE`, trained by `training.harness.train_one`, which names the tensors for the class
vLLM serves (D2). Thinking off in every render. The walking arms are served the user turn the corpus
taught — asserted byte-equal to the stored turn before a token is generated.

**Parameters.** Temperature 0; 160 tokens a step for an arm that walks, stopping at a closing verb tag,
result written inline; 320 tokens for an arm with no verbs, no stop strings; up to 64 calls, the
runtime's own budgets (48 opens, 12 searches) deciding first; `strict` guard; window 8 192 tokens, a
prompt that would exceed it is `context`, not an error; concurrency 8; ids re-drawn per conversation
from the row's seed.

**Cost.** Four Colab sessions, no provider dollars. **Ceiling: six sessions.**

**Abort rules.** S0: stop after `base-reads` if credit ≥ 51/56 on the headline (coded:
`verdict.no_headroom`). SA/SB: the trainer prints no loss line — watch the **step bar** the chain's
peek now shows (`n/114 [mm:ss<…]`); kill if it has not moved for 10 minutes, or if no
`adapters_out.tgz` exists at minute 52 of the session. SC: if G1 reads *not applied* the runner stops
itself. vLLM is not deterministic at temperature 0: read a verdict beside its pair, never off a total.

**Redesign count: 0** for this runner. (The grader it reads is redesign 2 of W4's instrument — see
W4's brief. A redesign of this verdict after an arm has been seen ends the step as *not passed*.)

**Not measured.** Retrieval by embeddings (R0/R1); walk lengths beyond training, as a claim; any second
subdomain; the `recover` guard mode; the money.

## Launch — three commands, plus the headroom session that goes first

```bash
R=results/M7-W5-kill-arm-20260919
# S0 — headroom: the two untrained-base arms. No adapters, no training.
GPU=L4 BRANCH=main RUN_DIR=$R MODULE=training.nursing.walks_arm MARGS="--arms base-reads,base-walks" \
  RESULTS_NAME=walks_arm.json BASE=Qwen/Qwen3.5-4B SKIP_ADAPTERS=1 SESSIONS=1 training/harness/chain_serve.sh
#    → read `verdict.reading`. NO HEADROOM stops the step here.

# SA — train the library arm (train only; the adapter is fetched while the session lives)
GPU=A100 BRANCH=main RUN_DIR=$R MODULE=training.nursing.walks_arm MARGS="--train withlib --stop-after-training" \
  RESULTS_NAME=walks_arm.json BASE=Qwen/Qwen3.5-4B TRAINDEPS=1 SKIP_ADAPTERS=1 SESSIONS=1 training/harness/chain_serve.sh
cp $R/adapters_out.tgz $R/adapters.tgz

# SB — train the no-library arm; the first adapter is carried in, and both are packed
GPU=A100 BRANCH=main RUN_DIR=$R MODULE=training.nursing.walks_arm MARGS="--train nolib --stop-after-training" \
  RESULTS_NAME=walks_arm.json BASE=Qwen/Qwen3.5-4B TRAINDEPS=1 SESSIONS=1 training/harness/chain_serve.sh
cp $R/adapters_out.tgz $R/adapters.tgz        # must now list BOTH adapter directories: tar tzf

# SC — score. Both adapters carried in; S0's records are resumed from walks_arm.json.
GPU=L4 BRANCH=main RUN_DIR=$R MODULE=training.nursing.walks_arm MARGS="--arms base-reads,base-walks,nolib,withlib" \
  RESULTS_NAME=walks_arm.json BASE=Qwen/Qwen3.5-4B SESSIONS=1 training/harness/chain_serve.sh
```

A session that ends with the run undecided writes `"trained_only"` — the chain's marker for *this
session is over, the run is not* — and the next session carries the results file in; only a decided
run writes `"finished"`, which the chain reads as *no further sessions*.

## Result **[ran]** 2026-09-19 · DOES NOT PASS W5 AS WRITTEN — the library arm ties the untrained base that reads, and the tie leans to a loss

Four Colab sessions of the ceiling of six: S0 (L4, headroom, 15 min), SA and SB (A100, one training
each, 114 steps, ~45 min; both adapters `named for serving`, 256 tensors), SC (L4, scoring, 21 min; S0's
280 records resumed, nothing re-run, nothing retrained). G1 `applied` 3/3 on both adapters. 0 transport
errors, 0 missing records, 0 `context` in any arm on any slice. Read off `walks_arm.json`.

**Headline — held-out procedure, depth ≤ 9, final line the procedure's own, n = 56.**

| arm | right | format | unread | wrong | **credit** |
|---|--:|--:|--:|--:|--:|
| `base-reads` — untrained base, the oracle's notes open | 23 | 22 | 0 | 11 | **45** |
| `base-walks` — untrained base, navigating by itself | 0 | 0 | 0 | 56 | **0** |
| `nolib` — trained, no verbs, no notes | 2 | 0 | 0 | 54 | **2** |
| **`withlib`** — trained on the habit of navigating | 30 | 5 | 1 | 20 | **35** |
| trivial policy (floor, zero GPU) | | | | | 3 |

**The pairs**, by case id, exact two-sided sign test on discordant pairs,
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:

| pair | only a : only b | $p$ | state |
|---|--:|--:|---|
| `withlib` vs `nolib` | 35 : 2 | ≈ 0 | **improvement** — the library is what the trained expert answers from |
| **`withlib` vs `base-reads`** | **6 : 16** | **0.052** | **tie** — and 16 of the 22 discordant cases are the base's. The verdict asks for *beats*: **not passed** |
| `withlib` vs `base-walks` | 35 : 0 | ≈ 0 | improvement — the price of navigation, untrained, is everything |

As the brief said before the run: this pair ties, the verdict is not softened, the decision is the
user's. **Redesign count of W5: 0. The grader is not touched.**

**Beside the headline, never folded in** (credit):

| slice | n | `base-reads` | `base-walks` | `nolib` | `withlib` |
|---|--:|--:|--:|--:|--:|
| held-out, final line shared with another procedure | 22 | 9 | 0 | 0 | **18** |
| held-out, depth 15 (deeper than any trained walk) | 2 | 2 | 0 | 0 | 0 |
| held-out quantity, site / case layer | 17 | 17 | 0 | 2 | 9 |
| held-out quantity, textbook layer | 6 | 6 | 0 | 0 | 2 |
| control (trained procedures) | 60 | 41 | 2 | 20 | **58** |
| control without `rate` | 45 | 34 | 2 | 8 | 43 |
| control `rate` | 15 | 7 | 0 | 12 | 15 |

Walking mechanics over all 140 walks: `withlib` 3 refused verbs, 0 malformed, 0 ran out, 4 retrieval
misses (0 on the headline); `base-walks` 368 refused, 6 ran out, 30 retrieval misses.

**Where the 21 headline failures are — read from the records, zero GPU.**

- **12 are `quantity`, and they are one failure.** In all 12 the walk is clean — the right note opened,
  the guard silent, no retrieval miss — and `base-reads` is `right` on all 12. The held-out procedure
  is the only one whose note states **two values for one quantity**: pressure for *n* minutes, *m* for a
  patient on anticoagulants. Asked the first value the adapter is right **11 of 12**; asked the second
  it is right **0 of 11** — it answers the first (`12 minutes` where 20 was asked) or recites both
  (`12 minutes (15 minutes for a patient on anticoagulant medication)`). The twelfth is a range cut
  short (`2 minutes` for `2-3 minutes`). **Of the 108 trained quantity rows, 0 read a note with more
  than one value** (cap seconds, flush mL). A corpus with one difficulty teaches a floor: the adapter
  learned *copy the number on the note*; the untrained base reads the condition.
- **8 are `carry/middle-find`** (8 of that variant's 14): entering a procedure in the middle with the
  page hidden, the place is found one step off or the walk stays on one step. `base-reads`, handed the
  right notes, is also wrong on 5 of these 8 — this is the hard variant for everyone.
- **1 is `unread`**: the right line, from a walk that never opened the note that states it. No credit,
  by the rule written before the run.

**What did transfer.** Navigation of a procedure never walked in training: 0 retrieval misses on the
headline, 3 refused verbs in 140 walks against the untrained base's 368, 35 : 0 against that base
navigating by itself. And where the base that reads is weakest — the shared-line rows, 18/22 against
9/22; control, 58/60 against 41/60 — the adapter is ahead. What did not transfer is *reading a kind of
note the corpus never showed*.

**The live peek clipped a verdict line.** The chain shows the last three matching lines; four were
printed in a burst and `withlib vs nolib` never reached `SC_chain.log`. The pairs are read from the
JSON, as every verdict is.

**What follows — not run, the user's decision.** Two arms, each with its prediction and what kills it:

1. **Composition — no training, one L4 session. Bought first; it is the cheap one.** The adapter walks;
   the *bare base* writes the final line from the notes the walk opened (same vLLM, the LoRA simply not
   named for the last call). *Prediction:* the 12 quantity failures fall to ≤ 2 and the pair with
   `base-reads` becomes a tie in totals or better. *Falsified if* quantity stays wrong — then the
   failure is not the reading, and this section's account is wrong.
2. **Corpus shape — two A100 sessions.** Two-valued and conditional notes added to the *trained*
   procedures' rows, retrain, score on a **new** held-out set written after the freeze — never again
   on these 80. *Prediction:* quantity recovers, `carry/middle-find` does not. *Falsified if* the
   second value is still missed after the corpus shows the shape.
