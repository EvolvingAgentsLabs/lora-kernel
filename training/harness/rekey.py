"""D2 — the C18 mechanism, read: an adapter's tensor names, moved to where vLLM looks.

WHAT WAS READ, vLLM v0.29.0 **[read]**. `Qwen/Qwen3.5-4B` declares
`Qwen3_5ForConditionalGeneration`; its checkpoint names the text stack
`model.language_model.layers.N…`, and vLLM's mapper for that class rewrites exactly
that prefix, `model.language_model.` → `language_model.model.`
(`models/qwen3_vl.py`). `tiny_adapter` loads the base through `AutoModelForCausalLM`
— the text-only class — so PEFT writes `base_model.model.model.layers.N…`. No prefix
of the mapper matches it, and the name reaches vLLM unchanged.

Two checks then disagree, and that disagreement is C18:

    loading      validates the LAST component only (`q_proj` is an expected module)
                 → passes → logs `Loaded new LoRA adapter`      (`lora/lora_model.py`)
    activating   looks each module up by its FULL name
                 → `language_model.model.layers.N…` is not `model.layers.N…`
                 → `reset_lora(index)` behind a `logger.debug`   (`lora/model_manager.py`)

so the slot is live, the LoRA kernel runs on zeros, and the base is served — every one
of P33's four observations. The prediction is that renaming the keys, with no
retraining, turns the identity gate to `applied`. `lora_matrix --rekey` buys that arm.

With $K$ the adapter's tensor names, $m$ vLLM's mapper and $M$ the served model's
module names, what activation applies is

$$\\text{applied}(K) = \\{\\,k \\in K : m(k) \\in M\\,\\}, \\qquad
|\\text{applied}(K)| = 0 \\ \\text{as trained}, \\quad
|\\text{applied}(\\rho(K))| = |K| \\ \\text{predicted, with } \\rho \\text{ the renaming below.}$$
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

FROM = "base_model.model.model.layers."
TO = "base_model.model.model.language_model.layers."


def rekey_name(name: str) -> str:
    """One tensor name, moved under the prefix vLLM's mapper rewrites. Idempotent:
    a name already under `language_model.` does not start with FROM."""
    return TO + name[len(FROM):] if name.startswith(FROM) else name


def vllm_module(name: str) -> str:
    """The module name vLLM 0.29.0 derives for the ConditionalGeneration class
    **[read]**: strip `base_model.model.`, apply the prefix mapper, drop the
    `lora_A/B.weight` tail. Zero GPU — this is the measurement at the point of
    failure, where the served text is only where it surfaces."""
    n = name[len("base_model.model."):] if name.startswith("base_model.model.") else name
    if n.startswith("model.language_model."):
        n = "language_model.model." + n[len("model.language_model."):]
    for tail in (".lora_A.weight", ".lora_B.weight", ".lora_A.default.weight",
                 ".lora_B.default.weight"):
        if n.endswith(tail):
            return n[: -len(tail)]
    return n


def would_match(names) -> dict:
    """How many of an adapter's tensors land on a text-stack module of the served
    model. The served stack lives under `language_model.model.layers.`."""
    names = list(names)
    hit = sum(vllm_module(n).startswith("language_model.model.layers.") for n in names)
    return {"tensors": len(names), "land_on_text_stack": hit}


def rekey_adapter(src: str, dst: str) -> dict:
    """Copy an adapter with its tensors renamed. Nothing is retrained."""
    from safetensors.torch import load_file, save_file

    s, d = Path(src), Path(dst)
    d.mkdir(parents=True, exist_ok=True)
    tensors = load_file(str(s / "adapter_model.safetensors"))
    renamed = {rekey_name(k): v for k, v in tensors.items()}
    assert len(renamed) == len(tensors), "two names collapsed into one"
    save_file(renamed, str(d / "adapter_model.safetensors"))
    for f in s.iterdir():
        if f.name != "adapter_model.safetensors" and f.is_file():
            shutil.copy2(f, d / f.name)
    return {"src": src, "dst": dst,
            "moved": sum(k != rekey_name(k) for k in tensors),
            "before": would_match(tensors), "after": would_match(renamed)}


if __name__ == "__main__":
    import sys
    print(json.dumps(rekey_adapter(sys.argv[1], sys.argv[2]), indent=1))
