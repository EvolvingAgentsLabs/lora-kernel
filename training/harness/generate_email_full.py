"""The ceiling: one adapter that learns the tools and the judgement together.

WHY THIS IS BOUGHT BEFORE ANY POOL ARRANGEMENT. After P31, P34 and P35 no arm has
cleared the gate and the suite's 0.320 of margin is unclaimed. **Nobody knows
whether it is reachable at all.** If a purpose-built adapter cannot take it, then
no split of adapters will either, and composition, a judgement adapter and a better
protocol corpus are three purchases made on a number that was never there.

So this is the analogue of what P8 used in fluid mechanics: *one adapter that
learned the physics and the `<calc>` syntax together — at 40/40* **[ran]**. It is a
reference point, not the architecture.

**THE MONOLITH IS NOT THE THESIS.** The thesis says a pool of separate adapters
should match a monolith while being swappable. A monolith that clears the gate is
permission to keep measuring, not a result about the pool — and this file says so
because the number is otherwise very easy to quote as a success.

WHAT IT TEACHES, WHICH IS EVERYTHING P35's CORPUS WITHHELD. Each example is a real
triage case: the listing, then the tool calls that supply the facts the listing
withholds, then the verdict. The criteria come from `training.email.inbox.important`
itself, so the corpus and the scorer cannot drift apart.

WHAT IT MUST NOT DO. It must not let the answer be recalled. A fresh inbox is drawn
every few examples, and the seeds are disjoint from the evaluation draw — the run
that scores it uses seed 717171, which never appears here. P15 measured 27/30 from
memorisation alone before a per-case handbook made that impossible **[ran]**.

    python3 -m training.harness.generate_email_full --out training/harness/data_ef/train.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
from collections import Counter

from training.email.inbox import generate
from training.email.tools import answer
from training.harness.agent_sim import SYSTEM
from training.harness.generate_email_protocol import INSTRUCTION

# THE EVALUATION'S DRAW, KEPT OUT BY NAME. triage_run scores seed 717171; a corpus
# that happened to include it would be scored on inboxes it had already seen.
EVAL_SEED = 717171


def listing(msg: dict) -> str:
    return (f"Message {msg['id']} in thread {msg['thread_id']}\n"
            f"From: {msg['from_name']} <{msg['from']}>\n"
            f"Subject: {msg['subject']}\n"
            f"Preview: {msg['preview']}\n\n"
            "Is this important?")


def chain_for(inbox: dict, msg: dict) -> list[tuple[str, str]]:
    """The calls a careful reader would make, in the order they make sense.

    AN AUTOMATED MESSAGE IS SETTLED BY ONE LOOK, and the corpus shows that: the
    sender is visible in the listing, so the right behaviour is to answer without
    asking. A corpus that queried three tools for every message would teach the
    model to spend calls it does not need, which is its own kind of wrong.
    """
    if msg["_facts"]["automated"]:
        return []
    return [("thread_history", f"thread_id={msg['thread_id']}"),
            ("sender_stats", f"address={msg['from']}"),
            ("message", f"id={msg['id']}")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=313131)
    ap.add_argument("--out", default="training/harness/data_ef/train.jsonl")
    args = ap.parse_args()

    # THE EVALUATION'S LISTINGS, EXCLUDED BY CONTENT AND NOT ONLY BY SEED. Skipping
    # seed 717171 is not enough: message ids run msg-000..msg-029 and subjects come
    # from a fixed list, so a different draw reproduces a listing by chance. Measured
    # on a 600-example corpus: **2 of 150** evaluation listings recurred, both with
    # the same verdict — small enough to sit inside the gate's noise, and cheap
    # enough to remove outright [ran] 2026-09-15.
    held_out = {listing(m) for m in generate(150, EVAL_SEED)["messages"]}

    rng = random.Random(args.seed)
    rows, seeds_used, no_call, skipped = [], set(), 0, 0
    for i in range(args.n):
        if i % 5 == 0:
            s = rng.randrange(10 ** 6)
            while s == EVAL_SEED:
                s = rng.randrange(10 ** 6)
            seeds_used.add(s)
            inbox = generate(30, s)
        msg = rng.choice(inbox["messages"])
        if listing(msg) in held_out:
            skipped += 1
            continue
        calls = chain_for(inbox, msg)
        no_call += not calls
        lines = []
        for tool, body in calls:
            lines.append(f"<{tool}>{body}</{tool}>= {answer(inbox, tool, body)}")
        lines.append("IMPORTANT" if msg["_truth"] else "NOT IMPORTANT")
        rows.append({"case_id": f"ef-{i:04d}", "truth": msg["_truth"],
                     "automated": msg["_facts"]["automated"], "calls": len(calls),
                     "messages": [{"role": "system", "content": SYSTEM},
                                  {"role": "user",
                                   "content": f"{listing(msg)}\n\n{INSTRUCTION}"},
                                  {"role": "assistant", "content": "\n".join(lines)}]})

    assert EVAL_SEED not in seeds_used, "the corpus drew the evaluation's inbox"
    # A CORPUS THAT IS MOSTLY ONE ANSWER TEACHES THAT ANSWER. The base already
    # replies NOT IMPORTANT to everything [ran] P31, so a lopsided corpus would
    # reinforce exactly the failure this adapter exists to fix.
    share = sum(r["truth"] for r in rows) / len(rows)
    assert 0.3 <= share <= 0.7, f"the corpus is {share:.0%} important — too lopsided"

    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(json.dumps({
        "written": len(rows), "path": str(p),
        "important_share": round(share, 3),
        "examples_answered_without_asking": no_call,
        "distinct_inboxes": len(seeds_used),
        "drew_the_evaluation_inbox": False,
        "listings_skipped_because_the_run_will_be_scored_on_them": skipped,
        "calls_per_example": round(sum(r["calls"] for r in rows) / len(rows), 2),
        "by_calls": dict(Counter(r["calls"] for r in rows)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
