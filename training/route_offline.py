"""Does agreement pick the right expert? Answered from runs already on disk.

THE CLAIM UNDER TEST is the architecture's central one: that acceptance against a
stronger model selects the expert that should answer, for free, inside a pass
already being paid for.

WHY THIS COSTS NOTHING. S4's region arms recorded, for the SAME twenty cases of
each clinic, the answer of the expert trained on that clinic and the answer of
the expert trained on the other one — and `adapter_val` recorded the all-clinics
adapter's answer on those same cases. Three answers per case, all persisted. The
routing question is a computation over them, not an experiment to buy.

WHAT STANDS IN FOR THE TARGET, AND WHAT THAT COSTS THE CLAIM. The all-clinics
adapter is the reference here, not a frontier model — S1 established there is no
frontier advantage to distil on this task. So this measures **the mechanism**:
whether agreement with a stronger reference picks the better expert. It does not
measure distillation, and it must not be reported as though it did.

    python3 -m training.route_offline
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from training.evaluate import parse_answer

RESULTS = Path("results/S4-qwen35-2b-20260908/s4_results.json")


def agree(a: str, b: str) -> float | None:
    """F1 between two parsed answers — the promotion criterion from §11."""
    x, y = parse_answer(a), parse_answer(b)
    if x is None or y is None:
        return None
    if not x and not y:
        return 1.0
    tp = len(x & y)
    p = tp / len(x) if x else 0.0
    r = tp / len(y) if y else 0.0
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def main() -> int:
    d = json.loads(RESULTS.read_text())
    reference = {r["case_id"]: r["raw"] for r in d["adapter_val"]["records"]}
    regions = d["regions"]

    rows = []
    for clinic, own_key, other_key, other_name in (
            ("alpha", "alpha_on_own", "beta_on_other", "beta"),
            ("beta", "beta_on_own", "alpha_on_other", "alpha")):
        own = {r["case_id"]: r for r in regions[own_key]["records"]}
        other = {r["case_id"]: r for r in regions[other_key]["records"]}
        for cid in sorted(set(own) & set(other) & set(reference)):
            rows.append({
                "case_id": cid, "clinic": clinic,
                "right_expert": clinic, "other_expert": other_name,
                "own_correct": own[cid]["passed"], "other_correct": other[cid]["passed"],
                "own_agreement": agree(own[cid]["raw"], reference[cid]),
                "other_agreement": agree(other[cid]["raw"], reference[cid]),
            })

    usable = [r for r in rows if r["own_agreement"] is not None
              and r["other_agreement"] is not None]

    # A case only tests routing when the two experts DISAGREE about it. Where both
    # are right or both are wrong, any router scores the same and counting those
    # inflates every routing scheme equally — including a coin.
    decisive = [r for r in usable if r["own_correct"] != r["other_correct"]]
    picked_right = sum(
        1 for r in decisive
        if (r["own_agreement"] > r["other_agreement"]) == bool(r["own_correct"])
        and r["own_agreement"] != r["other_agreement"])
    ties = sum(1 for r in decisive if r["own_agreement"] == r["other_agreement"])

    # The ceilings and floors this has to sit between.
    oracle = sum(1 for r in usable if r["own_correct"] or r["other_correct"])
    always_own = sum(1 for r in usable if r["own_correct"])
    always_other = sum(1 for r in usable if r["other_correct"])
    routed = sum(
        1 for r in usable
        if (r["own_correct"] if r["own_agreement"] >= r["other_agreement"]
            else r["other_correct"]))

    n = len(usable)
    out = {
        "n_cases": n, "unusable": len(rows) - n,
        "decisive_cases": len(decisive), "ties_among_decisive": ties,
        "routed_correct_on_decisive": picked_right,
        "accuracy": {
            "oracle (best expert per case)": round(oracle / n, 3),
            "routed by agreement": round(routed / n, 3),
            "always the region's own expert": round(always_own / n, 3),
            "always the other expert": round(always_other / n, 3),
        },
        "reference": "all-clinics adapter — NOT a frontier target (S1)",
    }
    print(json.dumps(out, indent=2))
    print()
    if len(decisive) - ties:
        print(f"On the {len(decisive) - ties} cases where the two experts disagree "
              f"and agreement is not tied, agreement picked the correct expert "
              f"{picked_right} times "
              f"({picked_right / (len(decisive) - ties):.1%}).")
    print("A router is only worth its complexity if it beats BOTH constant "
          "policies above, and the gap to the oracle is what it left on the table.")
    Path("results/S4-qwen35-2b-20260908/routing_offline.json").write_text(
        json.dumps({**out, "rows": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
