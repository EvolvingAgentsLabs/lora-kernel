# M2 arm 3 — the router as `cactus-compute/needle`'s embedding (pre-registered 2026-09-21)

**Question.** Arm 2 (`Qwen/Qwen3-Embedding-0.6B`) was safe on foreign text and lost 120 of 120
legitimate requests from unseen senders — not a calibration problem: "changing who writes moves a
request as far as changing what is asked" (`docs/RECORD.md` §2). Needle is read [read]
(`github.com/cactus-compute/needle`, Apache-2.0, fetched 2026-09-21) as a candidate not for its
size but for the two pieces arm 2 lacked: a calibrated confidence head, and local LoRA fine-tuning
from a contrastive-shaped data format. **This run is headroom, not a verdict** — the cheapest
first look, on the same eight sets arms 1 and 2 already ran, nothing frozen or iterated against.

**Mechanism.** `training/harness/needle_router.py`: the same `EmbedRouter`, `score_cases` and
`verdict` arm 2 used, unchanged — the only thing that changes is the encoder
(`NeedleEncoder.encode`, over `needle.Needle().embed`). Same grader for every arm.

**Subsampled, corrected mid-run [ran] 2026-09-21.** Needle's C engine embeds one string at a
time; arm 2's full scale (~2,000+ texts across the corpora and eight sets) ran silently for ~15
minutes with no progress line before this file's first launch attempt was stopped for that
reason alone — an experiment whose position cannot be seen cannot be stopped early. Fixed two
ways: `NeedleEncoder.encode` now prints every 25 embeddings, and `--limit` (default 40) caps
each corpus and each set to a fixed-seed sample. **This means the numbers below are a headroom
read on a smaller draw, not the same scale as arm 2's own verdict** — `sets_full_size` in the
output records what each set's true size is, so the gap is visible, not hidden.

**Provider.** Colab, through `training/harness/chain_serve.sh`, `SKIP_ADAPTERS=1` (nothing here
trains or serves a pool member). `../../CLAUDE.md`: "no model runs on the user's machine" — Needle
does not need a GPU to embed a few hundred short strings, but the rule is not "no model that needs
a GPU," so this runs on the rented card anyway, self-installing `cactus-needle` (not a
`TRAINDEPS` package) the first time `NeedleEncoder` is constructed.

**Abort rule.** No `[route] probe` line within 8 minutes of boot → stop the session. A probe whose
paraphrase cosine does not exceed its unrelated cosine → stop: the encoder or its pooling is
broken (the same rule arm 2 and the radar both use).

**What this decides.** Whether Needle is worth a real arm — its own BRIEF, its own falsifier fixed
before the run, on M2's own metric (misrouted-to-local, out-share) — not whether milestone 2
passes. If the numbers here look like arm 2's (safe, loses F), that is read as "no better than
what is already measured" and Needle is not bought further without the fine-tuned, contrastive
version its README itself points at. If F improves without foreign text getting worse, that is the
signal to spend a real arm.

**Launch:**

```bash
GPU=T4 BRANCH=main RUN_DIR=results/M2c-needle-router-20260921 MODULE=training.harness.needle_router \
  MARGS="" RESULTS_NAME=needle_router.json BASE=none SKIP_ADAPTERS=1 SESSIONS=1 \
  training/harness/chain_serve.sh
```

`BASE=none`: no vLLM base is served by this module; `chain_serve.sh`'s own vLLM-install gate runs
regardless (`docs/FRAMEWORK.md` §9), and this module never calls it.

**Redesign count: 0.**

## Result [ran] 2026-09-21

`results/M2c-needle-router-20260921/needle_router.json`, session `srv171022`. Probe passed
(paraphrase 0.9453 > unrelated 0.8966, dim 3072). Subsampled per the fix above — `sets` below
is the drawn size, `sets_full_size` the true size:

| set | what it is | n (of full) | local_right | misrouted_to_local | lost_local | abstained |
|---|---|---|---|---|---|---|
| A | in-distribution | 40 (715) | 36 | 1 | 3 | — |
| B | member's question, paraphrased | 40 (240) | 32 | 0 | 8 | — |
| C, C2 | keyed out-of-region text | 14+8 (22) | 0 | **0** | — | 22/22 |
| D | plain out-of-region + fluids | 40 (76) | 0 | **0** | — | 40/40 |
| E | same content, a different task | 40 (120) | 0 | **29** | — | 11 |
| E2 | E, fresh set | 40 (120) | 0 | **33** | — | 7 |
| F | legitimate, senders outside every pool | 40 (120) | 19 | 0 | 21 | — |

**Verdict: `NOT SAFE: serves foreign text locally`** — `passes: false`, `safe: false`,
`keeps_real_looking_traffic: false`. 62 of 142 out-of-region cases served locally (E: 29/40,
E2: 33/40 — a same-content-different-task swap is exactly arm 2's own failure mode, worse
here), against arm 2's 15/338 (4.4%). F recovers real traffic arm 2 lost completely (19/40 vs
0/120) but not reliably (52.5% still needlessly abstained), and A gives back 3 of 40 it should
have kept.

**Reading, against the brief's own rule.** Neither of the two named outcomes: this is not
"looks like arm 2, safe but loses F" (F improved, 0 → 47.5%), and it is not "F improves without
foreign text getting worse" (foreign-text leakage roughly **10×** arm 2's rate) either — the
uncalibrated default (`needle.Needle()`'s stock weights, the percentile-of-cosine τ arm 2 also
used) trades the property that matters most, since a router that serves foreign text locally is
the failure the whole design exists to prevent. **Read as: no real arm bought.** The two pieces
this arm was chosen for — a calibrated confidence head, local LoRA fine-tuning from a
`query`/`answers` format — are exactly what stock weights and a borrowed τ do not exercise;
spending a real arm (its own BRIEF, its own falsifier, the fine-tuned weights Needle's own
README points at) is not justified by this headroom alone. This is a subsampled look (40 per
bucket against sets sized up to 715) and should not be read at arm 2's own resolution — but the
direction (leak rate an order of magnitude higher, not lower) does not depend on the sample
size to be a real signal.
