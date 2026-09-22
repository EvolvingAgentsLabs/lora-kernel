# W8 — the encyclopedic "Wikipedia variant," a `refs` proof (pre-registered and run 2026-09-22)

**Question, from the user's own example.** *"Cuáles son las obras del autor de la Mona Lisa"* — on
Wikipedia the trajectory is Mona Lisa → its painter (a link) → Leonardo da Vinci → Drawings (a
section). Does this repository's memory schema support that shape, and if not, what is the cheapest
change that would, without training or measuring anything yet?

**Finding, before any code.** No — `parent`/`children` (the wiki shelf's only cross-note edge)
classify: general to specific, is-a. "The Mona Lisa was painted by Leonardo da Vinci" is not "the
Mona Lisa is a kind of Leonardo da Vinci." Wikipedia's own trajectory is not a taxonomy walk; it is a
reference followed, then a taxonomy walk from there (da Vinci → his drawings, which *is* a
part-of/kind-of relation and already fits `children`).

**Mechanism.** One field, `refs: [note id, …]`, added to `memory/notes.py`'s schema — generic,
untyped, legal on either shelf. The schema does not name what an edge means on purpose: per the
user's own point (2026-09-21 session), *which* reference matters for a given request, and when to
follow one instead of stopping, is a per-subdomain judgment that belongs in a LoRA's weights, not in
a runtime rule enumerating relation types. `memory.lint` checks only that a `refs` target resolves —
the same generic `link` rule `uses`/`requires`/`parent`/`children` already share, no new rule needed.

**The slice.** `knowledge/wikipedia-arts/` — three notes, wiki shelf only: `mona-lisa` (`refs` →
`leonardo-da-vinci`), `leonardo-da-vinci` (root, `children` → `drawings`), `drawings` (leaf). CC
BY-SA 4.0, restated from the English Wikipedia articles "Mona Lisa" and "Leonardo da Vinci" —
isolated to this one directory's licence (ShareAlike; the rest of this repository is Apache 2.0),
same discipline `knowledge/nursing-iv/`'s CC BY 4.0 attribution already established.

**Result [ran] 2026-09-22.** `python -m memory.lint knowledge/wikipedia-arts` — 0 findings.
`Library.load(...)["wikipedia-arts/wiki/mona-lisa"].refs[0]` resolves to `leonardo-da-vinci`, whose
`.children[0]` resolves to `drawings` — the exact trajectory named in the question, mechanically
followed, zero GPU, zero model. `tests/test_wikipedia_arts.py` (4 tests) and two new cases in
`tests/test_memory_notes.py` hold it as a regression; 631/631 of the repository's tests pass.

**What this is not.** Not a built library at the size of `nursing-iv` (three notes, not ninety-four),
not radar-indexed, not walked by any runtime yet, and nothing here is trained or measured against an
untrained base — this is the schema-level falsifier only: *can the format even express the
trajectory the question needs?* It can. **Next, if bought:** a radar/runtime pass over this slice
(reuses W2's referee, W3's radar unchanged — the same "same grader for every arm" discipline as the
router arms) to see whether a `<search>` on "who painted the Mona Lisa" surfaces `mona-lisa` and
whether the referee follows its `refs` the way it already follows `uses`; that is a new, larger
question and is not run here.

**Falsified by:** a `refs` target that does not resolve (lint would say so — it does not); a schema
change that required touching `requires`/`next`/`uses`/`parent`/`children` semantics (it did not —
`refs` is additive, and the toy-library regression test in `test_memory_notes.py` confirms the
existing rules are unchanged).

**Redesign count: 0.**
