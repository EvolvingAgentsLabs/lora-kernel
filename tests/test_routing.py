"""A router that escalates everything scores the frontier and is not a pool.

Each of these is a way this arithmetic could report a number the user would not
experience.
"""

import pytest

from training.harness.routing import by_case, by_region


def _rec(i, passed, chain="1. x: <calc>1+1</calc>= 2\n{\"answer\": 2}"):
    return {"id": f"c{i}", "passed": passed, "chain": chain,
            "unit": "N", "statement": "a statement"}


def test_what_is_delivered_is_what_the_user_gets():
    """Local answers where the router kept them, the frontier's where it did not."""
    local = [_rec(0, False), _rec(1, True)]
    front = [{"id": "c0", "passed": True}, {"id": "c1", "passed": False}]
    r = by_case(local, front, lambda *a: a[0].startswith("1. x") and False)
    # nothing escalated: delivered is the local score, not the frontier's
    assert r["escalated"] == 0 and r["delivered"] == 1


def test_a_router_that_escalates_everything_reports_the_frontier():
    """And the share makes that visible rather than hiding it in one number."""
    local = [_rec(0, False), _rec(1, False)]
    front = [{"id": "c0", "passed": True}, {"id": "c1", "passed": True}]
    r = by_case(local, front, lambda *a: True)
    assert r["delivered"] == 2 and r["escalated_share"] == 1.0


def test_a_record_without_a_chain_is_counted_and_not_silently_dropped():
    """P40's records had no chain; a report that ignored them would look complete."""
    local = [_rec(0, True), {"id": "c1", "passed": True}]   # second has no chain
    r = by_case(local, [], lambda *a: False)
    assert r["records_without_a_chain"] == 1 and r["n"] == 1


def test_a_case_sent_away_that_the_frontier_is_missing_is_not_counted_as_right():
    local = [_rec(0, False)]
    r = by_case(local, [], lambda *a: True)
    assert r["delivered"] == 0 and r["records_without_a_chain"] == 1


def test_an_unmeasured_frontier_yields_no_accuracy_rather_than_a_bound():
    """The earlier version reported `<= 0.871` assuming perfection. That is a bound,
    not a result, and this refuses to print it as one."""
    r = by_region(12, 90, None, None, send_away=True)
    assert r["delivered"] is None and "not measured" in r["why"]


def test_keeping_everything_local_escalates_nothing():
    r = by_region(12, 90, 80, 90, send_away=False)
    assert r == {"delivered": 12, "n": 90, "escalated": 0}


def test_the_two_rules_are_not_the_same_policy():
    """The tripwire never fires in region; the quality gate sends away good work."""
    from training.harness.escalate import has_left_its_region, is_probably_wrong
    bad = "1. x: <calc>2+2</calc>= 9\n{\"answer\": 9}"     # arithmetic disagrees
    assert is_probably_wrong(bad, "N", "") or not has_left_its_region(bad, "N", "")
