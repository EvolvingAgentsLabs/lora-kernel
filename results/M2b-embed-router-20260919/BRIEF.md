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
