r"""Merge a PEFT LoRA into its base's weights and write a standalone checkpoint — so a trained member can be served where
an adapter cannot be attached: as a speculative-decoding DRAFT MODEL (vLLM applies no LoRA to a drafter — RFC #52038).

For every adapted projection, with PEFT's shapes $A \in \mathbb{R}^{r\times d_{in}}$, $B \in \mathbb{R}^{d_{out}\times r}$
and the base weight $W \in \mathbb{R}^{d_{out}\times d_{in}}$ (FOUNDATIONS §4.1):

$$W' = W + \tfrac{\alpha}{r}\, B A$$

computed in float32 and stored back in the base's dtype. Names: the adapter's
`base_model.model.<path>.lora_A.weight` lands on the checkpoint's `<path>.weight`. Every other tensor and every
non-weight file (config, tokenizer, processor) is copied unchanged. The merge is exact up to the final rounding, so the
merged model is the member — served without the adapter machinery.

    python -m training.harness.merge_lora --base google/gemma-4-E4B-it --adapter adapters/wiki-walks-s1 --out merged/wiki-e4b
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

SHARD_BYTES = 2 * 1024 ** 3


def plan(adapter_keys: list[str]) -> dict[str, str]:
    """{adapter module prefix → checkpoint weight name} for every A/B pair."""
    mods = sorted({k.rsplit(".lora_", 1)[0] for k in adapter_keys if ".lora_A." in k or ".lora_B." in k})
    return {m: m.removeprefix("base_model.model.") + ".weight" for m in mods}


def merge_tensor(w, a, b, scale: float):
    """W + scale·(B @ A), in float32, back to W's dtype. Works for torch tensors and numpy arrays alike."""
    try:
        import torch
        if isinstance(w, torch.Tensor):
            return (w.float() + scale * (b.float() @ a.float())).to(w.dtype)
    except ImportError:
        pass
    import numpy as np
    return (w.astype(np.float32) + scale * (b.astype(np.float32) @ a.astype(np.float32))).astype(w.dtype)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="a HF repo id or a local checkpoint directory")
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file
    src = Path(a.base)
    if not src.exists():
        from huggingface_hub import snapshot_download
        src = Path(snapshot_download(a.base))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(Path(a.adapter, "adapter_config.json").read_text())
    scale = cfg["lora_alpha"] / cfg["r"]
    ad = safe_open(str(Path(a.adapter, "adapter_model.safetensors")), "pt")
    targets = plan(list(ad.keys()))
    by_weight = {w: m for m, w in targets.items()}
    done = set()
    # Written in ~2 GB shards with an index: the E4B ships as ONE 16 GB shard, and holding it whole swaps a 16 GB Mac
    # (MAC2, 2026-09-27). Readers (vLLM, transformers, convert_hf_to_gguf) take a sharded checkpoint through the index.
    weight_map, pending, size, n = {}, {}, 0, 0

    def flush():
        nonlocal pending, size, n
        if pending:
            n += 1
            name = f"merged-{n:05d}.safetensors"
            save_file(pending, str(out / name), metadata={"format": "pt"})
            weight_map.update({k: name for k in pending})
            pending, size = {}, 0

    for f in sorted(src.iterdir()):
        if f.suffix == ".safetensors":
            sh = safe_open(str(f), "pt")
            for k in sh.keys():
                t = sh.get_tensor(k)
                m = by_weight.get(k)
                if m is not None:
                    t = merge_tensor(t, ad.get_tensor(f"{m}.lora_A.weight"), ad.get_tensor(f"{m}.lora_B.weight"), scale)
                    done.add(m)
                pending[k] = t.contiguous()
                size += t.numel() * t.element_size()
                if size >= SHARD_BYTES:
                    flush()
        elif f.is_file() and not f.name.endswith(".safetensors.index.json"):
            shutil.copy2(f, out / f.name)
    flush()
    # HF's shard names: converters find a checkpoint by `model*.safetensors` (convert_hf_to_gguf read `merged-*` as empty)
    final = {f"merged-{i:05d}.safetensors": f"model-{i:05d}-of-{n:05d}.safetensors" for i in range(1, n + 1)}
    for old_name, new_name in final.items():
        (out / old_name).rename(out / new_name)
    weight_map = {k: final[v] for k, v in weight_map.items()}
    (out / "model.safetensors.index.json").write_text(json.dumps({"metadata": {}, "weight_map": weight_map}, indent=1))
    missing = sorted(set(targets) - done)
    report = {"base": a.base, "adapter": a.adapter, "scale": scale, "pairs": len(targets), "merged": len(done),
              "missing": missing[:5], "torch": torch.__version__}
    (out / "merge_lora.json").write_text(json.dumps(report, indent=1))
    print(f"[merge] {len(done)}/{len(targets)} projections merged into {out}" + (f" · MISSING {missing[:3]}" if missing else ""), flush=True)
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
