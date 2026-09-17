"""Phase 0's verdict logic, tested on the outcomes each gate can have.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §5.2). G1 is the test that the
delta term s·(xA)B is present in y = xW + s·(xA)B: with W frozen, a member whose
served text never differs from the base's is serving y = xW. The threshold is 2 of 3
probes because at temperature 0 a short prompt can coincide by chance and a false
NOT APPLIED costs a session; P55 A saw 6 of 8 differ on a real adapter.
"""

from training.harness.verify_substrate import NEED, verdict


def g1(differs, probed=3):
    return {"probed": probed, "differs": differs, "applied": differs >= NEED, "samples": []}


def test_two_of_three_probes_is_the_threshold():
    assert g1(2)["applied"] and g1(3)["applied"] and not g1(1)["applied"]


def test_every_member_applying_with_stop_honoured_passes():
    v = verdict({"G1": {"email-full": g1(3), "fluids-full": g1(2)},
                 "G2": None, "G3": {"stop_included": True}})
    assert v["pass"] is True and v["failed"] == [] and "OK" in v["reading"]


def test_one_member_serving_the_base_fails_the_substrate_and_is_named():
    v = verdict({"G1": {"email-full": g1(3), "fluids-full": g1(1)},
                 "G2": None, "G3": {"stop_included": True}})
    assert v["pass"] is False and v["failed"] == ["G1:fluids-full"]


def test_an_unreachable_tool_path_fails_even_when_identity_passes():
    """P51: 240 HTTP 400s that read as `calls 0`."""
    v = verdict({"G1": {"email-full": g1(3)},
                 "G2": {"email-full": {"reachable": False, "http": 400}},
                 "G3": {"stop_included": True}})
    assert v["failed"] == ["G2:email-full"]


def test_a_server_that_does_not_stop_fails():
    v = verdict({"G1": {"email-full": g1(3)}, "G2": None, "G3": {"stop_included": False}})
    assert v["failed"] == ["G3"]


def test_a_pool_with_no_member_is_empty_not_ok():
    v = verdict({"G1": {}, "G2": None, "G3": {"stop_included": True}})
    assert v["pass"] is False and "EMPTY" in v["reading"]
