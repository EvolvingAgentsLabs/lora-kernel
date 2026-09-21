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
