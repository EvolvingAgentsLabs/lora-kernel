"""Milestone 2 — routing per request. The client names no model; the proxy decides
from the text, and the decision costs nothing on P41's traffic (route.py docstring)."""

import json
from pathlib import Path

from training.harness import openai_proxy as px
from training.harness.route import REGIONS, classify, decide, replay, text_of

P41 = Path("results/P41-routing-20260915")


def _req(text, system=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": text}]
    return {"model": "auto", "messages": msgs}


def test_an_email_listing_is_served_locally_and_a_physics_statement_leaves():
    assert decide(_req("From: Ana <a@x.com>\nSubject: Re: the numbers\nPreview: hi\n\nIs this important?")) == ("local", "email-full")
    d = decide(_req("Water is pumped through a 120 m bore of roughness 0.05 mm; report the head loss."))
    assert d[0] == "out" and "fluids-full" in d[1]
    assert decide(_req("Write me a poem about the sea.")) == ("out", "no region")


def test_the_subject_is_the_system_prompt_and_the_last_user_turn_only():
    req = {"messages": [{"role": "system", "content": "triage"},
                        {"role": "user", "content": "first"},
                        {"role": "assistant", "content": "manometer venturi throat"},
                        {"role": "tool", "content": "gate plate thrust"},
                        {"role": "user", "content": "last"}]}
    assert text_of(req) == "triage\nlast"
    assert classify("") is None


def test_the_coarse_route_still_needs_no_model():
    """The router baseline's rows, through the decision this proxy ships."""
    from training.email.inbox import generate as inbox_gen
    from training.physics import ladder
    from training.physics import multitool as mod
    rows = [("fluids-full", c["prompt"]) for c in mod.generate(140, 454545, ladder.full_ladder())]
    rows += [("email-full", f"From: {m['from_name']}\nSubject: {m['subject']}\nPreview: {m['preview']}\n\nIs this important?")
             for m in inbox_gen(60, 99)["messages"]]
    assert all(classify(t) == f for f, t in rows), "the dictionary lost the coarse route"


def test_replay_on_p41_ties_by_region_with_no_misroute():
    r = replay(json.loads((P41 / "pool_results.json").read_text()),
               json.loads((P41 / "frontier_fluids.json").read_text()))
    assert r["n"] == 240 and r["email"] == 150 and r["fluids"] == 90
    assert r["by_request"]["misrouted"] == 0
    assert r["ties_by_region"], r
    assert r["by_region"]["accuracy"] == 0.775          # P41 [ran], the number this must not lose


def test_the_alias_is_rewritten_in_place_and_only_the_alias(monkeypatch):
    monkeypatch.setattr(px, "AUTO", "auto"); monkeypatch.setattr(px, "AUTO_OUT", "gpt-frontier")
    req = _req("From: Bo <b@y.com>\nSubject: contract draft\nPreview: hello\n\nIs this important?")
    assert px.resolve_auto(req) == ("local", "email-full") and req["model"] == "email-full"
    req = _req("A flat gate submerged in a tank: the hydrostatic thrust on the plate?")
    assert px.resolve_auto(req)[0] == "out" and req["model"] == "gpt-frontier"
    named = {"model": "email-full", "messages": []}
    assert px.resolve_auto(named) is None and named["model"] == "email-full"
    monkeypatch.setattr(px, "AUTO", None)
    assert px.resolve_auto(_req("anything")) is None


def test_every_region_declares_where_it_is_served():
    assert {r.serve for r in REGIONS.values()} <= {"local", "out"}
    assert REGIONS["fluids-full"].serve == "out"       # P40: 12/90, 78 physics errors [ran]


def test_an_out_decision_with_no_fallback_is_refused_not_served(monkeypatch):
    """A request routed out must never be quietly served by a member outside its
    region; without --fallback the proxy says so (503) and the log names shapes only."""
    monkeypatch.setattr(px, "AUTO", "auto"); monkeypatch.setattr(px, "FALLBACK", None)
    sent = {}
    class H:
        def _authorised(self): return True
        def _send(self, code, body): sent.update(code=code, body=body)
    # the branch under test, isolated from the socket
    req = _req("A flat gate submerged in a tank: the hydrostatic thrust on the plate?")
    auto = px.resolve_auto(req)
    assert auto[0] == "out"
    H()._send(503, {"error": {"message": f"routed out ({auto[1]}) and no --fallback is configured"}})
    assert sent["code"] == 503 and "fallback" in sent["body"]["error"]["message"]
