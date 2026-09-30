# REAL2 — does the walk work once a page shows its statements? The last runtime variant

**Written 2026-09-30, before anything runs.** M1 continued: REAL1 **[ran]** fixed the door (the supporting page reached
17/25) and found the next gap — the section. A real page's contents list is paragraph labels (`§a-2`), so a walk opens the
supporting statement 2/25 (member) or 6/25 (base) times. The reading is known to work: 22/25 with the right statements
open (REAL0 `base-reads`).

**The runtime change (`+page` arms; implies REAL1's entry):** `<open>page</open>` returns every statement under its
anchor — `§c (c) Carriers must retain training records…` — links rendered `[id] Title`; each counts as read for the
citation, not against the open budget (`Conversation.page_text`). The model reads the page and cites the statement, the
regime `base-reads` showed works, now reached by its own walk. The context is 16,384 tokens (the largest page, 1910.178,
is 6,859; the headline's pages are ≤ 2,208).

**This is the second runtime redesign on this question set, and the last.** If REAL2 does not reach the bar, the next
step is the corpus (M2: queries from the question, paraphrased recipe titles, a gate on repeated search strings; M3:
walks over ingested real documents, trained on one family, measured on another). **Whatever wins is confirmed on a new,
unseen question set before it is called the best.**

## Arms (one L4, vLLM, Gemma 4 E4B bf16, `--max-model-len 16384`), REAL0's frozen questions

| arm | what |
|---|---|
| `withlib-s1+page` | `distributor-wiki@v2`, entry + page text |
| `base-walks+page` | the untrained base, entry + page text |

## Verdict (fixed here), headline (25 multi-hop)

- **THE RUNTIME CLOSES IT** for an arm — ≥ 18/25 (≈ 80 % of the reading ceiling) and an improvement over the same arm
  in REAL1 (exact sign test, $p \lt 0.05$). If the **base** does it, real documents need a runtime, not a trajectory
  LoRA; if **only the member** does, the LoRA adds navigation on real text.
- **SHORT** — under 18/25 for both → the corpus (M2, then M3).
- Beside: `withlib-s1+page` vs `base-walks+page` (paired).

## Result [ran] — SHORT for both arms: the runtime alone does not close it

One L4 session, 0 errors, no context exhaustion. `real2.json` (the runner's `NOTHING SCORED` is W9's verdict).

| arm | headline (25) | value-right | one-hop (11) | all (40) | reached the supporting page |
|---|---|---|---|---|---|
| `base-walks+page` | **7** | 12 | 3 | 13 | 24/25 |
| `withlib-s1+page` | **5** | 8 | 0 | 8 | 24/25 |
| REAL1 (`+entry`) base / member | 4 / 1 | | | 10 / 4 | 17/25 |
| REAL0 `base-reads` (ceiling) | 22 | | | 37 | — |

- **Verdict: SHORT** — neither arm reaches 18/25. Beside: member vs base a tie (1 : 3, $p = 0.625$); the trajectory LoRA
  adds nothing on real text under any runtime tried.
- **Read where it happens.** The door and the page are now right (24/25 walks read the supporting page). What is lost:
  **no citation** — the model states a value but writes no `[id§anchor]` (base 12 of 18 misses, member 16 of 20); and
  reading the right paragraph among a page's 10–27 (value-right 12/25 against `base-reads`' 22/25, where only the
  supporting statements were shown).
- **Across REAL0 → REAL2 the base moved 1 → 4 → 7 and the member 0 → 1 → 5**: every runtime step helps, none is enough.

**As fixed in REAL2's brief, the runtime variants stop here** (two redesigns on one question set). Next is the corpus:
M2 (queries from the question, paraphrased recipe titles, a gate on repeated search strings) and M3 (walks over
ingested real documents — including the citation on a page read whole — trained on one document family and measured on
another), each with its own brief, and the winner confirmed on an unseen question set.
