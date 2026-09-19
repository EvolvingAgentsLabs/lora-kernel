"""W2 — the runtime: three verbs, opaque ids, layers before the note is shown, the guard.

docs/MEMORY.md §3, §5. The guard's rule is  violation(n | opened) = requires(n) \\ opened ≠ ∅ ; the
W2 search is lexical,  s(n|q) = overlap(q, when) + β·overlap(q, what), top k = 3 (§2.3's formula with
token overlap for the inner product). No model runs: walks are scripted generations through the
pool's own corpus-mode loop, `accept_rank.run_chain`, unchanged.
"""
import json
import re
import shutil
from pathlib import Path

import pytest

from memory.guard import Guard
from memory.notes import Library, Site
from memory.runtime import TAG, ChainSuite, Conversation, Lexical, split_call
from training.harness.accept_rank import run_chain
from training.nursing import walks
from training.nursing.library import ROOT, SUB

PROC = f"{SUB}/harness/discontinue-iv"


@pytest.fixture(scope="module")
def lib():
    return Library.load(ROOT)


def _open_procedure(conv, lib):
    out = conv.answer("search", f" shelf=harness>{lib[PROC].when}")
    shown = re.search(r"\[(\w+)\] procedure · " + re.escape(lib[PROC].title), out).group(1)
    return shown, conv.answer("open", f">{shown}")


def test_the_grammar_is_the_specs_three_verbs_and_one_attribute():
    m = TAG.search("so <search shelf=wiki>drip rate</search>")
    assert (m.group(1), split_call(m.group(2))) == ("search", ("wiki", "drip rate"))
    assert split_call(TAG.search("<open>k3f</open>").group(2)) == (None, "k3f")
    assert TAG.search("<lookup>x</lookup>") is None


def test_search_returns_titles_and_when_lines_never_bodies(lib):
    conv = Conversation(lib)
    out = conv.answer("search", " shelf=harness>a peripheral IV is to be removed")
    assert out.splitlines()[0] == "3 notes" and len(out.splitlines()) == 4
    for n in lib.notes.values():
        assert n.body.splitlines()[0] not in out


def test_no_library_id_ever_reaches_the_expert_and_ids_are_redrawn(lib):
    a, b = Conversation(lib, seed=1), Conversation(lib, seed=2)
    (sa, ta), (sb, tb) = _open_procedure(a, lib), _open_procedure(b, lib)
    assert SUB not in ta and "/" not in sa and sa != sb
    assert re.fullmatch(r"[a-z0-9]{3}", sa)


def test_an_id_exists_only_once_a_result_has_shown_it(lib):
    conv = Conversation(lib, mode="recover")
    assert conv.answer("open", ">k3f") == "ERROR: no note k3f in this conversation"
    assert conv.answer("open", f">{PROC}").startswith("ERROR: no note")     # a path opens nothing
    assert conv.errors == {"unknown_id": 2} and conv.opened == []


def test_a_site_rule_is_applied_before_the_note_is_shown_and_marked(lib):
    target = f"{SUB}/harness/discontinue-iv/07-hold-pressure"
    site = Site(name="t", overrides={target: {"minutes": 7}})
    plan = [("search", f"harness|{lib[PROC].when}"), ("open", PROC)] + [("open", s) for s in lib.walk(PROC)[:7]]
    chain, conv = walks.run(lib, plan, site=site)
    assert "7 [site]" in chain["text"] and conv.errors == {}
    line = [l for l in conv.log if l.get("note") == target][0]
    assert line["slots"]["minutes"] == [7, "site"]                          # §5.4: which layer spoke


def test_strict_cuts_and_recover_writes_the_error_inline(lib):
    for mode, ended in (("strict", "guard: requires"), ("recover", None)):
        conv = Conversation(lib, mode=mode)
        _open_procedure(conv, lib)
        deep = lib.walk(PROC)[6]
        out = conv.answer("search", f" shelf=harness>{lib[deep].when}")
        shown = re.search(r"\[(\w+)\] step · " + re.escape(lib[deep].title), out).group(1)
        res = conv.answer("open", f">{shown}")
        assert re.fullmatch(r"ERROR: requires \w{3} first", res)
        assert conv.ended == ended and deep not in conv.opened
        assert conv.guard.violations[0]["kind"] == "requires"
    strict = Conversation(lib)
    strict.ended = "guard: requires"
    assert strict.answer("calc", ">1+1").startswith("ERROR: this task has ended")


def test_a_cut_walk_generates_nothing_more_and_is_not_answered(lib):
    plan = walks.violating(lib)["skipped_requires"]
    chain, conv = walks.run(lib, plan, mode="strict")
    assert conv.ended and chain["verdict"] is None and chain["refused"] == 1
    assert chain["text"].rstrip().endswith("first")                          # the error is the last thing written


def test_calc_never_raises_and_errors_are_counted(lib):
    conv = Conversation(lib)
    assert conv.answer("calc", ">500 * 20 / (4 * 60)") == "41.6667"           # §3's own example
    assert conv.answer("calc", ">1/0").startswith("ERROR:")
    assert conv.answer("calc", ">__import__('os')").startswith("ERROR:")
    assert conv.errors == {"calc": 2}


def test_budgets_end_the_task_as_not_answered(lib):
    conv = Conversation(lib, max_searches=1)
    conv.answer("search", ">remove an IV")
    assert "search budget" in conv.answer("search", ">remove an IV") and not conv.answered


def test_a_bad_guard_mode_is_refused():
    with pytest.raises(ValueError):
        Guard("lenient")


def test_lexical_search_respects_the_shelf(lib):
    assert all(lib[i].shelf == "wiki" for i in Lexical(lib).search("hand hygiene before touching", "wiki"))


def test_the_log_is_one_json_line_per_command_and_shapes_by_default(lib):
    conv = Conversation(lib)
    _open_procedure(conv, lib)
    lines = [json.loads(l) for l in conv.log_lines().splitlines()]
    assert [l["verb"] for l in lines] == ["search", "open"] and all("arg" not in l for l in lines)


def test_the_loop_is_the_pools_own_and_counts_a_malformed_call(lib):
    conv = Conversation(lib, mode="recover")
    suite = ChainSuite(conv)
    chunks = iter(["<open k3f></open>", "Done."])
    chain = run_chain(suite.wrap(lambda prefix: next(chunks)), {}, max_calls=4, suite=suite)
    assert chain["malformed"] == 1 and chain["refused"] == 1


def test_w2_gate_all_72_walks_pass_and_the_violating_walks_are_cut():
    g = walks.gate()
    assert g["passed"] and g["passed_walks"] == g["walks"] == 72
    assert g["totals"]["refused"] == g["totals"]["malformed"] == 0
    assert g["violating_walks_ok"] and set(g["violating_walks"]) == {"skipped_requires", "unknown_id", "out_of_order"}
    stored = json.loads(Path("results/M7-W2-runtime-20260919/gate.json").read_text())
    assert stored["passed"] and stored["totals"] == g["totals"]


def test_the_gate_can_fail(tmp_path):
    """Break one `next` link: the walks that cross it can no longer be followed, and the gate says so."""
    root = tmp_path / SUB
    shutil.copytree(ROOT, root)
    p = root / "harness" / "discontinue-iv" / "03-prepare-gauze.md"
    p.write_text(p.read_text().replace("requires: [", f"requires: [{SUB}/harness/discontinue-iv/09-assess-site, "))
    g = walks.gate(root)
    assert not g["passed"] and g["failures"]
    assert any("guard spoke" in " ".join(v) for v in g["failures"].values())
