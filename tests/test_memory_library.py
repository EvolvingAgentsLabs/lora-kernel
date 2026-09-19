"""knowledge/nursing-iv — W1's gate (docs/MEMORY.md §10): the lint passes; every walk the oracle
needs exists. And the two ways that gate could pass while being wrong: the files on disk are not
what the builder makes, or the gate cannot fail.

    passed  ⇔  |lint findings| = 0  ∧  ∀ q ∈ questions.build(): oracle_walk(q) exists
"""

import shutil
from pathlib import Path

from memory.lint import lint
from memory.notes import Library, render
from training.nursing import library as lib_mod
from training.nursing.source import CHECKLISTS

ROOT = Path(__file__).resolve().parent.parent / "knowledge" / "nursing-iv"


def test_the_shipped_library_passes_the_lint():
    assert lint(ROOT) == []


def test_the_files_on_disk_are_what_the_builder_makes():
    files = lib_mod.build()
    repo = ROOT.parent.parent
    for rel, text in files.items():
        assert (repo / rel).read_text() == text, rel
    assert {str(p.relative_to(repo)) for p in ROOT.rglob("*.md")} == set(files)


def test_every_procedure_walks_its_checklist_in_the_source_s_order():
    lib = Library.load(ROOT)
    assert len(lib.procedures()) == 3
    for slug, p in lib_mod.PROCEDURES.items():
        walk = lib.walk(f"nursing-iv/harness/{slug}")
        lines = CHECKLISTS[p["checklist"]]
        assert len(walk) == len(lines)
        for note_id, line in zip(walk, lines):
            got = render(lib[note_id]).replace("at least 5 seconds", "at least five seconds")
            assert got == line, note_id          # the textbook layer renders the source back


def test_every_note_is_attributed():
    lib = Library.load(ROOT)
    for n in lib.notes.values():
        assert "CC BY 4.0" in n.source, n.id
    assert "CC BY 4.0" in (ROOT / "README.md").read_text()


def test_the_gate_passes_on_all_72_questions():
    g = lib_mod.gate(ROOT)
    assert g["passed"] and g["questions"] == 72 and g["walks_found"] == 72
    assert g["kinds"]["step"] == 70 and g["kinds"]["procedure"] == 3


def test_the_gate_can_fail(tmp_path):
    """Remove one step a walk needs: the lint AND the walks must both say so."""
    broken = tmp_path / "nursing-iv"
    shutil.copytree(ROOT, broken)
    (broken / "harness" / "discontinue-iv" / "07-hold-pressure.md").unlink()
    g = lib_mod.gate(broken)
    assert not g["passed"]
    assert g["lint_findings"] and g["walks_missing"]
    assert any(q.startswith("site-") for q in g["walks_missing"])


def test_a_site_question_is_answered_by_the_site_layer_and_not_by_the_textbook():
    from training.nursing.questions import build
    lib = Library.load(ROOT)
    for q in (q for q in build() if q["kind"] == "site"):
        walk = lib_mod.oracle_walk(q, lib)       # asserts `answer [site]` is in the served text
        assert walk[0].count("/") == 2 and len(walk) >= 2


def test_the_example_site_overrides_only_what_exists():
    lib = Library.load(ROOT)
    site = lib.sites["ward-7b"]
    n = lib["nursing-iv/harness/primary-infusion/20-cleanse-cap"]
    assert "15 [site] seconds" in render(n, site)
