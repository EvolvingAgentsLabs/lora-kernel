"""The role as the route — results/F2-role-as-route-20260920.

The zero term is a request served by a member it does not belong to (FOUNDATIONS §8.4):
misrouted_to_local = |{x : decide(x) is a member, decide(x) != truth(x)}|. A role tells WHICH member;
it does not tell WHETHER the request is in that member's region — `role_first` assumed it did and
served 120 of 120 foreign tasks; `role_confirmed` never misroutes more than the keys alone."""
import json
from pathlib import Path

import pytest

from training.harness import openai_proxy, role_route, route

TRIAGE = "Message msg-1 in thread thr-1\nFrom: A <a@x.com>\nSubject: hi\nPreview: x\n\n"
req = lambda text: {"messages": [{"role": "user", "content": text}]}


def test_no_role_or_no_policy_or_an_unknown_role_is_todays_route():
    r = req(TRIAGE + "Is this important?")
    assert route.decide(r) == route.decide(r, role="triage") == route.decide(r, role="nobody", policy="role_first")
    assert route.decide(req("Write a haiku."), role="nobody", policy="role_confirmed") == ("out", "no region")


def test_role_confirmed_serves_only_when_the_roles_own_keys_fire():
    assert route.decide(req(TRIAGE + "Is this important?"), role="triage", policy="role_confirmed") == ("local", "email-full")
    assert route.decide(req(TRIAGE + "Draft a reply to this."), role="triage", policy="role_confirmed")[0] == "out"
    # another member's keys never serve under this role
    assert route.decide(req(TRIAGE + "What date did you commit to in this thread?"), role="triage",
                        policy="role_confirmed")[0] == "out"


def test_role_first_serves_a_paraphrase_and_also_a_foreign_task__which_is_why_it_failed():
    assert route.decide(req(TRIAGE + "Does this matter?"), role="triage", policy="role_first") == ("local", "email-full")
    assert route.decide(req(TRIAGE + "Draft a reply to this."), role="triage", policy="role_first") == ("local", "email-full")


def test_a_member_measured_out_leaves_whatever_its_role_says():
    for policy in route.ROLE_POLICIES:
        assert route.decide(req("Find the head loss in the pipe."), role="fluids", policy=policy)[0] == "out"


def test_an_unknown_policy_is_an_error_not_a_default():
    with pytest.raises(ValueError):
        route.decide(req("x"), role="triage", policy="role_only")


def test_the_proxy_reads_the_role_off_the_model_id_and_leaves_plain_auto_alone(monkeypatch):
    monkeypatch.setattr(openai_proxy, "AUTO", "auto"); monkeypatch.setattr(openai_proxy, "AUTO_OUT", "frontier")
    monkeypatch.setattr(openai_proxy, "ROLE_POLICY", "role_confirmed")
    r = {**req(TRIAGE + "What date did you commit to in this thread?"), "model": "auto"}
    assert openai_proxy.resolve_auto(r) == ("local", "desk-commitment") and r["model"] == "desk-commitment"
    r = {**req(TRIAGE + "What date did you commit to in this thread?"), "model": "auto:triage"}
    assert openai_proxy.resolve_auto(r)[0] == "out" and r["model"] == "frontier"
    assert openai_proxy.resolve_auto({**req("x"), "model": "email-full"}) is None
    assert openai_proxy.resolve_auto({**req("x"), "model": "automatic"}) is None


def test_the_recorded_verdict_is_what_the_runner_computes_today():
    rec = json.loads(Path("results/F2-role-as-route-20260920/role_route.json").read_text())
    now = json.loads(json.dumps(role_route.measure()))
    assert now["verdict"] == rec["verdict"] and now["arms"] == rec["arms"] and now["replay"] == rec["replay"]
    v = rec["verdict"]
    assert v["default"] == "role_confirmed" and v["role_first"]["fails"] and not v["role_confirmed"]["fails"]
    assert v["role_first"]["c_silently_served_under_wrong_role"] == {"B": 131}
    assert rec["replay"]["true_role:role_confirmed"] == rec["replay"]["dictionary"]


def test_the_falsifier_can_fire():
    rec = json.loads(Path("results/F2-role-as-route-20260920/role_route.json").read_text())
    bad = json.loads(json.dumps(rec))
    bad["arms"]["wrong_role:role_confirmed"]["A"]["silently_served_by_the_wrong_member"] = 1
    assert role_route.verdict(bad)["role_confirmed"]["fails"]
    bad = json.loads(json.dumps(rec)); bad["replay"]["true_role:role_confirmed"]["delivered"] -= 1
    assert role_route.verdict(bad)["role_confirmed"]["fails"]
