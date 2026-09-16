"""The band rule, which decides what the remaining three sessions measure on.

It is pre-registered and it is code, so that choosing it twice is visible rather
than convenient.
"""

from training.harness.desk_profile import BAND_HIGH, BAND_LOW, TARGET_FLOOR, band


def cells(**kw):
    return {"by_cell": {k: {"n": 20, "correct": int(v * 20), "rate": v}
                        for k, v in kw.items()}}


def test_a_cell_the_base_already_passes_is_dropped():
    """P42: the base scored 0.815 where the adapter scored 0.825."""
    v = band(cells(**{"importance@1": 0.95, "owed@2": 0.4, "owed@3": 0.4}),
             cells(**{"importance@1": 0.99, "owed@2": 0.9, "owed@3": 0.9}))
    assert "importance@1" in v["dropped"]
    assert "ceiling" in v["dropped"]["importance@1"]


def test_a_cell_the_base_cannot_touch_is_dropped():
    """P45's mirror: every arm fails and it reads as the approach not working."""
    v = band(cells(**{"owed@4": 0.02, "owed@2": 0.4, "importance@3": 0.5}),
             cells(**{"owed@4": 0.8, "owed@2": 0.9, "importance@3": 0.9}))
    assert "floor" in v["dropped"]["owed@4"]


def test_a_cell_the_target_also_fails_is_dropped():
    """Nothing can be learned about ranking where the reference is wrong too."""
    v = band(cells(**{"owed@4": 0.4, "owed@2": 0.4, "importance@3": 0.5}),
             cells(**{"owed@4": 0.10, "owed@2": 0.9, "importance@3": 0.9}))
    assert "target fails it too" in v["dropped"]["owed@4"]


def test_the_band_is_inclusive_at_its_pre_registered_edges():
    v = band(cells(**{"a@1": BAND_LOW, "b@2": BAND_HIGH}),
             cells(**{"a@1": 0.9, "b@2": 0.9}))
    assert set(v["kept"]) == {"a@1", "b@2"}
    assert (BAND_LOW, BAND_HIGH, TARGET_FLOOR) == (0.15, 0.70, 0.40)


def test_a_surviving_diagonal_is_not_usable():
    """If every kept cell is one region, the grid has collapsed back.

    That is the failure every previous suite had, arriving through the back door:
    the generator produced a grid and the band threw all but one row of it away.
    """
    v = band(cells(**{"owed@1": 0.4, "owed@2": 0.5, "owed@3": 0.45}),
             cells(**{"owed@1": 0.9, "owed@2": 0.9, "owed@3": 0.9}))
    assert v["kept_regions"] == ["owed"]
    assert v["usable"] is False


def test_one_depth_surviving_is_also_not_usable():
    v = band(cells(**{"owed@2": 0.4, "importance@2": 0.5, "commitment@2": 0.45}),
             cells(**{"owed@2": 0.9, "importance@2": 0.9, "commitment@2": 0.9}))
    assert v["kept_depths"] == ["2"]
    assert v["usable"] is False


def test_a_real_grid_survives_and_is_usable():
    v = band(cells(**{"owed@1": 0.4, "owed@3": 0.3, "importance@2": 0.5,
                      "commitment@4": 0.25}),
             cells(**{"owed@1": 0.9, "owed@3": 0.8, "importance@2": 0.9,
                      "commitment@4": 0.7}))
    assert len(v["kept"]) == 4
    assert v["usable"] is True


# --------------------------------------------------------------------------
# The preflight. P51's first attempt spent an A100 arm scoring 240 cases that
# every one returned HTTP 400, and reported `correct 0 calls 0 refused 0` —
# indistinguishable from a model that cannot do the task **[ran]** 2026-09-16.
# --------------------------------------------------------------------------

import pytest

from training.email.desk import generate
from training.harness import desk_sim


def _case():
    return generate(4, 1)["cases"][0]


def test_a_serving_path_that_rejects_tools_stops_before_the_run(monkeypatch):
    monkeypatch.setattr(desk_sim, "ask_one", lambda *a, **k: {
        "said": None, "calls": 0, "refused": 0,
        "error": '{"error":{"message":"\\"auto\\" tool choice requires '
                 '--enable-auto-tool-choice"}}'})
    with pytest.raises(desk_sim.Preflight, match="rejected a tool call"):
        desk_sim.preflight("u", None, "m", _case(), 64)


def test_a_model_that_never_asks_is_also_a_stop(monkeypatch):
    """Either the tools are not reaching it or the prompt gives the answer away."""
    monkeypatch.setattr(desk_sim, "ask_one", lambda *a, **k: {
        "said": "yes", "calls": 0, "refused": 0})
    with pytest.raises(desk_sim.Preflight, match="without calling a tool"):
        desk_sim.preflight("u", None, "m", _case(), 64)


def test_a_working_path_passes_and_returns_the_probe(monkeypatch):
    monkeypatch.setattr(desk_sim, "ask_one", lambda *a, **k: {
        "said": "msg-003", "calls": 2, "refused": 0})
    assert desk_sim.preflight("u", None, "m", _case(), 64)["calls"] == 2


def test_the_progress_line_shows_errors_so_a_void_run_cannot_look_like_a_floor(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(desk_sim, "ask_one", lambda *a, **k: {
        "said": None, "calls": 3, "refused": 0, "error": "boom"})
    # preflight is what should stop this, so bypass it to test the reporting itself
    monkeypatch.setattr(desk_sim, "preflight", lambda *a, **k: {"calls": 1})
    cases = generate(20, 2)["cases"]
    desk_sim.run("u", None, "m", cases, 4, 64, tmp_path / "r.json", every=20)
    assert "ERRORS 20/20" in capsys.readouterr().out


def test_a_resumed_run_does_not_repeat_the_preflight(tmp_path, monkeypatch):
    """Resuming means the path already worked once; probing again costs a call."""
    import json
    out = tmp_path / "r.json"
    cases = generate(4, 3)["cases"]
    out.write_text(json.dumps({"records": [
        {"id": c["case_id"], "region": c["region"], "depth": c["depth"],
         "correct": True, "calls": 1} for c in cases]}))
    called = []
    monkeypatch.setattr(desk_sim, "preflight",
                        lambda *a, **k: called.append(1) or {"calls": 1})
    desk_sim.run("u", None, "m", cases, 4, 64, out)
    assert called == []
