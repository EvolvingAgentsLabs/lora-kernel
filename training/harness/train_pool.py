"""Train whatever the pool is missing, and nothing it already has.

P26 measures a serving stack. Retraining inside it would put forty minutes and a
second source of variance into a question about HTTP, so the adapters are carried
between sessions — but a carried tarball can be short one member, and P25's was:
its watcher fired before the domain adapter's weights existed and only `kernel-mt`
came back.

So this fills gaps. It keys on the weights file rather than the directory, which is
the check that was missing when an empty `adapters/domain-mt` nearly scored the base
model wearing an adapter's name **[ran]** 2026-09-12.

    python3 -m training.harness.train_pool --base Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

POOL = {
    "adapters/kernel-mt": "training/harness/data_mt/train.jsonl",
    "adapters/domain-mt": "training/physics/data_mt/train.jsonl",
    # P35: the same protocol, in the email suite's vocabulary. P34 measured the
    # physics kernel taking this base from 0 tool calls to 127 and every one
    # refused — the disposition travels, the names do not [ran].
    "adapters/kernel-email": "training/harness/data_ep/train.jsonl",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-seq", type=int, default=1536)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--targets",
                    default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    ap.add_argument("--four-bit", dest="four_bit", action="store_true")
    ap.add_argument("--only", default=None,
                    help="comma-separated substrings; train only matching adapters")
    args = ap.parse_args()

    from training.s4_train import free, train_adapter

    # `--only` EXISTS BECAUSE THE POOL GREW. Filling every gap is right when a
    # carried tarball is short a member; it is wrong when a step wants one adapter
    # and would otherwise pay for three on a fresh machine.
    wanted = POOL if not args.only else {
        p: c for p, c in POOL.items()
        if any(o.strip() in p for o in args.only.split(","))}
    if args.only and not wanted:
        print(f"[pool] --only {args.only!r} matched nothing in {sorted(POOL)}")
        return 1

    for path, corpus in wanted.items():
        if (Path(path) / "adapter_model.safetensors").exists():
            print(f"[pool] {path} already has weights", flush=True)
            continue
        if Path(path).exists():
            print(f"[pool] {path} exists with no weights in it — training", flush=True)
        rows = [json.loads(l) for l in open(corpus) if l.strip()]
        print(f"[pool] training {path} from {len(rows)} examples", flush=True)
        train_adapter(args.base, rows, path, args)
        free()
    # A CHAIN CANNOT WATCH FOR A THING THAT WRITES NOTHING. chain_separate.sh polls
    # a results file and breaks on its own markers; without one it would spend its
    # whole session allowance on a job that finished in twenty minutes.
    Path("pool.json").write_text(json.dumps({
        "base": args.base,
        "adapters": {p: (Path(p) / "adapter_model.safetensors").stat().st_size
                     for p in wanted if (Path(p) / "adapter_model.safetensors").exists()},
        "finished": True,
    }, indent=2))
    print("[pool] complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
