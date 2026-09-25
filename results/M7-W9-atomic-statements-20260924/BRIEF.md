# M7 · W9 — atomic statements: a wiki the small expert walks, and whether a LoRA has to (pre-registered 2026-09-24)

The user's design, 2026-09-24 ([`MEMORY.md`](../../docs/MEMORY.md) §1.6): the library shaped like
Wikipedia; a page is a list of **atomic statements** — the smallest piece of information that can be
checked on its own — under anchors; **links live inside the statement that names them**; operative
recipes have the same shape and branch by context; **every answer cites the statement it rests on**,
and that citation is what makes the memory verifiable. The harness that walks it is, as far as
possible, a LoRA per subdomain — bought only where it is shown to be needed.

**Question (stage 1, one unknown: can the untrained base walk it?).** On a wiki of atomic statements
whose facts no model can know, does the bare `Qwen3.5-4B` — given the verbs, the pages and the
sections — reach a *verified* answer on questions of two and three hops, and if not, is the gap
navigation (which a trajectory LoRA can be trained on) or reading?

## What was built, zero GPU **[ran]**

| piece | where | what it does |
|---|---|---|
| pages of statements | `memory/notes.py` | kinds `page` (wiki) and `recipe` (harness); a body of `§anchor sentence` lines; `[[id]]` links inside a statement; `refs` derived, never written |
| the lint | `memory/lint.py` | one sentence per statement, ≤ 40 tokens, unique anchors, every line a statement, links resolve, no hand-written `refs` — every rule shown able to fire (`tests/test_wiki.py`); the existing libraries lint as before (nursing-iv 0, wikipedia-arts 0) |
| the referee | `memory/runtime.py` | `<open>id</open>` on a page shows its **sections only**; `<open>id§anchor</open>` one statement, links as openable `[p7q] Title`; opened statements recorded for the citation check |
| the member's prompt | `memory/prompt.py` `SYSTEM_WIKI` | a second member shape; the nursing member's prompt is untouched |
| the world | `training/wiki/world.py` | a distributor per seed: 10 products, 5 suppliers, 4 depots, 3 carriers, 18 people, and **9 recipes, one per role of the reference organisation** (purchasing, receiving, dispatch, claims and returns, communications, finance, HR, marketing, IT); 49 pages, 0 lint findings |
| the questions | `training/wiki/questions.py` | 19 families: 1-hop (E1, O1), 2-hop (E2, O2 — an invoice's amount picks the threshold branch), 3-hop (E3, O3 — a recipe points into the wiki and a second search follows), `none`; **evaluation and training wording disjoint** |
| the grader | `training/wiki/grade.py` | `right` = value right **and** the citation names a statement the walk opened whose text holds the value; `unverified` otherwise; a hedged line (a second number) is `wrong` |
| the runner | `training/wiki/wiki_arm.py` | arms, the verdict below, the training and scoring stages |
| the sets | `training/wiki/corpus.py` | the evaluation world and questions; a 600-row corpus over 32 other worlds, gate G1–G5 |

Zero-GPU numbers, on the development world (seed 7; the evaluation world is written after this
freeze): the oracle, driven through the real loop, **67/67 verified**, 0 refused; the trivial policy
(search the question, open the first page and its first section, cite it) **0/40 on the headline**,
5/67 overall. Corpus gate on 600 rows: G1–G5 all 0, max 476 tokens (word-and-mark proxy).

## Sets — written after the freeze

The **evaluation world is seed `20260924`** (`knowledge/distributor-wiki/`, committed after the freeze
commit, byte-equal to the frozen generator's output — a test holds it) with **67 questions** in the
evaluation wording: **headline = the 40 of two hops or more** (E2 16, E3 12, O2 8, O3 4); beside it
1-hop (21) and `none` (6). No training world is it; no training question is worded like it.

## Arms — stage 1, one L4 session, no training

| # | arm | why |
|---|---|---|
| 1 | **`nolib`** — the question alone, `SYSTEM_NO_LIBRARY` | **the gate on the whole set:** the values must not be in the weights |
| 2 | **`base-reads`** — the oracle's statements open, each after its citation | the reading bar: can the base read and cite, handed the right statements? |
| 3 | **`base-walks`** — the verbs, the pages, the sections; the base navigates | the question |

## Verdict — written first (`wiki_arm.verdict`)

On the **headline**, by **credit** (`right` — value right and citation verified), paired by case id,
exact two-sided sign test on discordant pairs (FOUNDATIONS §7.1),
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, $p<0.05$ — read in this order:

| reading | condition | what follows |
|---|---|---|
| **VOID** | `nolib` value-right > 10 % | the set measures the weights; nothing else is read |
| **THE RUNTIME IS ENOUGH** | `base-walks` ≥ 85 % | for this shape the harness is the runtime; **no trajectory LoRA is bought** |
| **READING IS THE GAP** | `base-reads` < 70 % | a navigation LoRA would not close it; not bought — the format or the answer contract is next |
| **NAVIGATION IS THE GAP** | `base-reads` ≥ 70 % **and** `base-reads vs base-walks` is an improvement | **stage 2 is bought**: the trajectory LoRA |
| **NO ATTRIBUTABLE GAP** | otherwise | not bought |

Beside, never folded in: value-right beside credit (`unverified` counted), by hops, by block (E/O),
`none` rows, calls, refused and malformed verbs, sections opened, whether the cited statement is the
oracle's supporting one.

## Stage 2 and 3 — bought only on NAVIGATION IS THE GAP

**Training (one A100 per seed, two seeds, `SEEDS = (0, 1)`):** `wiki_arm --train-seed k` →
`adapters/wiki-walks-s<k>`, the pool's recipe (`release_gate.RECIPE`), `train_one --seed k`, on
`training/wiki/data/train.jsonl`. **Scoring (one L4):** `withlib-s0`, `withlib-s1` on the evaluation
set, beside the stage-1 records. **Verdict:** `withlib-s<k> vs base-walks` on the headline must be an
improvement — both seeds **PASSED**; one **DRAW-DEPENDENT**; none **FALSIFIED**. Two seeds because W5e
**[ran]** showed two draws of one recipe disagreeing on 25 of 67 rows; `train_one` had always used
seed 0, so W5e's two draws differed by GPU non-determinism alone and a seed prices the draw only beside
that noise.

## Suite, models, parameters

`Qwen/Qwen3.5-4B` (Hugging Face weights, bf16) served by **vLLM on Colab**; no API provider is called.
Thinking off in every render. Temperature 0; the walking arm 120 tokens a step, stop at the closing tag,
24 calls, 24 opens; single replies 160 tokens; window 8192; concurrency 8; searcher lexical.

## Cost, abort, redesigns

**Cost.** Stage 1: one L4 session, 201 replies of which 67 walks of ≤ 10 steps — minutes. Stages 2–3,
only if bought: two A100 sessions (~22 min each, W5e's rate at 600 rows), one L4. **Ceiling: 1 L4 +
2 A100 + 1 L4.** No dollars to a provider. **Abort.** No `[wiki]` line for 8 minutes once the base is up
→ stop; the runner persists every 10 records and resumes. **Redesign count: 0.** Changing the grader,
the verdict's bars or the question families after the freeze commit is a redesign and is counted.

**What is not measured.** Real Wikipedia text (the facts are in the weights — W8's three pages stay the
format's proof); retrieval by embeddings (R0 did not pass W3; the searcher is lexical); walks longer than
three hops; any domain but this one; whether the reference organisation's roles are the right split of
the harness (they are the user's example, adopted as structure — names and brands are not copied).

## Launch

```bash
R=results/M7-W9-atomic-statements-20260924
GPU=L4 BRANCH=w9-atomic-statements-20260924 RUN_DIR=$R MODULE=training.wiki.wiki_arm \
  MARGS="--concurrency 8" RESULTS_NAME=wiki_arm.json BASE=Qwen/Qwen3.5-4B SKIP_ADAPTERS=1 SESSIONS=1 \
  training/harness/chain_serve.sh
```

## Stage 1 result **[ran]** 2026-09-24 · NAVIGATION IS THE GAP — stage 2 bought

One L4 session, 0 transport errors, read off `wiki_arm.json`. Headline n = 40, credit (value right **and**
citation verified) · value right:

| arm | credit | value right |
|---|--:|--:|
| `nolib` | 0 | **0** — the set is valid: the values are not in the weights |
| `base-reads` | **29** | 40 |
| `base-walks` | **0** | 1 |

`base-reads vs base-walks` **29 : 0**, improvement. By the verdict as written: **NAVIGATION IS THE GAP** →
stage 2, two seeds.

**Read where it happens, and it is not section choice.** In 63 of 67 walks the untrained base writes one
`<search>`, reads the listing, and then **continues the listing** — inventing `[k3f] page · …` lines until its
token budget ends — instead of writing `<open>`. It never reaches a page. What is missing is the protocol
habit (write a verb after a result), which is exactly what a corpus of walks teaches; it is not yet evidence
about choosing the right section or following the right link. **And `base-reads` loses its 11 on the citation,
not the value:** 10 of them cite the chain's *first* statement (`§supplier`, `§carrier`) instead of the last
one that holds the value (`§town`, `§cutoff`) — a citation habit, also taught by the corpus, and the reason the
verdict reads credit and not value.

## Stage 2–3 result **[ran]** 2026-09-25 · PASSED — both seeds beat the untrained walk, 35 : 0

Two A100 sessions trained `wiki-walks-s0` (`d6f87d27…`) and `wiki-walks-s1` (`c1265178…`) on the 600-row
corpus of 32 other worlds; one L4 session scored both on the evaluation world, G1 `applied` on both, 0
transport errors; paired with stage 1's records by `wiki_arm --combine` (the verdict's code, unchanged).
Three scoring attempts before it were lost to harness bugs, none to a model, each fixed with a test — a
repeated `--lora-modules` flag vLLM 0.30 reads as one (only the last adapter loaded), the chain not stopping
on an exception, and arms asking vLLM for an adapter's path instead of its name; `training/harness/fake_vllm.py`
now reproduces vLLM at those edges and `tests/test_fake_vllm.py` fails on both runner bugs on the Mac.

| headline (40) | credit | value right |
|---|--:|--:|
| `base-walks` (stage 1) | 0 | 1 |
| `base-reads` (stage 1) | 29 | 40 |
| **`withlib-s0`** | **35** | 35 |
| **`withlib-s1`** | **35** | 35 |

Paired: `withlib-s0 vs base-walks` **35 : 0**, `withlib-s1 vs base-walks` **35 : 0** — improvement, both seeds:
**PASSED** as written. Beside, not folded in: against `base-reads` 9 : 3 and 8 : 2, ties — the adapter, walking
alone, reaches what the base reaches when handed the oracle's statements. By hops: 3-hop **16/16** on both seeds
(base-reads 11/16), 2-hop 19/24, 1-hop 18/21; `none` 5/6. Every walk that credits cites the statement that
holds its value; the 9 misses per seed are 6 citations of a statement that does not hold it, 2 with no
citation, 1 wrong. **The two draws agree on 57 of 67 rows** (53 walks byte-identical) — the draw that moved
W5d's verdict does not move this one.

**What this is and is not.** A trajectory LoRA taught the habit — search, open a page, choose the section,
follow the link inside the statement, cite — on worlds it never saw the values of, and on an evaluation world
it never saw at all. It is not real Wikipedia text, not retrieval by embeddings, not beyond three hops, not
another domain. The next claim is the same member on a second, differently shaped wiki.
