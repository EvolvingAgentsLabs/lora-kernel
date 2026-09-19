# nursing-iv — the first library

IV therapy management as a library of notes: three procedures on the `harness/` shelf, each a
skeleton plus one note per step; a small `wiki/` tree; two example `site/` layers. Format and rules:
[`docs/MEMORY.md`](../../docs/MEMORY.md) §1. Built by `python3 -m training.nursing.library`; checked
by `python3 -m memory.lint knowledge/nursing-iv`.

**Attribution.** Adapted from Nursing Skills (Open RN, Chippewa Valley Technical College), Chapter 23 IV Therapy Management, NCBI Bookshelf NBK596734, CC BY 4.0. The step bodies are that text, with adaptable quantities turned into
slots. Titles, `when:` / `what:` lines, links and the wiki notes were written for this repository.

**The `site/` layers are invented.** `ward-7b` changes values the textbook states; `unit-4c` ADDS
sentences the source does not have — made-up unit rules of the form "a quantity, and another value of
it under a condition", there so a corpus can show that shape. Their numbers are placeholders. No real
unit's protocol is represented. One wiki note, `rates/drop-factor`, carries the chapter's own
two-valued sentence (macro-drip against micro-drip sets), byte-checked against the page.

**This is training material for a language model. It is not clinical guidance.**
