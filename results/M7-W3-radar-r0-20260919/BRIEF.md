# Memory W3 — the radar R0 beside a lexical baseline (pre-registered 2026-09-19)

**Question.** Inside one subdomain's library (94 notes, IV therapy), does an off-the-shelf small
encoder put the *needed note* in the three a `<search>` returns — when the question does **not** use
the note's words — and does it do so where a word-matcher cannot? (`docs/MEMORY.md` §2.2 R0, §2.3.)

$$s(n\mid q)=\langle e(q),e_{\text{when}}(n)\rangle+\beta\,\langle e(q),e_{\text{what}}(n)\rangle,\ \beta=0.5,\qquad \text{recall@}3=\frac{|\{q:\operatorname{rank}_q\le 3\}|}{|Q|}$$

**Why W2's queries are void here.** W2's oracle searches for a note by that note's own `when:` line; any
searcher ranks a text first against itself (a test holds this for a hashing stub). W3 is measured on
queries written for it.

**The design, frozen before a query was written** (`training/nursing/radar_queries.py`):

| set | n | targets | what it is | job |
|---|--:|--:|---|---|
| **P** | 94 | 94 | one paraphrase per note, in bedside words, sharing as few content words with the target's `when:`/`what:` as practical; the three procedures repeat steps, so a query names its procedure in *other* words (*cannula*, *maintenance fluids*, *piggyback antibiotic*) | **the gate** — within-topic confusion is where flat retrieval failed before |
| **E** | 72 | 4 | the stem of each of the 72 nursing questions (text nobody wrote as a query) → the first note its oracle walk opens | reported beside; four targets cannot carry a gate |

P was written once, after the freeze, and has not been iterated against any searcher. A test asserts no
query is a substring of its target's fields, nor the reverse.

**Headroom FIRST — [ran] 2026-09-19, zero GPU, no model** (`lexical_baseline.json`,
`python -m training.nursing.radar_r0 --lexical-only`). The lexical baseline is W2's `Lexical`
(token overlap on `when` + 0.5 on `what`, its own stop list):

| set | overlap query→target (mean · median · max · queries at 0) | lexical recall@1 | **recall@3** | MRR | unranked | recall@3 restricted to the target's shelf |
|---|---|--:|--:|--:|--:|--:|
| **P** | 0.039 · 0.000 · 0.286 · 56 of 94 | 0.043 | **0.064** (6/94) | 0.090 | 56 | 0.117 |
| **E** | 0.192 · 0.182 · 0.364 · 3 of 72 | 0.014 | **0.125** (9/72) | 0.210 | 3 | 0.292 |

*Overlap* = share of the query's content words (the baseline's own tokenizer) found in the target's two
fields. **Reading: GO — and a warning.** The ceiling rule (lexical ≥ 0.95 → no headroom, harden the set
once) does not fire. The opposite does: on P the word-matcher is at the **floor by construction**, so
*R0 beats lexical* is close to a formality. The gate therefore carries an **absolute standard**, fixed
here before any R0 number exists. E is the fairer contest for a word-matcher — natural text, overlap
0.19 — and it scores 0.125 there because a question's stem quotes *steps*, and the note the walk needs
first is the *procedure*.

**Arms.** (1) lexical — done. (2) **R0**, β = 0.5 — the one bought now. Beside it, at no extra cost
(same vectors): R0 with β = 0, the single-`when`-vector baseline §2.3 keeps, and every rank again with
the search restricted to the target's shelf. **Not bought:** R1 (W6), any trajectory-conditioned term,
any second encoder.

**Verdict, written first (`radar_r0.verdict`)** — on P, *needed note in the top 3*, R0 against lexical,
paired, exact two-sided sign test on discordant pairs,
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, different at $p \le 0.05$; and recall@3 ≥ **0.80**:

| outcome | reading | what follows |
|---|---|---|
| R0 wins the pair **and** recall@3 ≥ 0.80 | the radar has a job and does it | W3 ✅; W4 proceeds; the runtime's `<search>` takes the index |
| R0 wins the pair, recall@3 < 0.80 | beats a word-matcher and is not enough | W3 not passed; read the misses' ranks (rank 4–6 = a threshold, rank 40 = a representation); this is the gap R1 (W6) is for, and W5 must not blame the expert for a note it was never shown |
| **tie** | **falsified: the radar has no job at this library size** | said so in MEMORY/PLAN; W5 runs on the lexical searcher; R1 has nothing to compress |
| lexical wins | a null, reported as one | same as tie |

**Models.** `Qwen/Qwen3-Embedding-0.6B` **[read]** — Hugging Face weights, `transformers` fp16,
last-token pooling (`embed_router.TransformerEncoder`, now taking its instruction as a parameter),
every text under one instruction: *represent the situation it is for*. **Provider: Colab, through
`training/harness/chain_serve.sh`. No API is called; nothing runs on the user's machine.** A probe
(paraphrase vs unrelated cosine) is printed before the index is built, so a dead encoder cannot look
like a floor.

**Parameters.** k = 3, β = 0.5 (and 0), no threshold, ties broken on note id; 94 notes × 2 fields +
166 queries ≈ 354 encodes. Deterministic given the weights.

**Cost.** One L4 session, minutes beyond boot, $0 to any provider. Ceiling: two sessions.

**Abort rule.** No `[radar] probe` line within 12 minutes of boot → stop the session. A probe whose
paraphrase cosine does not exceed its unrelated cosine → stop: the encoder or the pooling is broken.

**Launch (as run, 2026-09-19):**

```bash
GPU=L4 BRANCH=main RUN_DIR=results/M7-W3-radar-r0-20260919 MODULE=training.nursing.radar_r0 \
  MARGS="--beta 0.5" RESULTS_NAME=radar_r0.json BASE=Qwen/Qwen3-Embedding-0.6B \
  SKIP_ADAPTERS=1 SESSIONS=1 training/harness/chain_serve.sh
```

**Redesign count: 0.** The set may be hardened once, only if lexical had been at the ceiling; it was
not. A second reshaping of the set or the standard after an R0 number is seen ends W3 as *not passed*.

**Not measured:** whether an *expert* writes a query like P's (W5); retrieval mid-walk, where `next`
links do the work; any other library; R1.

## Result **[ran]** 2026-09-19 · NOT PASSED — R0 beats a word-matcher and is not enough

One Colab L4 session, ~8 minutes (the first boot attempt did not take and the chain retried; the
scoring itself took 30 seconds). Encoder `Qwen/Qwen3-Embedding-0.6B`. Probe: paraphrase cosine
**0.4019** against unrelated **0.2326** — the encoder and the pooling are alive. Read off
`radar_r0.json`. $\text{recall@}k = \lvert\{q : \operatorname{rank}_q \le k\}\rvert / \lvert Q\rvert$.

| arm | set | n | recall@1 | **recall@3** | MRR | unranked |
|---|---|--:|--:|--:|--:|--:|
| lexical | P | 94 | 0.043 | 0.064 | 0.090 | 56 |
| **R0, β = 0.5** | **P** | 94 | 0.255 | **0.638** | 0.463 | 0 |
| R0, β = 0 (`when:` only) | P | 94 | 0.223 | 0.362 | 0.352 | 0 |
| R0, β = 0.5, inside the target's shelf | P | 94 | 0.319 | 0.702 | 0.530 | 0 |
| lexical | E | 72 | 0.014 | 0.125 | 0.210 | 3 |
| R0, β = 0.5 | E | 72 | 0.125 | 0.125 | 0.218 | 0 |

Paired on P, needed note in the top 3, exact two-sided sign test on discordant pairs,
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$: **R0 against lexical 56 : 2** ($p \approx 0$);
β = 0.5 against β = 0, **30 : 4** ($p \approx 10^{-5}$) — the `what:` term earns its place. On E
(4 targets, not gated) 1 : 1, a tie.

**The verdict, as written before the run:** R0 wins the pair and **0.638 < 0.80**. W3 is not passed.
The standard is not loosened and the set is not reshaped. **Redesign count: 0.**

**Where the 34 misses sit (zero GPU, the per-query ranks).** Rank 1–3: 60 · 4–6: **13** · 7–10: 5 ·
11–20: 7 · 21+: 9. So recall@6 = 0.777 and recall@10 = 0.830: about half the misses are *near* — a
wider $k$ or a re-rank reaches them — and half are *far*, which is representation and is what R1's
learned projection is for. Four of the far ones collapse inside their own shelf (P-73 26 → 5, P-84
42 → 4, P-91 9 → 1, P-92 16 → 1): cross-shelf confusion, which the `shelf=` argument the verb
already takes removes.

**What follows.** (1) **W5 must not blame the expert for a note it was never shown:** its arms either
run on the oracle's search results or report retrieval misses as their own count, beside the score.
(2) The gap is W6's — R1, the projection trained on the oracle walks' (query, note) pairs — and it is
measured on **new** query sets, never on P, which has now been looked at. (3) On E every searcher is
at 0.125: four near-identical "first notes" are not separable by the question's stem, by words or
by vectors; that set says nothing about the radar and stays beside the gate.
