# M7 W5b — composition: the adapter walks, the bare base writes the final line (pre-registered 2026-09-19)

**Question (one unknown: who writes the last line).** W5 did not pass **[ran]**
(`results/M7-W5-kill-arm-20260919`): `withlib` 35/56 against the untrained base reading the oracle's
notes, 45/56 (6 : 16, $p=0.052$). Read where it happens, 12 of `withlib`'s 21 headline failures are
quantity rows on a **clean walk** — the right note opened, the guard silent, no retrieval miss — whose
final line carries the wrong one of the two values the held-out note states (11 asked
`anticoagulant_minutes`: 0/11), while the untrained base is right on all 12 and **0 of 108** training
quantity rows ever read a note with two values. Diagnosis: *the adapter navigates, and stopped reading
the condition.* **On the same recorded walks, if the bare base writes the final line from the pages
the walk opened, do those failures go?**

**This is attribution, not a second attempt at W5.** W5's verdict stands as recorded. These 80 cases
have been read one by one; a serving design built on this arm (*the LoRA navigates, the base reads*)
needs its own held-out set, written after its freeze, before anything is claimed for it.

**Prediction and falsifier — fixed in W5's brief before this one.** Of `withlib`'s 12 clean-walk
quantity failures, **≤ 2 remain** without credit → the diagnosis HOLDS. **≥ 6 remain** → FALSIFIED: it
was not the reading. 3–5: undecided, said so.

**The arm.** `composed` — `training/nursing/walks_composed.py`. The walk is **replayed, not
regenerated** (vLLM is not deterministic at temperature 0: a fresh walk is a second unknown): each
recorded `withlib` walk is run again through a fresh referee with the case's own seed and accepted
only if every recorded result comes back byte for byte — the ids shown are drawn from the whole
history, so they are a checksum of it. The pages that walk opened (opens and calcs that returned a
page; refused calls and search listings are not pages), in the order opened, behind the carried page
if the case has one, are put before the **bare base** exactly as `base-reads` is served:
`walks_arm.SYSTEM_READS`, the same layout, 320 tokens, no verbs, thinking off. Graded by the untouched
`grade_walks.grade`: the final line is the base's, the **walk evidence is the replayed walk's** — so
`unread` still applies and a walk the referee cut still earns nothing.

**What could be known with zero GPU, and is [ran] (`ceiling.json`, held by
`tests/test_walks_composed.py`).**

| | |
|---|--:|
| recorded walks that replay exactly (the record kept them whole) | 115 / 140 |
| lost head (the record keeps the last 1500 characters) rebuilt from a prefix of the oracle's plan, **proven** by replay | 11 |
| lost head holding only searches — every opened page still in the record verbatim, notes identified by content, `walk_ok` equal to the record's | 8 |
| **unreplayable — excluded from every slice, for every arm** | 6: `w5h-012`, `w5h-033` (headline) · `w5h-016`, `w5h-041`, `w5h-045`, `w5h-059` |
| **headline for this arm** | **54** of 56 |
| on those 54: `base-reads` · `withlib` · `nolib` · `base-walks` | 45 · 33 · 2 · 0 |
| headline walks that are clean (`walk_ok`) | 45 |
| **ceiling** — clean walk AND `base-reads` has credit | **41 / 54** |
| headline walks whose opened set is the oracle's walk · whose served turn is **byte-identical** to `base-reads`' | 37 · 30 |
| of the 12 quantity failures, served a turn byte-identical to one `base-reads` already got right | **10** |

Three things follow, and are said before the run:

1. **The exclusion is not neutral and its direction is known.** Both excluded headline cases are ones
   `withlib` won and `base-reads` lost. On the 54, `withlib vs base-reads` reads **4 : 16, $p=0.012$ —
   a regression**, where W5's 56 read 6 : 16, $p=0.052$, a tie. W5's verdict is W5's; this brief does
   not re-read it, and every pair below is on the 54 for every arm.
2. **`composed` cannot beat `base-reads`.** Its ceiling is 41 against 45: the walk is not clean on 9 of
   the 54, and no reader repairs a place found wrong (the 8 `carry/middle-find` failures stay). The
   best this arm can do on W5's bar is lose by less.
3. **The prediction is close to a determinism check, and is worth what that is worth.** For 10 of the
   12, the base will be asked the very turn it already answered correctly. What the run adds is the
   other 2, the 4 cases at risk (`w5h-006`, `-019`, `-030`, `-035`: `withlib` has credit, `base-reads`
   did not on the oracle's pages), the control set, and — on the 95 turns identical to `base-reads`' —
   a free measurement of how often vLLM gives the same credit twice.

**Verdict pairs, headline (n = 54), by CREDIT (`right` or `format`), paired by case id, exact
two-sided sign test on discordant pairs (FOUNDATIONS §7.1),
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, different at $p<0.05$:**

| pair | reading |
|---|---|
| `composed vs withlib` | must be an **improvement** for composition to be worth anything. Power, said now: gaining all 12 and keeping the 4 at risk is 12 : 0, $p=0.0005$; gaining 12 and losing the 4 is 12 : 4, $p=0.077$ — **a tie**. A tie here is reported as a tie |
| `composed vs base-reads` | W5's bar, read as W5 read it: the spec says *beats*. It cannot (ceiling 41 < 45); reported with totals |
| `composed vs nolib` | reported |

Beside them, never folded in: the same side slices as W5 (shared-line, depth-15, quantity by layer,
control with and without `rate`), `context`, `format`, `unread`, transport errors, and agreement with
`base-reads` on identical turns.

**Models.** `Qwen/Qwen3.5-4B`, bare, bf16, **vLLM on Colab**; no adapter is served (`SKIP_ADAPTERS=1`),
no API provider is called. The four W5 arms are **copied in from the committed `walks_arm.json`,
never re-run**; the W5 file is never written to (a test holds that). Results:
`results/M7-W5b-composition-20260919/walks_composed.json`.

**Parameters.** Temperature 0, 320 tokens, no stop strings, thinking off, window 8192 (a prompt that
outgrows it is `context`, not an error), concurrency 8.

**Cost.** One L4 session, ~10 minutes of scoring (140 single calls). **Ceiling: 2 sessions.** W5 used
4 of its 6; this arm opens its own budget of 2 and does not draw on W5's.

**Abort rule.** No `[arm] composed` progress line for 8 minutes after the base is up → stop the
session, fetch the partial file (records persist every 20), relaunch once to resume.

**Redesign count: 0.** Stopping condition: the prediction, the falsifier, the 54 and the pairs are
fixed above; a change to any of them after a number is seen ends the step as *undecided*.

**Launch** (`BRANCH=w5-composition` until this is merged, then `main`):

```bash
GPU=L4 BRANCH=w5-composition RUN_DIR=results/M7-W5b-composition-20260919 MODULE=training.nursing.walks_composed \
  MARGS="--concurrency 8" RESULTS_NAME=walks_composed.json BASE=Qwen/Qwen3.5-4B SKIP_ADAPTERS=1 SESSIONS=1 \
  training/harness/chain_serve.sh
```
