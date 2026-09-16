"""The gates that decide whether a suite's numbers are evidence.

Each one is a lesson this repository paid for, so each test names the run.
"""

import pytest

from training.suite_gates import (
    asking_is_a_decision,
    depth_is_not_the_region,
    has_a_difficulty_axis,
    inspect,
    region_not_in_the_prompt,
)


def case(region, prompt, depth, tools):
    return {"r": region, "p": prompt, "d": depth, "t": tools}


R = (lambda c: c["r"], lambda c: c["p"], lambda c: c["d"], lambda c: c["t"])


def test_a_prompt_that_names_its_region_fails_the_router_gate():
    """S3: routing tied exactly with a rule reading `clinic:` out of the text."""
    cases = [case("alpha", "clinic: alpha, patient presents", 2, ["a", "b"])
             for _ in range(20)]
    cases += [case("beta", "clinic: beta, patient presents", 2, ["a", "b"])
              for _ in range(20)]
    f = region_not_in_the_prompt(cases, *R[:2])
    assert f.passed is False
    assert f.value > 0.9


def test_two_regions_do_not_get_a_free_pass():
    """The gate's own bug: `2 * chance` is 1.000 for two regions and never fires.

    Email triage recovered its region 0.940 against 0.500 chance and passed
    **[ran]** 2026-09-16.
    """
    cases = [case("automated", "noreply notification unsubscribe", 0, [])
             for _ in range(50)]
    cases += [case("human", "hello could you confirm", 3, ["a", "b", "c"])
              for _ in range(50)]
    assert region_not_in_the_prompt(cases, *R[:2]).passed is False


def test_a_prompt_that_hides_its_region_passes():
    cases = [case(r, "the sender is waiting on a reply", 2, ["a", "b"])
             for r in ("x", "y", "z") for _ in range(20)]
    assert region_not_in_the_prompt(cases, *R[:2]).passed is True


def test_one_difficulty_is_not_an_axis():
    """P45: the fluids suite's floor was six steps and it had no case below it."""
    cases = [case("a", "p", 6, ["x"]) for _ in range(30)]
    assert has_a_difficulty_axis(cases, R[2]).passed is False


def test_three_depths_are():
    cases = [case("a", "p", d, ["x"]) for d in (1, 3, 6) for _ in range(10)]
    assert has_a_difficulty_axis(cases, R[2]).passed is True


def test_a_region_pinned_at_one_depth_confounds_the_two():
    """P45's other half, and it is the gate every existing suite fails.

    Four families each at a single oracle depth means depth and family are one
    variable, so no arm can separate the physics from the length of the chain.
    """
    cases = [case("hydro", "p", 6, ["x"]) for _ in range(10)]
    cases += [case("pipe", "p", 9, ["x"]) for _ in range(10)]
    f = depth_is_not_the_region(cases, R[0], R[2])
    assert f.passed is False
    assert f.value == 1.0


def test_regions_spanning_depths_pass():
    cases = [case(r, "p", d, ["x"]) for r in ("a", "b") for d in (1, 3, 6)]
    assert depth_is_not_the_region(cases, R[0], R[2]).passed is True


def test_one_tool_makes_asking_a_copy():
    """P13: a learned protocol scored 9/30 where twenty lines of `re` scored 23."""
    cases = [case("a", "p", 1, ["calc"]) for _ in range(30)]
    assert asking_is_a_decision(cases, R[3]).passed is False


def test_three_tools_with_real_choice_pass():
    cases = [case("a", "p", 2, ["calc", "lookup"]) for _ in range(20)]
    cases += [case("a", "p", 3, ["calc", "convert", "lookup"]) for _ in range(20)]
    assert asking_is_a_decision(cases, R[3]).passed is True


def test_the_model_gates_are_undecided_rather_than_assumed():
    """A suite's ceiling is a property of the suite AND the model.

    Returning a verdict without one would be the same class of mistake this module
    exists to catch.
    """
    # Three tools, because `asking_is_a_decision` requires a real choice — the
    # first version of this fixture used two and the gate was right to fail it.
    cases = [case(r, "hidden", d, ["a", "b", "c"][:max(d - 3, 2)])
             for r in ("x", "y", "z") for d in (1, 3, 6)]
    rep = inspect("t", cases, region_of=R[0], prompt_of=R[1], depth_of=R[2],
                  tools_of=R[3])
    assert len(rep.undecided) == 4
    assert "base_not_at_the_ceiling" in rep.undecided
    # usable is about gates that COULD be decided; the undecided ones do not veto.
    assert rep.usable is True


def test_a_failed_gate_makes_the_suite_unusable():
    cases = [case("a", "p", 6, ["x"]) for _ in range(20)]
    rep = inspect("t", cases, region_of=R[0], prompt_of=R[1], depth_of=R[2],
                  tools_of=R[3])
    assert rep.usable is False
    assert "FAIL" in rep.table()
