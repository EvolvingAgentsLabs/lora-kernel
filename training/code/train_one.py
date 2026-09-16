"""Train one adapter and exit. A separate process, on purpose.

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
    a = ap.parse_args()

    from training.s4_train import train_adapter

    rows = [json.loads(line) for line in open(a.train) if line.strip()]
    print(f"[train] {a.out_dir} from {len(rows)} examples", flush=True)
    train_adapter(a.base, rows, a.out_dir, SimpleNamespace(
        epochs=a.epochs, r=a.r, alpha=a.alpha, lr=a.lr, batch=2, accum=8,
        max_seq=1536, seed=0, four_bit=False,
        targets="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"))
    print("[train] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
