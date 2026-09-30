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

## Result [ran] — THE ENTRY DOES NOT HELP (the member); the section is the new gap

One L4 session (boot attempts 1–2 silent, 3 took), 0 errors. `real1.json`. The runner's printed verdict (`NOTHING
SCORED`) is W9's and does not apply.

| arm | headline (25) | one-hop (11) | none (4) | all (40) |
|---|---|---|---|---|
| `withlib-s1+entry` | **1** (value-right 2) | 0 | 3 | 4 |
| `base-walks+entry` | **4** (value-right 8) | 2 | 4 | 10 |
| REAL0 `withlib-s1` / `base-walks` | 0 / 1 | | | 4 / 2 |
| REAL0 `base-reads` (ceiling) | 22 | | | 37 |

- **Verdict:** `withlib-s1+entry` 1/25 against REAL0's 0/25 — no improvement: **THE ENTRY DOES NOT HELP** (for the
  member). Beside: `withlib-s1+entry` vs `base-walks+entry` a tie (1 : 4, $p = 0.375$).
- **Read where it happens — the entry works, the section does not.** Both arms now open pages in 40/40 walks and reach
  the supporting page in **17/25** headline walks, but open **the supporting statement** in only **2/25** (member) and
  **6/25** (base). The contents list a page shows is its anchors — on a regulation, paragraph labels (`§a-2`, `§h`) that
  name nothing. Choosing a section is choosing blind. (The member also still refuses 23/40 after reading a wrong section.)
- Zero-GPU checks beside it: descriptive anchors from a paragraph's first words let a word-overlap chooser pick the
  supporting section 5–7/25; statement-level BM25 puts it in the top 3 for 11/25 — neither closes it alone.

**Next: REAL2** — the page opens with its statements' text (the second and last runtime variant).
