"""The three-tool turn protocol, checked without a GPU."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.harness.multitool_run import run_case  # noqa: E402
from training.physics.multitool import generate  # noqa: E402

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


ROW = generate(4, 20260910)[0]          # a hydrostatic_force case


def _expert(labels, exprs):
    """A fake expert: names quantities, and writes expressions when asked."""
    state = {"i": 0, "j": 0}

    def step(adapter, user, prefix, stops):
        if prefix.rstrip().endswith(":"):          # asked for an expression
            e = exprs[min(state["j"], len(exprs) - 1)]
            state["j"] += 1
            return f" {e} = 0\n"
        i = state["i"]
        state["i"] += 1
        if i >= len(labels):
            return '\n{"answer": 42}'
        return f"{i + 1}. {labels[i]}:"
    return step


@check
def test_the_rule_layer_answers_queries_and_defers_the_rest():
    step = _expert(["Gate width", "Density of the fluid", "Area of the gate"],
                   ["2 * 3"])
    book = {tuple(k): v for k, v in ROW["handbook"]}
    out, queries, rejected, declined = run_case(step, ROW["prompt"], "rule", book)
    assert queries == 2 and rejected == 0, (queries, rejected)
    assert declined == 1, declined
    assert "<convert>" in out and "<lookup>" in out, out
    assert "= 6" in out, "the deferred step was not computed by the harness"


@check
def test_no_tool_layer_means_no_calls_at_all():
    step = _expert(["Gate width", "Density of the fluid"], ["2 * 3", "4 * 5"])
    out, queries, rejected, declined = run_case(step, ROW["prompt"], "none")
    assert queries == 0 and declined == 0, (queries, declined)
    assert "<convert>" not in out and "<lookup>" not in out, out


@check
def test_the_kernel_declines_by_choosing_calc():
    """Emitting <calc> is how the kernel says "this step needs an expression",
    and it must hand the step to the expert exactly as the rule's None does."""
    def step(adapter, user, prefix, stops):
        if adapter == "kernel":
            return " <calc>1+1</calc>"
        if prefix.rstrip().endswith(":"):
            return " 2 * 3 = 0\n"
        return '1. Area of the gate:' if not prefix else '\n{"answer": 42}'

    out, queries, rejected, declined = run_case(step, ROW["prompt"], "kernel")
    assert queries == 0 and declined == 1, (queries, declined)
    assert "<calc>" not in out, "a declined step must not leave a call behind"
    assert "= 6" in out, out


@check
def test_a_lookup_outside_this_problems_handbook_is_refused():
    """The handbook is per case, so a fluid from another problem is not an
    interpolation — it is an error, and the run must see it as one."""
    def step(adapter, user, prefix, stops):
        if adapter == "kernel":
            return " <lookup>fluid=ZZ-99; property=density; T=20</lookup>"
        return '1. Density of the fluid:' if not prefix else '\n{"answer": 42}'

    book = {tuple(k): v for k, v in ROW["handbook"]}
    out, queries, rejected, _ = run_case(step, ROW["prompt"], "kernel", book)
    assert queries == 1 and rejected == 1, (queries, rejected)
    assert "ERROR" in out and "zz-99" in out.lower(), out


@check
def test_a_query_the_tool_rejects_is_counted_and_shown():
    def step(adapter, user, prefix, stops):
        if adapter == "kernel":
            return " <lookup>fluid=mercury; property=density; T=20</lookup>"
        return '1. Density of the fluid:' if not prefix else '\n{"answer": 42}'

    out, queries, rejected, _ = run_case(step, ROW["prompt"], "kernel", {})
    assert queries == 1 and rejected == 1, (queries, rejected)
    assert "ERROR" in out, out


if __name__ == "__main__":
    for fn in CHECKS:
        fn()
        print("ok ", fn.__name__)
    print(f"{len(CHECKS)} checks passed")
