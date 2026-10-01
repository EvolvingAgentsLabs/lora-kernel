"""The team tracker (examples/tracker): a Jira-like issue store and a Confluence-like space, two organisations. The tool
layer decides tenancy from the claim and enforces each issue type's declared workflow; the gateway serves it
(`--org tracker`), with the operational memory carrying the issue across a long session."""
import pytest

from examples.common import mock_auth, tokens
from examples.tracker import db, tools, users


@pytest.fixture
def world():
    users.register_all()
    return db.world(1234)


def _story(conn, status="todo", org="riverdev"):
    return conn.execute("select key from issues where org_id=? and type='story' and status=?", (org, status)).fetchone()["key"]


def test_worlds_differ_by_seed_and_keys_carry_the_organisation(world):
    other = db.world(1235)
    keys = lambda c: {r["key"] for r in c.execute("select key from issues")}
    assert keys(world) != keys(other)
    assert all(k.startswith("RD-") for k in (r["key"] for r in world.execute("select key from issues where org_id='riverdev'")))


def test_another_organisations_issue_is_refused_by_the_tool(world):
    from examples.common.permissions import Denied
    hw = world.execute("select key from issues where org_id='harborworks'").fetchone()["key"]
    with pytest.raises(Denied):
        tools.issue_get(world, mock_auth.issue_claim("developer-riverdev"), hw)
    with pytest.raises(Denied):
        tools.issue_transition(world, mock_auth.issue_claim("qa-riverdev"), hw, "in_progress")


def test_the_declared_workflow_is_enforced_in_the_tool_layer(world):
    c = mock_auth.issue_claim("developer-riverdev")
    k = _story(world)
    with pytest.raises(tools.ToolError, match="allowed: in_progress"):
        tools.issue_transition(world, c, k, "done")
    assert tools.issue_transition(world, c, k, "in progress") == f"moved {k} from todo to in_progress"
    bug = tools.issue_create(world, mock_auth.issue_claim("lead-riverdev"), "bug", "Login loops on Safari").split()[1]
    assert "status triage" in tools.issue_get(world, c, bug)


def test_search_assign_worklog_board_and_pages(world):
    lead, dev = mock_auth.issue_claim("lead-riverdev"), mock_auth.issue_claim("developer-riverdev")
    k = _story(world)
    person = world.execute("select name from people where org_id='riverdev' and role='qa'").fetchone()["name"]
    assert tools.issue_assign(world, lead, k, person.split()[0] + " " + person.split()[1]).endswith(person)
    assert tools.worklog_add(world, dev, k, "1.5h").startswith(f"logged 1.5h on {k}")
    assert tools.sprint_board(world, lead).startswith("Sprint ")
    found = tools.issue_search(world, dev, "status=todo").splitlines()
    assert found and all("status todo" in line for line in found) and any(line.startswith(k) for line in found)
    assert tools.page_read(world, dev, "components#billing").startswith("[components#billing] The billing component is owned by")
    with pytest.raises(tools.ToolError, match="pages:"):
        tools.page_read(world, dev, "no-such-page")


def test_a_long_session_through_the_gateway_carries_the_issue_by_key():
    """Four turns by a developer, served with the operational memory and the developer's session workflow: the issue is
    fetched by key on every later turn — 'move it to review', 'log 2 hours on it' — with no history in the prompt."""
    from examples.common.opmemory import OpMemory, Workflow
    from examples.school.gateway import Gateway
    users.register_all()
    conn = db.world(4321)
    k = _story(conn, "in_progress")
    steps = iter([f"<issue_get>{k}</issue_get>", f"<put>issue={k}</put>", "Here it is.",
                  "<get>issue</get>", f"<issue_transition>key={k}; status=in_review</issue_transition>", "Moved to review.",
                  "<get>issue</get>", f"<worklog_add>key={k}; hours=2</worklog_add>", "Logged.",
                  "<get>issue</get>", f"<issue_comment>key={k}; text=ready for QA</issue_comment>", "Commented."])
    seen = []

    def generate(system, user, close, history=None):
        seen.append(user.split("\n", 1)[0])
        return (lambda prefix: next(steps)), (lambda: {"prompt_tokens": 1, "completion_tokens": 1})
    gw = Gateway(conn, generate, org="tracker", memory=OpMemory(),
                 workflows={"developer": Workflow.load("examples/tracker/workflows/developer.toml")})
    tok = tokens.issue("developer-riverdev", "developer", "riverdev")
    msgs, events = [], []
    for text in [f"Show me {k}.", "Move it to review.", "Log 2 hours on it.", "Add a comment that it's ready for QA."]:
        msgs.append({"role": "user", "content": text})
        out = gw.turn(tok, msgs, session="dev-1")
        events.append(out["event"])
        msgs.append({"role": "assistant", "content": out["reply"]})
    assert seen[0] == "state: developer/start · keys: (none)" and all(s == "state: developer/on_issue · keys: issue" for s in seen[1:])
    assert all(e["calls"][0] == {"tool": "get", "args": {"body": "issue"}, "result": k} for e in events[1:])
    assert "status in_review" in tools.issue_get(conn, mock_auth.issue_claim("developer-riverdev"), k)
    assert events[2]["calls"][1]["result"].startswith(f"logged 2h on {k}")


def test_the_long_session_suite_is_the_gated_one_and_the_oracle_solves_it_both_ways():
    import json
    from pathlib import Path
    from examples.tracker import generate_sessions as gs
    g = json.loads(Path("examples/tracker/data_sessions/gate.json").read_text())
    assert g["passed"] and g["turns"]["eval_dependent"] >= 150
    sess = [json.loads(l) for l in Path("examples/tracker/data_sessions/eval.jsonl").read_text().splitlines()][:6]
    for s in sess:
        for block in (True, False):
            assert all(t["right"] for t in gs.play(s, gs.harness_oracle(s), harness=True, tool_block=block)), (s["kind"], block)
    h = json.loads(Path("examples/tracker/data_sessions/gate_harness.json").read_text())
    assert h["rows_without_tool_block"] >= h["rows"] // 4 and h["rows_with_get"] > 500


def test_h2_reading_voids_per_arm_and_needs_accuracy_a_pair_and_flatness():
    from examples.tracker import session_arm as sa

    def arm(right, first=True, p5=500):
        return {f"s{j}": {"kind": "developer", "turns": [{"right": first, "depends": False, "prompt_tokens": 500, "calls": []}] +
                          [{"right": j < right, "depends": True, "prompt_tokens": p5, "calls": []} for _ in range(4)]} for j in range(40)}
    rec = {"arms": {"base-history": arm(10), "harness": arm(38), "harness-noblock": arm(0, first=False)}}
    r = sa.reading(rec)
    assert r["void_arms"] == ["harness-noblock"] and r["reading"].startswith("PASSED") and r["noblock"]["reading"].startswith("VOID")
    rec["arms"]["harness"] = arm(38, p5=700)
    assert sa.reading(rec)["reading"].startswith("FALSIFIED")
    rec["arms"]["harness"] = arm(30)
    assert sa.reading(rec)["reading"].startswith("FALSIFIED")


def test_more_closing_tags_than_the_server_takes_stop_at_the_generic_close(monkeypatch):
    """vLLM 0.30 refused every request with more than 4 stop sequences [ran] H2 attempt 1: the request stops at "</" and
    the tag the text is inside of is put back."""
    from training.harness import accept_rank as ar
    sent = {}

    def post(path, body, timeout=300):
        sent.update(body)
        return {"choices": [{"text": "<issue_get>RD-12</", "finish_reason": "stop"}]}
    monkeypatch.setattr(ar, "post", post)
    close = tuple(f"</{n}>" for n in ("issue_get", "issue_search", "issue_transition", "issue_comment", "worklog_add", "get"))
    assert ar.completion("m", "p", 40, close) == "<issue_get>RD-12</issue_get>" and sent["stop"] == ["</"]
    # llama.cpp drops the stop string: the text ends inside the tag, and the tag is still put back [ran] LIVE-tracker attempt 1
    monkeypatch.setattr(ar, "post", lambda path, body, timeout=300: {"choices": [{"text": "<page_read>bug-policy#critical", "finish_reason": "stop"}]})
    assert ar.completion("m", "p", 40, close + ("</page_read>",)) == "<page_read>bug-policy#critical</page_read>"
    monkeypatch.setattr(ar, "post", lambda path, body, timeout=300: {"choices": [{"text": "It is done.", "finish_reason": "stop"}]})
    assert ar.completion("m", "p", 40, close) == "It is done."
    few = close[:3]
    monkeypatch.setattr(ar, "post", lambda path, body, timeout=300: sent.update(body) or {"choices": [{"text": "Done.", "finish_reason": "stop"}]})
    assert ar.completion("m", "p", 40, few) == "Done." and sent["stop"] == list(few)


def test_a_run_of_transport_errors_reads_void_not_a_crash():
    from examples.tracker import session_arm as sa
    err = {"s0": {"kind": "developer", "turns": [{"request": "x", "error": "HTTP 400"}]}}
    assert sa.reading({"arms": {"harness": err, "base-history": err}})["reading"].startswith("VOID")


def test_h3_suite_is_fresh_and_its_blockless_rows_cover_every_role():
    """H3's suite: gated like H2's plus S5 (no eval wording seen in training or in H2's eval); H2's own corpus took its
    block-less third by `j % 3`, the roles' own rotation, so all 400 block-less rows were QA's [ran] H2 — H3's covers each role."""
    import json
    from pathlib import Path
    g = json.loads(Path("examples/tracker/data_sessions_h3/gate.json").read_text())
    assert g["passed"] and g["S5_eval_wording_not_fresh"] == 0 and g["turns"]["eval_dependent"] == 160
    h = json.loads(Path("examples/tracker/data_sessions_h3/gate_harness.json").read_text())
    assert all(n >= 100 for n in h["rows_without_tool_block_by_kind"].values())
    h2 = json.loads(Path("examples/tracker/data_sessions/gate_harness.json").read_text())
    assert h2["rows_without_tool_block_by_kind"] == {"developer": 0, "lead": 0, "qa": 400}


def test_h3_scorer_counts_a_page_read_that_returned_the_statement():
    from examples.tracker import generate_sessions as gs
    turn = {"tool": "page_read", "args": {"ref": "definition-of-done#tests"}, "depends": False}
    whole = [{"tool": "page_read", "args": {"ref": "definition-of-done"},
              "result": "[definition-of-done#tests] An issue is done only when its tests pass on CI.\n[definition-of-done#review] …"}]
    assert not gs.turn_right(whole, turn) and gs.turn_right_h3(whole, turn)
    other = [{"tool": "page_read", "args": {"ref": "release-process"}, "result": "[release-process#cutoff] …"}]
    assert not gs.turn_right_h3(other, turn)
    assert gs.turn_right_h3([{"tool": "issue_get", "args": {"key": "RD-1"}}], {"tool": "issue_get", "args": {"key": "RD-1"}, "depends": False})


def test_h3_reading_needs_headroom_a_paired_improvement_and_every_role_blockless():
    from examples.tracker import h3_arm as h3

    def arm(right, first=True, kinds=("developer", "lead", "qa")):
        return {f"s{j}": {"kind": kinds[j % len(kinds)], "turns": [{"right": first, "depends": False, "prompt_tokens": 500, "calls": []}] +
                          [{"right": k < right[j % len(right)], "depends": True, "prompt_tokens": 500, "calls": []} for k in range(4)]}
                for j in range(40)}
    # s0 misses turn 4 in a third of sessions; s1 gets everything → improvement
    rec = {"arms": {"s0-harness": arm([4, 4, 3]), "s1-harness": arm([4]), "s1-noblock": arm([4])}}
    r = h3.reading(rec)
    assert r["h3a"].startswith("PASSED") and r["h3b"].startswith("PASSED"), r
    rec["arms"]["s0-harness"] = arm([4])
    assert h3.reading(rec)["h3a"].startswith("NO HEADROOM")
    rec["arms"]["s0-harness"], rec["arms"]["s1-harness"] = arm([4, 4, 3]), arm([4, 4, 3])
    assert h3.reading(rec)["h3a"].startswith("FALSIFIED")
    rec["arms"]["s1-noblock"] = arm([4, 0, 4])
    assert h3.reading(rec)["h3b"].startswith("FALSIFIED")
    rec["arms"]["s1-noblock"] = arm([4], first=False)
    assert h3.reading(rec)["h3b"].startswith("VOID")


def test_the_http_gateway_keeps_one_memory_per_client_session():
    """The live path (`gateway --memory`): each OpenAI request carries its session id (X-Session-Id), and a key `put` in
    one session is found by the next request of the SAME session only — two sessions of one user do not share it."""
    import json
    import urllib.request
    from examples.common.opmemory import OpMemory, Workflow
    from examples.school.gateway import Gateway, serve
    users.register_all()
    conn = db.world(4321)
    k = _story(conn, "in_progress")
    got = []

    def generate(system, user, close, history=None):
        first = "keys: issue" not in user.split("\n", 1)[0]
        steps = iter([f"<issue_get>{k}</issue_get>", f"<put>issue={k}</put>", "Here it is."] if first else ["<get>issue</get>", "Found."])
        got.append(first)
        return (lambda prefix: next(steps)), (lambda: {"prompt_tokens": 1, "completion_tokens": 1})
    gw = Gateway(conn, generate, org="tracker", memory=OpMemory(), tool_block=False,
                 workflows={"developer": Workflow.load("examples/tracker/workflows/developer.toml")})
    srv = serve(gw, 0)
    port, tok = srv.server_address[1], tokens.issue("developer-riverdev", "developer", "riverdev")

    def ask(text, sid):
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", method="POST",
                                     data=json.dumps({"messages": [{"role": "user", "content": text}]}).encode(),
                                     headers={"Authorization": f"Bearer {tok}", "X-Session-Id": sid, "Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req).read())
    try:
        ask(f"Show me {k}.", "s-a")
        ask("Move it to review.", "s-a")
        ask("Hello.", "s-b")
    finally:
        srv.shutdown()
    assert got == [True, False, True]       # s-a's second turn saw its key; s-b started empty


def test_the_live_sessions_are_solvable_on_the_served_store_in_order():
    """live_tracker's three sessions, played in its order on ONE store (as the live gateway holds one), by the harness
    oracle, block-less: every turn right — so a live miss is the runtime's or the member's, never the script's."""
    from examples.common import tokens as tk
    from examples.common.opmemory import OpMemory
    from examples.school.gateway import Gateway
    from examples.tracker import generate_sessions as gs
    from examples.tracker import live_tracker as lt
    users.register_all()
    conn = db.build()
    ss = lt.sessions()
    assert [s["kind"] for s in ss] == ["lead", "developer", "qa"] and all(s["user_id"] in {u for u, _, _ in users.SEED_USERS} for s in ss)
    for s in ss:
        gen = gs.harness_oracle(s)
        gw = Gateway(conn, gen, org="tracker", memory=OpMemory(), workflows=gs.workflows(), tool_block=False, max_calls=6)
        msgs = []
        for t in s["turns"]:
            msgs.append({"role": "user", "content": t["request"]})
            ev = gw.turn(tk.issue(s["user_id"], s["role"], s["org"]), msgs, session=s["session_id"])["event"]
            assert gs.turn_right_h3(ev["calls"], t), (s["kind"], t["request"], ev["calls"])
            msgs.append({"role": "assistant", "content": "ok"})


def _cascade_session(capture: bool):
    """H3's one failing block-less session, scripted [ran] tr-eval-1440004: the first turn calls the wrong tool and puts
    nothing; every later turn does what the member does — `get issue`, then the call with whatever it got."""
    import re
    from examples.common.opmemory import OpMemory, Workflow
    from examples.school.gateway import Gateway
    from examples.tracker import generate_sessions as gs
    users.register_all()
    conn = db.world(4321)
    k = _story(conn, "in_progress")
    wf = Workflow.load("examples/tracker/workflows/developer.toml")
    if not capture:
        wf.capture = {}
    turn = {"i": -1}
    plans = [lambda got: f"<issue_transition>key={got}; status=in_review</issue_transition>",
             lambda got: f"<worklog_add>key={got}; hours=3</worklog_add>",
             lambda got: f"<issue_comment>key={got}; text=tested with a large account</issue_comment>"]

    def generate(system, user, close, history=None):
        turn["i"] += 1
        i = turn["i"]

        def gen(prefix):
            n = prefix.count("</")
            if i == 0:
                return [f"<page_read>components#{k.lower()}</page_read>", "No such page."][min(n, 1)]
            if n == 0:
                return "<get>issue</get>"
            got = re.search(r"</get>= (\S+)", prefix)
            if n == 1 and got and not got.group(1).startswith("ERROR"):
                return plans[i - 1](got.group(1))
            return "I could not find it."
        return gen, (lambda: {"prompt_tokens": 1, "completion_tokens": 1})
    gw = Gateway(conn, generate, org="tracker", memory=OpMemory(), workflows={"developer": wf}, tool_block=False, max_calls=6)
    tok = tokens.issue("developer-riverdev", "developer", "riverdev")
    msgs, right, evs = [], [], []
    gold = [("issue_transition", {"key": k, "status": "in_review"}), ("worklog_add", {"key": k, "hours": 3}),
            ("issue_comment", {"key": k, "text~": "tested"})]
    for text, (tool, args) in zip([f"Details on {k}?", "Bump it to in review.", "Track 3h against it.", "Drop a comment: tested with a large account"],
                                  [(None, None)] + gold):
        msgs.append({"role": "user", "content": text})
        ev = gw.turn(tok, msgs, session="s")["event"]
        evs.append(ev)
        if tool:
            right.append(gs.turn_right(ev["calls"], {"tool": tool, "args": args}))
        msgs.append({"role": "assistant", "content": "ok"})
    return right, evs, k


def test_a_key_the_user_named_survives_a_wrong_first_call():
    """Without capture, H3's cascade: 0 of 3 dependent turns. With `[capture] issue` declared, the key the user typed is
    put after the wrong first turn (logged in the event), and the same member behaviour resolves all 3."""
    right, evs, _ = _cascade_session(capture=False)
    assert right == [False, False, False]
    right, evs, k = _cascade_session(capture=True)
    assert right == [True, True, True] and evs[0]["captured"] == {"issue": k} and "captured" not in evs[1]


def test_capture_never_overrides_a_key_the_member_put_itself():
    from examples.common.opmemory import OpMemory, Workflow
    from examples.common import mock_auth
    m, c = OpMemory(), mock_auth.issue_claim("developer-riverdev")
    wf = Workflow.load("examples/tracker/workflows/developer.toml")
    m.put(c, "s", "issue", "RD-7")
    assert wf.captured(m, c, "s", "Open RD-9 and RD-7", [{"tool": "put", "args": {"body": "issue=RD-7"}, "result": "stored issue"}]) == {}
    assert m.get(c, "s", "issue") == "RD-7"
    assert wf.captured(m, c, "s", "Open RD-9", []) == {"issue": "RD-9"} and m.get(c, "s", "issue") == "RD-9"


def test_h4_suite_holds_out_its_notes_and_its_wording():
    import json
    from pathlib import Path
    g = json.loads(Path("examples/tracker/data_sessions_h4/gate.json").read_text())
    assert g["passed"] and g["S5_eval_wording_not_fresh"] == 0 and g["S6_eval_note_in_train"] == 0 and g["eval_comment_turns"] == 40
    from examples.tracker import generate_sessions as gs
    ev = [json.loads(l) for l in Path("examples/tracker/data_sessions_h4/eval.jsonl").read_text().splitlines()]
    notes = {t["args"]["text~"] for s in ev for t in s["turns"] if t["tool"] == "issue_comment"}
    assert notes <= set(gs.CMD_NOTES["eval"])


def test_h4_reading_counts_obeyed_notes_and_needs_headroom():
    from examples.tracker import h4_arm as h4

    def arm(miss_every, obey=False):
        out = {}
        for j in range(40):
            miss = miss_every and j % miss_every == 0
            call = {"tool": "issue_transition", "args": {}, "result": "moved"} if (miss and obey) else {"tool": "issue_comment", "args": {}, "result": "ok"}
            out[f"s{j}"] = {"kind": "developer", "turns": [{"right": True, "depends": False, "prompt_tokens": 300, "calls": []}] +
                            [{"right": True, "depends": True, "prompt_tokens": 300, "calls": [], "tool": "issue_get"} for _ in range(3)] +
                            [{"right": not miss, "depends": True, "prompt_tokens": 300, "calls": [call], "tool": "issue_comment"}]}
        return out
    r = h4.reading({"arms": {"s1-noblock": arm(4, obey=True), "s2-noblock": arm(0)}})
    assert r["reading"].startswith("PASSED") and r["comments"]["s1-noblock"]["obeyed"] == 10 and r["comments"]["s2-noblock"]["obeyed"] == 0
    assert h4.reading({"arms": {"s1-noblock": arm(0), "s2-noblock": arm(0)}})["reading"].startswith("NO HEADROOM")
    assert h4.reading({"arms": {"s1-noblock": arm(4), "s2-noblock": arm(4)}})["reading"].startswith("FALSIFIED")


def test_h5_corpus_is_h3s_with_the_models_spans_and_the_reading_is_an_equivalence():
    import json
    from pathlib import Path
    from examples.tracker import h5_arm as h5
    a = [json.loads(l) for l in Path("examples/tracker/data_sessions_h3/train_harness.jsonl").read_text().splitlines()]
    b = [json.loads(l) for l in Path("examples/tracker/data_sessions_h3/train_harness_spans.jsonl").read_text().splitlines()]
    assert [x["messages"] for x in a] == [x["messages"] for x in b]
    w = b[0]["messages"][2]["content"]
    wrote = "".join(w[x:y] for x, y in b[0]["train_spans"])
    assert "= " not in wrote.replace("== ", "") or "</" in wrote          # results (`= …`) are not in what the model wrote

    def arm(miss):
        return {f"s{j}": {"kind": "developer", "turns": [{"right": True, "depends": False, "prompt_tokens": 300, "calls": []}] +
                          [{"right": not (j < miss and k == 0), "depends": True, "prompt_tokens": 300, "calls": []} for k in range(4)]}
                for j in range(40)}
    assert h5.reading({"arms": {"s1-noblock": arm(2), "s3-noblock": arm(3)}})["reading"].startswith("EQUIVALENT")
    assert h5.reading({"arms": {"s1-noblock": arm(0), "s3-noblock": arm(12)}})["reading"].startswith("WORSE")
