"""The τ² shim (`examples/tau2/shim.py`) — G-shim-1's identities and G-shim-3's leak check, zero model.

G-shim-1 (no loss, both ways): for a tool call c, parse(serialize(c)) = c with every value's JSON type; for a
conversation m, unfold(fold(m)) = events(m). The full replay over τ²'s 800 shipped airline conversations is
`examples/tau2/check_shim.py` (5,829/5,829 calls, 800/800 folds **[ran]**, `results/TAU2-T0-recon-20261005/
g_shim_1.json`); here it runs over the six requests captured from τ²'s own `LLMAgent` (fixtures), and over the
shipped files when they are on this machine.

G-shim-3 (no leak): what the shim forwards is built from the request's `messages` and `tools` alone, and the
request τ² sends carries nothing of the task's grading: no gold action list, no `nl_assertions`, no scenario
instructions — a gold value reaches the shim only if the conversation itself said it.
"""
import ast
import json
import pathlib

import pytest

from examples.tau2 import shim as S

FIX = pathlib.Path("examples/tau2/fixtures")
REQUESTS = json.loads((FIX / "tau2_requests.json").read_text())
GOLD = json.loads((FIX / "tau2_gold.json").read_text())
TOOLS = json.loads((FIX / "airline_tools.json").read_text())
IDX = S.tool_index(TOOLS)
TAU2 = pathlib.Path.home() / "evolvingagents/tau2-bench"


def canon(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False)


def scripted(*texts):
    q = list(texts)
    seen = []

    def gen(model, prompt, max_tokens, close, temperature=0.0, seed=None):
        seen.append({"model": model, "prompt": prompt, "max_tokens": max_tokens, "close": close})
        return q.pop(0), {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10, "finish_reason": "stop"}
    return gen, seen


def concat(chat):
    """A stand-in chat template: every message, in order, then an open assistant turn."""
    return "".join(f"<{m['role']}>{m['content']}</{m['role']}>" for m in chat) + "<assistant>"


# ------------------------------------------------------------------------------------------- G-shim-1
@pytest.mark.parametrize("name,args,kind", [
    ("send_certificate", {"user_id": "mia_li_3668", "amount": 50}, "json"),
    ("get_user_details", {"user_id": "mia_li_3668"}, "positional"),
    ("transfer_to_human_agents", {"summary": "Wants a refund, policy says no; transferred = yes"}, "positional"),
    ("search_direct_flight", {"origin": "JFK", "destination": "SFO", "date": "2024-05-16"}, "kv"),
    ("list_all_airports", {}, "empty"),
    ("book_reservation", {"user_id": "u", "origin": "JFK", "destination": "SFO", "flight_type": "one_way",
                          "cabin": "economy", "flights": [{"flight_number": "HAT001", "date": "2024-05-16"}],
                          "passengers": [{"first_name": "A", "last_name": "B", "dob": "1990-01-01"}],
                          "payment_methods": [{"payment_id": "gift_card_1", "amount": 120}],
                          "total_baggages": 1, "nonfree_baggages": 0, "insurance": "no"}, "json"),
    ("calculate", {"expression": "<script>"}, "json"),
])
def test_a_call_comes_back_identical_with_its_types(name, args, kind):
    tag, k = S.call_to_tag(name, args, IDX[name])
    assert k == kind
    rep = S.parse_reply(tag, TOOLS)
    assert rep["call"] == (name, args) and canon(rep["call"][1]) == canon(args)
    assert S.call_to_tag(name, rep["call"][1], IDX[name])[0] == tag


def test_k_v_written_by_a_member_is_typed_by_the_schema():
    """τ² does not coerce (toolkit.py:138–142): `amount=50` must leave as the integer the DB hash expects."""
    rep = S.parse_reply("<send_certificate>user_id=u1; amount=50</send_certificate>", TOOLS)
    assert rep["call"] == ("send_certificate", {"user_id": "u1", "amount": 50})
    assert isinstance(rep["call"][1]["amount"], int)
    rep = S.parse_reply('<send_certificate>{"user_id": "u1", "amount": "50"}</send_certificate>', TOOLS)
    assert rep["call"][1]["amount"] == 50 and isinstance(rep["call"][1]["amount"], int)
    rep = S.parse_reply('<update_reservation_flights>{"reservation_id": "R", "cabin": "economy", "payment_id": "p",'
                        ' "flights": "[{\\"flight_number\\": \\"HAT1\\", \\"date\\": \\"2024-05-01\\"}]"}'
                        '</update_reservation_flights>', TOOLS)
    assert rep["call"][1]["flights"] == [{"flight_number": "HAT1", "date": "2024-05-01"}]


def test_coercion_leaves_a_string_where_a_string_is_declared():
    rep = S.parse_reply("<get_reservation_details>12345</get_reservation_details>", TOOLS)
    assert rep["call"][1] == {"reservation_id": "12345"}


def test_the_block_placeholder_is_not_a_call_but_an_empty_body_is():
    assert S.parse_reply("<get_user_details>...</get_user_details>", TOOLS)["malformed"] == 1
    assert S.parse_reply("<list_all_airports></list_all_airports>", TOOLS)["call"] == ("list_all_airports", {})


def test_a_tag_nobody_offered_is_text_and_counted():
    rep = S.parse_reply("Let me see. <refund_everything>all</refund_everything>", TOOLS)
    assert rep["call"] is None and rep["unknown"] == 1 and "refund_everything" in rep["content"]


def test_one_call_per_turn_and_text_after_the_tag_is_cut():
    rep = S.parse_reply('One moment. <get_user_details>u1</get_user_details>= {"invented": 1}'
                        "<get_user_details>u2</get_user_details>", TOOLS)
    assert rep["call"] == ("get_user_details", {"user_id": "u1"}) and rep["content"] == "One moment."


@pytest.mark.parametrize("i", range(len(REQUESTS)))
def test_the_captured_conversation_folds_and_unfolds_without_loss(i):
    msgs = REQUESTS[i]["body"]["messages"]
    chat, prefix, _ = S.fold(msgs, TOOLS)
    assert canon(S.unfold(chat, prefix, TOOLS)) == canon(S.events_of(msgs))
    assert (REQUESTS[i]["cut"] == "after_last_tool") == bool(prefix)   # an open turn is continued, not re-opened


@pytest.mark.parametrize("i", range(len(REQUESTS)))
def test_every_call_in_the_captured_conversations_round_trips(i):
    for m in REQUESTS[i]["body"]["messages"]:
        for tc in m.get("tool_calls") or []:
            name, args = tc["function"]["name"], json.loads(tc["function"]["arguments"])
            rep = S.parse_reply(S.call_to_tag(name, args, IDX[name])[0], TOOLS)
            assert canon(rep["call"][1]) == canon(args) and rep["call"][0] == name


def test_a_result_lands_on_the_line_after_its_tag():
    msgs = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "hi, I am u1"},
            {"role": "assistant", "tool_calls": [{"id": "a", "type": "function", "function": {
                "name": "get_user_details", "arguments": '{"user_id": "u1"}'}}]},
            {"role": "tool", "tool_call_id": "a", "content": '{"user_id": "u1"}'}]
    chat, prefix, _ = S.fold(msgs, TOOLS)
    assert prefix == '<get_user_details>u1</get_user_details>= {"user_id": "u1"}\n'
    assert chat[0] == {"role": "system", "content": "SYS"}


def test_the_full_shipped_replay_when_the_trajectories_are_here():
    """G-shim-1 itself, over every shipped airline conversation; skipped where τ² is not installed (CI)."""
    from examples.tau2 import check_shim as C
    import glob
    files = sorted(glob.glob(str(TAU2 / "data/tau2/results/final/*airline*.json")))
    if not files:
        pytest.skip("τ²'s shipped trajectories are not on this machine")
    sims = []
    for f in files:
        sims += json.load(open(f))["simulations"]
    system = next(m["content"] for m in REQUESTS[0]["body"]["messages"] if m["role"] == "system")
    calls = C.check_calls(sims, TOOLS)
    assert calls["lost"] == 0 and calls["calls"] > 5000
    assert C.check_fold(sims, TOOLS, system)["passed"]
    assert C.control_repo_serializer(sims)["lost"] > 0, "the control must fail, or the check measures nothing"


# ------------------------------------------------------------------------------------------- the shim's own rules
def test_tau2_system_prompt_is_kept_and_a_member_prompt_goes_in_front():
    body = REQUESTS[0]["body"]
    system = next(m["content"] for m in body["messages"] if m["role"] == "system")
    chat, _, _ = S.fold(body["messages"], body["tools"], member_prompt="MEMBER")
    assert chat[0]["content"] == "MEMBER\n\n" + system
    chat, _, _ = S.fold(body["messages"], body["tools"])
    assert chat[0]["content"] == system and "<policy>" in system


def test_no_round_trip_cap_and_max_tokens_at_least_512():
    gen, seen = scripted("<get_user_details>u1</get_user_details>")
    sh = S.Shim("member", concat, generate=gen)
    msgs = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "hi"}]
    for j in range(40):                                  # forty round trips already in the history
        msgs += [{"role": "assistant", "tool_calls": [{"id": f"c{j}", "type": "function", "function": {
            "name": "get_user_details", "arguments": '{"user_id": "u1"}'}}]},
                 {"role": "tool", "tool_call_id": f"c{j}", "content": "{}"}]
    out = sh.handle({"model": "member", "messages": msgs, "tools": TOOLS, "max_tokens": 64})
    assert out["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "get_user_details"
    assert seen[0]["max_tokens"] >= 512
    with pytest.raises(ValueError):
        S.Shim("member", concat, max_tokens=256)


def test_call_ids_are_unique_within_a_conversation():
    gen, _ = scripted(*["<get_user_details>u1</get_user_details>"] * 5)
    sh = S.Shim("member", concat, generate=gen)
    msgs, ids = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "hi"}], []
    for _ in range(5):
        tc = sh.handle({"model": "m", "messages": list(msgs), "tools": TOOLS})["choices"][0]["message"]["tool_calls"][0]
        ids.append(tc["id"])
        msgs += [{"role": "assistant", "tool_calls": [tc]}, {"role": "tool", "tool_call_id": tc["id"], "content": "{}"}]
    assert len(set(ids)) == 5


def test_the_stop_is_every_offered_closing_tag():
    gen, seen = scripted("Hello.")
    S.Shim("member", concat, generate=gen).handle(REQUESTS[0]["body"])
    assert set(seen[0]["close"]) == {f"</{n}>" for n in IDX}


# ------------------------------------------------------------------------------------------- G-shim-3
def _gold_strings(g: dict) -> tuple[list[str], list[str]]:
    """(never: strings that must not reach the shim at all, provenance: gold values allowed only via the chat)."""
    us = g["user_scenario"]["instructions"]
    never = [s for s in g["evaluation_criteria"].get("nl_assertions") or []]
    if isinstance(us, dict):
        never += [v for k, v in us.items() if isinstance(v, str) and k != "domain"]
    else:
        never.append(us)
    never.append(canon([{"name": a["name"], "arguments": a["arguments"]}
                        for a in g["evaluation_criteria"].get("actions") or []]))
    prov = list(g["evaluation_criteria"].get("communicate_info") or [])
    for a in g["evaluation_criteria"].get("actions") or []:
        prov += [v for v in a["arguments"].values() if isinstance(v, str) and len(v) >= 4]
    return [s for s in never if s and len(s) >= 20], prov


def _leaks(req: dict, prompt: str, gold: dict) -> list[str]:
    never, prov = _gold_strings(gold)
    wire = json.dumps(req, ensure_ascii=False)
    chat_text = "\n".join(str(m.get("content") or "") + json.dumps(m.get("tool_calls") or [])
                          for m in req["messages"] if m["role"] != "system")
    out = [f"never:{s[:40]}" for s in never if s in wire or s in prompt]
    out += [f"provenance:{s}" for s in prov if (s in prompt or s in wire) and s not in chat_text
            and s not in json.dumps(req.get("tools"))]
    return out


def test_the_tau2_request_carries_messages_and_tools_only():
    for r in REQUESTS:
        body = r["body"]
        assert set(body) == {"model", "messages", "tools", "tool_choice", "temperature"}
        assert {m["role"] for m in body["messages"]} <= {"system", "user", "assistant", "tool"}
        system = [m for m in body["messages"] if m["role"] == "system"]
        assert len(system) == 1 and system[0]["content"].startswith("<instructions>")
        assert "<resolution_steps>" not in system[0]["content"]    # the GT agent's channel is not this one
        assert body["tools"] == TOOLS


@pytest.mark.parametrize("i", range(len(REQUESTS)))
def test_no_grading_criteria_reach_the_shim(i):
    r = REQUESTS[i]
    gen, seen = scripted("How can I help?")
    sh = S.Shim("member", concat, generate=gen)
    sh.handle(json.loads(json.dumps(r["body"])))
    assert _leaks(r["body"], seen[0]["prompt"], GOLD[r["task_id"]]) == []


def test_the_leak_detector_fires_on_a_planted_leak():
    """A guard nobody has seen fail: plant one nl_assertion in a user turn, and one gold value nobody said."""
    r = json.loads(json.dumps(REQUESTS[0]))
    g = GOLD[r["task_id"]]
    planted = (g["evaluation_criteria"].get("nl_assertions") or [g["user_scenario"]["instructions"]["reason_for_call"]])[0]
    r["body"]["messages"][-1]["content"] += " " + planted
    gen, seen = scripted("ok")
    S.Shim("member", concat, generate=gen).handle(r["body"])
    assert any(x.startswith("never:") for x in _leaks(r["body"], seen[0]["prompt"], g))
    _, prov = _gold_strings(g)
    unsaid = next(s for s in prov if s not in json.dumps(r["body"], ensure_ascii=False))
    assert _leaks(r["body"], seen[0]["prompt"] + unsaid, g)


def test_the_forwarded_prompt_is_a_function_of_messages_and_tools_alone():
    body = REQUESTS[1]["body"]
    sh = S.Shim("member", concat)
    bare = {"messages": body["messages"], "tools": body["tools"]}
    noisy = {**body, "metadata": {"task_id": "x", "evaluation_criteria": "GOLD"}, "user": "grader"}
    assert sh.prompt_for(noisy)[0] == sh.prompt_for(bare)[0]
    assert "GOLD" not in sh.prompt_for(noisy)[0]


def test_the_shim_source_cannot_reach_a_task():
    """Read the code, not prose (CLAUDE.md §3): no tau2 import, no reference to a task's grading fields."""
    tree = ast.parse(pathlib.Path("examples/tau2/shim.py").read_text())
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not any(m.split(".")[0] == "tau2" for m in mods), mods
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names |= {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    for field in ("evaluation_criteria", "nl_assertions", "communicate_info", "user_scenario", "reward_basis",
                  "resolution_steps", "env_assertions"):
        assert field not in names, field
