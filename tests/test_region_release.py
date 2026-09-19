"""The re-release of a region measured to fail — what is checkable with zero GPU.

The verdict is three paired exact sign tests (FOUNDATIONS §7.1),
p = 2 * sum_{k<=min(b,c)} C(b+c,k) 2^-(b+c): the member must not lose to its recorded run, must
beat its bare base, must not lose to the frontier. A tie against the base is NOT a release —
a baseline at the ceiling makes every arm tie and the tie reads as success.
"""
import json
from pathlib import Path

from training.harness import region_release as rr, suites


def _rec(recorded="tie", base="improvement", frontier="improvement", applied=True):
    return {"G1": {"applied": applied},
            "pairs": [{"pair": "new vs recorded", "state": recorded}, {"pair": "new vs base", "state": base},
                      {"pair": "new vs frontier", "state": frontier}]}


def test_released_only_when_all_three_hold():
    assert rr.verdict(_rec())["released"] is True
    assert rr.verdict(_rec(frontier="tie"))["released"] is True
    for bad in (_rec(recorded="REGRESSION"), _rec(base="tie"), _rec(frontier="REGRESSION"), _rec(applied=False)):
        assert rr.verdict(bad)["released"] is False


def test_a_tie_with_the_base_is_named_as_the_reason():
    assert "new vs base is tie" in rr.verdict(_rec(base="tie"))["reading"]


def test_an_empty_record_is_not_a_release():
    v = rr.verdict({})
    assert v["released"] is False and "NOTHING SERVED" in v["reading"]


def test_both_recorded_arms_rescore_to_their_stored_totals():
    suite = suites.load("fluids")
    by_id = {c.id: c for c in suite.cases(suite.eval_n, suite.eval_seed)}
    spec = rr.REGIONS["fluids-full"]
    path, name = spec["recorded"]
    old = json.loads(Path(path).read_text())["arms"][name]["records"]
    old = old if isinstance(old, list) else list(old.values())
    assert sum(r["correct"] for r in rr.rescored(old, by_id)) == 90
    fr = json.loads(Path(spec["frontier"]).read_text())
    assert sum(r["correct"] for r in rr.rescored(fr["records"], by_id)) == fr["passed"] == 66


def test_the_corpus_is_the_one_the_recorded_member_was_trained_on_and_holds_no_evaluated_case():
    spec = rr.REGIONS["fluids-full"]
    rows = [json.loads(l) for l in Path(spec["corpus"]).read_text().splitlines()]
    assert len(rows) == 600
    suite = suites.load("fluids")
    text = Path(spec["corpus"]).read_text()
    for c in suite.cases(suite.eval_n, suite.eval_seed):
        assert json.dumps(suite.user_text(c))[1:-1] not in text
