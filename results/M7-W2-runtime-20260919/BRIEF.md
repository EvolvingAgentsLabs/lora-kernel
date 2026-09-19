# M7 · W2 — the runtime: three verbs, layers, the conformance guard (pre-registered 2026-09-19)

**Question.** Can the referee of `docs/MEMORY.md` §5 carry every walk the oracle needs — on the
corpus-mode loop the pool already runs (`accept_rank.run_chain`, unchanged) — and does it cut a walk
that breaks the library's own links, without consulting any answer?

**Falsification, written before the runtime exists.** The gate fails if any of:
- one of the **72** oracle walks of `training/nursing/library.py` (W1, `gate.json`) does not pass
  through the runtime: a refusal, a malformed call, a guard violation, a budget reached, or a note
  the walk needs that the runtime's own results never offered an id for;
- a `site` walk does not show the question's answer, marked `[site]`, in the text the runtime wrote;
- a `rate` walk's `<calc>` does not return the question's answer within its tolerance;
- any path-shaped id (`nursing-iv/…`) appears in any text the expert would read;
- in `strict` mode any of three violating walks is **not** cut: a step opened with its `requires`
  unopened; an id opened that the conversation never returned; a step opened out of order (two
  ahead along `next`). In `recover` mode the same walks must continue, with the error inline.

**Arms.** One: scripted generations. No model runs — W2 needs none, and no model runs on this
machine. The script reads the ids it opens **from the runtime's own output**, by title, so an id the
runtime never offered cannot be opened by the script either; the oracle knows *which note*, never
*which id*.

**Suite.** The 72 questions of `training/nursing/questions.py` (24 order, 24 next, 12 rate, 12
site), fixed seed; walks of 2 to 33 notes. `site` questions are served through a site layer holding
that question's value. Budgets are the spec's (§3): k = 3, 24 opens, 12 searches — except that the
longest oracle walk is 33 notes, so the open budget is a parameter of the runtime and the gate runs
it at the value reported in `gate.json`; **said here because a cap below the corpus's depth scores
the cap** (the fluids suite already paid for that).

**Models / provider.** None.

**Parameters.** Opaque ids: 3 characters of `[a-z0-9]`, re-drawn per conversation from a seeded
generator. `<search>` in W2 is **lexical** — overlap on `when`, plus β = 0.5 on `what`, top 3 — behind
the interface W3's radar replaces (§2.3 keeps lexical search as a baseline in any case). Its recall
on oracle queries is *reported*, not gated beyond "the walk could start": ranking is W3's gate.

**Cost.** Zero GPU, zero dollars, seconds.

**Abort rule.** None needed at this cost. **Redesign count: 0**; a second reshaping of the gate after
its first run ends W2 as *not passed*.

**The gate can fail** — a test breaks a `requires` link's target out of a walk and the gate reports it.

## Result **[ran]** 2026-09-19 · PASSED — 72 of 72 walks through the runtime

Zero GPU, under a second. Read off `gate.json`.

| | |
|---|--:|
| oracle walks through the runtime | **72 / 72** (order 24, next 24, rate 12, site 12) |
| commands | 949 — 72 searches, 865 opens, 12 calcs; one log line each |
| refused · malformed · guard violations | 0 · 0 · 0 |
| site walks showing `answer [site]` · rate walks whose `<calc>` is the answer | 12 / 12 · 12 / 12 |
| library ids in text shown to the expert | 0 |
| violating walks cut in `strict` / continued in `recover` | 3 / 3 · 3 / 3 |

`skipped_requires` is cut at call 4 of 11 (`ERROR: requires gsj first`), `unknown_id` at 3 of 5
(`ERROR: no note zz9 in this conversation`), `out_of_order` at 5 of 7. The gate fails on a copy of the
library with one `requires` pointing forward (`tests/test_memory_runtime.py::test_the_gate_can_fail`).

**What this does not say.** No model ran: whether an expert *writes* these verbs, or recovers from an
inline error, is W5 and the `recover` arm. Search is lexical and the oracle queries each note by its
own `when`, so 72/72 at rank 1 is no evidence about ranking — that is W3's gate. With opaque ids a
step can only be jumped to through `<search>`, which is how the violating walks do it.

**Spec amended by this run:** §3's budget of 24 opens was below the first library's 32-step
procedure; it is 48. **Redesign count: 0** — the gate is the one written above; the script changed
once before its first complete run (the oracle now remembers the ids `next` lines taught it, which
`recover` walks need to go back).
