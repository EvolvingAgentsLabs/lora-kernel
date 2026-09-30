# H3 — the tracker member's second corpus against its first

**Written 2026-09-29, before any stage runs.** The user accepted H2's readable conditions as its verdict (reading 1:
harness 146/160, flat; the void comparison and the anchor check kept as instrument errors) and asked to continue.

## What and why

H2's harness member `tr-s0` missed in two places, both read where they happened **[ran]** `results/H2-tracker-harness-20260929`:

1. **QA's final comment, 6/20.** Split by wording: *"Note on it: …"* 1/15, *"Put a comment on it: …"* 5/5. One terse
   eval phrasing the training never showed a shape of; the member re-read the issue or tried a refused transition.
2. **Block-less, the lead's lane 0/20 and half the developer's.** Not "learned in part": the corpus rendered its block-less
   third by `j % 3 == 2`, and the roles rotate by `% 3` too — **all 400 block-less rows were QA's**. The member learned
   block-less exactly the role it was shown (QA 80/80 block-less; lead only `sprint_board`, a call with no argument).

H3 trains `tr-s1` on a second corpus that fixes the cause, not the case:
- training wording widened by two phrasings **per turn in every role** (not only where H2 missed), written without reading
  any model output (`EXTRA_H3` in `examples/tracker/generate_sessions.py`);
- a block-less third of **each** role (165 / 165 / 132 rows).

It is measured on a **fresh** held-out suite — new worlds (seeds from 1,440,000) and wording that neither the training nor
H2's eval uses (gate S5 = 0). **H2's eval is not re-asked**: its wording is what the designer has now read failures on.

## Model, provider, stages

- Base `google/gemma-4-E4B-it` bf16, LoRA recipe `release_gate.RECIPE`, seed 0 — as `tr-s0`.
- **T** (one Colab L4 session): `python -m examples.tracker.h3_arm --train-seed 0` → `adapters/tracker-wf-s1`.
- **S** (one or two L4 sessions): `--arms s0-harness,s1-harness,s1-noblock` — vLLM 0.30, both adapters resident, the gateway
  `--org tracker` with the operational memory and the role's workflow.
- **The baseline is our own previous member, `tr-s0`**, not the bare base (H2 measured that: 4/160).

## The scorer, fixed here

`turn_right_h3`: as H2's `turn_right`, except a turn that needs one statement of a page (`page#anchor`) is right when a page
read **returned** that statement. H2 scored reading the whole page as a miss while the statement sat in what was read.
Applied to every arm. (Rescoring H2's records with it changes no dependent count — the anchor turns are independent:
harness 146/160, base 4/160, no-block 80/160 unchanged.)

## Verdicts (in `h3_arm.reading`, tested in `tests/test_tracker.py`)

Every arm is a trained member, so the per-arm VOID applies to each: **first turns under 90 % → that arm VOID**. It is never
asked of an untrained baseline (H2's lesson).

| | condition | reading |
|---|---|---|
| **H3a headroom** | `s0-harness` dependent ≥ 95 % (≥ 152/160) on the fresh suite | **NO HEADROOM** — reported, never a pass |
| **H3a** | `s1-harness` dependent ≥ 90 % **and** paired against `s0-harness` an improvement (exact sign test, $p \lt 0.05$) **and** loses ≤ 3 turns `s0` got right **and** flat, $\bar p_5 \le 1.1\,\bar p_1$ | **PASSED**, else **FALSIFIED** |
| **H3b** | `s1-noblock` loses ≤ 8 of the dependent turns `s1-harness` gets right (H2's bar, 5 %); reported by role | **PASSED**, else **FALSIFIED** |

**Falsified** if the second corpus does not beat the first on turns it has not seen phrased — the widened wording bought
nothing a fresh reader can see — or if block-less still fails a role whose rows it now has.

## Stopping condition

One training, one measurement. A redesign of the suite, the scorer or the bars after S has started is not allowed; a
transport error re-plays the session (resume), it is never scored. If `s0-harness` has no headroom, H3a is reported as
such and H3b stands alone.

## Not in this run

The attribution arm (`s0-noblock` on the fresh suite, to split the role fix from the wording fix) — bought only if H3b
passes. H2's eval with `tr-s1` — its wording is no longer held out from the designer.

## Run log

- **T attempt 1 (L4), 2026-09-29 19:58–20:59 — ended by Colab's sixty-minute cap** at step 114/264 of training: the boot took
  ~37 min (attempt 1 silent, attempt 2 installed), training needs ~50 min on an L4 (H2's `tr-s0`: 50 min, which fit only
  because its boot was short). Nothing scored; `T_attempt1_L4_ttl.log`.
- **T attempt 2 on an A100** — same recipe, same corpus, same seed, bf16 on both cards; the card changes the arithmetic's
  order, not the recipe. Stated here before it runs. S stays on an L4, as H2's.

## Result [ran] — H3a PASSED, H3b PASSED

T attempt 2 on an A100 (seed 0, 1,400 rows, 264 steps, ~32 min); S on one L4 session, G1 both members applied, 0 transport
errors, no arm void. `h3.json`, `train_tr_s1.json` (corpus and adapter sha256).

| arm | first | dependent | independent | $\bar p_1 \ldots \bar p_5$ |
|---|---|---|---|---|
| `s0-harness` (`tr-s0`, H2's member) | 60/60 | **147/160** (91.9 %) | 49/60 | 1619 · 1221 · 967 · 1090 · 1275 |
| `s1-harness` (`tr-s1`) | 60/60 | **158/160** (98.8 %) | 60/60 | 1465 · 1219 · 958 · 1086 · 1275 |
| `s1-noblock` (`tr-s1`, no tool block) | 59/60 | **156/160** (97.5 %) | 60/60 | 503 · 359 · 285 · 326 · 380 |

- **Headroom:** `tr-s0` at 147/160 is under the 95 % ceiling — the comparison is readable. It is H2's number again
  (146/160) on a suite it had never seen phrased: the fresh suite is not easier.
- **H3a PASSED:** `tr-s1` 158/160 against `tr-s0` 147/160 on the same turns, **11 : 0**, exact sign test $p = 0.00098$,
  **0 lost**, flat ($\bar p_5 = 1275 \le 1.1 \cdot 1465$).
- **H3b PASSED:** block-less loses **4** dependent turns to the block (bar 8) — developer 76/80, lead 40/40, QA 40/40. H2's
  block-less, whose rows were all QA's, got 80/160. It reads **~3× fewer prompt tokens** per turn (285–503 against 958–1465).

**Read where it happens.**
1. `tr-s0`'s 13 dependent misses: the developer's component owner (10/20 — "Who do I ask about its component?" / "Its
   component — who owns it?"), one developer comment, two QA comments. On the fresh wording QA's comment is 18/20: H2's
   6/20 was the one phrasing.
2. `tr-s1`'s 2 misses are one case: *"Annotate it: ready for QA"* — the note's text read as an instruction, and it tries
   `issue_transition → qa`, which the tool layer refuses. A real miss, new: text **inside** an argument taken as a command.
3. `s1-noblock`'s 4 dependent misses are **one session**: its first turn, "Details on RD-220?", called `page_read`
   (`components#rd-220`) instead of `issue_get`; nothing was `put`, and the four dependent turns found an empty memory
   (`get issue` → `no key issue`). A first-turn error cascades — the harness's failure mode, not reference resolution.
4. The anchor-by-result scorer credited 9 turns of `tr-s0` (independent, QA's "where must tests pass?"), 0 of `tr-s1`: it
   does not carry H3a, which is decided on dependent turns.

**Not bought:** the attribution arm (`s0-noblock` on the fresh suite). H2's gate already names the cause — `tr-s0` saw no
block-less row outside QA — so the arm would price a number whose reason is on disk.

**What it means.** The member is its corpus: widening the wording per turn and rendering a block-less third of every role
took the tracker member to 158/160 with the block and 156/160 without it, on turns no corpus and no designer had seen
phrased. The block-less member is the compact context the user's design asked for — one line of state, the keys, no tool
schema — at a third of the tokens.
