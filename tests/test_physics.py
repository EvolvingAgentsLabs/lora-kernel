"""The oracle is checked against arithmetic done by hand, not against itself.

Every family computes its own answer, so the only way it stops being a claim is
if the numbers are reproduced independently here. Each test recomputes the
physics inline from the values the statement contains.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.physics.generate import (  # noqa: E402
    G, HELD_OUT_FAMILIES, TRAIN_FAMILIES, generate,
)


def _num(stmt: str, before: str, after: str = " ") -> float:
    return float(stmt.split(before)[1].split(after)[0])


def test_hydrostatic_force_matches_hand_arithmetic():
    """F = rho g h_c A, with h_c the depth of the centroid."""
    for row in generate(24, 1, TRAIN_FAMILIES):
        if row["family"] != "hydrostatic_force":
            continue
        s = row["prompt"]
        w = _num(s, "gate ", " m wide")
        h = _num(s, "wide and ", " m tall")
        rho = _num(s, "density ", " kg")
        top = _num(s, "top edge ", " m below")
        assert abs(row["answer"] - rho * G * (top + h / 2) * w * h) < 1e-6
        return
    raise AssertionError("no hydrostatic case generated")


def test_manning_matches_hand_arithmetic():
    for row in generate(24, 2, TRAIN_FAMILIES):
        if row["family"] != "manning_channel":
            continue
        s = row["prompt"]
        b = _num(s, "bed width ", " m")
        y = _num(s, "depth of ", " m")
        slope = _num(s, "bed slope is ", " and")
        n = float(re.search(r"coefficient is ([\d.]+?)\.\s", s).group(1))
        a, per = b * y, b + 2 * y
        assert abs(row["answer"] - (1 / n) * a * (a / per) ** (2 / 3) * math.sqrt(slope)) < 1e-9
        return
    raise AssertionError("no manning case generated")


def test_head_loss_is_physically_plausible():
    """The reason the ranges were changed: arithmetic can be right and the
    problem still absurd, which invites a capable model to argue with it."""
    for row in generate(60, 3, TRAIN_FAMILIES):
        if row["family"] not in ("pipe_head_loss", "pump_power"):
            continue
        v = row["workings"]["velocity"]
        assert 0.3 <= v <= 4.0, f"velocity {v} m/s is outside the engineering range"
        head = row["workings"].get("head_loss", row["answer"])
        assert head < 200, f"head loss {head} m is not a pipe, it is a mountain"


def test_stokes_cases_are_actually_in_the_stokes_regime():
    """The statement says "assume Stokes". If Re is not below 1, the assumption
    is false and a model that notices is punished for being right."""
    for row in generate(40, 7, TRAIN_FAMILIES):
        if row["family"] != "terminal_velocity":
            continue
        assert row["workings"]["reynolds"] < 1.0, \
            f"Re = {row['workings']['reynolds']:.2f} is not creeping flow"


def test_every_family_answers_a_finite_positive_number():
    for fams in (TRAIN_FAMILIES, HELD_OUT_FAMILIES):
        for row in generate(4 * len(fams), 4, fams):
            a = row["answer"]
            assert math.isfinite(a) and a > 0, f"{row['family']} produced {a}"
            assert row["unit"] in ("m", "W", "m/s", "m^3/s", "N")


def test_held_out_families_are_disjoint_from_training():
    """The generalisation probe only works if the split is actually a split."""
    assert not (set(TRAIN_FAMILIES) & set(HELD_OUT_FAMILIES))


def test_the_statement_never_leaks_the_answer():
    """A number in the prompt equal to the answer would make this a reading test."""
    for row in generate(24, 5, TRAIN_FAMILIES):
        for tok in re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", row["prompt"]):
            if abs(float(tok)) > 1e-12:
                assert abs(float(tok) - row["answer"]) / abs(row["answer"]) > 1e-6, \
                    f"{row['family']}: the statement contains its own answer"


def test_prompt_asks_for_one_json_object():
    row = generate(1, 6, TRAIN_FAMILIES)[0]
    assert '{"answer": <number>}' in row["prompt"] and row["unit"] in row["prompt"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} checks passed")
