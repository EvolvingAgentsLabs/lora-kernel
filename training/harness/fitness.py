"""Four ways to combine two judges, and the one a tournament should use.

P19 measured a fitness that selects for failing quietly: the model judge accepts
**41% of wrong work that looks clean** and only 7% of wrong work that shows an
error, so a variant whose failures are invisible outranks one that is more often
right [ran] `results/P19-tournament-20260911/`.

Subtracting the tool layer's rejections is the obvious fix and it is backwards —
it penalises the arm that shows its failures, which is the better one. What is
needed separates *clean because correct* from *clean because it never tried*, and
the procedural check does exactly that: it asks whether a chain's answer follows
from its own arithmetic and is indifferent to how the chain looks.

FOUR COMBINATIONS, AND THERE IS NO FIFTH. All four are reported. Choosing among
them by which orders the pairs correctly would be the failure this module exists
to fix, so the list is fixed in the brief before any of them was scored.

    python3 -m training.harness.fitness
"""

from __future__ import annotations

import argparse
import json
from itertools import combinations
from pathlib import Path

from training.harness.judges import judge_procedural
from training.harness.tournament import VERDICTS, candidates

COMBOS = {
    "model judge alone": lambda m, p: m,
    "procedural alone": lambda m, p: p,
    "both must accept": lambda m, p: m and p,
    "either may accept": lambda m, p: m or p,
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="results/P20-fitness-20260911/fitness.json")
    args = ap.parse_args()

    cache = json.loads(VERDICTS.read_text())
    cands = candidates()
    for c in cands:
        key = f"{c['pool']}::{c['name']}"
        for r in c["records"]:
            r["_model"] = cache.get(f"{key}::{r['case_id']}")
            r["_proc"] = judge_procedural({"chain": r["raw"]})

    rows = []
    for name, fn in COMBOS.items():
        for c in cands:
            seen = [fn(r["_model"], r["_proc"]) for r in c["records"]
                    if r["_model"] is not None]
            c[name] = sum(bool(v) for v in seen) / len(seen) if seen else 0.0
        agree = total = 0
        detail = []
        for a, b in combinations(cands, 2):
            if a["pool"] != b["pool"] or a["true_accuracy"] == b["true_accuracy"]:
                continue
            # ONE PAIR IS A SINGLE PROBLEM IN TWENTY AND IS COUNTED SEPARATELY.
            # 0.05 against 0.00 is one case, and a judge that is 82% accurate per
            # item cannot be asked to resolve it. Reporting it inside the headline
            # would make a coin toss look like a failure or a success.
            meaningful = abs(a["true_accuracy"] - b["true_accuracy"]) >= 0.10
            better = a if a["true_accuracy"] > b["true_accuracy"] else b
            pick = a if a[name] > b[name] else b
            if meaningful:
                total += 1
                agree += pick is better
            detail.append({"pool": a["pool"], "a": a["name"], "b": b["name"],
                           "gap": round(abs(a["true_accuracy"] - b["true_accuracy"]), 3),
                           "meaningful": meaningful, "oracle": better["name"],
                           "picked": pick["name"], "right": pick is better})
        rows.append({"fitness": name, "pairs": total, "agree": agree,
                     "detail": detail,
                     "scores": {f"{c['pool']} · {c['name']}": round(c[name], 3)
                                for c in cands}})

    print(f"{'candidate':<46}{'true':>7}" +
          "".join(f"{n.split()[0]:>12}" for n in COMBOS))
    for c in sorted(cands, key=lambda c: (c["pool"], -c["true_accuracy"])):
        print(f"{c['pool'] + ' · ' + c['name']:<46}{c['true_accuracy']:>7.3f}" +
              "".join(f"{c[n]:>12.3f}" for n in COMBOS))

    print(f"\n{'fitness':<24}{'pairs with a real gap ordered right':>38}")
    for r in rows:
        print(f"{r['fitness']:<24}{str(r['agree']) + '/' + str(r['pairs']):>38}")
    ignored = [d for d in rows[0]["detail"] if not d["meaningful"]]
    if ignored:
        print(f"\n{len(ignored)} pair(s) excluded for a gap under 0.10: " +
              ", ".join(f"{d['a']} vs {d['b']} ({d['gap']})" for d in ignored))
    print("\nTwo pairs is not a tournament. What this can show is whether the "
          "mechanism P19 found — false acceptance of clean wrong work — is closed "
          "by asking the chain's own arithmetic to agree.")
    Path(args.out).write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
