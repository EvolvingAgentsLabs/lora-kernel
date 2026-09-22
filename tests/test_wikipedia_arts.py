"""knowledge/wikipedia-arts — the `refs` proof (docs/PLAN.md addendum, W8, results/W8-wikipedia-refs-20260922).

The trajectory the user asked whether this memory could do: a request about the Mona Lisa follows
`refs` to its painter, then `children` to what else that painter made — a cross-shelf-shaped edge
`parent`/`children` cannot express, since a painting is not a kind of its painter.

    passed  ⇔  |lint findings| = 0  ∧  mona.refs → da_vinci.children → drawings resolves
"""

from pathlib import Path

from memory.lint import lint
from memory.notes import Library, Note

ROOT = Path(__file__).resolve().parent.parent / "knowledge" / "wikipedia-arts"


def test_the_shipped_library_passes_the_lint():
    assert lint(ROOT) == []


def test_the_mona_lisa_to_drawings_trajectory_resolves_through_refs_then_children():
    lib = Library.load(ROOT)
    mona = lib["wikipedia-arts/wiki/mona-lisa"]
    assert mona.refs == ["wikipedia-arts/wiki/leonardo-da-vinci"]
    da_vinci = lib[mona.refs[0]]
    assert da_vinci.children == ["wikipedia-arts/wiki/leonardo-da-vinci/drawings"]
    drawings = lib[da_vinci.children[0]]
    assert "Vitruvian Man" in drawings.body


def test_refs_is_generic_a_wiki_note_and_a_harness_note_may_both_carry_it():
    """The field is untyped on purpose (docs/MEMORY.md §1 addendum) — the lint does not restrict
    it to one shelf the way `parent`/`children` and `requires`/`next`/`uses` are restricted."""
    wiki_with_refs = Note.parse("""---
id: t/wiki/a
shelf: wiki
kind: concept
title: A
when: t
what: t
refs: [t/wiki/b]
---
body
""")
    harness_with_refs = Note.parse("""---
id: t/harness/a
shelf: harness
kind: step
title: A
when: t
what: t
refs: [t/wiki/b]
---
body
""")
    assert wiki_with_refs.refs == ["t/wiki/b"] and harness_with_refs.refs == ["t/wiki/b"]


def test_every_note_is_attributed_and_the_directory_names_its_own_licence():
    lib = Library.load(ROOT)
    for n in lib.notes.values():
        assert "CC BY-SA 4.0" in n.source, n.id
    readme = (ROOT / "README.md").read_text()
    assert "CC BY-SA 4.0" in readme and "isolated to this directory" in readme
