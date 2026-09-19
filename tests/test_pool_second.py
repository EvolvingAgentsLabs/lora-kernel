"""Milestone 5 (synthetic): the second member's door, and the router over three regions."""

from collections import Counter

from training.harness.pool_second import NAME, verdict
from training.harness.route import REGIONS, classify


def test_regions_are_their_questions_and_the_four_prompt_sets_separate():
    """[ran] zero GPU, P64: keyed on the listing's markers the desk routed to triage
    15/60; keyed on the question, 60/60, 60/60, 150/150, 140/140."""
    from training.harness.suites import load
    from training.email.inbox import generate as inbox_gen
    from training.harness.generate_email_full import listing
    from training.physics import ladder, multitool as mod
    sets = {"desk-commitment": [c.user for c in load("desk").cases(60, 424242)]
                               + [c.user for c in load("desk:commitment_deep").cases(60, 424242)],
            "email-full": [listing(m) for m in inbox_gen(150, 717171)["messages"]],
            "fluids-full": [c["prompt"] for c in mod.generate(140, 454545, ladder.full_ladder())]}
    for region, rows in sets.items():
        assert Counter(classify(t) for t in rows) == {region: len(rows)}, region
    assert REGIONS[NAME].serve == "local"


def test_the_pool_declares_the_desk_member_with_its_prompt():
    from training.harness import contract
    from training.harness.desk_sim import SYSTEM
    from training.harness.train_pool import POOL
    rec = contract.validate("adapters/desk-commitment", POOL["adapters/desk-commitment"])
    assert rec["surface"] == ["inbox", "thread_history", "sender_stats", "message"]
    assert rec["system"] == SYSTEM


def _rec(released=True):
    ok = {"applied": True, "differs": 3, "probed": 3, "empty": 0}
    return {"G1": {"email-full": ok, NAME: ok},
            "G2": {"email-full": {"reachable": True}, NAME: {"reachable": True}},
            "G2_auto": {"desk": {"served": NAME if released else "email-full"}, "email": {"served": "email-full"}},
            "pairs": [{"pair": "new vs recorded", "state": "tie"},
                      {"pair": "new vs base", "state": "improvement"}]}


def test_the_release_needs_every_gate_and_the_live_route():
    assert verdict(_rec())["released"]
    v = verdict(_rec(released=False))
    assert not v["released"] and "auto_routes" in v["reading"]
    r = _rec(); r["pairs"][0]["state"] = "REGRESSION"
    assert not verdict(r)["released"]
    r = _rec(); r["pairs"][1]["state"] = "tie"
    assert not verdict(r)["released"]
