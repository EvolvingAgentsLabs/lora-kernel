# REAL1 — is the entry the gap? The runtime's first search, on the question, over the statements

**Written 2026-09-30, before anything runs.** The first of three mitigations for REAL0's failure, bought in order,
each only if the one before leaves a gap: **M1 runtime (this)** → M2 a corpus whose queries come from the question
(paraphrased recipe titles, a gate on repeated search strings) → M3 a corpus over ingested real documents, trained on one
family, measured on another.

## What and why

REAL0 **[ran]**: `distributor-wiki@v2` never entered the real library — 40/40 walks began with a harness-shelf search
memorised from its generated world, found nothing, refused. Two things were wrong at the door, measured with no model:
the member's query (memorised) and the search itself — the library's `Lexical` scores `when`/`what`, which on an
ingested page is its section title, and a person's question shares few words with it: the page a walk starts on is in
the top 3 for **5 of 36** questions, the supporting page for 10. Full-text BM25 over the statements (`FullText`, standard
$k_1 = 1.2$, $b = 0.75$, never tuned here) finds them **34/36** and **32/36**.

**M1 — the entry is the runtime's, not the member's (`+entry` arms):** the conversation's first search runs on the
**question's own words**, on **every shelf**, with **full-text search**; any later search on a named shelf that finds
nothing falls back to every shelf and says so. The member is unchanged; after the first result it walks as it learned.

## Arms (one L4 session, vLLM, Gemma 4 E4B bf16) — REAL0's frozen questions and library

| arm | what |
|---|---|
| `withlib-s1+entry` | `distributor-wiki@v2` (unchanged) with M1 |
| `base-walks+entry` | the untrained base with M1 — does the LoRA add anything once the door is open? |

Beside them, from REAL0 on the same 40 rows (paired across sessions, vLLM's spread stated): `withlib-s1` 0/25 and
`base-walks` 1/25 on the headline, `base-reads` 22/25 (the ceiling).

**The questions are REAL0's, and their failures have been read** (the first search of each walk). M1 does not depend on
any question — the same entry for every row, BM25 untuned — which is why they are reused; a new set is the cleaner
instrument, and it is what M2/M3 will be measured on.

## Verdict (fixed here), on the headline (25 multi-hop)

- **THE ENTRY WAS THE GAP** — `withlib-s1+entry` ≥ 18/25 (≈ 80 % of the reading ceiling) and an improvement over REAL0's
  `withlib-s1` (exact sign test, $p \lt 0.05$). The walk inside pages transfers; the radar is the missing component.
- **THE ENTRY HELPS, THE WALK IS STILL SHORT** — an improvement, under 18/25 → M2.
- **THE ENTRY DOES NOT HELP** — no improvement → M2, the corpus.
- Beside, never folded in: `withlib-s1+entry` vs `base-walks+entry` (does the trajectory LoRA beat the untrained base
  once both enter the same way? A tie means the LoRA adds nothing on real documents).

## Stopping condition

One session; no change to the entry, the searcher or the bars after it starts.

## Result

*(written after S)*
