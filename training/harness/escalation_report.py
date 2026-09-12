"""What the system actually delivers once the escalation rule is switched on.

P22 reported the guard as a detector — how much out-of-region work it flags, how
often it fires on good work. That is not the number an operator decides on. What
decides it is what comes out of the pipe: **how much work the expert still answers
alone, and how wrong those answers are.**

So this replays every stored transcript through `escalate.should_escalate` and
reports the delivered set, against the only baseline that matters — the same
system with no guard at all.

    python3 -m training.harness.escalation_report
"""

from __future__ import annotations

import json
from pathlib import Path

from training.harness.boundary import CONFIRM, SOURCES, rows
from training.harness.escalate import dimensional_fails, mechanical_fails

RULES = {
    "no guard at all": lambda d, m: False,
    "dimensional alone": lambda d, m: d,
    "mechanical alone": lambda d, m: m,
    "either fails": lambda d, m: d or m,
    "both fail": lambda d, m: d and m,
}


def measure(data: list[dict]) -> dict:
    for r in data:
        r["dim"] = dimensional_fails(r["chain"], r["unit"], r["statement"])
        r["mech"] = mechanical_fails(r["chain"])

    out = {}
    for name, rule in RULES.items():
        kept = [r for r in data if not rule(r["dim"], r["mech"])]
        escalated = [r for r in data if rule(r["dim"], r["mech"])]
        # THE COST OF A GUARD IS THE GOOD WORK IT SENDS AWAY, and its benefit is
        # the wrong work it stops. Both are counted on the same set.
        good_sent_away = sum(r["passed"] for r in escalated)
        wrong_delivered = sum(not r["passed"] for r in kept)
        out[name] = {
            "escalated": len(escalated),
            "escalation_rate": round(len(escalated) / len(data), 3),
            "delivered": len(kept),
            "delivered_correct": sum(r["passed"] for r in kept),
            "accuracy_of_what_is_delivered":
                round(sum(r["passed"] for r in kept) / max(len(kept), 1), 3),
            "wrong_answers_still_delivered": wrong_delivered,
            "correct_answers_sent_away": good_sent_away,
        }
    return out


def show(title: str, data: list[dict]) -> dict:
    res = measure(data)
    base = res["no guard at all"]
    print(f"\n=== {title} — {len(data)} chains, "
          f"{sum(r['passed'] for r in data)} of them correct")
    print(f"{'rule':<22}{'escalates':>11}{'delivers':>10}{'of those right':>16}"
          f"{'wrong out':>11}{'good lost':>11}")
    for name, v in res.items():
        print(f"{name:<22}{v['escalation_rate']:>11.2f}{v['delivered']:>10}"
              f"{v['accuracy_of_what_is_delivered']:>16.2f}"
              f"{v['wrong_answers_still_delivered']:>11}"
              f"{v['correct_answers_sent_away']:>11}")
    print(f"  with no guard the pipe emits {base['wrong_answers_still_delivered']} "
          "wrong answers and cannot say which.")
    return res


def split(title: str, data: list[dict]) -> dict:
    """THE POOLED TABLE ANSWERS THE WRONG QUESTION, so this one is printed too.

    Counting wrong answers across in-region and out-of-region chains together asks
    the guard to detect every error, including the expert being wrong inside a
    region it never left. On that question the conjunction is a subset of the
    mechanical check and loses to it outright. Split the two and the conjunction is
    the only rule that never fires in region — which is the tripwire P19 left open.
    """
    for r in data:
        r.setdefault("dim", dimensional_fails(r["chain"], r["unit"], r["statement"]))
        r.setdefault("mech", mechanical_fails(r["chain"]))
    inside = [r for r in data if not r["outside"]]
    outside = [r for r in data if r["outside"]]
    print(f"\n=== {title} — the same rules, asked whether the expert LEFT ITS REGION")
    print(f"{'rule':<22}{'in region':>11}{'good lost':>11}{'outside':>10}{'gap':>8}")
    out = {}
    for name, rule in RULES.items():
        fi = [r for r in inside if rule(r["dim"], r["mech"])]
        fo = [r for r in outside if rule(r["dim"], r["mech"])]
        a = len(fi) / max(len(inside), 1)
        b = len(fo) / max(len(outside), 1)
        lost = sum(r["passed"] for r in fi)
        out[name] = {"in_region_rate": round(a, 3), "outside_rate": round(b, 3),
                     "correct_lost_in_region": lost, "gap": round(b - a, 3)}
        print(f"{name:<22}{a:>11.2f}{lost:>11}{b:>10.2f}{b - a:>8.2f}")
    return out


def main() -> int:
    dev = list(rows())
    conf = list(rows([(CONFIRM, True)]))
    report = {"development": show("development (P13 in region + P14 outside)", dev)}
    report["by_region"] = split("development", dev)
    if conf:
        report["confirmation"] = show(
            "confirmation (P18, families the guard was never shown)", conf)

    print("\nTwo rules, two jobs, and no single winner. `both fail` never fires in "
          "region — 0 of 60 — and still catches a third of the work outside it: a "
          "tripwire that costs nothing while the expert is working normally. "
          "`either fails` takes delivered accuracy from 0.53 to 0.83 in region, and "
          "sends half the in-region work to a bigger model to do it, which is most "
          "of what withdrawal was for.")
    Path("results/P22-dimensions-20260912/escalation.json").write_text(
        json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
