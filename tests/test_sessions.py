r"""MT0's instrument: sessions whose dependent turn needs an earlier turn, the gateway's optional history, the argument
match, and the reading written first (history's dependent turns under 80 % → HEADROOM; first turns under 90 % → VOID)."""
import json
from pathlib import Path

from examples.distributor import generate_sessions as gs
from examples.distributor import session_arm as sa
from examples.school.gateway import earlier_turns

SESS = [json.loads(l) for l in (Path("examples/distributor/data_sessions/eval.jsonl")).read_text().splitlines()]


def test_the_suite_is_the_gated_one():
    g = json.loads(Path("examples/distributor/data_sessions/gate.json").read_text())
    assert g["passed"] and g["turns"]["eval_dependent"] == sum(t["depends"] for s in SESS for t in s["turns"]) > 40


def test_history_reaches_the_model_only_when_asked():
    s = next(x for x in SESS if x["kind"] == "receiving")
    seen = []

    def spy(system, user, close, history=None):
        seen.append(history)
        return gs.oracle_generate(s)(system, user, close, history)
    assert all(t["right"] for t in gs.play(s, spy, history=True))
    assert seen[0] is None and [m["role"] for m in seen[1]] == ["user", "assistant"]
    seen.clear()
    gs.play(s, spy, history=False)
    assert seen == [None, None]


def test_earlier_turns_are_read_like_the_last_request():
    msgs = [{"role": "user", "content": "[Mon 2026-09-28 10:00 GMT-3] Put order 7 on dock 2."},
            {"role": "assistant", "content": "Done: assigned order #7 to dock 2."},
            {"role": "user", "content": "Move it to dock 5."}]
    assert earlier_turns(msgs) == [{"role": "user", "content": "Put order 7 on dock 2."},
                                   {"role": "assistant", "content": "Done: assigned order #7 to dock 2."}]


def test_the_argument_match_is_exact_or_contains():
    assert gs.call_matches({"tool": "dock_assign", "args": {"order_id": "7", "dock_number": "5"}}, "dock_assign", {"order_id": 7, "dock_number": 5})
    assert not gs.call_matches({"tool": "dock_assign", "args": {"order_id": "7", "dock_number": "2"}}, "dock_assign", {"order_id": 7, "dock_number": 5})
    assert gs.call_matches({"tool": "claim_create", "args": {"description": "order 7 arrived crushed"}}, "claim_create", {"description~": "7"})
    assert not gs.call_matches({"tool": "order_status", "args": {"order_id": "7"}, "denied": "x"}, "order_status", {"order_id": 7})


def _rec(first, dep, n_first=60, n_dep=54):
    arm = lambda f, d: {"first": f"{f}/{n_first}", "dependent": f"{d}/{n_dep}", "independent": "10/10", "prompt_tokens_by_turn": {1: 300}}
    return {"summary": {"last": arm(first, 2), "history": arm(first, dep)}}


def test_the_reading_bands_written_first():
    assert sa.reading(_rec(58, 30))["reading"].startswith("HEADROOM")
    assert sa.reading(_rec(58, 50))["reading"].startswith("NO ACCURACY HEADROOM")
    assert sa.reading(_rec(50, 50))["reading"].startswith("VOID")


def test_the_harness_oracle_resolves_every_session_by_key_with_and_without_the_tool_block():
    for s in SESS[:12]:
        for block in (True, False):
            cap = []
            res = gs.play(s, gs.harness_oracle(s), harness=True, tool_block=block, capture=cap)
            assert all(t["right"] for t in res), (s["kind"], block)
            assert cap[0]["user"].startswith(f"state: {s['kind']}/start · keys: (none)")
            assert ("The following tools are available" in cap[0]["user"]) == block
            if len(res) > 1 and gs.PUTS.get(s["kind"]):
                assert "Put order" not in cap[1]["user"] and "keys: " in cap[1]["user"] and gs.PUTS[s["kind"]] in cap[1]["user"]


def test_the_harness_corpus_extends_m10s_byte_for_byte_and_teaches_both_verbs():
    d = Path("examples/distributor/data_turns")
    assert (d / "train_harness.jsonl").read_bytes().startswith((d / "train_out.jsonl").read_bytes())
    g = json.loads(Path("examples/distributor/data_sessions/gate_harness.json").read_text())
    assert g["passed"] and g["rows_with_get"] > 200 and g["rows_with_put"] > 200


def test_h1_reading_written_first():
    def arm(right_dep, p3=300, first=True):
        return {f"s{j}": {"kind": "receiving", "turns": [
            {"right": first, "depends": False, "calls": [], "prompt_tokens": 300},
            {"right": j < right_dep, "depends": True, "prompt_tokens": 320 if p3 else 0,
             "calls": [{"tool": "get", "result": "41"}] if j < right_dep else []},
            {"right": True, "depends": True, "prompt_tokens": p3, "calls": [{"tool": "get", "result": "41"}]}]} for j in range(20)}
    rec = {"arms": {"history": arm(18), "harness": arm(16), "harness-noblock": arm(15)}}
    r = sa.h1_reading(rec)
    assert r["lost"] == 2 and r["reading"].startswith("PASSED") and r["noblock"]["reading"] == "PASSED"
    rec["arms"]["harness"] = arm(14)
    assert sa.h1_reading(rec)["reading"].startswith("FALSIFIED")
    rec["arms"]["harness"] = arm(18, p3=400)
    assert sa.h1_reading(rec)["flat"] is False and sa.h1_reading(rec)["reading"].startswith("FALSIFIED")
