# wikipedia-arts — the first encyclopedic-only slice, a `refs` proof

Three notes, wiki shelf only, no harness: `leonardo-da-vinci` (root, one child, `drawings`) and
`mona-lisa`, which points at `leonardo-da-vinci` through the new `refs` field — not a `parent`,
because a painting is not a kind of its painter. This is the trajectory the user asked whether this
repository's memory could do: *Mona Lisa → its painter → what else that painter made → drawings*,
built from one cross-shelf-shaped edge instead of the tree. Format and rules:
[`docs/MEMORY.md`](../../docs/MEMORY.md) §1; checked by `python3 -m memory.lint knowledge/wikipedia-arts`.

**Why `refs` and not a bigger schema.** `parent`/`children` classify; `requires`/`next`/`uses` are
control flow. Neither shape fits "the Mona Lisa was painted by Leonardo da Vinci." `refs` is one
generic, untyped list any note on either shelf may carry — the schema does not name what an edge
*means*. Which reference matters for a given request, and when to follow one instead of stopping, is
left to be a per-subdomain judgment a LoRA is trained on: the criterion is domain-specific, so it
belongs in the weights, not in a runtime rule enumerating relation types.

**Attribution — CC BY-SA 4.0, not this repository's Apache 2.0.** Adapted from the English Wikipedia
articles "Mona Lisa" and "Leonardo da Vinci" (and its "Drawings" section), each CC BY-SA 4.0. Titles,
`when:`/`what:` lines and the `refs` edge were written for this repository; the body sentences
restate the articles' own facts in the note's own words. **Wikipedia's licence is ShareAlike: this
directory's own text — the three `.md` files under `wiki/` and this README — is itself CC BY-SA 4.0,
not Apache 2.0, and stays isolated to this directory.** No code here is licensed under it; only the
note text is.

**This is a proof of the schema, not a built or measured library.** No radar, no LoRA, no runtime
walk over it yet — `results/W8-wikipedia-refs-20260922/BRIEF.md` names what would come next and what
would falsify it. Three notes is a slice, not Wikipedia: no page beyond these two, and no claim that
this generalises past them.
