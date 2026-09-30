# REAL0 — does a trajectory member walk a library it was not written for?

**Written 2026-09-30, before the questions exist and before anything runs.** The user chose the source (option A: real
public documents of the same kind of domain as the distributor).

## What and why

Every walk the memory has been measured on crossed a library a generator wrote — W9's invented distributor, B5's
comparisons, the tracker's pages. The thesis (docs/MEMORY.md): **the LoRA holds the navigation, the library holds the
content.** It has never met content nobody designed for the member. If the trained walker falls to the untrained base
on real documents, the trajectory does not generalise past the generator — and that changes the plan for the whole
library, not only for ingestion.

**One unknown: the content.** The member is `distributor-wiki@v2` (B5 **[ran]**: W9's corpus plus comparisons, Gemma 4
E4B), **not retrained**. The library is new; its shape is the library's own (pages of `§anchor` statements, links inside
statements, the same verbs and the same citation contract).

## The library — real, public, ingested mechanically

`knowledge/logistics-regs/`, built by `memory/ingest.py` from the eCFR's XML (public domain), no statement written or
reworded by anyone:

- **21 CFR Part 1, Subpart O** — sanitary transportation of human and animal food: shippers, loaders, carriers,
  receivers (18 sections);
- **29 CFR 1910.176** (handling materials) and **1910.178** (powered industrial trucks) — a warehouse's own rules.

20 pages, 265 statements; one section → one page, one paragraph → one statement anchored by its label path (`§b-3-ii`),
a cross-reference inside the ingest (`§ 1.908(b)(3)`) → a link where the regulation put it. **Different from W9 by
construction, and said so:** 112 statements exceed W9's 40-token limit and 123 hold more than one sentence (the linter
reports both; the ingest keeps paragraphs whole, because cutting them is rewriting them).

## The questions — written and frozen before any model answers one

`questions.jsonl`, 40 rows in W9's row format (`question`, `plan` executable by `memory.runtime`, `support`,
`answer`, `check`), written from the documents by a designer who has not seen a model's answer on them, committed before
the run. 1-hop, 2-hop (a statement's cross-reference must be followed to the page that holds the value), 3-hop, and a
few the library does not answer (`Not in my library.`). The headline is the multi-hop questions. The oracle's walks must
score 40/40 verified through the real loop and grader (`--zero-gpu`) before the file is frozen.

### Frozen 2026-09-30, before any model answered — what the set is, and its limits

`questions.jsonl` (written by `make_questions.py`, a designer who saw no model answer): **40 rows — 11 one-hop, 24
two-hop, 1 three-hop, 4 the library cannot answer; headline (hops ≥ 2) 25 rows.** The oracle walks all 40 through the
real loop and grader: **40/40 verified, 0 refused** (`zero_gpu.json`). Checked on every row: each search ranks the plan's
page first; every hop follows a real link inside a statement; no check token appears in a statement opened before the
supporting one. The sources are committed (`sources/*.xml`) and `tests/test_wiki.py` re-ingests them byte-identical.

**Strict citation, fixed before the run.** On real documents a value repeats: "12 months" is the answer to 9 headline
rows and "12" occurs in 12 statements, so W9's rule — the cited statement opened and holding the value — would pass a
walk that cited the wrong records paragraph. Every value row here sets `check.cite = "support"`: **the citation must be
the supporting statement itself** (`grade.py`, opt-in per row; W9's rows unchanged; a test holds both behaviours).

**Limits, stated before the number exists.** The regulation links sparsely: 22 link edges across 20 pages, none inside
1910.176/178 (their references are plain text). So **every multi-hop row is in 21 CFR 1 Subpart O**, 14 of the 25 go
into the records section (1.912) from transport operations (1.908) or carrier training (1.910), and one real three-hop
chain exists. All 11 one-hop rows are single statements (8 on forklifts, 3 definitions). The headline measures following
a regulation's own cross-references — one shape of walk, on one document family.

## Arms (one L4 session, vLLM, Gemma 4 E4B bf16)

| arm | what | role |
|---|---|---|
| `nolib` | the question alone | **gate: are the values in the weights?** (regulations are public; a 4B may know them) |
| `base-reads` | the oracle's statements open | the reading bar |
| `base-walks` | the untrained base with the verbs | **the baseline** |
| `withlib-s1` | `distributor-wiki@v2` (`adapters/wiki-cmp-walks-s1`, B5's seed 1), the verbs | **the treatment** |

## Verdict (fixed here)

- **VOID** if `nolib` gets the value right on more than 10 % of the headline — the values are in the weights, and the
  library measures nothing.
- **GENERALISES** if `withlib-s1` beats `base-walks` on the headline (paired, exact sign test $p \lt 0.05$).
- **DOES NOT GENERALISE** if it does not — the trajectory learned the generator's library, not the habit.
- Beside it, never folded in: `withlib-s1` against `base-reads` (is the gap navigation or reading?) and its verified
  rate against W9's 35/40 on the invented world.

**Where the verdict is read.** `training/wiki/wiki_arm.py` prints W9's own headroom verdict, which answers W9's
question (is a trajectory LoRA worth buying?) — not this one. REAL0's verdict is read from the same file's
`analysis.pairs` on the headline slice: `withlib-s1 vs base-walks` (the verdict), `withlib-s1 vs base-reads` (beside),
and `nolib`'s value-right rate (the gate).

## Stopping condition

One L4 session. No question edited after the first model answer; no redesign of the library after S starts. If the
headline has fewer than 20 multi-hop rows, the brief is re-issued before running, not after.

## Result [ran] — DOES NOT GENERALISE (not VOID)

Session 2 of 2 on an L4 (session 1 was ended by Colab's sixty-minute cap while the laptop slept; nothing had been
scored); G1 applied; 0 errors. `real0.json`.

| arm | headline (25, multi-hop) | one-hop (11) | none (4) | all (40) |
|---|---|---|---|---|
| `nolib` (closed book) | 0 | 0 (value-right 1) | 0 | 0 |
| `base-reads` (the right statements open) | **22** | 11 | 4 | **37** |
| `base-walks` (untrained, the verbs) | 1 | 0 | 1 | 2 |
| `withlib-s1` (`distributor-wiki@v2`) | **0** | 0 | 4 | 4 |

- **Gate:** `nolib` 0/25 — the values are not in the weights; the run reads.
- **Verdict: `withlib-s1` vs `base-walks` on the headline — a tie (0 : 1, $p = 1.0$): DOES NOT GENERALISE.**
- Beside it: `base-reads` 22/25 — the regulation's long paragraphs are **read** well once open; the gap is entirely
  navigation (`base-reads` vs `base-walks` 21 : 0).

**Read where it happens — the member never entered the library.** In **40 of 40** walks its first act was a search of
the **harness shelf** with a query from its training world — *"approve a supplier invoice payment"* (7),
*"deliver a pallet of goods"* (5), *"approve a supplier contract"* (4), *"goods arrived damaged or wrong item claim"* (4),
… — the first of those occurs **61 times in its corpus** (`train_cmp.jsonl`). This library has no harness shelf: 0
notes, `Not in my library.`, and **it opened no page in any of the 40 walks**. Its 4 credited rows are the 4 the library
cannot answer — credit for refusing, not for walking.

**What it means.** The trajectory LoRA learned **the generator's library** — its shelves, its recipe vocabulary, the
queries its corpus repeated — not the habit of searching for the question's own terms. It is M2's lesson (*a model of
a generated corpus learns the generator*) measured on the memory: W9's 35/40 and B5's 37/40 were walks over a world
the generator shaped, and they do not transfer to text the generator did not write. The untrained base walks the real
library (it opens pages, 13 empty finals and 17 refusals) but reads the wrong statements; the reading is there
(`base-reads` 37/40), the navigation is not, in either model.

**Not concluded here.** That navigation cannot be learned for real documents: the corpus never showed the member one.
The next test is the one this points to — a trajectory corpus written over **ingested** real documents, trained on one
document family and measured on another it never saw — with its own brief.
