"""The repair walk, checked on chains whose right answer is known by hand."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.physics.repair import repair  # noqa: E402

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@check
def test_a_correct_chain_is_left_where_it_is():
    text = ("1. Flow area: 1.96 * 1.27 = 2.4892\n"
            "2. Wetted perimeter: 1.96 + 2*1.27 = 4.5\n"
            '{"answer": 4.5}')
    got, ok, bad = repair(text)
    assert (round(got, 4), ok, bad) == (4.5, 2, 0), (got, ok, bad)


@check
def test_one_bad_multiplication_is_repaired_and_carried_forward():
    # Step 1 is wrong (2.4892 written as 2.0); step 2 reuses it. Repairing only
    # step 1 would leave step 2 reading the stale number, which is the whole
    # reason the corrected value is substituted forward.
    text = ("1. Flow area: 1.96 * 1.27 = 2.0\n"
            "2. Discharge: 2.0 * 10 = 20.0\n")
    got, ok, bad = repair(text)
    assert ok == 2 and bad == 0, (ok, bad)
    assert abs(got - 24.892) < 1e-6, got


@check
def test_prose_without_arithmetic_scores_nothing_rather_than_zero():
    got, ok, bad = repair("1. Use the Manning equation.\n2. Then solve it.\n")
    assert got is None and ok == 0, (got, ok)


@check
def test_a_step_the_evaluator_rejects_is_counted_not_swallowed():
    text = ("1. Area: 1.96 * 1.27 = 2.4892\n"
            "2. Radius: \\frac{2.4892}{4.5} = 0.5531\n"
            "3. Discharge: 2.4892 * 2 = 4.9784\n")
    got, ok, bad = repair(text)
    assert bad == 1 and ok == 2, (ok, bad)
    assert abs(got - 4.9784) < 1e-3, got


if __name__ == "__main__":
    for fn in CHECKS:
        fn()
        print("ok ", fn.__name__)
    print(f"{len(CHECKS)} checks passed")
