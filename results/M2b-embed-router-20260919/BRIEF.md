# M2 arm 2 — the router as an embedding model of the members' corpora (pre-registered 2026-09-19)

**Question.** Arm 1 (an n-gram model of each corpus) was safe on foreign text and **lost 120 of 120
legitimate requests from unseen senders**, and recovered 0 of 240 paraphrases **[ran]** M2. Does an
embedding model — which should not care that an address ends `.io` — keep arm 1's safety *and* keep
real-looking traffic?

**Model, provider, cost.** `Qwen/Qwen3-Embedding-0.6B` **[read]** — the smallest embedding model of
the pool's family, instruction-following, last-token pooling — loaded with `transformers` in fp16 on
a **Colab L4** through `training/harness/chain_serve.sh`. No API, no training, a few minutes beyond
boot. **Nothing runs on the user's machine.** It is the encoder a subdomain's knowledge base would
share (`docs/KNOWLEDGE-TRAJECTORIES.md` §4).

**The rule, fixed here before any number of this arm exists.** $s_m(x)$ = mean cosine of $x$ to its
$k = 5$ nearest requests of member $m$'s corpus; served by $\hat m = \arg\max_m s_m(x)$ iff
$s_{\hat m}(x) \ge \tau_{\hat m}$, with $\tau_m$ the **1st percentile** of $s_m$ on a 20 % split held
out of the index; otherwise out. Every text — corpus and request — is embedded under **one
instruction: represent the task being asked, not the content it is about.** Both members read one
inbox, so a plain embedding of a request mostly says "an email"; the instruction is this design's
one bet.

**The sets are arm 1's, all eight, unchanged** (`training/harness/router_sets.py`). They were
written before this arm was designed and this arm has never been scored on them; what *is* carried
over is that their author has seen where a lexical model breaks. Said, not hidden.

**Verdict, written first (`embed_router.verdict`).**

| outcome | reading |
|---|---|
| foreign text (C, D, E, C₂, E₂ — 338): ≥ 95 % abstained, and no more misrouted-to-local than the dictionary's 60 on the iterated sets; A: 0 misrouted, ≤ 1 % lost; **F: ≤ 5 % lost** | **PASSES** → becomes `--router embed`; the `serve: local\|out` table still decides what a recognised region does |
| serves foreign text locally | **NOT SAFE** — the predicted way to fail: E and E₂ are a member's own listing followed by another task, and an embedding that mostly sees "an email" will claim them. If so, the instruction did not do its job |
| safe, and loses F | the same wall arm 1 hit, from the other side |

B (paraphrases) is reported, never gated: whether a member *answers* a paraphrase of its one
trained question correctly is unmeasured, so recovering it is a share of traffic kept local, not
correctness.

**Probe before scoring:** cosine("Is this important?", "Does this matter?") against
cosine("Is this important?", "Write a haiku about rain.") — if the first is not clearly above the
second, the encoder or its pooling is wrong and nothing after it means anything.

**Redesign counter for arm 2: 0.** (Milestone 2 overall: arm 1 spent two of three.)

## Run 1 **[ran]** 2026-09-19 — does not pass: the same wall arm 1 hit (`run1_summary_only/`)

`Qwen/Qwen3-Embedding-0.6B`, fp16, Colab L4. Probe sound: paraphrase 0.739 against unrelated 0.345.

| set | n | dictionary · misrouted / lost | n-grams (arm 1) | **embeddings (arm 2)** |
|---|--:|---|---|---|
| A in distribution | 715 | 0 / 0 | 0 / 0 | 0 / **13** (1.8 %) |
| B paraphrased question | 240 | 0 / 131 | 0 / 240 | 0 / **141** — 99 recovered |
| C, D, E, C₂, E₂ foreign | 338 | **119** / — | 0 / — | **15** / — (5 on E, 10 on E₂; 95.6 % abstained) |
| **F** unseen senders | 120 | 0 / 0 | 0 / 120 | 0 / **120** |

By the table written first: **SAFE AND LOSES REAL-LOOKING TRAFFIC.** It is safe enough (15 ≤ 60,
95.6 % ≥ 95 %), it fails A by a little (1.8 % lost against ≤ 1 %), and it fails F completely. The
predicted failure — a member's own listing followed by another task — did happen, 15 times of 240,
far less than feared: the *task* instruction did most of its job.

**What the thresholds say:** τ = **0.977** (desk) and **0.944** (email). A generated corpus is so
uniform that *looking like the corpus* means a cosine of 0.98 to five neighbours; a sender the
generator never drew cannot reach it. Arm 1 learned the generator's `.com`; arm 2 learned the
generator's *sameness*. One cause, two forms.

**And an instrument fault of mine:** this run stored one summary row per set and no per-case score,
so nothing on disk can say whether F sits a hair under τ — a calibration problem, fixable by where τ
is set — or far below — a representation problem. *Keep the chain, not the last line* was already a
rule here. **Run 2 changes only what is written down** — per-case scores and the held-out
distribution; rule, parameters, sets and verdict untouched, so it is not a redesign and the verdict
above stands whatever it shows.
