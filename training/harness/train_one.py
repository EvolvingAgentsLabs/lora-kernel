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
    a = ap.parse_args()

    from training.s4_train import train_adapter

    rows = [json.loads(line) for line in open(a.train) if line.strip()]
    print(f"[train] {a.out_dir} from {len(rows)} examples", flush=True)
    train_adapter(a.base, rows, a.out_dir, SimpleNamespace(
        epochs=a.epochs, r=a.r, alpha=a.alpha, lr=a.lr, batch=2, accum=8,
        max_seq=1536, seed=a.seed, four_bit=False,
        targets="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"))
    named_for_serving(a.base, a.out_dir)
    print("[train] done", flush=True)
    return 0


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
