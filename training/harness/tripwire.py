"""Does the tool layer's behaviour mark a region's edge that the prose does not?

The six signals are fixed in `results/P16-tripwire-20260910/BRIEF.md` and every
one of them is reported. A signal that separates on only one arm does not count,
and anything that does separate is a hypothesis for families neither P13 nor P14
used — not a detector. Fifty points is not a detector.

    python3 -m training.harness.tripwire
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from training.physics.repair import STEP, TAGS, repair

IN = Path("results/P13-sequential-20260910/sequential_results.json")
OUT = Path("results/P14-held-out-20260910/sequential_results_heldout.json")
CONFIRM = Path("results/P18-confirm-20260910/sequential_results_confirm.json")
SIGNALS = ("calls", "rejected", "rejection_rate", "steps", "no_chain", "chars")

# THE CUT FROM P16, WRITTEN DOWN SO IT CANNOT BE REFITTED. Rejection rate above
# this means "outside the region". It was chosen on P13 and P14's fifty problems
# and it is applied to P18's families unchanged — refitting it there would make the
# confirmation the same measurement again, with a new coat of paint.
P16_CUT = 0.50
P16_SIGNAL = "rejection_rate"


def features(rec: dict) -> dict:
    raw = rec.get("raw", "")
    calls = rec.get("tool_calls", 0)
    rejected = rec.get("steps_rejected", 0) or raw.count("= ERROR")
    value, ok, _ = repair(raw)
    return {"calls": calls, "rejected": rejected,
            "rejection_rate": rejected / calls if calls else 0.0,
            "steps": len(list(STEP.finditer(TAGS.sub("", raw)))),
            "no_chain": 1.0 if value is None else 0.0,
            "chars": len(raw)}


def best_threshold(inside: list[float], outside: list[float]) -> tuple[float, float, str]:
    """The single cut that classifies most cases, and which side is 'outside'."""
    best = (0.0, 0.0, ">")
    for direction in (">", "<"):
        for t in sorted(set(inside + outside)):
            if direction == ">":
                hit = sum(v <= t for v in inside) + sum(v > t for v in outside)
            else:
                hit = sum(v >= t for v in inside) + sum(v < t for v in outside)
            acc = hit / (len(inside) + len(outside))
            if acc > best[1]:
                best = (t, acc, direction)
    return best


def main() -> int:
    din, dout = json.loads(IN.read_text()), json.loads(OUT.read_text())
    arms = [k for k in din["arms"] if k in dout["arms"]]
    print(f"arms compared: {arms}\n")

    table: dict[str, dict[str, tuple]] = {}
    for arm in arms:
        ins = [features(r) for r in din["arms"][arm]["records"]]
        outs = [features(r) for r in dout["arms"][arm]["records"]]
        print(f"=== {arm}  (in {len(ins)}, out {len(outs)})")
        print(f"{'signal':<18}{'in mean':>10}{'out mean':>10}{'cut':>10}"
              f"{'accuracy':>10}")
        for s in SIGNALS:
            a = [f[s] for f in ins]
            b = [f[s] for f in outs]
            t, acc, d = best_threshold(a, b)
            table.setdefault(s, {})[arm] = (sum(a) / len(a), sum(b) / len(b), t, acc, d)
            print(f"{s:<18}{sum(a)/len(a):>10.2f}{sum(b)/len(b):>10.2f}"
                  f"{d + format(t, '.2f'):>10}{acc:>10.2f}")
        print()

    print("=== which signals separate on BOTH arms (the only ones that count)")
    for s in SIGNALS:
        accs = [table[s][arm][3] for arm in arms]
        verdict = "both" if min(accs) >= 0.75 else ("one arm only" if max(accs) >= 0.75
                                                    else "neither")
        print(f"{s:<18}{'  '.join(f'{a:.2f}' for a in accs):<14}{verdict}")
    print("\nA signal that separates on one arm is a coincidence with a number "
          "attached. Anything that separates on both is a hypothesis for families "
          "neither run used, and 50 points is not a detector.")
    if CONFIRM.exists():
        conf = json.loads(CONFIRM.read_text())
        print("\n=== confirmation on families no earlier run used, "
              f"cut fixed at {P16_SIGNAL} > {P16_CUT}")
        for arm in conf["arms"]:
            if arm not in din["arms"]:
                continue
            ins = [features(r)[P16_SIGNAL] for r in din["arms"][arm]["records"]]
            new = [features(r)[P16_SIGNAL] for r in conf["arms"][arm]["records"]]
            hit = sum(v <= P16_CUT for v in ins) + sum(v > P16_CUT for v in new)
            acc = hit / (len(ins) + len(new))
            print(f"{arm:<46}in {sum(ins)/len(ins):.2f}  new {sum(new)/len(new):.2f}"
                  f"  accuracy {acc:.2f}  (n={len(ins)}+{len(new)})")
        print("P16 measured 0.86 with the cut fitted on the same data. Anything "
              "near that here, with the cut fixed, is a detector; well below it "
              "means P16 found a property of two families rather than of a region.")

    Path("results/P16-tripwire-20260910/tripwire.json").write_text(
        json.dumps({"arms": arms, "signals": {s: {k: list(v) for k, v in table[s].items()}
                                              for s in SIGNALS}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
