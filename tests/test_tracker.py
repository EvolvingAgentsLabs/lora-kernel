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
    few = close[:3]
    monkeypatch.setattr(ar, "post", lambda path, body, timeout=300: sent.update(body) or {"choices": [{"text": "Done.", "finish_reason": "stop"}]})
    assert ar.completion("m", "p", 40, few) == "Done." and sent["stop"] == list(few)


def test_a_run_of_transport_errors_reads_void_not_a_crash():
    from examples.tracker import session_arm as sa
    err = {"s0": {"kind": "developer", "turns": [{"request": "x", "error": "HTTP 400"}]}}
    assert sa.reading({"arms": {"harness": err, "base-history": err}})["reading"].startswith("VOID")
