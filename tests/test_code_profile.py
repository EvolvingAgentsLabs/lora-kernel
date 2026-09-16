"""The band, the preflight, and the flaw P51 found reported rather than fixed."""

import pytest

from training.code.profile import (
    BAND_HIGH,
    BAND_LOW,
    TARGET_FLOOR,
    Preflight,
    band,
    preflight,
    summarise,
)


def cells(**kw):
    return {"by_cell": {k: {"n": 12, "correct": int(v * 12), "rate": v}
                        for k, v in kw.items()}}


def test_a_cell_the_base_already_passes_is_dropped():
    v = band(cells(**{"levenshtein@1": 0.95, "crc32@2": 0.4, "crc32@3": 0.4}),
             cells(**{"levenshtein@1": 1.0, "crc32@2": 0.9, "crc32@3": 0.9}))
    assert "ceiling" in v["dropped"]["levenshtein@1"]


def test_a_cell_the_target_also_fails_is_broken_rather_than_hard():
    v = band(cells(**{"base32@4": 0.3, "crc32@2": 0.4, "dft@3": 0.5}),
             cells(**{"base32@4": 0.10, "crc32@2": 0.9, "dft@3": 0.9}))
    assert "broken, not hard" in v["dropped"]["base32@4"]


def test_the_flaw_p51_found_is_counted_and_not_acted_on():
    """base 0.000 against target 1.000 — the largest distance an expert could close.

    P51's band dropped exactly such a cell for being on the floor, by a clause
    written for *every arm fails*. Changing the rule with the result in hand is
    indistinguishable from moving the band to fit it, so the cell is still dropped
    and the evidence is made visible instead.
    """
    v = band(cells(**{"xorshift128@4": 0.0, "crc32@2": 0.4, "dft@3": 0.5}),
             cells(**{"xorshift128@4": 1.0, "crc32@2": 0.9, "dft@3": 0.9}))
    assert "xorshift128@4" not in v["kept"], "the rule was quietly changed"
    assert v["floor_but_target_clears"] == ["xorshift128@4"]
    assert "but the target clears it" in v["dropped"]["xorshift128@4"]


def test_a_floor_cell_the_target_also_fails_is_not_counted_as_that():
    v = band(cells(**{"a@1": 0.0, "b@2": 0.4, "c@3": 0.5}),
             cells(**{"a@1": 0.2, "b@2": 0.9, "c@3": 0.9}))
    assert v["floor_but_target_clears"] == []


def test_the_band_edges_are_the_ones_p51_pre_registered():
    v = band(cells(**{"a@1": BAND_LOW, "b@2": BAND_HIGH}),
             cells(**{"a@1": 0.9, "b@2": 0.9}))
    assert set(v["kept"]) == {"a@1", "b@2"}
    assert (BAND_LOW, BAND_HIGH, TARGET_FLOOR) == (0.15, 0.70, 0.40)


def test_a_surviving_diagonal_is_not_usable():
    v = band(cells(**{"crc32@1": 0.4, "crc32@2": 0.5, "crc32@3": 0.45}),
             cells(**{"crc32@1": 0.9, "crc32@2": 0.9, "crc32@3": 0.9}))
    assert v["kept_algorithms"] == ["crc32"] and v["usable"] is False


def test_a_real_grid_is_usable():
    v = band(cells(**{"crc32@1": 0.4, "crc32@3": 0.3, "base32@2": 0.5,
                      "xorshift128@4": 0.25}),
             cells(**{"crc32@1": 0.9, "crc32@3": 0.8, "base32@2": 0.9,
                      "xorshift128@4": 0.7}))
    assert len(v["kept"]) == 4 and v["usable"] is True


def test_a_transport_error_stops_the_arm_before_it_is_paid_for(monkeypatch):
    from training.code import profile as mod
    monkeypatch.setattr(mod, "complete",
                        lambda *a, **k: {"completion": None, "error": "HTTPError 400"})
    with pytest.raises(Preflight, match="rejected a completion"):
        preflight("u", "m", {"prompt": "x"}, 64)


def test_an_empty_completion_is_also_a_stop(monkeypatch):
    """An empty arm scores zero exactly like an arm that cannot do the task."""
    from training.code import profile as mod
    monkeypatch.setattr(mod, "complete", lambda *a, **k: {"completion": "   \n"})
    with pytest.raises(Preflight, match="empty completion"):
        preflight("u", "m", {"prompt": "x"}, 64)


def test_summarise_separates_did_not_run_from_wrong_output():
    """Two very different failures that one accuracy would hide."""
    recs = [{"algorithm": "crc32", "depth": 1, "region": "c", "correct": False,
             "why": "compile: expected ';'"},
            {"algorithm": "crc32", "depth": 1, "region": "c", "correct": False,
             "why": "output differs"},
            {"algorithm": "crc32", "depth": 1, "region": "c", "correct": True,
             "why": ""}]
    s = summarise(recs)
    assert s["did_not_run"] == 1 and s["wrong_output"] == 1
    assert s["by_cell"]["crc32@1"]["rate"] == pytest.approx(1 / 3, abs=1e-3)


# ---------------------------------------------------------------------------
# Training in-process left 6.7 GiB held and vLLM refused to start beside it.
# `free()` returns cached blocks to the allocator; it cannot release the CUDA
# context, and nothing that runs inside a process can **[ran]** 2026-09-16.
# ---------------------------------------------------------------------------

def test_step_zero_trains_in_a_separate_process():
    """A comment saying so is not the same as doing so.

    P26's brief already said not to train inside a serving run. That was overridden
    with a reason sound about the question and wrong about the mechanism, so the
    check is on the code rather than on the intent.
    """
    import pathlib
    body = pathlib.Path("training/code/step_zero.py").read_text()
    assert "training.code.train_one" in body
    # and NOT by importing the trainer into this process
    assert "from training.s4_train import" not in body
    assert "train_adapter(" not in body


def test_train_one_exits_after_training_rather_than_serving():
    import pathlib
    body = pathlib.Path("training/code/train_one.py").read_text()
    assert "train_adapter" in body
    for must_not in ("vllm", "serve", "urllib"):
        assert must_not not in body.lower().split("\"\"\"")[-1], must_not


def test_step_zero_passes_maps_to_compare_not_counts():
    """`TypeError: 'int' object is not iterable`, twice — P53 and again P54.

    The first time it was worked around by computing the verdict by hand rather
    than repaired, so it cost the same crash again at the end of a second session.
    """
    import pathlib
    body = pathlib.Path("training/code/step_zero.py").read_text()
    assert "compare({r[\"id\"]" in body
    assert "compare(only_a, only_b)" not in body
