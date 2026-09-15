"""Is a confidence worth reading? Three numbers, and they disagree on purpose.

P41 measured per-case escalation delivering LESS than routing by region, because
the only signal separating a right local answer from a wrong one was agreement with
the frontier — which costs a frontier call. These are the metrics that would let a
cheaper signal be judged.
"""

import random

import pytest

from training.harness.bar import aurc, aurc_floor, brier, calibration, ece


def test_a_perfectly_calibrated_model_has_near_zero_ece():
    rng = random.Random(1)
    probs = [rng.random() for _ in range(4000)]
    correct = [rng.random() < p for p in probs]
    assert ece(probs, correct) < 0.05


def test_calibrated_is_not_the_same_as_useful():
    """Always saying 0.5 on a coin is perfectly calibrated and tells you nothing.
    Brier is what separates being true from being sharp."""
    rng = random.Random(2)
    correct = [rng.random() < 0.5 for _ in range(2000)]
    half = [0.5] * 2000
    assert ece(half, correct) < 0.05           # calibrated
    assert brier(half, correct) == pytest.approx(0.25, abs=0.01)   # and useless


def test_aurc_is_the_number_a_router_reads():
    """A model can be badly calibrated and perfectly rankable, and that routes fine."""
    correct = [i < 600 for i in range(1000)]
    # squashed into [0.80, 0.85] — wildly overconfident, perfectly ordered
    probs = [0.85 if c else 0.80 for c in correct]
    assert ece(probs, correct) > 0.2                       # badly calibrated
    assert aurc(probs, correct) == pytest.approx(aurc_floor(correct), abs=1e-9)


# --- the bug this module's own first test found ---------------------------

def test_ties_do_not_resolve_by_position():
    """`sorted` is stable, so equal confidences would break by index — and the
    first check written here called a constant-confidence model **perfectly
    ordered**, purely because the correct cases came first. Reordering the same
    data moved the answer from 0.094 to 0.766 **[ran]** 2026-09-15."""
    flat = [0.9] * 1000
    first = aurc(flat, [i < 600 for i in range(1000)])
    last = aurc(flat, [i >= 400 for i in range(1000)])
    assert first == pytest.approx(last, abs=1e-9)


def test_a_constant_confidence_orders_nothing_and_says_so():
    flat = [0.9] * 1000
    correct = [i < 600 for i in range(1000)]
    got, floor = aurc(flat, correct), aurc_floor(correct)
    assert got > floor + 0.2, "a flat confidence must not look like a good ranking"


def test_the_floor_is_reported_because_an_aurc_alone_is_unreadable():
    """On an easy suite a useless confidence still scores well."""
    easy = [True] * 95 + [False] * 5
    rng = random.Random(3)
    noise = [rng.random() for _ in easy]
    d = calibration(noise, easy)
    assert d["aurc"] < 0.1                     # looks excellent
    assert d["aurc_gap"] > 0.0                 # and the gap says it is not


def test_empty_bins_do_not_count_as_perfect():
    """A sparse histogram that flattered itself would hide a bad model."""
    probs = [0.95] * 10
    assert ece(probs, [True] * 10) == pytest.approx(0.05, abs=1e-9)


def test_every_metric_survives_an_empty_suite():
    assert ece([], []) == 0.0 and brier([], []) == 0.0 and aurc([], []) == 0.0
