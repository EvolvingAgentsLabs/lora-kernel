"""The Mac track's pure parts (examples/mac/mlx_spec_lora.py) — names, hot switching, the summary. MLX only exists on Apple
Silicon, so this file skips elsewhere (CI); it runs on the user's Mac, where the track runs."""
import pytest

mx = pytest.importorskip("mlx.core")
from examples.mac import mlx_spec_lora as m  # noqa: E402


def test_peft_names_map_onto_the_mlx_modules():
    assert m.mlx_path("base_model.model.model.language_model.layers.3.self_attn.q_proj") == \
        "language_model.model.layers.3.self_attn.q_proj"


def test_hot_lora_switches_experts_without_touching_the_base():
    import mlx.nn as nn
    base = nn.Linear(4, 3, bias=False)
    hl = m.HotLoRA(base)
    a, b = mx.ones((2, 4)), mx.ones((3, 2))
    hl.add("e1", a, b, 0.5)
    x = mx.ones((1, 4))
    m.HotLoRA.active = None
    y0 = hl(x)
    m.HotLoRA.active = "e1"
    y1 = hl(x)
    assert mx.allclose(y1 - y0, mx.full((1, 3), 4.0)).item()       # 0.5 * (x·Aᵀ = [4,4]) · Bᵀ = 0.5·8 = 4
    m.HotLoRA.active = "unknown"
    assert mx.allclose(hl(x), y0).item()                            # an expert not attached here is the base
    m.HotLoRA.active = None


def test_the_summary_reports_speedup_identity_and_g1():
    run = lambda text, tps: {"text": text, "tokens": 100, "tps": tps}
    rec = {"adapters": {"w": {}}, "runs": {
        "base/domain/off": [run("a", 10)], "base/domain/mtp": [dict(run("a", 20), mean_accepted_per_round=1.5)],
        "w/domain/off": [run("b", 10)], "w/domain/mtp": [dict(run("c", 15), mean_accepted_per_round=1.0)]}}
    s = m.summarise(rec)
    assert s["base/domain"] == {"tps_off": 10.0, "tps_mtp": 20.0, "speedup": 2.0, "identical": "1/1", "accepted_per_round": 1.5}
    assert s["w/domain"]["identical"] == "0/1" and s["G1:w"].startswith("1/1")
