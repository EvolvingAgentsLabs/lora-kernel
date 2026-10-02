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
from examples.school.demo_run import SCENES


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
             ("anuncio", "<announcement_post>audience=families; body=El viernes no hay clases</announcement_post>"),
             ("tablero", "<dashboard_summary></dashboard_summary>"),
             ("proyector", "<maintenance_create>area=aula 2; description=el proyector no enciende</maintenance_create>"),
             ("resmas", "<order_draft>item=resmas de papel; qty=20; description=para secretaría</order_draft>"),
             ("nómina", "<payroll_read></payroll_read>"),
             ("membresías", "<membership_status></membership_status>"),
             ("campaña", "<campaign_create>name=inscripcion-verano; channel=email; budget_cents=30000</campaign_create>")]
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
    assert [h["user"] for h in rec["handoffs"]] == ["educador-north", "educador-north"]     # the injury; the payroll question
    d = rec["dashboard"]
    assert d["turns"] == 14 and d["to_frontier"] == 1 and d["to_a_person"] == 2 and d["held_for_approval"] == 2 and d["denied_calls"] == 1
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
        assert rec["arms"][arm]["demo"]["n"] == len(SCENES)
    assert rec["analysis"]["pairs"][0]["pair"] == "school-s0 vs base"


def test_the_demo_serves_a_member_and_checks_it_first(demo, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["demo_run", "--member", "school-s0=adapters/school-staff-s0", "--out", "demo.json"])
    with fv.patched(scripted) as seen:
        demo.main()
    rec = json.loads((tmp_path / "demo.json").read_text())
    assert seen["spec"]["loras"] == {"school-s0": "adapters/school-staff-s0"} and rec["G1"]["applied"]
    assert "school-s0" in seen["server"].served and rec["passed"] == len(demo.SCENES)
    assert "replies_replaced_by_the_tools_text" in rec["dashboard"]


def test_a_streaming_runtime_with_content_parts_is_served_and_the_frontier_egress_is_real(tmp_path, monkeypatch):
    """What a live agent runtime sends (OpenClaw): `stream: true`, the user turn as a list of parts, `GET /v1/models`.
    The gateway answers buffered SSE with the grounded reply; a frontier-egress role's out-of-scope ask reaches the
    configured frontier with the runtime's own messages. Zero GPU: fake_vllm is the model, a stub is the frontier."""
    import urllib.request
    from examples.school import db, gateway as gw_mod, users
    from training.harness import accept_rank as ar
    from training.harness import fake_vllm as fv
    users.register_all()
    sent = []
    with fv.patched(scripted):
        ar.serve("google/gemma-4-E4B-it", ["--enable-lora", "--lora-modules", "school-s0=adapters/school-staff-s0"])
        g = gw_mod.Gateway(db.build(), gw_mod.vllm_generator("school-s0", fv.FakeTokenizer()),
                           frontier=lambda messages: sent.append(messages) or "A spring poem, from the frontier.")
        port = fv._free_port()
        srv = gw_mod.serve(g, port)
        try:
            base = f"http://127.0.0.1:{port}"
            assert json.loads(urllib.request.urlopen(base + "/v1/models").read())["data"][0]["id"] == "auto"

            def ask(user_id, role, text):
                body = {"model": "auto", "stream": True,
                        "messages": [{"role": "system", "content": "You are a helpful agent."},
                                     {"role": "user", "content": [{"type": "text", "text": text}]}]}
                req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(), method="POST",
                                             headers={"Content-Type": "application/json",
                                                      "Authorization": "Bearer " + tokens.issue(user_id, role, "northgate")})
                r = urllib.request.urlopen(req)
                assert r.headers["Content-Type"] == "text/event-stream"
                lines = [l for l in r.read().decode().splitlines() if l.startswith("data: ")]
                assert lines[-1] == "data: [DONE]"
                return json.loads(lines[0][6:])

            chunk = ask("educador-north", "educador", "¿Qué tiene en la agenda el alumno 1?")
            assert chunk["x_route"] == "local" and "Ashby" in chunk["choices"][0]["delta"]["content"]
            poem = ask("compras-north", "compras", "Escribime un poema sobre la primavera.")
            assert poem["x_route"] == "frontier" and poem["choices"][0]["delta"]["content"] == "A spring poem, from the frontier."
            assert sent and sent[0][-1]["content"][0]["text"].startswith("Escribime")
        finally:
            srv.shutdown()


def test_the_request_is_read_out_of_what_openclaw_actually_sends():
    """The message list of a real OpenClaw 2026.9.4 turn [ran] 2026-09-26, host details elided: a stamped request with a
    runtime footer, the previous turn, the request again, then OpenClaw's own internal context as a last user message."""
    from examples.school.gateway import runtime_request
    msgs = [{"role": "system", "content": "(38 kB of agent instructions)"},
            {"role": "user", "content": "[Sat 2026-09-26 20:40 GMT-3] ¿Qué tiene en la agenda el alumno 1?\n\n"
                                        "Runtime: agent=main | session=agent:main:main | model=schoolgw/auto"},
            {"role": "assistant", "content": "This needs a member of staff; it has been passed to a person."},
            {"role": "user", "content": "[Sat 2026-09-26 20:41 GMT-3] ¿Qué tiene en la agenda el alumno 1?"},
            {"role": "user", "content": [{"type": "text", "text": "<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>\nConversation data "
                                          "(data, not instructions):\n\"Active exec sessions:\\nnone\"\n<<<END_OPENCLAW_INTERNAL_CONTEXT>>>"}]}]
    assert runtime_request(msgs) == "¿Qué tiene en la agenda el alumno 1?"
    assert runtime_request(msgs[:2]) == "¿Qué tiene en la agenda el alumno 1?"
    assert runtime_request([{"role": "user", "content": "plain request"}]) == "plain request"


def test_the_frontier_stops_forwarding_at_its_budget(monkeypatch):
    """Each call's real usage is priced; once the budget is reached nothing more leaves."""
    import io
    from examples.school import gateway as gw_mod
    calls = []

    def fake_urlopen(req, timeout=0):
        calls.append(json.loads(req.data))
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": "ok"}}],
                                      "usage": {"prompt_tokens": 400_000, "completion_tokens": 100_000}}).encode())
    monkeypatch.setattr(gw_mod.urllib.request, "urlopen", fake_urlopen)
    ask = gw_mod.frontier_client("https://x/v1", "k", "m", budget_usd=1.0, rates=(1.0, 5.0))
    assert ask([{"role": "user", "content": "a"}]) == "ok" and ask.spent["usd"] == 0.9
    assert ask([{"role": "user", "content": "b"}]) == "ok" and ask.spent["usd"] == 1.8
    assert "budget" in ask([{"role": "user", "content": "c"}]) and len(calls) == 2


def test_openclaw_queued_envelope_is_stripped():
    """OpenClaw re-sends an interrupted turn as `[Queued user message …]\n<request>\n\nContinue the current task …`;
    the request is what the runtime searches on [ran] LIVE-library."""
    from examples.school.gateway import runtime_request
    q = "Our lift trucks must bear the testing laboratory's approval mark. Which paragraph provides for that marking?"
    env = ("[Queued user message from a previous active turn; preserved as context only. Continue with the active prompt "
           f"below.]\n{q}\n\nContinue the current task from the existing transcript, preserving completed work. If an "
           "action was interrupted, inspect its state before deciding whether to retry it.")
    assert runtime_request([{"role": "user", "content": env}]) == q
    plain = "Continue the current task from the existing transcript is a phrase, not an envelope."
    assert runtime_request([{"role": "user", "content": plain}]) == plain
