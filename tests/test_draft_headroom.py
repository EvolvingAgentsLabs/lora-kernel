"""P49's gate, and the shape of what it reads.

The gate decides whether three corpora get built at all, so it is code rather than
a reading, and it is tested with the two outcomes the brief pre-registered.
"""

import pytest

from training.email.drafting import generate
from training.harness.draft_headroom import (
    MIN_MARGIN,
    summarise,
    thread_inline,
    verdict,
)


def rec(topic, found, needed, complete, error=False):
    r = {"id": "x", "topic": topic, "found": found, "needed": needed,
         "complete": complete}
    if error:
        r["error"] = "boom"
    return r


def test_the_headline_is_per_draft_not_per_fact():
    """Two facts of three is still a reply somebody has to fix."""
    s = summarise([rec("client", 2, 3, False), rec("client", 3, 3, True)])
    assert s["complete_rate"] == 0.5
    assert s["fact_rate"] == pytest.approx(5 / 6, abs=1e-4)


def test_a_clear_margin_buys_the_design():
    v = verdict({"n": 90, "complete_rate": 0.70}, {"n": 90, "complete_rate": 0.30})
    assert v["bought"] is True and "BOUGHT" in v["reading"]


def test_a_thin_margin_leaves_acceptance_nothing_to_rank():
    v = verdict({"n": 90, "complete_rate": 0.34}, {"n": 90, "complete_rate": 0.30})
    assert v["bought"] is False
    assert "rank nothing" in v["reading"] and "tie" in v["reading"]


def test_the_boundary_is_inclusive_and_pre_registered():
    v = verdict({"n": 9, "complete_rate": 0.50},
                {"n": 9, "complete_rate": 0.50 - MIN_MARGIN})
    assert v["bought"] is True
    assert MIN_MARGIN == 0.10


def test_an_arm_that_produced_nothing_is_unreadable_not_zero():
    assert verdict({"n": 0}, {"n": 90, "complete_rate": 0.3})["readable"] is False


def test_errors_are_counted_rather_than_silently_scoring_zero():
    s = summarise([rec("team", 0, 3, False, error=True), rec("team", 3, 3, True)])
    assert s["errors"] == 1
    # A transport failure still counts as an incomplete draft — it did not arrive —
    # but the count says how much of the arm was transport rather than writing.
    assert s["complete_rate"] == 0.5


def test_by_topic_is_reported_because_a_flat_average_hides_a_temática():
    s = summarise([rec("client", 3, 3, True), rec("client", 3, 3, True),
                   rec("vendor", 0, 3, False), rec("vendor", 0, 3, False)])
    assert s["by_topic"]["client"]["rate"] == 1.0
    assert s["by_topic"]["vendor"]["rate"] == 0.0


def test_the_thread_is_handed_over_inline_and_names_both_sides():
    """The deliberate simplification: neither arm needs a tool to see the thread."""
    inbox = generate(3, 5)
    c = inbox["cases"][0]
    text = thread_inline(inbox, c)
    assert "me:" in text
    assert c["from_name"] + ":" in text
    # And the facts the reply depends on are in there, or the arm is unanswerable.
    for m in c["must_carry"]:
        assert m.lower() in text.lower()
