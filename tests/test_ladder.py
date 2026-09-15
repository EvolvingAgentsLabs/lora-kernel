"""The ladder's own arithmetic, checked by running its oracle chains.

A generated suite whose answer disagrees with its own solution is the purest form
of an instrument that lies: every arm fails and the failure looks like the model's.
So each rung is scored by ANSWERING ITS OWN CHAIN with the real tools, and the
result must match the answer the generator published.
"""

import math

import pytest

from training.physics import multitool as mod
from training.physics import ladder
from training.physics.tools import CALL, answer


def _run_chain(case):
    """Execute the oracle chain with the real tools; return the last value."""
    book = {tuple(k): v for k, v in case["handbook"]}
    last = None
    for _label, tool, body in case["chain"]:
        last = answer(tool, body, book)
    return last


@pytest.mark.parametrize("family", sorted(ladder.LADDER))
def test_every_rung_solves_to_its_own_published_answer(family):
    cases = mod.generate(24, 99, {family: ladder.LADDER[family]})
    assert cases
    for c in cases:
        got = _run_chain(c)
        assert math.isclose(got, c["answer"], rel_tol=1e-6), (
            f"{c['case_id']} {family}: chain gives {got}, generator says {c['answer']}")


@pytest.mark.parametrize("family,steps", sorted(
    (f, ladder.STEPS[f]) for f in ladder.LADDER))
def test_each_rung_has_the_depth_it_claims(family, steps):
    cases = mod.generate(12, 5, {family: ladder.LADDER[family]})
    assert {len(c["chain"]) for c in cases} == {steps}


def test_the_ladder_sits_below_the_suite_it_extends():
    """The point of the ladder is the rungs the suite never had."""
    existing = {mod.generate(4, 1, {f: mod.FAMILIES[f]})[0] for f in ()} or None
    depths = sorted({len(c["chain"])
                     for f in mod.FAMILIES
                     for c in mod.generate(4, 1, {f: mod.FAMILIES[f]})})
    assert min(depths) == 6, f"the suite's floor moved: {depths}"
    assert max(ladder.STEPS[f] for f in ladder.LADDER) < 6


def test_the_handbook_is_never_printed_in_the_statement():
    """P15's fault with a new face: a value in the prompt makes the lookup decoration."""
    for family in ladder.LADDER:
        for c in mod.generate(16, 3, {family: ladder.LADDER[family]}):
            stmt = c["prompt"]
            for (_name, _t), row in ((tuple(k), v) for k, v in c["handbook"]):
                for value in row.values():
                    assert f"{value}" not in stmt, f"{c['case_id']} prints {value}"


def test_full_ladder_covers_one_to_nine_and_names_every_rung():
    fams = ladder.full_ladder()
    assert set(fams) == set(ladder.STEPS)
    for name in fams:
        assert name in ladder.STEPS
