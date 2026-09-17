"""Phase 5's first buy: the verdict logic of the --prune attribution arm, and the
client's resolution of a runtime's namespaced tool names.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §9.2). Two arms on the same cases,
compared on the discordant ones by p = min(1, 2·Pr[Bin(n_d, ½) ≥ max(u, n_d−u)]);
pruning pays when the on-arm wins resolvably, hurts when it loses, and anything else
is a tie — never two totals.
"""

from training.harness.agent_sim import inbox_tool
from training.harness.prune_attribution import compare


def arm(correct, calls, human_accuracy):
    return {"records": [{"id": f"m{i}", "correct": c, "verdict": True} for i, c in enumerate(correct)],
            "calls": calls, "human_accuracy": human_accuracy}


def test_pruning_pays_when_the_on_arm_wins_resolvably():
    off = arm([False] * 60 + [True] * 40, calls=0, human_accuracy=0.345)
    on = arm([True] * 70 + [False] * 30, calls=900, human_accuracy=0.74)
    v = compare(off, on)
    assert v["state"] == "PRUNING PAYS" and v["calls_off"] == 0 and v["calls_on"] == 900


def test_a_tie_is_a_tie_not_a_win():
    off = arm([True] * 50 + [False] * 50, 100, 0.5)
    on = arm([True] * 52 + [False] * 48, 110, 0.52)
    assert compare(off, on)["state"] == "a tie"


def test_the_runtime_name_resolves_to_the_inbox_tool_on_its_last_segment():
    for name in ("lora-inbox__thread_history", "mcp__x__thread_history", "a.b.thread_history"):
        assert inbox_tool(name) == "thread_history"
    assert inbox_tool("message") == "message"
