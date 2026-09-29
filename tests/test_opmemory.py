"""The short-term operational memory (examples/common/opmemory.py): two scopes, the claim's boundary, declared workflows,
and a two-turn session through the gateway where "move it to dock 5" is resolved by `get`, with no history in the prompt."""
import pytest

from examples.common import tokens
from examples.common.opmemory import MemoryError, OpMemory, Workflow, context_line
from examples.common.permissions import Claim

A1 = Claim(user_id="receiving-riverside", role="receiving", org_id="riverside")
A2 = Claim(user_id="dispatch-riverside", role="dispatch", org_id="riverside")
B1 = Claim(user_id="receiving-harbor", role="receiving", org_id="harbor")


def test_session_keys_belong_to_one_conversation_and_global_keys_to_the_organisation():
    m = OpMemory()
    m.put(A1, "s1", "order", "41")
    m.put(A1, "s1", "global.sprint", "Sprint 14")
    assert m.get(A1, "s1", "order") == "41" and m.get(A2, "x", "global.sprint") == "Sprint 14"
    for claim, session in ((A1, "s2"), (A2, "s1")):                    # another session, another user
        with pytest.raises(MemoryError):
            m.get(claim, session, "order")
    with pytest.raises(MemoryError):                                    # another organisation, whatever the key
        m.get(B1, "s1", "global.sprint")
    assert m.keys(A1, "s1") == ["order", "global.sprint"] and m.keys(B1, "s1") == []
    assert [e["key"] for e in m.log] == ["order", "global.sprint"] and m.log[0]["user"] == A1.user_id


def test_malformed_keys_and_long_values_are_refused():
    m = OpMemory()
    for bad in ("Order", "a b", "../x", "global.", "", "x" * 60):
        with pytest.raises(MemoryError):
            m.put(A1, "s", bad, "v")
    with pytest.raises(MemoryError):
        m.put(A1, "s", "note", "x" * 501)
    assert m.answer(A1, "s", "put", "note=ok") == "stored note" and m.answer(A1, "s", "get", "note") == "ok"
    with pytest.raises(MemoryError):
        m.answer(A1, "s", "put", "no-equals-sign")


def test_a_workflow_moves_only_on_calls_that_ran_and_the_line_shows_names_not_values():
    w = Workflow.load("examples/distributor/workflows/receiving.toml")
    m = OpMemory()
    assert context_line(m, A1, "s", w) == "state: receiving/start · keys: (none)"
    w.advance(m, A1, "s", [{"tool": "dock_assign", "error": "no order 99"}])
    assert w.state(m, A1, "s") == "start"
    w.advance(m, A1, "s", [{"tool": "dock_assign", "result": "assigned order #41 to dock 3"}])
    m.put(A1, "s", "order", "41")
    line = context_line(m, A1, "s", w)
    assert line == "state: receiving/assigned · keys: order" and "41" not in line


def test_two_turns_through_the_gateway_resolve_it_by_key_with_no_history():
    from examples.distributor import generate_turns as gt
    from examples.distributor import users
    from examples.school.gateway import Gateway
    users.register_all()
    seen = []

    def generate(system, user, close, history=None):
        seen.append(user)
        return (lambda prefix: next(replies)), (lambda: {"prompt_tokens": 1, "completion_tokens": 1})
    conn = gt._world(960_001)
    oid = next(r["id"] for r in conn.execute("select id from orders where org_id='riverside'"))
    replies = iter([s.replace("order_id=5", f"order_id={oid}").replace("order=5", f"order={oid}") for s in
                    ["<dock_assign>order_id=5; dock_number=3</dock_assign>", "<put>order=5</put>", "Done.",
                     "<get>order</get>", "<dock_assign>order_id=5; dock_number=5</dock_assign>", "Done: moved."]])
    mem = OpMemory()
    gw = Gateway(conn, generate, org="distributor", memory=mem,
                 workflows={"receiving": Workflow.load("examples/distributor/workflows/receiving.toml")})
    tok = tokens.issue("receiving-riverside", "receiving", "riverside")
    msgs = [{"role": "user", "content": f"Put order {oid} on dock 3."}]
    one = gw.turn(tok, msgs, session="s1")
    msgs += [{"role": "assistant", "content": one["reply"]}, {"role": "user", "content": "Move it to dock 5."}]
    two = gw.turn(tok, msgs, session="s1")
    assert seen[0].startswith("state: receiving/start · keys: (none)")
    assert seen[1].startswith("state: receiving/assigned · keys: order") and "Put order" not in seen[1]
    calls = two["event"]["calls"]
    assert calls[0] == {"tool": "get", "args": {"body": "order"}, "result": str(oid)}
    assert calls[1]["tool"] == "dock_assign" and calls[1]["args"] == {"order_id": str(oid), "dock_number": "5"} and "result" in calls[1]
    assert two["event"]["state"] == "assigned"
