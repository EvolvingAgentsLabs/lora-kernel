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


# --------------------------------------------------------------------------
# The two failures that cost P47's first run: a key written from memory, and a
# summary computed before the records were on disk **[ran]** 2026-09-16.
# --------------------------------------------------------------------------

def test_calibration_returns_the_keys_its_consumer_reads():
    """Written against the real shape, not a remembered one.

    The first draft read `aurc_floor` and recomputed a gap that `calibration()`
    already returns. The KeyError landed after 475 cases had been scored and
    before the file was opened, so the whole run was lost.
    """
    from training.harness.bar import calibration
    c = calibration([0.9, 0.6, 0.3], [True, False, False])
    for key in ("aurc", "aurc_oracle_floor", "aurc_gap", "ece", "brier", "n"):
        assert key in c, f"{key} is missing; a consumer reading it would crash"
    assert "aurc_floor" not in c, "the name the first draft invented is still absent"


def test_the_records_are_on_disk_before_the_summary_math_can_fail(tmp_path,
                                                                 monkeypatch):
    """A crash in the summary must not cost the run that produced it."""
    import json
    import sys

    from training.harness import agent_sim

    monkeypatch.setattr(agent_sim, "triage_one", lambda *a, **k: {
        "verdict": True, "calls": 1, "refused": 0, "turns": 2,
        "confidence": 0.8, "answered_first": True, "asked": [], "text": "IMPORTANT"})
    # Make the calibration block blow up the way the real one did.
    import training.harness.bar as bar
    monkeypatch.setattr(bar, "calibration",
                        lambda *a, **k: (_ for _ in ()).throw(KeyError("aurc_floor")))
    out = tmp_path / "r.json"
    monkeypatch.setattr(sys, "argv", ["p", "--n", "8", "--out", str(out),
                                      "--logprobs", "20"])
    assert agent_sim.main() == 0
    saved = json.loads(out.read_text())
    assert len(saved["records"]) == 8, "the expensive part was lost to a summary bug"
    assert "calibration_error" in saved
