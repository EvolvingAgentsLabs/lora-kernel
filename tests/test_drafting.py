"""The drafting suite's own invariants, asserted rather than trusted.

There is no mechanical verifier for a draft — that is the point, and why the metric
is speculative acceptance. What CAN be asserted mechanically is that the suite is
answerable from the tools and not from the listing, and the first draft of the
generator failed exactly that: `must_carry` asked for a deadline and an amount that
appeared nowhere a tool could reach, so every arm would have scored zero on two of
three facts and the model would have looked broken because the suite was.
"""

import collections

import pytest

from training.email.drafting import TOPICS, carries, generate, render


def _thread_text(inbox, case):
    return " | ".join(m["preview"] for m in inbox["threads"][case["thread_id"]])


@pytest.mark.parametrize("topic", sorted(TOPICS))
def test_every_required_fact_is_reachable_through_the_thread(topic):
    """A compliant reply has to be POSSIBLE. This is the bug that was caught."""
    inbox = generate(24, 11, topics=(topic,))
    for c in inbox["cases"]:
        text = _thread_text(inbox, c).lower()
        missing = [m for m in c["must_carry"] if m.lower() not in text]
        assert not missing, f"{c['case_id']} needs {missing}, which no tool can reach"


@pytest.mark.parametrize("topic", sorted(TOPICS))
def test_the_listing_leaks_nothing_the_reply_depends_on(topic):
    """P15's fault with a new face: a value in the prompt makes the tool decoration."""
    inbox = generate(24, 12, topics=(topic,))
    for c in inbox["cases"]:
        leaked = [m for m in c["must_carry"] if m.lower() in c["prompt"].lower()]
        assert not leaked, f"{c['case_id']} prints {leaked} in the listing"


def test_the_subject_line_does_not_name_the_tematica():
    """The whole design is the regime where the prompt does NOT carry the answer.

    A subject reading `Invoice 4471` would hand a keyword rule the temática and turn
    this back into the 1.000 routing problem the suite exists to get away from.
    """
    inbox = generate(60, 13)
    for c in inbox["cases"]:
        s = c["subject"].lower()
        for word in ("invoice", "quote", "ticket", "eng-", "inv-", "q-"):
            assert word not in s, f"{c['case_id']} subject {c['subject']!r} tells"


def test_the_temáticas_are_evenly_spread():
    inbox = generate(60, 14)
    counts = collections.Counter(c["topic"] for c in inbox["cases"])
    assert set(counts) == set(TOPICS)
    assert max(counts.values()) - min(counts.values()) <= 1


def test_carries_is_a_floor_and_says_what_is_missing():
    must = ["Q-1234", "March 5", "12,345"]
    full = carries("Confirming Q-1234 for March 5, held at 12,345.", must)
    assert full["complete"] and full["missing"] == []
    # The failure acceptance cannot see: two models agreeing at length on nothing.
    empty = carries("Thanks for your note, I will revert shortly.", must)
    assert not empty["complete"]
    assert empty["missing"] == must


def test_carries_is_case_insensitive_but_not_a_paraphrase_check():
    must = ["INV-500"]
    assert carries("attached inv-500 as requested", must)["complete"]
    # It does not reward a near miss; a floor that accepts one is not a floor.
    assert not carries("attached the invoice as requested", must)["complete"]


def test_render_is_called_rather_than_copied():
    """P38: a corpus must teach the prompt the model will be served.

    The generator stores `prompt` by CALLING `render`, so a change to the served
    shape cannot drift from what a corpus was built against.
    """
    inbox = generate(6, 15)
    for c in inbox["cases"]:
        assert c["prompt"] == render(c)
