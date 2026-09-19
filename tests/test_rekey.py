"""D2: the renaming that moves an adapter's tensors to where vLLM 0.29.0 looks.

$\\text{applied}(K) = \\{k \\in K : m(k) \\in M\\}$ — as trained through the text-only
class no tensor lands on the served text stack; renamed, every one does. Zero GPU."""

from training.harness.rekey import rekey_name, vllm_module, would_match

AS_TRAINED = [
    "base_model.model.model.layers.3.self_attn.q_proj.lora_A.weight",
    "base_model.model.model.layers.3.self_attn.q_proj.lora_B.weight",
    "base_model.model.model.layers.0.linear_attn.in_proj_qkv.lora_A.weight",
    "base_model.model.model.layers.0.mlp.down_proj.lora_B.weight",
]


def test_as_trained_no_tensor_lands_on_the_served_stack():
    assert would_match(AS_TRAINED) == {"tensors": 4, "land_on_text_stack": 0}


def test_renamed_every_tensor_lands():
    assert would_match(map(rekey_name, AS_TRAINED)) == {"tensors": 4, "land_on_text_stack": 4}


def test_the_module_name_is_the_one_vllm_activates_by():
    assert (vllm_module(rekey_name(AS_TRAINED[0]))
            == "language_model.model.layers.3.self_attn.q_proj")


def test_renaming_twice_is_renaming_once():
    once = [rekey_name(n) for n in AS_TRAINED]
    assert [rekey_name(n) for n in once] == once


def test_a_name_outside_the_layers_is_left_alone():
    n = "base_model.model.lm_head.lora_A.weight"
    assert rekey_name(n) == n
