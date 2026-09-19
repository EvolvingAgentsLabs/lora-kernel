# M7 · W1 — the first library and its lint

**What.** `memory/notes.py` (a note, a library, the layers case ▸ site ▸ textbook), `memory/lint.py`
(§1.5 of [`docs/MEMORY.md`](../../docs/MEMORY.md)), and `knowledge/nursing-iv/`: three Open RN IV
procedures (CC BY 4.0) as skeleton + one note per step, a wiki tree, one example site layer.

**Why.** W1 of the memory's build order. Nothing after it can be built on a library that does not
hold the walks the oracle needs.

**Model, provider.** None. No model runs in W1, locally or anywhere.

**Gate (written before the library was).** The lint reports 0 findings **and** for each of the 72
questions of `training/nursing/questions.py` the oracle's walk exists:

$$\text{passed} \iff |\text{findings}| = 0 \;\wedge\; \forall q:\ \text{walk}(q)\ \text{exists}$$

where a walk *exists* means: every note on it resolves; each step's textbook rendering is the
source's checklist line; for a `site` question, serving the note through a site layer that overrides
that one slot puts `answer [site]` in the text, and the textbook rendering does not contain it.

**Falsified by** any finding, any missing walk — or a gate that cannot fail (a test removes one
step and requires both the lint and the walks to say so).

**Not measured here.** Whether any model can follow these notes. That is W5.

## Verdict [ran] 2026-09-19

| | |
|---|---|
| notes | 94 — 3 procedures, 70 steps, 18 concepts, 2 formulas, 1 table; 1 site layer |
| lint | **0 findings** (first build: 2 — both skeletons over the 150-token limit; see below) |
| oracle walks | **72 / 72** exist; length 2 (a rate: concept → formula) to 33 (procedure + 32 steps) |
| gate can fail | yes — one step removed: lint fires and the `site-*` walks over it go missing |
| **W1** | **PASSED** — `gate.json` |

**What the lint found on its first run.** A 32-step procedure's skeleton, written as the spec says
("its ordered step titles"), is 230 tokens against the 150 limit. The skeleton now lists each step's
*label* — the slug of its id, `20 cleanse cap` — 98 tokens; the full title lives in the step. The
limit held; the skeleton's wording gave.
