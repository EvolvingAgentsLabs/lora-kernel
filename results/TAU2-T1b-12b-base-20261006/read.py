"""T1b's verdict (BRIEF.md), read from the records — the runner's own gate keys VOID on τ²'s label, which T1's decision
(reading 1) overruled for empty first replies. Pass^1 per task = mean reward over k trials, an empty first reply (τ²'s
`AssistantMessage must have either content or tool_calls`) scored 0 as the agent's own failure; any OTHER
infrastructure/unexpected error over 5 % of an arm's simulations VOIDs that arm. Paired over tasks:
Δ = mean_t (p_A(t) − p_B(t)), 95 % CI by bootstrap over tasks (10,000, seed 0) — T1's computation.

    python results/TAU2-T1b-12b-base-20261006/read.py
"""
import base64, collections, gzip, json, random, sys
from pathlib import Path

HERE = Path(__file__).parent
T1 = HERE.parent / "TAU2-T1-baselines-20261005" / "t1.json"
EMPTY = "AssistantMessage must have either content or tool_calls"


def arm(rec: dict, name: str) -> dict:
    a = rec["arms"][name]
    raw = json.loads(gzip.decompress(base64.b64decode(a["tau2_raw"])))
    per, empty, other = collections.defaultdict(list), 0, 0
    for s in raw["simulations"]:
        why = s.get("termination_reason")
        r = (s.get("reward_info") or {}).get("reward")
        if why in ("infrastructure_error", "unexpected_error"):
            if EMPTY in str((s.get("info") or {}).get("error", "")):
                empty += 1
            else:
                other += 1
            r = 0.0
        per[str(s["task_id"])].append(float(r or 0.0))
    n = sum(len(v) for v in per.values())
    return {"p": {t: sum(v) / len(v) for t, v in per.items()}, "n": n, "empty_first_reply": empty, "other_errors": other,
            "void": other > 0.05 * n, "pass1": round(sum(sum(v) for v in per.values()) / n, 4)}


def gap(x: dict, y: dict) -> dict:
    tasks = sorted(set(x["p"]) & set(y["p"]))
    d = [x["p"][t] - y["p"][t] for t in tasks]
    m = sum(d) / len(d)
    random.seed(0)
    bs = sorted(sum(random.choice(d) for _ in d) / len(d) for _ in range(10000))
    return {"delta_pp": round(100 * m, 1), "ci_pp": [round(100 * bs[250], 1), round(100 * bs[9750], 1)],
            "wins": f"{sum(v > 0 for v in d)}:{sum(v < 0 for v in d)}", "tasks": len(tasks)}


def main() -> int:
    t1, t1b = json.loads(T1.read_text()), json.loads((HERE / "t1.json").read_text())
    if not t1b["arms"].get("base", {}).get("complete"):
        print("INCOMPLETE: the 12B arm is not complete"); return 1
    e4b, b31, b12 = arm(t1, "base"), arm(t1, "teacher"), arm(t1b, "base")
    out = {"pass1": {"31B": b31["pass1"], "12B": b12["pass1"], "E4B": e4b["pass1"]},
           "errors": {k: {"empty_first_reply": v["empty_first_reply"], "other": v["other_errors"]}
                      for k, v in (("31B", b31), ("12B", b12), ("E4B", e4b))},
           "12B_vs_E4B": gap(b12, e4b), "31B_vs_12B": gap(b31, b12)}
    g = out["12B_vs_E4B"]
    if b12["void"]:
        out["decision"] = f"VOID: the 12B arm has {b12['other_errors']} non-empty-reply errors (> 5 %)"
    elif g["delta_pp"] >= 15 and g["ci_pp"][0] > 0:
        out["decision"] = "12B IS THE STUDENT"
    else:
        out["decision"] = "E4B STAYS THE STUDENT"
    h = out["31B_vs_12B"]
    out["teacher_headroom_over_12B"] = "yes" if h["delta_pp"] >= 15 and h["ci_pp"][0] > 0 else "no"
    (HERE / "verdict.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
