"""T1's instrument (`examples/tau2/t1_run.py`), zero GPU: the metrics agree with τ²'s own, the gate reads as
written, the raw results survive the chain's marker grep, and the chain watches the runner's prefix.

    pass^k(task) = C(c, k) / C(n, k), averaged over tasks (τ² agent_metrics.py:113–126)

τ²'s `compute_metrics` on its four shipped airline files gives pass^1..4 = (0.5, 0.41, 0.375, 0.36),
(0.56, 0.456667, 0.42, 0.40), (0.505, 0.393333, 0.32, 0.26), (0.59, 0.483333, 0.42, 0.38) **[ran]** 2026-10-05,
in τ²'s venv; the runner's re-statement must give the same numbers from the same files.
"""
import glob
import json
import pathlib
import re

import pytest

from examples.tau2 import t1_run as T

TAU2 = pathlib.Path.home() / "evolvingagents/tau2-bench"
TAU2_OWN = {"claude-3-7-sonnet": (0.5, 0.41, 0.375, 0.36), "gpt-4.1-2025": (0.56, 0.456667, 0.42, 0.40),
            "gpt-4.1-mini": (0.505, 0.393333, 0.32, 0.26), "o4-mini": (0.59, 0.483333, 0.42, 0.38)}


def sim(task, trial, reward, term="user_stop"):
    return {"task_id": str(task), "trial": trial, "reward": reward, "termination": term, "duration": 10.0,
            "messages": 20, "tool_calls": 3, "tool_errors": 0, "malformed": 0, "agent_turns": 8,
            "agent_prompt_tokens": 1000, "agent_completion_tokens": 100, "user_tokens": 300, "agent_gen_s": 4.0}


def test_pass_hat_k_is_taus_formula():
    assert T.pass_hat_k(4, 4, 4) == 1.0 and T.pass_hat_k(4, 3, 4) == 0.0
    assert T.pass_hat_k(4, 2, 1) == 0.5 and T.pass_hat_k(4, 3, 2) == pytest.approx(3 / 6)
    assert T.pass_hat_k(3, 3, 4) is None


@pytest.mark.parametrize("key", sorted(TAU2_OWN))
def test_the_runner_reproduces_taus_own_metrics_on_the_shipped_files(key):
    files = [f for f in glob.glob(str(TAU2 / "data/tau2/results/final/*airline*.json")) if pathlib.Path(f).name.startswith(key)]
    if not files:
        pytest.skip("τ²'s shipped trajectories are not on this machine")
    sims = [T.sim_record(s) for s in json.load(open(files[0]))["simulations"]]
    m = T.arm_metrics(sims, 4)
    for k, want in enumerate(TAU2_OWN[key], 1):
        assert m[f"pass^{k}"] == pytest.approx(want, abs=1e-4)
    assert m["simulations"] == 200 and m["tasks"] == 50 and m["malformed_calls"] == 0


def _arm(rates, k=4):
    """rates[t] successes out of k for task t."""
    return {"complete": True, "preflight": {"ok": True},
            "sims": [sim(t, j, 1.0 if j < c else 0.0) for t, c in enumerate(rates) for j in range(k)]}


def _with_metrics(arm):
    arm["metrics"] = T.arm_metrics(arm["sims"], 4)
    return arm


def test_the_gate_distils_on_a_clear_gap():
    arms = {"teacher": _with_metrics(_arm([4] * 14 + [0] * 6)), "base": _with_metrics(_arm([4] * 6 + [0] * 14))}
    v = T.verdict(arms, 4, 20, 15.0)
    assert v["decision"] == "DISTIL HERE" and v["gap_pass^1"]["gap"] == pytest.approx(0.4)


def test_the_gate_refuses_a_gap_under_the_threshold_or_inside_the_noise():
    small = {"teacher": _with_metrics(_arm([4] * 12 + [0] * 8)), "base": _with_metrics(_arm([4] * 10 + [0] * 10))}
    assert T.verdict(small, 4, 20, 15.0)["decision"] == "NO NEED TO DISTIL HERE"          # 10 pp
    # 15 pp on the mean, but carried by noise: teacher wins 7 tasks, base wins 4
    noisy = {"teacher": _with_metrics(_arm([4] * 7 + [0] * 4 + [2] * 9)),
             "base": _with_metrics(_arm([0] * 7 + [4] * 4 + [2] * 9))}
    v = T.verdict(noisy, 4, 20, 15.0)
    assert v["gap_pass^1"]["gap"] == pytest.approx(0.15)
    assert v["decision"] == "NO NEED TO DISTIL HERE" and v["gap_pass^1"]["ci95"][0] <= 0


def test_void_and_incomplete_are_per_arm_and_read_first():
    t = _with_metrics(_arm([4] * 20))
    b = _arm([0] * 20)
    b["sims"][0]["termination"] = b["sims"][1]["termination"] = b["sims"][2]["termination"] = \
        b["sims"][3]["termination"] = b["sims"][4]["termination"] = "unexpected_error"
    b = _with_metrics(b)
    assert T.verdict({"teacher": t, "base": b}, 4, 20, 15.0)["decision"] == "VOID"
    short = _with_metrics(_arm([4] * 19))
    assert T.verdict({"teacher": t, "base": short}, 4, 20, 15.0)["decision"] == "INCOMPLETE"
    # a base that fails every task by its own errors is headroom, not a broken run
    weak = _arm([0] * 20)
    for s in weak["sims"]:
        s["termination"] = "too_many_errors"
    assert T.verdict({"teacher": t, "base": _with_metrics(weak)}, 4, 20, 15.0)["decision"] == "DISTIL HERE"


def test_parser_markup_left_in_content_counts_as_malformed():
    s = {"task_id": "1", "trial": 0, "reward_info": {"reward": 0.0}, "termination_reason": "user_stop", "messages": [
        {"role": "assistant", "content": "<|tool_call>call:get_user_details{user_id:<|\"|>u1<|\"|>}<tool_call|>"},
        {"role": "assistant", "content": "Your reservation is confirmed."}]}
    r = T.sim_record(s)
    assert r["malformed"] == 1 and r["tool_calls"] == 0


def test_raw_results_carry_no_string_the_chain_stops_on():
    raw = json.dumps({"simulations": [{"note": "finished", "decision": 1, "stopped_at_gate": 1}]}).encode()
    packed = T.pack(raw)
    for marker in ('"finished"', '"decision"', "stopped_at_gate", '"trained_only"'):
        assert marker not in json.dumps({"tau2_raw": packed})
    assert T.unpack(packed) == raw


def test_the_chain_watches_every_prefix_the_tau2_code_prints():
    """tests/test_chain_scripts.py derives runners from training/ and experiments/ only; examples/tau2 is checked here."""
    peek = pathlib.Path("training/harness/chain_serve.sh").read_text()
    watched = set()
    for group in re.findall(r"\(([\w|]+)\)\\\\\]", peek):
        watched |= set(group.split("|"))
    printed = set()
    for f in pathlib.Path("examples/tau2").glob("*.py"):
        printed |= set(re.findall(r'print\(f?"\[(\w+)\]', f.read_text()))
    assert printed and printed <= watched, printed - watched


def test_the_runner_never_says_stopped_unless_it_stops():
    """The chain's watcher breaks on `STOPPED`: a note about the base arm on a small card must not say it."""
    src = pathlib.Path("examples/tau2/t1_run.py").read_text()
    for line in src.splitlines():
        if "STOPPED" in line and "say(" in line:
            nxt = src[src.index(line):].splitlines()[1:4]
            assert any("return" in l or "save()" in l for l in nxt), line
