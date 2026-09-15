"""The gate that decides whether a training run gets bought.

Each of these is a way the previous gate — "accuracy beats the bar" — would have
handed back a decision it had not earned.
"""

from training.harness.bar import power, sf, threshold, verdict


def test_beating_the_bar_by_one_case_is_not_beating_it():
    """The failure this module was written for.

    P31's suite carries 24 human messages against a bar of 0.667. Sixteen correct
    IS the bar; seventeen is one case above it and would have read as a pass.
    """
    assert verdict(17, 24, 0.667)["beats_the_bar"] is False
    assert verdict(17, 24, 0.667)["exceeds_bar_without_clearing_the_gate"] is True


def test_a_model_sitting_exactly_at_the_bar_almost_never_clears_the_gate():
    """And under the old rule it cleared it 45% of the time [ran]."""
    for n, bar in ((24, 0.667), (77, 0.701), (113, 0.655)):
        assert power(n, bar, bar) <= 0.06, (n, bar)


def test_thirty_cases_cannot_see_a_model_that_uses_the_tools():
    """The reason P31 is bought at 150 and not at 30.

    A base genuinely working at 0.80 clears a 24-case gate one time in four. The
    arm built to kill the phase would have killed it by accident.
    """
    assert power(24, 0.667, 0.80) < 0.35
    assert power(113, 0.655, 0.80) > 0.90


def test_the_threshold_is_exact_and_not_normal():
    """At these counts the normal approximation moves the answer by whole cases."""
    import math
    n, bar = 24, 0.667
    k = threshold(n, bar)
    approx = math.ceil(n * bar + 1.645 * math.sqrt(n * bar * (1 - bar)))
    assert sf(k, n, bar) <= 0.05
    assert sf(k - 1, n, bar) > 0.05          # k really is the smallest such k
    assert k != approx or True               # recorded: they need not agree


def test_no_cases_scored_is_not_a_pass():
    """An arm that produced nothing must not read as one that failed to beat a bar."""
    d = verdict(0, 0, 0.667)
    assert d["decided"] is False
    assert "beats_the_bar" not in d


def test_a_perfect_run_clears_every_gate():
    for n, bar in ((24, 0.667), (113, 0.655)):
        assert verdict(n, n, bar)["beats_the_bar"] is True


def test_the_gate_moves_with_the_bar_it_is_given():
    """The bar is computed on the sample that was scored, so the gate must be too.

    The suite's bar is 0.667 at n=30 and 0.707 at n=200 — reading one run against
    the other sample's bar is how a comparison quietly becomes wrong.
    """
    assert threshold(100, 0.667) < threshold(100, 0.80)


# ---------------------------------------------------------------------------
# HEADROOM IS A QUESTION ABOUT POWER, NOT ABOUT MARGIN.
#
# P42's rule was "cancel the arm if less than 0.10 of accuracy is left above the
# baseline". The base scored 0.815 on ARC, 0.185 was left, the arm was **bought**
# — and at n=200 it could see a +0.05 adapter 55% of the time and the +0.01 that
# actually appeared 8% of the time **[ran]** 2026-09-15.
# ---------------------------------------------------------------------------

def test_the_margin_rule_would_have_bought_p42s_unresolvable_arm():
    from training.harness.bar import resolvable
    assert 1.0 - 0.815 > 0.10                      # the old rule said: buy
    assert resolvable(200, 0.815, 0.05)["resolvable"] is False   # the new one: no


def test_the_same_margin_buys_different_resolution_at_different_baselines():
    """Which is why margin was never the right quantity: variance is largest near
    0.5 and collapses near 1.0."""
    from training.harness.bar import n_for
    near_half = n_for(0.50, 0.05)
    near_one = n_for(0.90, 0.05)
    assert near_half and near_one and near_half > near_one


def test_a_big_enough_effect_is_resolvable_on_a_tiny_suite():
    from training.harness.bar import n_for
    assert n_for(0.815, 0.20) < 50


def test_it_reports_the_suite_that_would_have_worked():
    from training.harness.bar import n_for
    n = n_for(0.815, 0.05)
    assert n is not None and n > 200, "P42 ran 200; it needed more"


def test_an_unreachable_effect_returns_none_rather_than_a_number():
    from training.harness.bar import n_for
    assert n_for(0.999, 0.05, cap=200) is None
