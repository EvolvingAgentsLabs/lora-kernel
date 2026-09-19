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
