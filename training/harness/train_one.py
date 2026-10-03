"""Train one adapter, name it for the class that will serve it, and exit. A separate process, on purpose.

WHY A MODULE FOR FOUR LINES. P53 trained an adapter in-process and then started vLLM
beside it, and vLLM refused:

    ValueError: Free memory on device cuda:0 (32.79/39.49 GiB) on startup is less
    than desired GPU memory utilization (0.9, 35.54 GiB)

**The trainer's process was still holding 6.7 GiB.** `free()` runs `gc.collect()` and
`torch.cuda.empty_cache()`, which return cached blocks to the allocator — they do not
release the CUDA context, and nothing that runs *inside* a process can. Only exiting
does.

P26's brief already said not to train inside a serving run. That was overridden here
with a reason that was sound about the **question** — this run is about a delta on one
card, not about HTTP — and wrong about the **mechanism**, which bites either way. So
the question keeps its single session and the training gets its own process.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--train", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    # 0 is every adapter trained before W9. W5e's retrain of W5c's recipe, at seed 0 both times,
    # disagreed with the original on 25 of 67 rows [ran]: the GPU is not deterministic, so a seed
    # prices the draw only beside that noise, never instead of it.
    ap.add_argument("--seed", type=int, default=0)
    # REAL3: a real page read whole runs to ~4k tokens; the window is the corpus's, and a longer one trains one row at a
    # time with twice the accumulation — the same 16 rows per step
    ap.add_argument("--max-seq", type=int, default=1536)
    ap.add_argument("--span-logits", action="store_true", help="PAIR1: logits only where the span-masked loss is taken")
    ap.add_argument("--layers-from", default=None, help="E6: a LoRA on decoder layers k…N-1 only — 'half' or k")
    a = ap.parse_args()

    from training.s4_train import train_adapter

    rows = [json.loads(line) for line in open(a.train) if line.strip()]
    print(f"[train] {a.out_dir} from {len(rows)} examples", flush=True)
    model, tok = train_adapter(a.base, rows, a.out_dir, SimpleNamespace(
        epochs=a.epochs, r=a.r, alpha=a.alpha, lr=a.lr, batch=1 if a.max_seq > 2048 else 2, accum=16 if a.max_seq > 2048 else 8,
        max_seq=a.max_seq, seed=a.seed, four_bit=False, layers_from=a.layers_from, span_logits=a.span_logits,
        targets="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"))
    if a.layers_from:
        from training.s4_train import layers_from, n_layers
        k = layers_from(a.layers_from, n_layers(model))
        texts = [tok.apply_chat_template(r["messages"], tokenize=False) for r in rows[:4]]
        check = lower_layers_identical(model, tok, texts, k)
    named_for_serving(a.base, a.out_dir)
    if a.layers_from:                                 # written after the rename, which replaces the directory
        check.update(adapter_file_layers(a.out_dir, k))
        Path(a.out_dir, "lower_identity.json").write_text(json.dumps(check, indent=1))
        print(f"[e6] lower layers <{k}: control {check['control_identical']}, kv identical {check.get('kv_identical')}, "
              f"inputs identical {check['inputs_identical']}, layer {k} moved {check['adapted_moves']}, "
              f"file below k {check['file_layers_below_k']}", flush=True)
    print("[train] done", flush=True)
    return 0


def adapter_file_layers(out_dir: str, k: int) -> dict:
    """What the saved adapter touches, read from the file — not from the config that asked for it."""
    from safetensors import safe_open

    from training.s4_train import adapter_layers
    with safe_open(str(Path(out_dir, "adapter_model.safetensors")), "pt") as f:
        layers = adapter_layers(f.keys())
    return {"file_layers": layers, "file_layers_below_k": [i for i in layers if i < k]}


def _cache_layers(pkv) -> list:
    """(keys, values) per cached layer, across the cache classes transformers has shipped."""
    if hasattr(pkv, "layers"):
        return [(c.keys, c.values) for c in pkv.layers if getattr(c, "keys", None) is not None]
    if hasattr(pkv, "key_cache"):
        return list(zip(pkv.key_cache, pkv.value_cache))
    return [tuple(x[:2]) for x in pkv]


def lower_layers_identical(model, tok, texts: list[str], k: int) -> dict:
    r"""E6's mechanical gate, measured where it happens: one prefix through the trained model with the adapter on and
    with it off (`disable_adapter`), same process, same kernels. For a layer $l\lt k$ the KV is
    $K_l = W_K\,h_{l-1}$ and $h_{l-1}$ depends only on layers below $l$, so with no LoRA below $k$ the cache of every
    layer below $k$ must be the base's **bit for bit** (`torch.equal`, not a tolerance). Layer $k$'s output must move —
    otherwise the adapter was not active and the identity is vacuous. A second adapter-off pass is the control: if base
    against base is not bit-identical, the engine is not deterministic here and the test cannot be read."""
    import torch
    was = model.training
    model.eval()
    res = {"k": k, "prompts": len(texts), "inputs_identical": True, "adapted_moves": False, "kv_identical": None,
           "kv_layers_compared": 0}
    try:
        for text in texts:
            ids = tok(text, return_tensors="pt", truncation=True, max_length=512).to(model.device)
            with torch.no_grad():
                on = model(**ids, use_cache=True, output_hidden_states=True)
                with model.disable_adapter():
                    off = model(**ids, use_cache=True, output_hidden_states=True)
                    off2 = model(**ids, use_cache=True, output_hidden_states=True)
            # the control (F0b's lesson [ran]): base against base must already be bit-identical, or the test reads the engine
            res["control_identical"] = res.get("control_identical", True) and all(
                torch.equal(x, y) for x, y in zip(off.hidden_states, off2.hidden_states))
            # hidden_states[i] is the input to decoder layer i: 0…k are fixed by layers below k
            res["inputs_identical"] &= all(torch.equal(on.hidden_states[i], off.hidden_states[i]) for i in range(k + 1))
            res["adapted_moves"] |= not torch.equal(on.hidden_states[k + 1], off.hidden_states[k + 1])
            try:
                a, b = _cache_layers(on.past_key_values), _cache_layers(off.past_key_values)
                lower = min(k, len(a))
                same = all(torch.equal(a[i][0], b[i][0]) and torch.equal(a[i][1], b[i][1]) for i in range(lower))
                res["kv_identical"] = same if res["kv_identical"] is None else (res["kv_identical"] and same)
                res["kv_layers_compared"], res["kv_cached_layers"] = lower, len(a)
            except Exception as e:                            # a cache class this reader does not know — say so
                res["kv_error"] = repr(e)[:200]
    finally:
        model.train(was)
    return res


def named_for_serving(base: str, out_dir: str) -> dict:
    """D2 **[ran]** 2026-09-19: an adapter trained through `AutoModelForCausalLM` names its
    tensors `model.layers.N…`; a base vLLM serves as `…ForConditionalGeneration` activates
    by `language_model.model.layers.N…`, loads the adapter, says so, and serves the base.
    The release is the adapter **as it will be served**, so the renaming happens here,
    once, and what it did is written beside the weights."""
    import shutil
    from pathlib import Path

    from transformers import AutoConfig

    from training.harness.rekey import rekey_adapter

    arch = (AutoConfig.from_pretrained(base).architectures or [""])[0]
    note = {"base": base, "architecture": arch, "renamed": False}
    if arch.endswith("ForConditionalGeneration"):
        tmp = out_dir.rstrip("/") + ".renamed"
        note.update(rekey_adapter(out_dir, tmp), renamed=True)
        shutil.rmtree(out_dir)
        shutil.move(tmp, out_dir)
    Path(out_dir, "rekey.json").write_text(json.dumps(note, indent=1))
    print(f"[train] named for serving: {note}", flush=True)
    return note


if __name__ == "__main__":
    raise SystemExit(main())
