"""The sweep's verdict, which is the only thing in it that decides anything."""

from training.harness.ladder_sweep import FLAT_WITHIN, SUFFICIENCY_GATE, verdict_of


def steps(**kw):
    return {"by_steps": {d: {"n": n, "passed": k, "accuracy": round(k / n, 4)}
                         for d, (n, k) in kw.items()}}


def test_a_flat_curve_falsifies_the_analysis_that_bought_the_run():
    # Fails the one-step rung about as often as the nine-step one.
    arms = {"expert": steps(**{"1": (20, 4), "2": (20, 3), "6": (20, 3), "9": (20, 2)}),
            "base": steps(**{"1": (20, 1), "9": (20, 0)})}
    v = verdict_of(arms)
    assert v["curve_is_flat"] is True
    assert "FALSIFIED" in v["reading"]


def test_a_rising_curve_names_the_depths_where_the_expert_is_sufficient():
    arms = {"expert": steps(**{"1": (20, 20), "2": (20, 19), "3": (20, 14),
                               "6": (20, 2), "9": (20, 0)}),
            "base": steps(**{"1": (20, 3), "2": (20, 1), "3": (20, 0),
                             "6": (20, 0), "9": (20, 0)})}
    v = verdict_of(arms)
    assert v["curve_is_flat"] is False
    assert v["sufficient_at_depths"] == [1, 2]      # 14/20 = 0.70 misses the gate
    assert v["base_already_clears"] == []


def test_a_rung_the_base_already_clears_is_reported_as_having_no_headroom():
    arms = {"expert": steps(**{"1": (20, 20), "9": (20, 1)}),
            "base": steps(**{"1": (20, 19), "9": (20, 0)})}
    v = verdict_of(arms)
    # The expert is sufficient at depth 1 AND the base already was — a number that
    # would otherwise be published as the adapter's doing.
    assert 1 in v["sufficient_at_depths"]
    assert v["base_already_clears"] == [1]


def test_the_gate_is_absolute_and_not_read_off_the_frontier():
    # 0.89 does not clear 0.90 no matter what anything else scored.
    arms = {"expert": steps(**{"1": (100, 89), "9": (100, 1)}), "base": steps()}
    assert verdict_of(arms)["sufficient_at_depths"] == []
    assert SUFFICIENCY_GATE == 0.90


def test_an_empty_expert_arm_is_unreadable_rather_than_zero():
    assert verdict_of({"expert": {}, "base": {}})["readable"] is False


def test_the_unknown_depth_bucket_never_enters_the_arithmetic():
    arms = {"expert": {"by_steps": {"1": {"n": 10, "passed": 10, "accuracy": 1.0},
                                    "9": {"n": 10, "passed": 0, "accuracy": 0.0},
                                    "?": {"n": 90, "passed": 0, "accuracy": 0.0}}},
            "base": steps()}
    v = verdict_of(arms)
    assert v["n_easy"] == 10 and v["n_hard"] == 10
    assert v["expert_easy"] == 1.0
    assert FLAT_WITHIN == 0.15
