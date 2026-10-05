# RFT0 — rejection-sampling fine-tuning: the member's own walks, kept where the strict grader verifies them

**Written 2026-10-05, after the sampler and its gate were frozen (code and tests) and before anything is sampled,
trained or scored.**

## What and why

The real-document member `real-none-s0` (REAL4 **[ran]**, the served member) misses about a quarter of the answerable
rows of a fresh family under the served runtime — 34/44 on PAGE0's set with `page_top = 8` **[ran]**, 33/44 in FMT0's
session on the same rows **[ran]** — and the failure that survives every runtime change is **the wrong statement cited on
the right page** (6 of PAGE0's 10 top-8 misses **[ran]**). Three supervised corpus lines aimed at it changed nothing:
REAL6 (one-hop repeated values, tie 1 : 1 **[ran]**), REAL7 (decoys across a link, tie 4 : 4 **[ran]**), FMT0 (the served
page form plus recovery, tie 1 : 1 **[ran]**). All three trained the member on **the oracle's walks**. By the rule on
counting redesigns, a fourth oracle corpus is not bought.

What none of them did is train on **the member's own walks, scored by the verifier**. Hugging Face's multi-harness result
**[read]** is that SFT on demonstrations plateaued below RL against a verifier on the same tasks. The cheapest
falsifiable version of "RL against a verifier beats SFT on oracle walks" is **on-policy rejection sampling** (RFT): sample
the served member on the questions it was trained on, keep the walks the strict grader calls `right`, add them to its
corpus, retrain with the same recipe. No reward model, no policy gradient, one module. **GRPO is bought only if this
shows signal.**

## The treatment — `real-rft-s0`

`training/wiki/rft_sample.py` (session S1, frozen with `tests/test_rft_sample.py`):

- **The policy:** `real-none-s0` (`~/lora-kernel-adapters/REAL4-real-none-s0/adapters.tgz`, adapter sha256 recorded by
  the sampler) on vLLM, LoRA served by name, **G1** identity check before any walk (generic probes, then the domain
  probes, wiki_arm's rule).
- **The questions:** every question `real-none-s0` was trained on — `real_questions.jsonl` (327) +
  `real_none_questions.jsonl` (29) = **356** (193 one-hop, 134 multi-hop, 29 unanswerable), `knowledge/regs-train`.
  Case ids as `real_corpus.walk_rows` numbered them, so each conversation's opaque ids are the oracle walk's.
- **The runtime: what serving is now** — the question's full-text entry on every shelf with fallback, pages opened with
  their statements, `page_top = 8`, strict guard (wiki_arm's `+page+top8`), `--max-model-len 16384`, 120 tokens a step.
- **The sampling:** $k = 4$ walks per question, temperature 0.7, seeds 1…4, each through `accept_rank.run_chain`.
- **The filter (the verifier):** a walk is accepted iff `grade.py` says `right` — value right **and** the citation is the
  supporting statement (`cite = "support"`); for an unanswerable question, `Not in my library.` — and its rendered turn is
  under the trainer's 4,096 window. At most **2 distinct** accepted walks per question (walks with no ERROR line first,
  then seed order).
- **The loss:** span-masked on the model's own spans, recorded exactly as `walk_rows` records them (tested byte for byte
  against the oracle's walk replayed); a span the runtime answered with an ERROR is kept out of the loss.
- **The corpus:** `training/wiki/data/train_real_rft.jsonl` = `train_real_none.jsonl` **byte for byte** (315 rows), then
  the self-walks. **The cap, fixed now:** the self-walks never outnumber the oracle's — at most **315** — so T fits one
  sixty-minute A100 session ($\approx (20 \cdot 22\,\mathrm{s} + 20 \cdot 17\,\mathrm{s}) \cdot 3 \approx 38$ min for
  630 rows at REAL7's and FMT0's step times **[ran]**, estimate). Coverage first: one walk of every covered question (a
  fixed shuffled order, seed 20261005), then second walks.
- **The gate** (`gate_real_rft.json`): `real_corpus.gate` over the whole corpus with its evaluation files — REAL0, REAL3,
  REAL4, REAL5, CITE0, **PAGE0** (G1: no evaluation library; G2: no evaluation question); G3 every row `right`; G4 no value
  in a question; G5 every row under the window; G6 reported, not gated (the self-walks repeat REAL4's questions by design).
  Beside it: accepted counts by kind, per-question coverage, the acceptance rate, same-page-wrong walks, walks kept with an
  ERROR line. **Passes only if all 356 questions were sampled.**
- **The training (T):** Gemma 4 E4B + LoRA, `release_gate.RECIPE`, seed 0, span-masked, window 4,096, one A100 —
  `real-none-s0`'s recipe, only the corpus changes.

**One unknown at the corpus level, said so:** the self-walks are in the served top-8 form and REAL4's oracle walks read
pages whole. FMT0 **[ran]** already measured an oracle corpus in the top-8 form against this baseline on this set: 1 : 1.
The page form alone is not expected to move it; attribution only if there is an effect.

## The hand-back between sessions

The chain fetches the runner's `--out` (`RESULTS_NAME`) on every poll and at the end, plus `run.log`, `vllm.log` and
`adapters_out.tgz` — nothing else (`chain_serve.sh` **[read]**). So the sampler **writes every accepted walk, with its
messages and spans, into `rft_sample.json`**, persisted per question (resumable: a second session carries the partial
record in and resumes). The corpus is then **assembled at zero GPU** from that record, on this machine, committed to the
branch, and pushed — T clones the branch, so the corpus must be on it before T starts.

## Arms (S2, one L4, vLLM, `--max-model-len 16384`), on PAGE0's 52 rows (`knowledge/hazwaste-regs`)

PAGE0's set is fresh to both members: its library is not in either corpus (G1), its questions never were (G2).

| arm | member |
|---|---|
| `withlib-s0+page+top8` | `real-none-s0` — the served member, **the baseline** (our previous version) |
| `withlib-s1+page+top8` | `real-rft-s0` — **the treatment** |

Both adapters in one session, so the pair is not split by vLLM's run-to-run spread: `adapters/rft0-s0` = `real-none-s0`,
`adapters/rft0-s1` = `real-rft-s0` (FMT0's packing).

## Headroom, stated now

`real-none-s0` scored 34/44 (PAGE0) and 33/44 (FMT0) on the answerable rows: **at most 10–11 rows to win**, 6 of them
same-page wrong statements in PAGE0's top-8 arm. With the exact two-sided sign test on discordant pairs,
$p = 2\sum_{k \le \min(b,c)} \binom{b+c}{k} 2^{-(b+c)}$, the smallest results that reach $p \lt 0.05$ are **6 : 0**
($p = 0.031$), **8 : 1** ($p = 0.039$), **10 : 2** ($p = 0.039$); 5 : 0 is $p = 0.0625$. **WORKS needs at least six net
repairs out of about ten available and no loss** — a large effect, by construction of the set. Said now, so a HELPS is
not later read as a near-WORKS.

## Verdict (fixed here; `python -m training.wiki.rft_sample --verdict <S2 record>`)

Treatment against baseline on the 44 answerable rows, paired:

- **RFT WORKS** — wins > losses, exact sign test $p \lt 0.05$, **and** refusals (8 rows) do not drop by more than one.
- **RFT HELPS** — wins > losses and not WORKS ($p \ge 0.05$, or the refusals dropped by more than one — said which).
- **FALSIFIED** — wins ≤ losses: training on the member's own verified walks does not repair what three oracle corpora did
  not.
- **VOID** — G1 does not show both members applied, or more than 3 rows lost to transport.
- Beside, never folded in: the **same-page wrong statement** count in each arm (the failure targeted), one-hop and
  multi-hop apart, refusals; from S1, the **acceptance rate** (right walks of 1,424), coverage by kind, and same-page-wrong
  walks among the samples.

## Run — the three chain commands

```bash
R=results/RFT0-rejection-sampling-20261005
# the branch must be pushed: the chain clones BRANCH from GitHub

# S1 — sample (one L4). The policy's adapter, carried in as REAL4's tarball (adapters/real-none-s0).
cp ~/lora-kernel-adapters/REAL4-real-none-s0/adapters.tgz $R/adapters.tgz
GPU=L4 BRANCH=rft0-20261005 RUN_DIR=$R MODULE=training.wiki.rft_sample BASE=google/gemma-4-E4B-it \
  MARGS="--member-prefix adapters/real-none-s --member-seed 0 --max-model-len 16384" \
  RESULTS_NAME=rft_sample.json SESSIONS=2 training/harness/chain_serve.sh 2>&1 | tee $R/S1_chain.log
# zero GPU: the corpus from the record, then commit train_real_rft.jsonl + gate_real_rft.json and push
python -m training.wiki.rft_sample --assemble $R/rft_sample.json

# T — train real-rft-s0 (one A100), REAL4's recipe on the new corpus
GPU=A100 BRANCH=rft0-20261005 RUN_DIR=$R MODULE=training.wiki.wiki_arm BASE=google/gemma-4-E4B-it \
  MARGS="--train-seed 0 --corpus train_real_rft --member-prefix adapters/real-rft-s --max-seq 4096" \
  RESULTS_NAME=train_rft_s0.json TRAINDEPS=1 SKIP_ADAPTERS=1 SESSIONS=1 training/harness/chain_serve.sh 2>&1 | tee $R/T_chain.log
mkdir -p ~/lora-kernel-adapters/RFT0-real-rft-s0 && cp $R/adapters_out.tgz ~/lora-kernel-adapters/RFT0-real-rft-s0/adapters.tgz

# S2 — score both members in one session (one L4): real-none-s0 as rft0-s0, real-rft-s0 as rft0-s1
T=$(mktemp -d)
tar xzf ~/lora-kernel-adapters/REAL4-real-none-s0/adapters.tgz -C $T && mv $T/adapters/real-none-s0 $T/adapters/rft0-s0
tar xzf ~/lora-kernel-adapters/RFT0-real-rft-s0/adapters.tgz -C $T && mv $T/adapters/real-rft-s0 $T/adapters/rft0-s1
tar czf $R/adapters.tgz -C $T adapters/rft0-s0 adapters/rft0-s1
GPU=L4 BRANCH=rft0-20261005 RUN_DIR=$R MODULE=training.wiki.wiki_arm BASE=google/gemma-4-E4B-it \
  MARGS="--arms withlib-s0+page+top8,withlib-s1+page+top8 --member-prefix adapters/rft0-s --library knowledge/hazwaste-regs --rows results/PAGE0-page-top-20261002/questions.jsonl --max-model-len 16384" \
  RESULTS_NAME=rft0.json SESSIONS=1 training/harness/chain_serve.sh 2>&1 | tee $R/S2_chain.log
python -m training.wiki.rft_sample --verdict $R/rft0.json      # → $R/verdict.json
```

(wiki_arm's own verdict prints `NOTHING SCORED` on these arms, as in FMT0 — it reads W9's three-arm headroom; the
verdict is `rft_sample --verdict`, fixed above.)

## Cost and abort

Three Colab sessions: S1 on an L4 (1,424 walks; PAGE0's top-8 arm ran 52 walks in 38 s at concurrency 8 **[ran]** →
~17 min plus boot, estimate), T on an A100 (~40 min, estimate above), S2 on an L4 (104 walks, minutes). **Abort rules:**
S1 stops if G1 does not show the member applied (the runner does). **If the S1 gate fails** (a G clause, or fewer than all
356 questions sampled after two sessions), T is not started. **If S1's acceptance leaves fewer than 50 self-walks**, T is
not bought — the corpus would be REAL4's with noise — and the result is reported as "no on-policy signal to train on".

## Stopping condition

One sample, one training, one scoring. The questions, $k$, the temperature, the filter, the cap, the arms, the set and
the bars do not change after S1 starts. Redesign count for this instrument: 0 (it is new); for the citation question on
this set, the fourth attempt after REAL6, REAL7, FMT0 — and the first that changes **whose walks** are trained on, not
which oracle walks.

## Result [ran] 2026-10-05 — RFT HELPS as written; a tie in substance

`python -m training.wiki.rft_sample --verdict rft0.json` → `verdict.json`:

| | `real-none-s0` (baseline) | `real-rft-s0` (treatment) |
|---|---|---|
| answerable | 34/44 | **35/44** |
| multi-hop | 24/30 | 25/30 |
| one-hop | 10/14 | 10/14 |
| refusals | 7/8 | 7/8 |
| another statement cited on the supporting page | 0 | 0 |

Paired **2 : 1**, exact sign test $p = 1.0$; no row lost to transport; G1 shows both members applied (domain probes 3/3
differ). By the table fixed above that is **RFT HELPS** (wins > losses, $p \ge 0.05$) — one net row, inside the run-to-run
spread this repository has measured (33/44 and 34/44 for the same baseline on this set). **GRPO is not bought.**

S1 **[ran]**: 924 of 1,424 sampled walks `right` (65 %), 453 accepted over 281 of the 356 questions, corpus 315 oracle + 315
self-walks, gate passed. T **[ran]**: one A100 session, 120 steps, window 4,096 (the queue passed `--max-seq 4096`; the
training record's `recipe` field copies `release_gate.RECIPE` verbatim and shows 1,536 — a recording flaw, also in
REAL4's record, not a training one).

**Read where the misses happen — the failure this attempt and the three before it targeted is not on this set.** This
instrument counts "wrong statement on the right page" strictly — the walk cites *another* statement on the supporting
page — and finds **0 in both arms**. PAGE0's count of 6 (`results/PAGE0-page-top-20261002/read.py`) counted any miss
whose citation was on the supporting page, **including the supporting statement itself**. Broken down, the misses are:

| miss | baseline | treatment |
|---|---|---|
| the supporting statement cited, the value wrong or partial | 7 | 7 |
| no citation | 2 | 1 |
| another page | 1 | 1 |

The seven are an answer that names one of two values the row asks for (180 of 180/270 days; 45 of 45/30 days; the last
line keeping 72 hours of 30 days / 72 hours), and a CFR part written as `40 CFR part 279` — **the grader reads the CFR
title, 40, as a second number** (`grade.value_right`: any number not asked for and not in the question is a hedge). Read
beside, not folded in: with the title not counted, 35/44 against 37/44 — still no effect.

So the line of four attempts (REAL6, REAL7, FMT0, RFT0) was aimed, since PAGE0, at a failure mislabelled by a counter that
included the right citation. What remains on this set is answer completeness on two-value rows and one grader rule; neither
is a citation failure, and neither is bought here. Changing the grader is an instrument change and needs its own brief.
