# M7 · W5c — the corpus-shape arm: does a corpus that shows a conditional value teach the expert to read one? (pre-registered 2026-09-19)

**Question (one unknown: the corpus's shape).** W5 **[ran]**: the library arm walked cleanly to the
held-out note and wrote the wrong one of its TWO values — the conditional value **0 of 11**, the plain
one 11 of 12 — while the untrained base read all of them. W5b **[ran]**: with the bare base writing the
last line, **0 of those 12** failures remain; and composition loses 0 : 19 on what the adapter trained
on, so it is not a serving design. Of the first corpus's 108 quantity rows, **0** read a note that
states two values of one quantity. *A corpus with one difficulty teaches a floor.* **Same base, same
recipe, same library shelves, same held-out procedure — a corpus in which a note states a quantity and
a second value of it under a condition, asked both ways in equal shares: does the adapter now read the
condition on a procedure it never trained on?** ([`docs/MEMORY.md`](../../docs/MEMORY.md) W5, W5c.)

**The prediction, fixed by W5's brief before this arm existed:** the conditional quantities recover;
`carry/middle-find` does not (the place is found by the walk, and nothing here teaches that).

**Falsification — an exact test, decided now** (`walks_arm.conditional_reading`). On the new held-out
set's conditional-value slice (n = 15), the v2 library arm's credit $x$ is compared with the first
corpus's 0 of 11 by a one-sided Fisher exact test,
$p = \sum_{k \ge x} \binom{n}{k}\binom{n_0}{K-k} / \binom{n+n_0}{K}$ with $K = x + 0$, $n_0 = 11$:

| credit on the conditional slice | $p$ | reading |
|---|--:|---|
| **≤ 4 of 15** | ≥ 0.091 | **FALSIFIED** — indistinguishable from 0/11: showing the shape did not teach reading it; the fault is not the corpus's shape, or not only |
| 5 – 11 of 15 | ≤ 0.046 | PARTIAL — distinguishable from the first corpus, under the 80 % absolute standard |
| **≥ 12 of 15** | ≤ 0.00005 | **RECOVERS** |

Beside it, never instead of it: the same slice for `base-reads` (W5: right on all 12 rows the adapter
failed), the plain-value slice (it must not fall: a corpus that teaches "the second number" has taught
another floor), explicit against implicit statements of the condition, and `carry/middle-find` against
W5's 6 of 14 (two-sided Fisher; predicted: no difference).

**W5's verdict is asked again, as W5 asked it, on the NEW headline.** `withlib vs nolib` and
`withlib vs base-reads`, paired by case id, exact two-sided sign test on discordant pairs,
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, different at $p<0.05$, success = credit
(`right` or `format`, `grade_walks`, untouched). The spec says *beats*; **a tie is a tie** and reads
NOT PASSED, with `base-walks` printed beside it as the price of navigation. W5's recorded verdict is
not re-read whatever happens here: this is a new arm on a new set.

**Arms, in the order bought.**

| # | arm | session | why now |
|---|---|---|---|
| 0 | `base-reads` · `base-walks` on the new sets | S0, L4, no training, ~15 min | **headroom first.** If `base-reads` has credit on **≥ 61 of 66** headline rows at most 5 pairs can be discordant and 5 : 0 is $p = 0.0625$ — no trained arm can beat it; stop before training (coded: credit ≥ n − 5, which at n = 56 is W5's 51) |
| 1 | `withlib` on corpus v2 — train only | SA, A100, ~45 min | the treatment |
| 2 | `nolib` on the v2 twin — train only | SB, A100, ~35 min | the control that isolates the library |
| 3 | score `nolib`, `withlib` (S0's records resumed) | SC, L4, ~25 min | the verdict and the falsifier |

**Not bought:** R0/R1 retrieval (the searcher is the lexical one the corpus was generated with); the
first corpus's adapter on the new set (its 0/11 is recorded; re-serving it is an attribution arm, bought
only if this one leaves something to attribute); W5's 80 rows as evidence — they may be scored as a
regression check and are reported as that and nothing else.

**Where the second value comes from — and the caveat that goes with every number here.**
**A — one real note.** `wiki/…/rates/drop-factor` now carries the chapter's own sentences, byte-checked
against the page (`source.PROSE`): *"A macro-drip infusion set delivers 10, 15, or 20 drops per
milliliter, whereas a micro-drip infusion set delivers 60 drops per milliliter."* One quantity (a set's
drop factor), two values, one condition (which kind of set). The macro value is a list in the
textbook; a unit stocks one set, so a site or a case names it (10 or 15 in the corpus, 20 reserved for
the control) and the micro value stays the textbook's 60 — a constant, hence memorisable, which is why
this note alone would not be a test. **B — sentences a site ADDS** (`Site.adds`, new in
`memory/layers.py`; `library.SITE_RULES`; shipped as the example site `unit-4c`): four rules over seven
notes of both trained procedures — cap cleansing (3 notes), patency flush (2), y-port cleansing (1),
reassessment time (1). **They are invented example content, approved as such by the user, marked as
invented in the site file, the library README and the builder; only the condition's wording is fixed,
every number is drawn per case.** The textbook layer is not altered to say anything its source does
not say. So: 30 conditional training rows stand on a real sentence and 123 on invented ones; the
held-out note the verdict is read on is real and untouched.

**Suite — NEW, written after the generator was frozen.** `training/nursing/data_walks_v2/`:
`eval_heldout.jsonl` (**88**, all on `discontinue-iv`, all within the trained depth ≤ 9 — W5's two
deeper rows were a second unknown and are not drawn) and `eval_control.jsonl` (**80**). New openings,
new asks, new value pools (hold 3/5/7/10, anticoagulant 14/16/18/22/30 — W5's were 4–12 and 11–25), a
control from windows, values and topics the v2 corpus refuses. A 14-step procedure has finitely many
windows and W5 walked most of them: a v2 case is new by its **statement and its world**, never by its
window alone — gate G5 asserts no v2 evaluation statement or (statement, values) pair is one of W5's
140. **Headline = held-out, final line the procedure's own: n = 66.** Beside it: shared-line (22),
quantity by layer (25 site/case · 6 textbook), **conditional value asked (15) · plain (16)**, explicit /
implicit condition, control (80; 68 without `rate`, 12 `rate`), retrieval misses, `unread` / `format` /
`context`.

**The corpus, gate PASSED [ran]** (`gate.json`, zero GPU): 600 rows + the no-library twin; families
{"conditional": 153, "none": 56, "carry": 222, "quantity": 44, "rate": 125}; **153 conditional rows** over 8 notes (5 quantities, 30–31 each), the conditional value asked
75/153, the condition implicit 76/153, **"copy the first number on the page" is worth 0.51**
(held-out 0.516, control 0.5); 192 rows in a unit with no added rule, so the single-valued page
survives; dead ends 30; G1 value-in-statement 0 · G2 evaluated-walk-in-corpus 0 · G3 held-out note
opened 0 of 600 (17 held-out-only notes) · G4 every row replays through the referee in `strict`, 0
failures of 768 · G5 a-W5-case 0 · G6 ok · G7 ok. Each clause is shown able to fail
(`tests/test_walks_v2.py`). Rows fit: longest 1373 of 1536 tokens under the base's tokenizer (held-out
936, control 1263), 0 over. v1's files have not moved (`generate_walks --check`).

**The floor, zero GPU [ran]** (`walks_arm --data … --floor`, `floor.json`) — open the first result,
follow `next`, repeat the last page: **headline 6 / 66 · shared-line 5 / 22 · conditional 0 / 15 ·
plain 0 / 16 · control 6 / 80 (0 / 12 on `rate`)**. The headroom stop is **61 of 66**.

**Models.** Base `Qwen/Qwen3.5-4B`, Hugging Face weights, bf16, served by **vLLM on Colab**; no API
provider is called. Adapters: QLoRA, `release_gate.RECIPE`, `training.harness.train_one` (renames the
tensors for serving), directories `adapters/nursing-walks-v2-q35` and `…-nolib-v2-q35` — never W5's.
Thinking off in every render.

**Parameters.** As W5: temperature 0; 160 tokens a step for a walking arm, 320 for an arm with no
verbs; window 8192; the referee in `strict`; up to 64 calls. Runner: `training.nursing.walks_arm`,
**parameterised** (`--data`, `--tag`), not copied; it keeps the whole walk and the opened ids.

**Cost.** Four Colab sessions, no provider dollars. **Ceiling: six.**

**Abort rules.** S0: stop if `base-reads` ≥ 61/66 (coded). Training: watched by the **step bar**
(`N/114 [..<..]`, which the chain's peek shows) — no step for 10 minutes ends the session; the trainer
prints no loss line and none is waited for. Scoring: no `[arm]` line for 8 minutes after the base is
up. A session that dies before its adapter is home is relaunched once.

**Redesign count: 0 for this arm; the instrument's stays 2** (`gate.json`). This is a new arm of the
experiment — a corpus and a held-out set — not a redesign of the grader, the verdict or the runner's
rules; the headroom rule is W5's, restated for any n. A third redesign of the instrument ends the step.

**Not measured.** Whether the invented conditions resemble any real unit's; retrieval by embeddings;
walk lengths beyond training; any subdomain but this one; the saving in money.

## Launch — the headroom session first, then three

`R=results/M7-W5c-conditional-corpus-20260919`, `D="--data training/nursing/data_walks_v2 --tag v2"`,
every line through `training/harness/chain_serve.sh` (`BRANCH=w5-arm2-conditional` until this is
merged, then `main`):

```bash
# S0 — headroom, no training
GPU=L4 BRANCH=main RUN_DIR=$R MODULE=training.nursing.walks_arm MARGS="$D --arms base-reads,base-walks" \
  RESULTS_NAME=walks_arm.json BASE=Qwen/Qwen3.5-4B SKIP_ADAPTERS=1 SESSIONS=1 training/harness/chain_serve.sh
# SA — train the library arm          (then: cp $R/adapters_out.tgz $R/adapters.tgz)
GPU=A100 BRANCH=main RUN_DIR=$R MODULE=training.nursing.walks_arm MARGS="$D --train withlib --stop-after-training" \
  RESULTS_NAME=walks_arm.json BASE=Qwen/Qwen3.5-4B TRAINDEPS=1 SKIP_ADAPTERS=1 SESSIONS=1 training/harness/chain_serve.sh
# SB — train the no-library arm, the first adapter carried in   (then copy the tarball again; it must list BOTH)
GPU=A100 BRANCH=main RUN_DIR=$R MODULE=training.nursing.walks_arm MARGS="$D --train nolib --stop-after-training" \
  RESULTS_NAME=walks_arm.json BASE=Qwen/Qwen3.5-4B TRAINDEPS=1 SESSIONS=1 training/harness/chain_serve.sh
# SC — score: both adapters carried in, S0's records resumed
GPU=L4 BRANCH=main RUN_DIR=$R MODULE=training.nursing.walks_arm MARGS="$D --arms base-reads,base-walks,nolib,withlib" \
  RESULTS_NAME=walks_arm.json BASE=Qwen/Qwen3.5-4B SESSIONS=1 training/harness/chain_serve.sh
```

Read the pairs and `verdict.conditional_value` from `walks_arm.json`, never from the chain's peek: it
shows the last three matching lines and clipped a verdict line in W5 **[ran]**.
