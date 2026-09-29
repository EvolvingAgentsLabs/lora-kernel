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
