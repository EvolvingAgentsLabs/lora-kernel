"""`s4_train.towers_to_exclude` — Gemma 4's towers excluded only where Gemma4ClippableLinear exists (B1, P29).

Every other base, Qwen's included, must come out with exactly the targets it always had: `None`. No torch
needed — the rule reads class names off `model.modules()`, so stand-ins carry the names.
"""
import re

import pytest

s4 = pytest.importorskip("training.s4_train")


class Gemma4ClippableLinear:
    pass


class Linear:
    pass


class _Model:
    def __init__(self, *mods):
        self._m = mods

    def modules(self):
        return iter(self._m)


def test_no_gemma_class_no_exclusion():
    assert s4.towers_to_exclude(_Model(Linear(), Linear())) is None


def test_the_towers_are_excluded_and_the_language_model_is_not():
    pat = re.compile(s4.towers_to_exclude(_Model(Linear(), Gemma4ClippableLinear())))
    assert pat.fullmatch("model.vision_tower.encoder.layers.0.self_attn.q_proj")
    assert pat.fullmatch("model.audio_tower.layers.3.self_attn.k_proj")
    assert not pat.fullmatch("model.language_model.layers.0.self_attn.q_proj")
