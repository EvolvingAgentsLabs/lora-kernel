"""Milestone 7, arm 0b: the fluids suite in corpus mode, and the arm's verdict.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §4.4, §9.2). A member is served the prompt
and the result format its corpus taught, or it is a different model; and a harness that its
own oracle cannot pass through measures the harness. Zero GPU."""

import re

from training.harness import corpus_mode_arm, suites
from training.harness.accept_rank import run_chain
from training.physics import multitool


def _oracle_gen(steps):
    state = {"i": 0}

    def gen(prefix):
        i = state["i"]; state["i"] += 1
        if i < len(steps):
            return ("\n" if i else "") + steps[i]
        last = re.findall(r"</\w+>= (\S+)", prefix)[-1]
        return f'\n\n{{"answer": {last}}}'
    return gen


def test_every_oracle_chain_passes_through_the_corpus_mode_loop():
    s = suites.load("fluids")
    raw = {c["case_id"]: c for c in multitool.generate(s.eval_n, s.eval_seed)}
    passed = 0
    for c in s.cases(s.eval_n, s.eval_seed):
        steps = [f"{i}. {lab}: <{tool}>{body}</{tool}>"
                 for i, (lab, tool, body) in enumerate(raw[c.id]["chain"], 1)]
        r = run_chain(_oracle_gen(steps), c.ctx, max_calls=s.max_calls, suite=s)
        assert r["refused"] == 0 and not r["ran_out"], (c.id, r["text"][-200:])
        passed += bool(c.verify(r["verdict"]))
    assert passed == s.eval_n


def test_the_call_cap_is_above_the_deepest_chain():
    s = suites.load("fluids")
    deepest = max(len(c["chain"]) for c in multitool.generate(s.eval_n, s.eval_seed))
    assert s.max_calls > deepest, "a loop capped below the corpus's depth scores the cap"


def test_the_served_turn_is_what_render_tools_writes():
    from training.harness.openai_proxy import render_tools
    from training.physics.tools import SCHEMA
    s = suites.load("fluids")
    c = s.cases(4, s.eval_seed)[0]
    served = render_tools([{"role": "user", "content": c.user}], SCHEMA)[-1]["content"]
    assert s.user_text(c) == served


def test_the_recorded_run_scores_the_same_under_this_suites_rule():
    import json
    s = suites.load("fluids")
    by = {c.id: c for c in s.cases(s.eval_n, s.eval_seed)}
    old = json.load(open("results/P41-routing-20260915/pool_results.json"))["arms"]["fluids-full"]["records"]
    old = old if isinstance(old, list) else list(old.values())
    assert sum(bool(by[r["id"]].verify(r.get("got"))) for r in old) == sum(bool(r["passed"]) for r in old) == 11


def test_the_verdict_reads_three_ways_and_void():
    v = corpus_mode_arm.verdict
    assert v({"G1": {"applied": False}})["reading"].startswith("VOID")
    assert v({"G1": {"applied": True}, "pairs": [{"state": "improvement", "a_total": 40, "b_total": 11}]})["reading"].startswith("THE PATH WAS PART OF IT")
    assert v({"G1": {"applied": True}, "pairs": [{"state": "tie", "a_total": 12, "b_total": 11}]})["reading"].startswith("THE PATH WAS NOT IT")
    assert "WORSE" in v({"G1": {"applied": True}, "pairs": [{"state": "REGRESSION", "a_total": 3, "b_total": 11}]})["reading"]
