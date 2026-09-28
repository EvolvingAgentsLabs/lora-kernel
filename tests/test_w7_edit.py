r"""W7's instrument (training/wiki/w7_edit.py): the patch is one line of one Markdown page, the oracle follows it, and the
verdict's bands are the BRIEF's — $\mathrm{follows}\ge 0.9\cdot\mathrm{control}$ and $\mathrm{stale}\le 2$, control ≥ 32."""
import tempfile
from pathlib import Path

from training.wiki import grade as gr
from training.wiki import w7_edit as w


def test_fixtures_are_training_rows_with_numeric_answers_spread_over_families():
    rows = w.fixtures()
    assert len(rows) == 40 == len({r["case_id"] for r in rows})
    assert all(1000 <= int(r["world"]) < 1032 for r in rows)                   # the member's own training worlds
    assert all(all(gr._NUM.fullmatch(t) for t in r["check"]["tokens"]) for r in rows)
    assert len({r["family"] for r in rows}) >= 12 and w.fixtures() == rows      # deterministic


def test_the_patch_changes_one_statement_line_and_the_library_reads_it_back():
    r = w.fixtures()[0]
    root = Path(tempfile.mkdtemp())
    p = w.patch(r, root)
    page = root / p["patch"]["file"]
    before = [l for l in p["patch"]["-"].splitlines()]
    assert p["patch"]["-"] != p["patch"]["+"] and p["patch"]["+"] in page.read_text() and before[0] not in page.read_text()
    nid, anchor = r["support"]
    assert all(t in p["lib"].notes[nid].body for t in p["tokens"])
    assert not any(gr._has(p["patch"]["+"], t) for t in r["check"]["tokens"])  # the old value is gone from the line


def test_the_edited_row_asks_for_the_new_value_and_refuses_the_old():
    r = w.fixtures()[1]
    e = w.edited_row(r, ["99:99"] if ":" in r["check"]["tokens"][0] else ["987654"])
    assert e["check"]["never"] == r["check"]["tokens"] and e["answer"] != r["answer"]
    assert r["answer"] == w.fixtures()[1]["answer"]                            # the original is not mutated


def _rec(ctrl, follows, stale, memory=10, g1=True):
    ids = [f"c{i}" for i in range(40)]
    c = {i: {"credit": k < ctrl} for k, i in enumerate(ids)}
    e = {i: {"credit": k < follows, "stale": k >= 40 - stale} for k, i in enumerate(ids)}
    cb = {i: {"memory": k < memory} for k, i in enumerate(ids)}
    return {"G1": {"applied": g1}, "arms": {"control": c, "edited": e, "closedbook": cb}}


def test_the_verdict_bands_written_first():
    assert w.verdict(_rec(40, 36, 2))["reading"].startswith("PASSED")
    assert w.verdict(_rec(40, 35, 0))["reading"].startswith("FALSIFIED")
    assert w.verdict(_rec(40, 40, 3))["reading"].startswith("FALSIFIED")
    assert w.verdict(_rec(31, 31, 0))["reading"].startswith("VOID: the control")
    assert w.verdict(_rec(40, 40, 0, g1=False))["reading"].startswith("VOID: G1")
    assert "reading, not overruling" in w.verdict(_rec(40, 40, 0, memory=4))["reading"]
