"""ROUTE1: the tracker's abstaining turns — the oracle abstains with no call, the gateway routes it to the role's
egress, and the scorer counts an out-of-scope turn right only when no tool was called."""
from examples.tracker import generate_sessions as gs


def test_an_abstaining_session_reaches_the_roles_egress_with_no_call():
    for kind, egress in (("developer", "frontier"), ("qa", "person")):
        s = next(x for x in (gs.out_session(gs.OUT_SEED0["eval"] + i, "eval", kind) for i in range(50)) if x)
        cap: list = []
        turns = gs.play(s, gs.harness_oracle(s), harness=True, capture=cap, scorer=gs.turn_right_out)
        assert turns[0]["route"] == egress and not turns[0]["calls"] and turns[0]["right"]
        assert cap[0]["walk"].strip() == "OUT OF SCOPE"


def test_the_out_scorer_fails_a_turn_that_called_a_tool():
    turn = {"request": "Move RD-1 to done.", "tool": None, "args": {}, "depends": False}
    assert not gs.turn_right_out([{"tool": "issue_get", "args": {"key": "RD-1"}}], turn)
    assert gs.turn_right_out([], turn)
