"""Does dimensional consistency mark the edge of a specialist's region?

The rule was fixed in `results/P22-dimensions-20260912/BRIEF.md` before anything was
scored: a chain is flagged when the dimension its final step produces is not the one
the problem asked for. No threshold, no per-family exceptions, no second signal
folded in.

Two numbers decide it, and both were named in advance:

  separation   in-region against out-of-region, where chance is 0.60
  false alarm  how often it fires on in-region work that is CORRECT — a guard that
               flags good chains will be switched off whatever its headline says

    python3 -m training.harness.boundary
"""

from __future__ import annotations

import json
from pathlib import Path

from training.physics.dimensions import check
from training.physics.generate import HELD_OUT_FAMILIES, TRAIN_FAMILIES, generate

SOURCES = [("results/P13-sequential-20260910/sequential_results.json", False),
           ("results/P14-held-out-20260910/sequential_results_heldout.json", True)]


def rows():
    for path, outside in SOURCES:
        p = Path(path)
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        fams = HELD_OUT_FAMILIES if outside else TRAIN_FAMILIES
        cases = {c["case_id"]: c
                 for c in generate(30, 515151, fams, style="working")}
        for arm, v in d["arms"].items():
            for r in v["records"]:
                c = cases.get(r["case_id"])
                if c is None or not r.get("raw"):
                    continue
                yield {"arm": arm.split("·")[0].strip(), "outside": outside,
                       "passed": bool(r["passed"]), "unit": c["unit"],
                       "statement": c["prompt"].split("\n\n")[0], "chain": r["raw"]}


def main() -> int:
    data = list(rows())
    for r in data:
        v = check(r["chain"], r["unit"], r["statement"])
        r["verdict"] = v
        r["flagged"] = v.consistent is False

    inside = [r for r in data if not r["outside"]]
    outside = [r for r in data if r["outside"]]
    no_opinion = sum(r["verdict"].consistent is None for r in data)

    hits = sum(not r["flagged"] for r in inside) + sum(r["flagged"] for r in outside)
    sep = hits / len(data)
    chance = max(len(inside), len(outside)) / len(data)
    good_inside = [r for r in inside if r["passed"]]
    false_alarm = sum(r["flagged"] for r in good_inside) / max(len(good_inside), 1)

    print(f"{'group':<28}{'n':>5}{'flagged':>10}{'rate':>8}")
    for name, group in (("in region", inside), ("outside the region", outside),
                        ("in region AND correct", good_inside)):
        f = sum(r["flagged"] for r in group)
        print(f"{name:<28}{len(group):>5}{f:>10}{f/max(len(group),1):>8.2f}")

    # A DETECTOR THAT ABSTAINS HAS TWO NUMBERS, NOT ONE. Counting "no opinion" as
    # "not flagged" credits it for in-region chains it never judged and penalises it
    # for out-of-region ones it declined. Coverage and conditional accuracy are
    # reported beside the headline so neither hides in it.
    opinionated = [r for r in data if r["verdict"].consistent is not None]
    o_in = [r for r in opinionated if not r["outside"]]
    o_out = [r for r in opinionated if r["outside"]]
    cov = len(opinionated) / len(data)
    cond = ((sum(not r["flagged"] for r in o_in) + sum(r["flagged"] for r in o_out))
            / max(len(opinionated), 1))
    o_good = [r for r in o_in if r["passed"]]
    cond_alarm = sum(r["flagged"] for r in o_good) / max(len(o_good), 1)

    print(f"\nseparation {sep:.2f} against a chance line of {chance:.2f}")
    print(f"  counting only the {len(opinionated)} chains it had an opinion on "
          f"(coverage {cov:.2f}): {cond:.2f}, false alarm {cond_alarm:.2f}")
    print(f"false alarm on correct in-region work: {false_alarm:.2f}")
    print(f"chains the checker could not type at all: {no_opinion}/{len(data)}")
    print("\nA guard that flags correct chains will be switched off whatever its "
          "headline says, so the second number is not a footnote.")

    Path("results/P22-dimensions-20260912/boundary.json").write_text(json.dumps({
        "separation": round(sep, 4), "chance": round(chance, 4),
        "false_alarm_on_correct_in_region": round(false_alarm, 4),
        "no_opinion": no_opinion, "n": len(data),
        "coverage": round(cov, 4), "conditional_separation": round(cond, 4),
        "conditional_false_alarm": round(cond_alarm, 4),
        "by_group": {name: {"n": len(g), "flagged": sum(r["flagged"] for r in g)}
                     for name, g in (("in", inside), ("out", outside),
                                     ("in_correct", good_inside))},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
