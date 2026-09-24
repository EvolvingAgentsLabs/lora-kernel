# distributor-wiki — W9's evaluation world, pages of atomic statements

**An invented distribution company, not a real one.** Every name, number and link here was drawn by
`training/wiki/world.py` from seed `20260924`; any resemblance to a real firm, person or place is the
generator's, not a claim. It exists so a model cannot know its facts by heart: famous Wikipedia facts
are in a 4B's weights, and a test of the memory on them would measure the weights
([`docs/MEMORY.md`](../../docs/MEMORY.md) §1.6).

Shaped like Wikipedia: each page is a list of `§anchor` statements, one sentence each, links inside
them. `wiki/` holds products, suppliers, depots, carriers and staff; `harness/` one recipe per role of
the reference organisation. **Do not edit by hand** — it is the frozen generator's output, and
`tests/test_wiki.py` holds the two byte-equal. Never used for training: the corpus is drawn from other
worlds. Apache 2.0 like the rest of the repository.
