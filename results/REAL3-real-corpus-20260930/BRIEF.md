# REAL3 — a trajectory member trained on real documents, measured on a family it never saw (M3)

**Written 2026-09-30, before the corpus is final and before anything trains or runs.**

## What and why

REAL0–REAL2 **[ran]**: the member trained on a generator's world never entered a real library (memorised queries and
shelves); the runtime's mitigations — the question's full-text entry on every shelf, pages opened with their statements —
took walks to the supporting page 24/25 but left the untrained base at 7/25 and `distributor-wiki@v2` at 5/25 on the
multi-hop headline, against a reading ceiling of 22/25. The loss is no citation, or the wrong paragraph among a page's
many. Neither model has ever been **shown** a real page read whole and the one statement cited from it.

**Order, and why M3 before M2.** M2 (a generated corpus with queries from the question and paraphrased recipe titles)
repairs the memorised entry — which the runtime's entry now bypasses. M3 trains the step that still fails. If M3 fails,
M2 would not rescue it; M2's lesson (no repeated strings) is carried into M3's gate instead (G6).

## The member — `real-walks-s0`

Gemma 4 E4B + LoRA (`release_gate.RECIPE`, seed 0, window 4,096 — a real page runs long), trained on
`training/wiki/data/train_real.jsonl` (`training/wiki/real_corpus.py`):

- **Documents — a different family from the evaluation.** `knowledge/regs-train`, ingested verbatim from 49 CFR 391/395/396
  (drivers, hours of service, inspection), 21 CFR 117 (food manufacturing practices, records), 29 CFR 1910 Subpart E
  (exits, emergency plans): 134 pages, 1,927 statements, 305 links. **21 CFR Part 1 and 29 CFR 1910.176/178 are absent.**
- **Questions written by a model (Claude Haiku) from one page, or from a statement and the page its link leads to,**
  then checked mechanically: the anchor exists, every number of the value is in the supporting statement (paragraph
  labels stripped) and none in the question, no section number in the question, no duplicate. Spend capped at $5.
- **Walks are the oracle's through the runtime the member is served with:** the question's full-text entry on every shelf,
  fallback, pages opened with their statements; graded by the strict grader (the citation must be the supporting
  statement).
- **Gate (`gate_real.json`):** G1 no evaluation library in the corpus · G2 no evaluation question · G3 every walk verified
  · G4 no value in a question · G5 every row within the window · G6 no question opening shared by more than 2 % of the
  corpus (M2's lesson).

## The evaluation — two sets on `knowledge/logistics-regs`, both written by someone other than the corpus's generator

1. **REAL3 fresh (the verdict):** `questions.jsonl` here — 40 new rows, ≥ 22 multi-hop, written blind to the training
   questions and to every model answer, no REAL0 question repeated, oracle 40/40 before freezing.
2. **REAL0's set (comparability):** the same 40 rows REAL0–REAL2 used — its failures have been read, so it is beside the
   verdict, never the verdict.

### REAL3's set as frozen (2026-09-30, before training) — and its limits, written before any answer

40 rows (`make_questions.py`): 13 one-hop, 19 two-hop, 4 three-hop, 4 the library cannot answer — **headline 23**; oracle
40/40 verified; every hop a real link; no token in an earlier statement; no value or section number in a multi-hop ask.
**Limits, stated now:** the library links sparsely (9 kinds of link; numbers only on 1.904, 1.900, 1.906§a, 1.912), so
the 23 headline rows hold 17 distinct (statement, question) pairs — 6 ask another row's question from a different
starting duty — and 11 reuse a REAL0 supporting statement with a different question. Many answers are **references**
(a section of the FD&C Act — 402, 801 — or a CFR number — 11.3, 1.227), where the training corpus asks mostly
**quantities**. Two rows (40 hours, 52 weeks) lose value credit if a model writes the whole product 40 × 52 = 2,080.

**Slices reported beside the verdict, fixed now:** the headline without the three rows closest to a REAL0 question
(`duty-electronic-29`, `duty-agreement-30`, `duty-agreement-31`; headline 20), and the headline split into quantity
answers and reference answers.

## Arms (one L4, vLLM, Gemma 4 E4B bf16, `--max-model-len 16384`), every arm with REAL2's runtime (`+page`)

| arm | what |
|---|---|
| `withlib-s0+page` with `--member-prefix adapters/real-walks-s` | `real-walks-s0` — the treatment |
| `base-walks+page` | the untrained base, same runtime — the baseline |

`distributor-wiki@v2` is not re-run: REAL2 measured it under this runtime (5/25 on REAL0's set).

## Verdict (fixed here), on REAL3's fresh headline

- **M3 WORKS** — `real-walks-s0` ≥ 70 % of the headline **and** an improvement over `base-walks+page` on the same rows
  (exact sign test, $p \lt 0.05$). Navigation and citation on real pages are learnable and transfer across document
  families: the trajectory LoRA is real, and its corpus must be real text.
- **M3 HELPS** — an improvement, under 70 %.
- **M3 FALSIFIED** — no improvement over the base: training on real walks does not transfer to another family.
- Beside: the same pair on REAL0's set; one-hop and `none` rows reported apart.

## Stopping condition

One training (A100, one session), one scoring (L4). No change to the corpus, the gate, the questions or the bars after
training starts. A second seed is bought only if M3 WORKS (W5e: two draws of one recipe can disagree).

## Run log

- **T [ran]:** `real-walks-s0` trained on an A100 (284 rows, 3 epochs, 54 steps, window 4,096); adapter home.
- **S1 attempt 1 — stopped by G1, nothing scored.** vLLM's identity probe (three generic prompts) saw the adapter change 1
  of 3 — a narrow, short training leaves off-domain text almost untouched. **Instrument redesign, before any score:** the
  G1 falls back to three domain probes (the evaluation rows' own questions, as the member is served) under the same rule
  — M9's redesign of 2026-09-26 for the same reason. A member vLLM did not apply serves the base's text on those too.
  S2 was stopped before it booted. This is the first redesign of REAL3's instrument.

## Result

*(written after S)*
