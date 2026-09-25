"""The school demo's system, end to end on the Mac — the token, the approval queue, the gateway over HTTP,
the scripted day — against `fake_vllm` with a scripted model. Zero GPU.

What this proves is the SYSTEM: a request's role and tenant come from a signed token, never the model;
another school's student is refused by the tool layer; a payment and an all-families announcement are
held until a DIRECTOR approves (the CFO who asked cannot, a director of another school cannot); the
approved charge runs with the requester's claim and lands in the ledger; out-of-scope requests follow
the role's egress policy; every request is logged and the dashboard prices the local tokens. Whether the
REAL local model behaves is what the Colab run (`examples.school.demo_run`) measures — not this.
"""
import json
import sys
import types

import pytest

from examples.common import approvals, mock_billing, tokens
from examples.common.permissions import Claim, Denied
from training.harness import fake_vllm as fv


def test_a_token_is_the_identity_and_a_tampered_one_is_refused():
    t = tokens.issue("cfo-north", "cfo", "northgate")
    assert tokens.verify(t) == Claim("cfo-north", "cfo", "northgate")
    head, body, sig = t.split(".")
    forged = tokens._b64(json.dumps({"sub": "cfo-north", "role": "director", "org": "northgate", "exp": 9e9}).encode())
    with pytest.raises(tokens.InvalidToken):
        tokens.verify(f"{head}.{forged}.{sig}")


def test_a_held_write_runs_only_on_a_directors_approval_with_the_requesters_scope():
    q = approvals.Queue()
    cfo, director = Claim("cfo-north", "cfo", "northgate"), Claim("director-north", "director", "northgate")
    msg = q.hold(cfo, "billing_charge", {"membership_id": "1", "amount_cents": "4500"})
    assert msg.startswith("PENDING APPROVAL #1") and "has not been executed" in msg
    ran = []
    with pytest.raises(Denied):
        q.approve(1, cfo, lambda *a: ran.append(a))                                  # the role that asked
    with pytest.raises(Denied):
        q.approve(1, Claim("director-south", "director", "southport"), lambda *a: ran.append(a))   # another school
    assert not ran
    q.approve(1, director, lambda c, tool, args: ran.append((c, tool)) or "done")
    assert ran == [(cfo, "billing_charge")] and q.items[0]["decided_by"] == "director-north"
    with pytest.raises(KeyError):
        q.approve(1, director, lambda *a: None)                                       # once


def scripted(model: str, prompt: str) -> str:
    """A stand-in model: the right tag for each scene's request, a line after a result, OUT OF SCOPE otherwise."""
    turn = prompt.rsplit("<|assistant|>", 1)[-1]
    if "ERROR: permission denied" in turn:
        return "No tengo acceso a ese alumno."
    if "</" in turn and ">=" in turn:
        return "Listo: " + turn.rsplit(">= ", 1)[1].strip().splitlines()[0]     # answered FROM the result
    asked = prompt.rsplit("<|user|>", 1)[-1]
    rules = [("agenda del alumno 3", "<agenda_read>3</agenda_read>"), ("alumno 3", "<agenda_read>3</agenda_read>"),
             ("alumno 1", "<agenda_read>1</agenda_read>"),
             ("Inscribí al alumno 2", "<enrollment_draft>student_id=2; program=after-school-robotics</enrollment_draft>"),
             ("membresía 1", "<billing_charge>membership_id=1; amount_cents=4500</billing_charge>"),
             ("anuncio", "<announcement_post>audience=families; body=El viernes no hay clases</announcement_post>")]
    return next((tag for key, tag in rules if key in asked), "OUT OF SCOPE")


@pytest.fixture
def demo(monkeypatch):
    from examples.school import demo_run
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoTokenizer=fv.FakeTokenizer))
    monkeypatch.setattr(demo_run, "PORT", fv._free_port())
    mock_billing.LEDGER.charges.clear()
    return demo_run


def test_the_scripted_day_runs_through_the_gateway_over_http(demo, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["demo_run", "--out", "demo.json"])
    with fv.patched(scripted):
        demo.main()
    rec = json.loads((tmp_path / "demo.json").read_text())
    assert rec["passed"] == len(demo.SCENES), [s for s in rec["scenes"] if not s["passed"]]
    assert rec["cfo_cannot_approve"] and "charged $45.00" in rec["director_approved"]["result"]
    assert rec["ledger_after"] == [{"org_id": "northgate", "membership_id": 1, "amount_cents": 4500, "id": 1}]
    assert [h["user"] for h in rec["handoffs"]] == ["educador-north"]
    d = rec["dashboard"]
    assert d["turns"] == 7 and d["to_frontier"] == 1 and d["to_a_person"] == 1 and d["held_for_approval"] == 2 and d["denied_calls"] == 1
    assert (tmp_path / "events.jsonl").read_text().count("\n") == len(demo.SCENES)
    assert "## A director's side" in demo.render(rec)


def test_a_role_cannot_be_claimed_by_the_model_id(demo):
    from examples.school import db
    from examples.school.gateway import Gateway
    gw = Gateway(db.build(), generate=lambda *a: (lambda p: "", lambda: {}))
    with pytest.raises(Denied):
        gw.turn(tokens.issue("educador-north", "educador", "northgate"), [{"role": "user", "content": "x"}], "auto:cfo")


def test_the_school_arm_scores_base_and_a_member_end_to_end_against_the_fake(tmp_path, monkeypatch):
    """examples.school.school_arm on the fake: G1, the 70 held-out turns and the demo day for both arms."""
    from pathlib import Path as P
    repo = P(__file__).resolve().parent.parent
    (tmp_path / "examples").symlink_to(repo / "examples")
    d = tmp_path / "adapters" / "school-staff-s0"
    d.mkdir(parents=True)
    (d / "adapter_model.safetensors").write_bytes(b"stand-in")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoTokenizer=fv.FakeTokenizer))
    from examples.school import school_arm
    monkeypatch.setattr(sys, "argv", ["school_arm", "--arms", "base,school-s0", "--out", "s.json"])
    with fv.patched(scripted) as seen:
        school_arm.main()
    rec = json.loads((tmp_path / "s.json").read_text())
    assert rec["G1"]["school-s0"]["applied"] and seen["server"].refused == []
    for arm in ("base", "school-s0"):
        assert len(rec["arms"][arm]["held_out"]) == 70 and not [r for r in rec["arms"][arm]["held_out"].values() if "error" in r]
        assert rec["arms"][arm]["demo"]["n"] == 8
    assert rec["analysis"]["pairs"][0]["pair"] == "school-s0 vs base"
