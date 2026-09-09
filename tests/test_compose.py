"""The composition run's bookkeeping, checked without a GPU.

Both tests exist because of the same reclaimed session: an arm that had scored
twenty of thirty cases came back holding nothing, so the resume has to work at
case granularity or the next reclaim costs the same again.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.harness.compose import score  # noqa: E402
from training.physics.generate import TRAIN_FAMILIES, generate  # noqa: E402

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


def _rows(n=6):
    return generate(n, 4242, TRAIN_FAMILIES, style="calc")


def _oracle_step(rows):
    """A generator that answers every case correctly, in one shot."""
    by_prompt = {r["prompt"]: r["answer"] for r in rows}

    def step(system, user, prefix, stop):
        return '{"answer": %r}' % by_prompt[user] if not prefix else ""

    return step


@check
def test_every_case_is_banked_as_it_lands():
    rows = _rows()
    saved = []
    out = score(_oracle_step(rows), rows, 0.02, "arm", None, saved.append)
    assert len(saved) == len(rows), f"{len(saved)} saves for {len(rows)} cases"
    assert [s["scored"] for s in saved] == list(range(1, len(rows) + 1))
    assert all(not s["complete"] for s in saved), "a partial claimed completion"
    assert out["complete"] and out["passed"] == len(rows), out["passed"]


@check
def test_a_reclaimed_arm_resumes_where_it_stopped():
    rows = _rows()
    saved = []
    score(_oracle_step(rows[:3]), rows[:3], 0.02, "arm", None, saved.append)
    partial = saved[-1]                       # what a killed session left behind

    seen = []

    def counting_step(system, user, prefix, stop):
        seen.append(user)
        return _oracle_step(rows)(system, user, prefix, stop)

    out = score(counting_step, rows, 0.02, "arm", partial, None)
    assert len(seen) == len(rows) - 3, f"regenerated {len(seen)} cases"
    assert out["scored"] == len(rows) and out["passed"] == len(rows)
    assert [r["case_id"] for r in out["records"]] == [r["case_id"] for r in rows]


if __name__ == "__main__":
    for fn in CHECKS:
        fn()
        print("ok ", fn.__name__)
    print(f"{len(CHECKS)} checks passed")
