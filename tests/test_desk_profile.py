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
