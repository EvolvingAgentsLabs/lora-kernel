"""Milestone 1: the pool on another base — the verdict, and the holes the rewrite left.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §9.2). A member holds its recorded release
iff the exact sign test on discordant pairs reads a tie or an improvement; it loses iff it
reads a regression. `moved` needs every gate and both members.
"""

import re
from pathlib import Path

from training.harness import pool_base


def _rec(email=("tie", "improvement"), desk=("tie", "improvement"), g1=True):
    pr = lambda a, b: [{"pair": "new vs recorded", "state": a}, {"pair": "new vs base", "state": b}]
    names = list(pool_base.MEMBERS)
    return {"G1": {m: {"applied": g1} for m in names},
            "G2": {m: {"reachable": True} for m in names},
            "G2_auto": {m: {"served": m} for m in names},
            "pairs": {"email-full": pr(*email), "desk-commitment": pr(*desk)}}


def test_both_holding_and_every_gate_is_moved():
    assert pool_base.verdict(_rec())["moved"] is True


def test_an_improvement_over_the_recorded_run_also_holds():
    assert pool_base.verdict(_rec(email=("improvement", "improvement")))["moved"] is True


def test_a_member_losing_to_its_own_release_keeps_the_pool_where_it_is():
    v = pool_base.verdict(_rec(desk=("REGRESSION", "improvement")))
    assert v["moved"] is False and "desk-commitment" in v["reading"]


def test_a_member_that_only_ties_the_new_base_is_not_a_member():
    assert pool_base.verdict(_rec(email=("tie", "tie")))["moved"] is False


def test_an_adapter_that_is_not_applied_stops_the_run_and_says_so():
    v = pool_base.verdict(_rec(g1=False))
    assert v["moved"] is False and v["reading"].startswith("STOPPED AT G1")


def test_every_member_names_a_corpus_and_a_recorded_run_that_exist():
    for m, spec in pool_base.MEMBERS.items():
        assert Path(spec["corpus"]).exists(), m
        assert Path(spec["recorded"][0]).exists(), m


def test_a_module_run_by_name_exists():
    """The rewrite of 2026-09-19 cleaned the tree by import closure and removed
    `training.code.train_one`, which three living runners start with
    `subprocess … "-m", "training.code.train_one"` — a string, invisible to an import
    graph [ran]. Every `training.*` module named in a string, a chain or a document has to
    be a file."""
    named = set()
    roots = [*Path("training").rglob("*.py"), *Path("training").rglob("*.sh"),
             *Path("docs").glob("*.md"), Path("README.md"), Path("training/README.md")]
    for f in roots:
        for m in re.findall(r"(?:-m\s+|MODULE=|[\"'])(training\.[a-z_0-9.]+)", f.read_text(errors="replace")):
            named.add(m.rstrip("."))
    missing = sorted(m for m in named
                     if not Path(m.replace(".", "/") + ".py").exists()
                     and not Path(m.replace(".", "/")).is_dir()
                     and not m.endswith("<runner>"))
    assert not missing, f"named and absent: {missing}"


def test_only_without_stop_after_training_is_refused(monkeypatch):
    """A session lives sixty minutes and a member takes ~45 to train, so the pool is trained a
    member a session. A partly trained pool must never reach the gates: it would score a member
    that is not there."""
    import sys
    monkeypatch.setattr(sys, "argv", ["p", "--only", "desk-commitment", "--out", "/tmp/_pb_refused.json"])
    assert pool_base.main() == 2


def test_only_refuses_a_name_that_is_no_member(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["p", "--only", "nobody", "--stop-after-training", "--out", "/tmp/_pb_unknown.json"])
    assert pool_base.main() == 2
