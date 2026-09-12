"""The dimensional algebra. Each check pins a way it could convict the innocent."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.physics.dimensions import check  # noqa: E402

CHECKS = []


def check_(fn):
    CHECKS.append(fn)
    return fn


GATE = ("A vertical rectangular gate 4.87 m wide and 0.98 m tall is submerged in a "
        "fluid of density 1025.0 kg/m^3, with its top edge 2.26 m below the surface.")


@check_
def test_a_correct_chain_carries_the_unit_that_was_asked_for():
    chain = ("1. Depth of the centroid: 2.26 + 0.98/2 = 2.75\n"
             "2. Area of the gate: 4.87 * 0.98 = 4.7726\n"
             "3. Resultant force: 1025.0 * 9.80665 * 2.75 * 4.7726 = 131926\n")
    v = check(chain, "N", GATE)
    assert v.consistent is True, (v.got, v.want, v.reason)


@check_
def test_an_invented_law_comes_out_as_the_wrong_kind_of_quantity():
    """The exact chain P14 produced outside the region: a drag force divided by an
    area, which is a pressure. This is the failure the guard exists to see."""
    stmt = ("A sphere of diameter 0.304 m moves at 3.88 m/s through a fluid of "
            "density 998.0 kg/m^3.")
    chain = ("1. Volume fraction: 4/3 * pi/6 = 0.698132\n"
             "2. Drag force: 998.0*3.88**2/(2*0.698132) = 10029.3\n")
    v = check(chain, "N", stmt)
    assert v.consistent is False and v.got == (1, -1, -2), (v.got, v.reason)


@check_
def test_an_untypeable_final_step_is_an_abstention_and_never_a_conviction():
    """Manning ends in R**(2/3), which this algebra cannot type. Reading the verdict
    off the previous step compared a length against a flow rate and convicted twenty
    correct chains."""
    stmt = "A rectangular channel 2.7 m wide runs 0.6 m deep on a bed slope of 0.01."
    chain = ("1. Flow area: 2.7 * 0.6 = 1.62\n"
             "2. Hydraulic radius: 1.62 / 3.9 = 0.415385\n"
             "3. Discharge: (1/0.015) * 1.62 * 0.415385**(2/3) * sqrt(0.01) = 6.15\n")
    v = check(chain, "m^3/s", stmt)
    assert v.consistent is None, (v.consistent, v.got, v.reason)


@check_
def test_every_spelling_of_a_unit_the_material_uses_is_read():
    """`Pa.s` matched the `Pa` prefix and typed a viscosity as a pressure, which put
    the time exponent out by one and flagged twenty correct chains."""
    stmt = ("A sphere of diameter 0.000171 m and density 1250.8 kg/m^3 settles in a "
            "fluid of density 998.0 kg/m^3 and dynamic viscosity 0.0015 Pa.s.")
    chain = ("1. Density difference: 1250.8 - 998.0 = 252.8\n"
             "2. Terminal velocity: 252.8 * 9.80665 * 0.000171**2 / (18*0.0015) = 0.00268\n")
    v = check(chain, "m/s", stmt)
    assert v.consistent is True, (v.got, v.want, v.reason)


@check_
def test_an_unknown_constant_is_dimensionless_rather_than_a_guess():
    chain = "1. Something: 2 * 3.14159 * 7 = 43.98\n"
    v = check(chain, "N", "A problem with no units in it at all.")
    assert v.consistent is False and v.got == (0, 0, 0), (v.got, v.reason)


if __name__ == "__main__":
    for fn in CHECKS:
        fn()
        print("ok ", fn.__name__)
    print(f"{len(CHECKS)} checks passed")
