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

from training.harness import contract
from training.harness.agent_sim import SYSTEM as EMAIL_SYSTEM
from training.harness.desk_sim import SYSTEM as DESK_SYSTEM

# EACH MEMBER IS A RECORD, NOT A PATH. A corpus is everything the trainer needs and
# nothing a caller needs; see `contract.py` for why a band and an output kind are
# declared. A MEMBER IS WHAT ITS CORPUS TAUGHT — the tool block, the argument keys,
# their order, the system prompt and the depth band are all read off the corpus, and
# `tests/test_prune.py` / `tests/test_contract.py` re-read every corpus and fail if a
# declaration drifts from what was trained. The same corpora are what the router is
# trained on: a request belongs to the member whose corpus distribution it falls in,
# and to the frontier when it falls in none.
#
# THE POOL IS THE RELEASED MEMBERS, AND ONLY THEM. The retired ones — the two `-mt`
# kernels, `kernel-email`, `fluids-full` — live at the tag `v0.1-foundations` with the
# runs that measured them. Fluids remains in `route.REGIONS` marked `out` — on a measurement
# that turned out to be the serving path (90/90 as taught, [ran] M7 arm 0b); it comes back here
# when it has been through the release gate in corpus mode.
POOL = {
    # P64: the desk's `commitment` region — the same inbox and tools as the triage
    # member, a different question. Saturates at 240/240 from 75 examples (P55b).
    "adapters/desk-commitment": contract.text(
        "training/harness/data_desk/train.jsonl", contract.band(1, 1),
        note="every one of its 600 examples calls `message` exactly once — the shallow band",
        tags=["inbox", "thread_history", "sender_stats", "message"],
        # ONLY THE KEYS THE CORPUS WRITES: it calls `<message>id=…</message>` and nothing
        # else, so `thread_history` and `sender_stats` declare no keys.
        args={"message": ["id"]},
        system=DESK_SYSTEM),
    # P36: tools and judgement in one adapter. 0 is not an error in its band: 154 of
    # 598 examples answer with no call at all — the corpus teaching that some messages
    # need no lookup.
    "adapters/email-full": contract.text(
        "training/harness/data_ef/train.jsonl", contract.band(0, 3),
        tags=["thread_history", "sender_stats", "message"],
        system=EMAIL_SYSTEM,
        # THE KEYS THE CORPUS WRITES: OpenClaw offers its own `message` tool beside
        # `lora-inbox__message` (id). Only the key tells them apart (P59).
        args={"thread_history": ["thread_id"], "sender_stats": ["address"], "message": ["id"]}),
}

# Checked at import, so a member that a caller could not act on never reaches a
# training run, a serving run or a router.
contract.validate_pool(POOL)


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

    for path, record in wanted.items():
        corpus = record["corpus"]
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
