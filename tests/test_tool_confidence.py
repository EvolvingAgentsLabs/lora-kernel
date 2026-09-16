"""P47's gate, which decides whether a typed adapter is trained at all."""

from training.harness.tool_confidence import BUYS, CANCELS, arm_verdict


def test_a_large_gap_buys_the_arm():
    assert "BOUGHT" in arm_verdict(0.22, 1.0)


def test_a_small_gap_cancels_it_because_the_expert_already_ranks():
    assert "CANCELLED" in arm_verdict(0.01, 1.0)


def test_the_middle_is_temperature_scaling_and_not_a_model():
    """The row that stops a bad ECE being spent on training."""
    v = arm_verdict((BUYS + CANCELS) / 2, 1.0)
    assert "temperature scaling" in v and "NOT a typed head" in v


def test_the_boundaries_are_not_accidentally_inclusive():
    # Exactly at a threshold is the middle, not the decision either side of it.
    assert "temperature" in arm_verdict(BUYS, 1.0)
    assert "temperature" in arm_verdict(CANCELS, 1.0)


def test_a_low_read_rate_voids_the_run_before_any_gap_is_read():
    """A model that preambles puts a word where the verdict should be.

    Averaging those in would measure phrasing, so the read rate is checked FIRST —
    a void run must not be able to come back with a verdict attached.
    """
    v = arm_verdict(0.40, 0.5)
    assert v.startswith("VOID")
    assert "BOUGHT" not in v


def test_no_confidence_at_all_is_void_rather_than_a_zero_gap():
    assert arm_verdict(None, 1.0).startswith("VOID")
