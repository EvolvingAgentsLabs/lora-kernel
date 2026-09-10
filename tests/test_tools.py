"""The three tools. Each check pins a way a tool could lie instead of failing."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.physics.tools import ToolError, answer, fill  # noqa: E402

CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@check
def test_a_lookup_returns_the_table_value():
    assert answer("lookup", "fluid=water; property=density; T=20") == 998.2
    assert answer("lookup", "fluid=glycerin, property=viscosity, T=20") == 1.412


@check
def test_a_missing_entry_is_an_error_and_never_an_interpolation():
    for bad in ("fluid=water; property=density; T=25",
                "fluid=mercury; property=density; T=20",
                "fluid=water; property=colour; T=20"):
        try:
            answer("lookup", bad)
        except ToolError:
            continue
        raise AssertionError(f"{bad!r} returned a number instead of failing")


@check
def test_the_default_temperature_is_the_one_the_table_is_written_for():
    # A statement that says "water" with no temperature means the table's 20 C
    # row; guessing a different row silently would be the same failure as
    # interpolating.
    assert answer("lookup", "fluid=water; property=density") == 998.2


@check
def test_conversions_are_exact_and_dimension_checked():
    assert abs(answer("convert", "value=45; from=L/s; to=m^3/s") - 0.045) < 1e-12
    assert abs(answer("convert", "value=220; from=mm; to=m") - 0.22) < 1e-12
    assert abs(answer("convert", "value=1.5; from=bar; to=Pa") - 150000) < 1e-9
    try:
        answer("convert", "value=1; from=L/s; to=m")
    except ToolError as e:
        assert "flow" in str(e) and "length" in str(e), e
        return
    raise AssertionError("a flow was converted into a length")


@check
def test_a_malformed_argument_list_fails_loudly():
    for bad in ("fluid water; property=density", "", "value=x; from=mm; to=m"):
        try:
            answer("convert" if "value" in bad else "lookup", bad)
        except ToolError:
            continue
        raise AssertionError(f"{bad!r} was accepted")


@check
def test_fill_answers_every_kind_of_call_in_one_chain():
    text = ("1. Flow: <convert>value=45; from=L/s; to=m^3/s</convert>\n"
            "2. Density: <lookup>fluid=water; property=density; T=20</lookup>\n"
            "3. Mass flow: <calc>0.045 * 998.2</calc>\n")
    out, calls, fails = fill(text)
    assert (calls, fails) == (3, 0), (calls, fails)
    assert "= 0.045" in out and "= 998.2" in out and "= 44.919" in out, out


if __name__ == "__main__":
    for fn in CHECKS:
        fn()
        print("ok ", fn.__name__)
    print(f"{len(CHECKS)} checks passed")
