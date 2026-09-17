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

# EACH MEMBER IS A RECORD, NOT A PATH. A corpus is everything the trainer needs and
# nothing a caller needs; see `contract.py` for why a band and an output kind are
# now declared, and what P44 and P45 measured to make each of them a field.
#
# THE SURFACES ARE READ THE SAME WAY, and for the same reason: P43's OpenClaw turn
# made zero tool calls because the agent offered its own toolbox to an expert trained
# on three tags [ran]. `tests/test_prune.py` re-reads every corpus for both fields.
#
# ORDER IS DECLARED WHERE IT WAS TAUGHT AND NOWHERE ELSE. The email corpora carry an
# offered block, and every one of their prompts lists it `thread_history,
# sender_stats, message` — so that order is a fact about what the adapter read, and
# rendering it any other way ships a prompt it never saw. `fluids-full` has a block
# too, reading `calc, lookup, convert`. The two `-mt` corpora carry **no listing at
# all**: their call order varies row to row, so there is nothing to preserve and
# `kernel-mt`'s tags are written alphabetically to say so.
#
# THE BANDS BELOW ARE READ OFF THE CORPORA, NOT CHOSEN — and doing that rather than
# asserting it caught three of five wrong on the first pass: `kernel-mt` is 2-4 and
# not 6-9, `kernel-email` is 1-1 exactly, and `domain-mt` calls nothing at all in
# 600 of 600 examples **[ran]** 2026-09-15. `tests/test_contract.py` re-reads every
# corpus and fails if a declaration drifts from what was trained.
POOL = {
    "adapters/kernel-mt": contract.text(
        "training/harness/data_mt/train.jsonl", contract.band(2, 4),
        tags=["calc", "convert", "lookup"]),
    # Zero throughout: this is the physics corpus with the protocol removed and the
    # reasoning kept, so it never calls a tool. Declaring that is what stops a
    # router handing it a task whose answer has to come from a handbook.
    # Its surface is empty for the same reason its band is (0, 0) — not an omission,
    # the true statement about a corpus that calls nothing in 600 of 600 examples.
    "adapters/domain-mt": contract.text(
        "training/physics/data_mt/train.jsonl", contract.band(0, 0), tags=[]),
    # P35: the same protocol, in the email suite's vocabulary. P34 measured the
    # physics kernel taking this base from 0 tool calls to 127 and every one
    # refused — the disposition travels, the names do not [ran].
    "adapters/kernel-email": contract.text(
        "training/harness/data_ep/train.jsonl", contract.band(1, 1),
        note="every one of its 600 examples calls exactly once",
        tags=["thread_history", "sender_stats", "message"],
        args={"thread_history": ["thread_id"], "sender_stats": ["address"], "message": ["id"]}),
    # P36: the ceiling. Tools and judgement in one adapter — the reference point a
    # pool has to match, not the architecture itself.
    # 0 is not an error here: 154 of 598 examples answer with no call at all, which
    # is the corpus teaching that some messages need no lookup. An expert whose floor
    # is 1 would have to invent a call for those, which is P45's failure mode in the
    # other direction.
    "adapters/email-full": contract.text(
        "training/harness/data_ef/train.jsonl", contract.band(0, 3),
        tags=["thread_history", "sender_stats", "message"],
        # THE KEYS THE CORPUS WRITES, and why they are declared: P59 recorded OpenClaw
        # offering its own `message` tool (action, channel, target, …) beside
        # `lora-inbox__message` (id). Only the key tells them apart.
        args={"thread_history": ["thread_id"], "sender_stats": ["address"], "message": ["id"]}),
    # P37: the second pool member. A genuinely different subdomain on the same
    # resident base — one member is not a pool.
    #
    # ITS BAND IS THE WHOLE P45 RESULT. Trained on 6-to-9-step chains only, it
    # over-solves on 18 of 18 cases below that and the bare base beats it at three
    # steps, 0.167 to 0.000 [ran]. Declaring (6, 9) is what lets a router refuse it
    # a two-step problem instead of receiving fluent nonsense.
    "adapters/fluids-full": contract.text(
        "training/physics/data_ff/train.jsonl", contract.band(6, 9),
        tags=["calc", "lookup", "convert"]),
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
