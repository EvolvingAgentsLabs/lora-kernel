"""The turn protocol, checked without a GPU.

The string handling here decides what each patch is asked to produce, so it is
pinned before a session is bought rather than debugged inside one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.harness.sequential import _expression, sequential  # noqa: E402

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def _pair(labels, exprs, final):
    """A fake domain that names quantities and a fake kernel that computes them."""
    seen = {"domain": 0, "kernel": 0}

    def step(adapter, system, user, prefix, stops):
        i = seen[adapter]
        seen[adapter] += 1
        if adapter == "domain":
            if i < len(labels):
                return f"{i + 1}. {labels[i]}: 999 * 999 = 12345\n"
            return final
        return f" <calc>{exprs[i]}</calc>= 0\n"

    return step, seen


@check
def test_the_two_patches_alternate_and_the_harness_answers():
    step, seen = _pair(["area", "velocity"], ["2 * 3", "6 / 2"],
                       '\n{"answer": 3}')
    out, calls, rejected = sequential(step, "sys", "usr", max_steps=4)
    assert calls == 2 and rejected == 0, (calls, rejected)
    assert "1. area: <calc>2 * 3</calc>= 6" in out, out
    assert "2. velocity: <calc>6 / 2</calc>= 3" in out, out
    assert seen["domain"] == 3 and seen["kernel"] == 2, seen
    assert '{"answer": 3}' in out, "the final answer must reach the transcript"


@check
def test_the_harness_cannot_reconstruct_the_kernels_contribution():
    """The measurement is void if the expression exists before the kernel writes
    it — a channel nobody needs cannot lose anything. The domain turn stops at
    the colon precisely so the harness has nothing to copy."""
    captured = {}

    def step(adapter, system, user, prefix, stops):
        if adapter == "kernel":
            captured["prefix"] = prefix
            return " <calc>2 * 3</calc>= 0\n"
        return "1. area: 999 * 999 = 12345\n"

    sequential(step, "sys", "usr", max_steps=1)
    prefix = captured["prefix"]
    assert prefix.endswith("1. area:"), repr(prefix)
    assert _expression(prefix, tagged=True) is None, \
        "the harness could already evaluate something before the kernel spoke"


@check
def test_the_control_arm_uses_the_experts_own_expression_and_loads_no_kernel():
    used = []

    def step(adapter, system, user, prefix, stops):
        used.append(adapter)
        if prefix.rstrip().endswith(":"):
            return " 2 * 3 = 999\n"          # the expert's own, badly computed
        return "1. area: 999 * 999 = 12345\n"

    out, calls, _ = sequential(step, "sys", "usr", max_steps=1,
                               kernel_executes=False)
    assert "kernel" not in used, used
    assert calls == 1 and "= 6" in out, (calls, out)


@check
def test_an_expression_the_evaluator_rejects_is_counted_and_shown():
    def step(adapter, system, user, prefix, stops):
        if adapter == "kernel":
            return " <calc>__import__('os')</calc>= 0\n"
        return "1. area: 999 * 999 = 12345\n"

    out, calls, rejected = sequential(step, "sys", "usr", max_steps=1)
    assert calls == 1 and rejected == 1, (calls, rejected)
    assert "ERROR" in out, out


if __name__ == "__main__":
    for fn in CHECKS:
        fn()
        print("ok ", fn.__name__)
    print(f"{len(CHECKS)} checks passed")
