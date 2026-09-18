"""Milestone 3 — the live turn's instrument: what it reads from the shapes, and the
pre-registered verdict (openclaw_live.py docstring)."""

import json

from training.harness.openclaw_live import parse_verdict, shapes_of, verdict


def test_the_verdict_is_the_last_thing_the_agent_said():
    assert parse_verdict("thinking… IMPORTANT") is True
    assert parse_verdict("IMPORTANT? no — NOT IMPORTANT") is False
    assert parse_verdict("I cannot tell") is None
    assert parse_verdict("") is None


def test_shapes_count_calls_and_invented_names_from_the_proxy_s_record():
    lines = [json.dumps({"tools": ["thread_history", "sender_stats", "message"], "tools_offered": 54,
                         "reply": "<thread_history>thread_id=thr-001</thread_history>"}),
             json.dumps({"tools": ["thread_history", "sender_stats", "message"], "tools_offered": 54,
                         "reply": "<apply_patch>x</apply_patch>\nNOT IMPORTANT\n<message>...</message>"}),
             "not json"]
    s = shapes_of(lines)
    assert s == {"requests": 2, "tools_offered": 54, "tools_kept": 3, "calls": 2, "invented": 1}


def _rec(i, human=True, truth=True, said=True, route="local", calls=1, invented=0):
    return {"id": f"m{i}", "human": human, "truth": truth, "verdict": said, "correct": said == truth,
            "route": route, "shapes": {"requests": 1, "tools_offered": 3, "tools_kept": 3,
                                       "calls": calls, "invented": invented}}


def test_the_pre_registered_gate_needs_all_three_and_reports_the_bar():
    good = [_rec(i) for i in range(20)] + [_rec(20 + i, human=False, truth=False, said=False, calls=0) for i in range(5)]
    v = verdict(good, 25)
    assert v["passes"] and v["routed_local_all"] and v["human"]["call_share"] == 1.0
    assert v["gate"]["beats_the_bar"] is True                 # 20/20 human against the 0.655 bar
    no_calls = [_rec(i, calls=0) for i in range(20)]
    assert not verdict(no_calls, 20)["agent_uses_the_tools"]
    invented = [_rec(i, invented=1) for i in range(20)]
    assert not verdict(invented, 20)["calls_reach_the_live_path"]
    leaked = [_rec(i, route="out") for i in range(20)]
    assert not verdict(leaked, 20)["routed_local_all"]
    assert verdict(no_calls, 20)["reading"].startswith("NOT LIVE")
