"""merge_lora: names and arithmetic, zero GPU — the merged weight is W + (alpha/r)·B·A on exactly the adapted projections."""
import pytest

np = pytest.importorskip("numpy")                      # CI installs no numpy; the arithmetic runs where it exists

from training.harness import merge_lora as m


def test_names_land_on_the_checkpoint_weights():
    keys = ["base_model.model.model.language_model.layers.0.mlp.down_proj.lora_A.weight",
            "base_model.model.model.language_model.layers.0.mlp.down_proj.lora_B.weight"]
    assert m.plan(keys) == {"base_model.model.model.language_model.layers.0.mlp.down_proj":
                            "model.language_model.layers.0.mlp.down_proj.weight"}


def test_the_merge_is_the_lora_forward_pass():
    rng = np.random.default_rng(0)
    w, a, b = rng.normal(size=(5, 7)).astype(np.float32), rng.normal(size=(2, 7)).astype(np.float32), rng.normal(size=(5, 2)).astype(np.float32)
    x = rng.normal(size=(3, 7)).astype(np.float32)
    merged = m.merge_tensor(w, a, b, 2.0)
    assert np.allclose(x @ merged.T, x @ w.T + 2.0 * (x @ a.T) @ b.T, atol=1e-5)
