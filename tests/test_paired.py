"""Every arm here runs the same fixtures, so two totals are not two samples.

The test that matters is the one over the recorded runs: it re-reads what the plan
already claims and checks the claim against the cases behind it.
"""

import glob
import json

import pytest

from training.harness.bar import compare, sign_test


def test_three_disagreements_all_one_way_is_not_a_win():
    """P15's headline, exactly. 10/30 against 7/30 hides three disagreements."""
    a = {f"c{i}": i < 10 for i in range(30)}
    b = {f"c{i}": i < 7 for i in range(30)}
    r = compare(a, b)
    assert r["discordant"] == 3 and r["different"] is False
    assert "tie" in r["reading"]


def test_the_same_totals_can_be_a_real_difference_or_a_tie():
    """What separates them is the disagreements, which the totals do not show."""
    twenty = {f"c{i}": True for i in range(20)}
    # arm B fails the same 10 the other fails -> nothing to learn
    same = dict(twenty, **{f"c{i}": False for i in range(10)})
    a = dict(twenty, **{f"c{i}": False for i in range(10)})
    assert compare(a, same)["different"] is False
    # arm B fails a DIFFERENT 10 -> twenty disagreements, all informative
    other = dict(twenty, **{f"c{i}": False for i in range(10, 20)})
    assert compare(a, other)["discordant"] == 20


def test_ties_between_the_arms_carry_no_information():
    """Cases both arms pass, or both fail, must not enter the test."""
    a = {f"c{i}": True for i in range(100)}
    b = dict(a)
    b["c0"] = False
    assert compare(a, b)["discordant"] == 1


def test_sign_test_is_exact_and_two_sided():
    assert sign_test(0, 0) == 1.0
    assert sign_test(3, 0) == pytest.approx(0.25)
    assert sign_test(5, 0) == pytest.approx(0.0625)
    assert sign_test(6, 0) <= 0.05


ARMED = sorted(glob.glob("results/*/multitool_results.json"))


def _arms(path):
    d = json.load(open(path))
    return {k: {r["case_id"]: r["passed"] for r in v["records"]}
            for k, v in d["arms"].items()
            if isinstance(v, dict) and v.get("records")}


@pytest.mark.parametrize("path", ARMED, ids=lambda p: p.split("/")[1])
def test_the_recorded_runs_still_say_what_the_plan_says(path):
    """A regression test over history: these numbers must not drift under us.

    It does not assert that any arm won. It asserts the comparisons are computable
    and the pairing is intact — a records list that lost its case_ids, or an arm
    scored on a different draw, would silently turn every paired test into a
    comparison of two unrelated samples.
    """
    arms = _arms(path)
    assert len(arms) >= 2, f"{path} has fewer than two scored arms"
    ids = [set(a) for a in arms.values()]
    assert all(s == ids[0] for s in ids), (
        f"{path}: the arms were not scored on the same cases, so no paired "
        "comparison between them is valid")


def test_p15_reversal_of_p13_is_a_tie_on_both_metrics():
    """The claim this module was written for, pinned so it cannot quietly return."""
    p = "results/P15-multitool-20260910/multitool_results.json"
    arms = _arms(p)
    r = compare(arms["kernel adapter writes the calls"],
                arms["hand-written rule writes the calls"])
    assert (r["a_total"], r["b_total"]) == (10, 7)
    assert r["different"] is False, "if this ever passes, the plan needs rewriting"


def test_p24_rule_beating_the_adapter_survives_the_paired_test():
    """And the one difference that IS real stays real — this is not a blanket doubt."""
    p = "results/P24-constrained-20260912/multitool_results.json"
    arms = _arms(p)
    r = compare(arms["hand-written rule writes the calls"],
                arms["kernel adapter writes the calls"])
    assert r["different"] is True and r["p_value"] <= 0.05
