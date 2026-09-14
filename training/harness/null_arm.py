"""Before training anything for a new deployment: can the base do the job at all?

WHY THIS RUNS FIRST. CLAUDE.md's first measurement rule is that if the baseline
already sits at the ceiling, every arm ties and the tie reads as success — and the
mirror of it is just as expensive: if the baseline sits at the floor, no adapter
placed on top of it can move anything either. Both are one control arm away, and it
is the cheapest thing this project ever runs.

Applied to an agent runtime, the question has two halves and neither needs a GPU
beyond the base model already being served:

    IS THERE A REGION?      does the traffic concentrate in a few repeated shapes,
                            or is it a long tail? The architecture's whole claim is
                            "a small expert beats a generalist INSIDE its region" —
                            with no region there is nothing to be expert in.

    CAN THE BASE SPEAK?     how often does the base model alone emit a well-formed
                            tool call? If it cannot, an adapter on top will not fix
                            it, and we learn that in a day instead of after training.

    python3 -m training.harness.null_arm --log traffic.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from training.harness.tool_calls import to_tool_calls

# A request's shape: which tools were offered and how many turns it had. Two
# requests with the same tools and a similar depth are doing the same kind of work.
def shape(row: dict) -> str:
    tools = ",".join(sorted(row.get("tools") or [])) or "(none)"
    turns = row.get("turns") or 0
    depth = "single" if turns <= 2 else "short" if turns <= 6 else "long"
    return f"{tools} · {depth}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log", required=True, help="written by openai_proxy --log")
    ap.add_argument("--region-bar", type=float, default=0.60,
                    help="share of traffic the top shapes must cover for a region "
                         "to be worth building an expert for")
    args = ap.parse_args()

    rows = [json.loads(l) for l in Path(args.log).read_text().splitlines() if l.strip()]
    if not rows:
        print("the log is empty; there is nothing to measure")
        return 1

    print(f"requests: {len(rows)}\n")

    # --- IS THERE A REGION? ---------------------------------------------------
    shapes = Counter(shape(r) for r in rows)
    top = shapes.most_common(3)
    covered = sum(n for _, n in top) / len(rows)
    print("the three commonest shapes:")
    for s, n in top:
        print(f"  {n:>5}  {n/len(rows):>6.1%}  {s}")
    print(f"\nthey cover {covered:.1%} of traffic, against a bar of {args.region_bar:.0%}")
    if covered < args.region_bar:
        print("  NO REGION. This is a long tail, and a pool of specialists has\n"
              "  nothing to specialise in. The honest recommendation is a generalist.")
    else:
        print("  A REGION EXISTS. An expert for the commonest shape is worth costing.")

    # --- CAN THE BASE SPEAK THE PROTOCOL? -------------------------------------
    offered = [r for r in rows if r.get("tools")]
    if not offered:
        print("\nno request offered tools; the protocol question does not arise here")
        return 0
    well_formed = sum(bool(to_tool_calls(r.get("reply") or "")) for r in offered)
    named = Counter()
    for r in offered:
        for tc in to_tool_calls(r.get("reply") or ""):
            named[tc["function"]["name"]] += 1
    # A CALL FOR A TOOL NOBODY OFFERED IS NOT A CALL. It is the model inventing a
    # name, which is the failure P25 measured at 56% of refusals on a new subject.
    invented = sum(n for t, n in named.items()
                   if not any(t in (r.get("tools") or []) for r in offered))

    print(f"\nrequests that offered tools: {len(offered)}")
    print(f"  replies carrying a well-formed call: {well_formed} = "
          f"{well_formed/len(offered):.1%}")
    print(f"  calls naming a tool nobody offered:  {invented}")
    print("\nIf the first number is near zero the base cannot hold the protocol, and\n"
          "an adapter over it is not the next purchase — a different base is.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
