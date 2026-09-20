"""W5d — the answer policy: the adapter walks, and WHO WRITES the final line depends on the kind of task.

What is held here with zero GPU. The kind of a task is read off the STATEMENT alone — an evaluation
row's `family` does not exist at serving time. The table is frozen: carry and rate to the adapter, a
value to the bare base. A policy record is the adapter's own record where the adapter writes, and its
RECORDED walk plus the base's line where the base does, graded by the untouched grader — so a right
value over a note the walk never opened still earns nothing. The verdict is three paired exact sign
tests, p = 2 * sum_{k<=min(b,c)} C(b+c,k) 2^-(b+c) (FOUNDATIONS §7.1): policy vs withlib must be an
improvement, the control must not regress, and against base-reads a tie is reported as a tie.
"""
import json
import pathlib
import re

import pytest

from memory.notes import Library
from training.nursing import answer_policy as ap
from training.nursing import walks_policy as wp
from training.nursing.library import ROOT

LIB = Library.load(ROOT)
W5C = json.loads(wp.W5C.read_text())
V2 = wp.load_sets(wp.DATA["attribution"])


def test_the_table_is_the_one_the_brief_froze():
    assert ap.WRITER == {"carry": "adapter", "rate": "adapter", "value": "base"}
    assert ap.KIND_OF_FAMILY == {"carry": "carry", "none": "carry", "rate": "rate", "quantity": "value", "conditional": "value"}


def test_the_kind_is_read_off_the_statement_alone_and_agrees_with_the_generator_on_rows_nobody_evaluates():
    got = ap.agreement([pathlib.Path("training/nursing/data_walks_v2/train.jsonl"),
                        pathlib.Path("training/nursing/data_walks/train.jsonl")])
    for path, a in got.items():
        assert a["agreement"] == 1.0 and not a["disagree"], path
        assert a["agreement"] >= 0.98          # the bar under which the brief says: stop and report, do not tune


def test_an_ask_that_names_no_form_is_the_adapters_and_one_that_names_two_is_refused():
    assert ap.kind("A central line dressing is due to be changed. What do you do?") == "carry"
    with pytest.raises(ValueError):
        ap.kind("Report the last step you carried out. Answer with the quantity and its unit.")


def test_the_kind_does_not_look_at_the_family(monkeypatch):
    row = dict(V2["heldout"][0])
    assert ap.kind(row["statement"]) == ap.kind({**row, "family": "rate"}["statement"])


def _walked(cid):
    for s in ("heldout", "control"):
        if cid in W5C["arms"]["withlib"][s]["records"]:
            return W5C["arms"]["withlib"][s]["records"][cid]


def _gen(final):
    return lambda system, user, conv=None: (lambda prefix: final)


def test_where_the_adapter_writes_the_policy_record_is_the_adapters_own_record():
    row = next(r for r in V2["heldout"] if r["family"] == "carry")
    walked = _walked(row["case_id"])
    got = wp.policy_case(LIB, row, walked, _gen("never asked"))
    assert got["written_by"] == "adapter" and got["kind"] == "carry"
    assert (got["state"], got["credit"], got["final"]) == (walked["state"], walked["credit"], walked["final"])


def test_where_the_base_writes_it_reads_the_pages_the_adapters_walk_opened_and_the_grader_is_untouched():
    failed = [r for r in V2["heldout"] if r["family"] == "conditional" and not _walked(r["case_id"])["credit"]]
    assert len(failed) == 14                     # W5c [ran]: every one on a clean walk
    row = failed[0]
    right = wp.policy_case(LIB, row, _walked(row["case_id"]), _gen(row["answer"]))
    assert right["written_by"] == "base" and right["credit"] and right["state"] == "right"
    wrong = wp.policy_case(LIB, row, _walked(row["case_id"]), _gen("0 minutes"))
    assert not wrong["credit"]


def test_a_right_value_over_a_walk_that_never_opened_the_note_still_earns_nothing():
    row = next(r for r in V2["heldout"] if r["family"] == "conditional")
    walked = dict(_walked(row["case_id"]))
    walked.update(text="Not in my library.", calls=0, opened=0, opened_ids=[], violations=[], refused=0, malformed=0)
    got = wp.policy_case(LIB, row, walked, _gen(row["answer"]))
    assert not got["credit"] and got["state"] in ("unread", "wrong", "unreplayable")


def test_a_walk_lost_to_transport_is_an_error_not_a_score():
    row = V2["heldout"][0]
    got = wp.policy_case(LIB, row, {"id": row["case_id"], "error": "ReadTimeout"}, _gen("x"))
    assert "error" in got and "credit" not in got


def test_every_recorded_walk_the_base_would_read_from_replays_and_the_ceiling_is_what_the_brief_quotes():
    walks = {**W5C["arms"]["withlib"]["heldout"]["records"], **W5C["arms"]["withlib"]["control"]["records"]}
    reads = {**W5C["arms"]["base-reads"]["heldout"]["records"], **W5C["arms"]["base-reads"]["control"]["records"]}
    c = wp.ceiling(LIB, V2, walks, reads)
    assert c["headline"] == {"n": 66, "written_by_base": 31, "unreplayable": 0, "ceiling": 56, "withlib": 42,
                             "base_reads": 46, "prompt_identical_to_base_reads": 23}
    assert (c["control"]["ceiling"], c["control"]["withlib"], c["control"]["unreplayable"]) == (75, 78, 0)


def _rec(policy, withlib, reads, control=("tie", 1, 1), applied=True, errors=0):
    def pr(label, state, a, b):
        return {"pair": label, "state": state, "only_a": a, "only_b": b, "p_value": 0.01 if state != "tie" else 0.5}
    s = lambda credit: {"credit": credit, "scored": 60, "right": credit - 5, "errors": errors, "missing": 0}
    summ = {x: {"headline": s(v), "control": s(70)} for x, v in (("policy", 50), ("withlib", 40), ("base-reads", 45))}
    return {"G1": {"withlib": {"applied": applied}},
            "claim": {"analysis": {"excluded_unreplayable": [], "summary": summ,
                                   "pairs": {"headline": [pr("policy vs withlib", *withlib), pr("policy vs base-reads", *reads)],
                                             "control": [pr("policy vs withlib", *control)]},
                                   "pairs_right_only": {"headline": []}}}}


def test_the_verdict_has_every_outcome_the_brief_names():
    good = wp.verdict(_rec(None, ("improvement", 12, 1), ("improvement", 9, 1)))
    assert good["passed"] and "BEATS" in good["reading"]
    tie = wp.verdict(_rec(None, ("improvement", 12, 1), ("tie", 6, 4)))
    assert tie["decided"] and not tie["passed"] and "TIE" in tie["reading"] and tie["policy_buys_something"]
    assert "FALSIFIED" in wp.verdict(_rec(None, ("tie", 3, 2), ("tie", 2, 2)))["reading"]
    assert "NOT A SERVING DESIGN" in wp.verdict(_rec(None, ("improvement", 12, 1), ("tie", 6, 4), ("REGRESSION", 0, 9)))["reading"]
    assert "VOID" in wp.verdict(_rec(None, ("improvement", 12, 1), ("tie", 6, 4), applied=False))["reading"]
    assert "VOID" in wp.verdict(_rec(None, ("improvement", 12, 1), ("tie", 6, 4), errors=1))["reading"]
    assert wp.verdict({})["decided"] is False


def test_the_recorded_file_is_read_and_never_written(tmp_path):
    before = wp.W5C.read_bytes()
    src = pathlib.Path("training/nursing/walks_policy.py").read_text()
    assert "W5C.write" not in src and 'open(W5C, "w"' not in src
    assert wp.W5C.read_bytes() == before


def test_every_prefix_the_runner_prints_reaches_the_watching_terminal():
    from tests.test_chain_scripts import peek_patterns
    watched = peek_patterns(pathlib.Path("training/harness/chain_serve.sh"))
    printed = set(re.findall(r'print\(f?"\[(\w+)\]', pathlib.Path("training/nursing/walks_policy.py").read_text()))
    assert printed and printed <= watched, printed - watched


def test_the_results_file_never_says_finished_before_the_run_is():
    """The chain greps the local results file for `"finished"` before it buys a session."""
    src = pathlib.Path("training/nursing/walks_policy.py").read_text()
    assert src.count('rec["finished"]') == 1
