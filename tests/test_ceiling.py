"""The ceiling on ranking, which P44 had no way to ask about."""

import pytest

from training.harness.ceiling import best_possible, room


def test_a_suite_where_every_case_looks_alike_cannot_be_ranked():
    # One group: the model sees nothing that separates the cases, so the best it
    # can do is a constant, and a constant orders nothing.
    out = best_possible(["same"] * 10, [True] * 6 + [False] * 4)
    assert out["distinct_groups"] == 1
    assert out["rankable"] is False
    assert out["ceiling_gap"] > 0        # a constant leaves the whole floor unmet


def test_a_perfectly_informative_grouping_reaches_the_floor():
    groups = ["a", "a", "b", "b"]
    truth = [True, True, False, False]
    out = best_possible(groups, truth)
    assert out["accuracy"] == 1.0
    assert out["ceiling_gap"] == 0.0     # nothing left for a better model to take


def test_the_ceiling_uses_each_group_s_own_base_rate():
    # 'a' is 3/4 important, 'b' is 1/4 — a predictor that sees the letter can rank.
    groups = list("aaaabbbb")
    truth = [True, True, True, False, True, False, False, False]
    out = best_possible(groups, truth)
    assert out["distinct_groups"] == 2
    assert out["accuracy"] == 0.75
    assert out["rankable"] is True


def test_beating_the_ceiling_indicts_the_grouping_not_the_model():
    """A model cannot beat the best predictor of what it can see.

    The first draft read this as the model ranking worse than nothing — the sign
    the wrong way round. It means the grouping left out something visible.
    """
    r = room(measured_gap=0.40, ceiling_gap=0.45)
    assert r["room"] < 0
    assert "grouping omits" in r["reading"]


def test_a_gap_at_the_ceiling_leaves_nothing_to_buy():
    r = room(measured_gap=0.128, ceiling_gap=0.124)
    assert 0 <= r["room"] < 0.05
    assert "no room" in r["reading"]


def test_room_names_the_share_that_is_the_suite():
    # The P44 numbers: 0.400 measured against a 0.311 ceiling.
    r = room(0.3997, 0.3108)
    assert r["room"] == pytest.approx(0.0889, abs=1e-3)
    assert r["share_irreducible"] == pytest.approx(0.7776, abs=1e-3)
    assert "claimable" in r["reading"]


def test_mismatched_lengths_are_refused_rather_than_zipped_short():
    # zip() would silently drop the tail, which is how an arithmetic bug already
    # published 0.957 for 0.733 once.
    with pytest.raises(ValueError, match="against"):
        best_possible(["a", "b"], [True])


def test_an_empty_suite_is_an_error_not_a_zero_ceiling():
    with pytest.raises(ValueError, match="nothing"):
        best_possible([], [])
