r"""E6 — a LoRA on the upper half of the layers (docs/review/00-thesis-review.md §5).

The adapter's reach is read back from its file, and the verdict needs both halves: at most three of the 70 held-out turns
lost against the full member, $\ell\le 3$, and the layers below $k$ bit-identical to the base with a base-vs-base control
that is itself identical."""
from __future__ import annotations

import json
import re
import sys
import types

import pytest

from training.harness import fake_vllm as fv
from training.s4_train import adapter_layers, layer_regex, layers_from

TARGETS = "q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj".split(",")


def test_the_regex_takes_the_upper_layers_and_nothing_below():
    rx = re.compile(layer_regex(TARGETS, range(21, 42)))
    assert rx.fullmatch("model.language_model.layers.21.self_attn.q_proj")
    assert rx.fullmatch("model.language_model.layers.41.mlp.down_proj")
    assert not rx.fullmatch("model.language_model.layers.20.self_attn.q_proj")
    assert not rx.fullmatch("model.language_model.layers.2.mlp.up_proj")        # "2" is not "21"
    assert not rx.fullmatch("model.language_model.layers.21.self_attn.q_norm")


def test_half_means_n_over_two_and_nothing_means_every_layer():
    assert layers_from("half", 42) == 21 and layers_from("30", 42) == 30
    assert layers_from(None, 42) == 0 and layers_from("0", 42) == 0


def test_the_layers_an_adapter_touches_are_read_from_its_tensor_names():
    names = ["base_model.model.language_model.model.layers.21.self_attn.q_proj.lora_A.weight",
             "base_model.model.language_model.model.layers.40.mlp.up_proj.lora_B.weight"]
    assert adapter_layers(names) == [21, 40]


def _identity(**over):
    return {"k": 21, "control_identical": True, "inputs_identical": True, "kv_identical": True, "adapted_moves": True,
            "file_layers": list(range(21, 42)), "file_layers_below_k": [], **over}


def _run(tmp_path, monkeypatch, identity):
    from pathlib import Path as P

    from tests.test_school_demo import scripted
    repo = P(__file__).resolve().parent.parent
    (tmp_path / "examples").symlink_to(repo / "examples")
    for d in ("school-staff-s0", "school-upper-s0"):
        (tmp_path / "adapters" / d).mkdir(parents=True)
        (tmp_path / "adapters" / d / "adapter_model.safetensors").write_bytes(b"stand-in")
    (tmp_path / "adapters" / "school-upper-s0" / "lower_identity.json").write_text(json.dumps(identity))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "transformers", types.SimpleNamespace(AutoTokenizer=fv.FakeTokenizer))
    from examples.school import school_arm
    monkeypatch.setattr(sys, "argv", ["school_arm", "--arms", "school-s0,upper-s0", "--out", "e6.json"])
    with fv.patched(scripted):
        school_arm.main()
    return json.loads((tmp_path / "e6.json").read_text())


def test_e6_passes_when_nothing_is_lost_and_the_lower_layers_are_the_bases(tmp_path, monkeypatch):
    rec = _run(tmp_path, monkeypatch, _identity())
    e6 = rec["analysis"]["E6"]["upper-s0"]
    assert rec["lower_identity"]["upper-s0"]["k"] == 21
    assert e6["pair"]["pair"] == "upper-s0 vs school-s0" and e6["lost"] == 0
    assert e6["reading"].startswith("PASSED")


@pytest.mark.parametrize("over, reading", [
    ({"control_identical": False}, "VOID: base against base"),
    ({"adapted_moves": False}, "VOID: the adapter does not move"),
    ({"kv_identical": False}, "FALSIFIED: the layers below k"),
    ({"file_layers_below_k": [3]}, "FALSIFIED: the layers below k"),
])
def test_an_unreadable_or_broken_identity_is_never_a_pass(tmp_path, monkeypatch, over, reading):
    rec = _run(tmp_path, monkeypatch, _identity(**over))
    assert rec["analysis"]["E6"]["upper-s0"]["reading"].startswith(reading)


def test_the_verdict_counts_the_turns_the_full_member_passes_and_the_upper_one_fails():
    from examples.school.school_arm import e6
    held = lambda fails: {f"c{i}": {"credit": i not in fails} for i in range(70)}
    rec = {"arms": {"school-s0": {"held_out": held(set())}, "upper-s0": {"held_out": held({1, 2, 3, 4})}},
           "G1": {"upper-s0": {"applied": True}}, "lower_identity": {"upper-s0": _identity()}}
    assert e6(rec)["upper-s0"]["lost"] == 4 and e6(rec)["upper-s0"]["reading"].startswith("FALSIFIED: 4 turns lost")
    rec["arms"]["upper-s0"]["held_out"] = held({1, 2, 3})
    assert e6(rec)["upper-s0"]["reading"].startswith("PASSED: 3 of 70")
