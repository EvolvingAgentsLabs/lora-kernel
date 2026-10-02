"""GATE0's replay — the gate applied to recorded walks, which is the gated run exactly (the walk does not change). Zero GPU.

    python results/GATE0-cite-gate-20261002/replay.py
"""
import glob
import json
from collections import Counter, defaultdict

from memory.notes import Library
from memory.runtime import Conversation, citation_problem
from training.wiki import grade as gr

R = "results/GATE0-cite-gate-20261002"
FILES = {"REAL3": ("logistics-regs", "results/REAL3-real-corpus-20260930/real3_*.json"),
         "REAL4": ("logistics-regs", "results/REAL4-refusal-20260930/real4.json"),
         "REAL5": ("spcc-regs", "results/REAL5-third-family-20261001/real5.json"),
         "REAL6": ("spcc-regs", "results/REAL6-citation-20261001/real6_real5.json"),
         "REAL7": ("spcc-regs", "results/REAL7-crosslink-20261001/real7_real5.json")}
BESIDE = {"REAL3-attempt1": ("logistics-regs", "results/REAL3-real-corpus-20260930/attempt1_real3_fresh.json")}


def problem(lib, text_of, x):
    line = gr.final_line(x.get("final", ""))
    cited = x.get("cited")
    resolve = (lambda o: cited[0]) if isinstance(cited, list) else (lambda o: None)
    return line, citation_problem(line, resolve, {tuple(s) for s in x.get("opened_statements", [])}, text_of)


def replay(groups):
    tab, by, why = Counter(), defaultdict(Counter), Counter()
    for run, (libname, pat) in groups.items():
        lib = Library.load(f"knowledge/{libname}")
        text_of = lambda nid, a, c=Conversation(lib): c._statement_text(lib[nid], a)
        for f in sorted(glob.glob(pat)):
            rec = json.load(open(f))
            for arm, recs in rec.get("arms", {}).items():
                if "+page" not in arm or not isinstance(recs, dict):
                    continue
                for cid, x in recs.items():
                    if "error" in x:
                        continue
                    none = x.get("family") == "none" or x.get("hops") == 0
                    line, p = problem(lib, text_of, x)
                    right = x.get("state") == "right"
                    k = ("none-" if none else "") + ("right" if right else "not-right") + ("" if line else "-noline")
                    blocked = bool(p) and bool(line)
                    tab[(k, blocked)] += 1
                    by[f"{run}:{f.split('/')[-1]}:{arm}"][(k, blocked)] += 1
                    if blocked:
                        why["does not hold" if "does not hold" in p else "not opened" if "not opened" in p else
                            "never shown" if "never shown" in p else p] += 1
    return tab, by, why


def summary(tab):
    R_ = sum(v for (k, b), v in tab.items() if k == "right")
    Rb = tab[("right", True)]
    N_ = sum(v for (k, b), v in tab.items() if k == "not-right")
    Nb = tab[("not-right", True)]
    return {"right": R_, "right_blocked": Rb, "right_blocked_pct": round(100 * Rb / max(1, R_), 2),
            "not_right_delivered": N_, "not_right_blocked": Nb, "not_right_blocked_pct": round(100 * Nb / max(1, N_), 1),
            "precision_before": round(R_ / max(1, R_ + N_), 3), "precision_after": round((R_ - Rb) / max(1, R_ - Rb + N_ - Nb), 3),
            "none_rows_answered_blocked": tab[("none-not-right", True)], "none_rows_answered": sum(
                v for (k, b), v in tab.items() if k == "none-not-right"),
            "no_line_rows": sum(v for (k, b), v in tab.items() if k.endswith("noline"))}


tab, by, why = replay(FILES)
s = summary(tab)
pct_r, pct_n = s["right_blocked_pct"], s["not_right_blocked_pct"]
s["reading"] = ("GATE COSTS" if pct_r > 1 else "GATE WORKS" if pct_n >= 15 else "GATE IDLE")
s["fires_by_reason"] = dict(why)
s["per_arm"] = {k: summary(v) for k, v in by.items()}
btab, _, _ = replay(BESIDE)
s["beside_attempt1"] = summary(btab)
json.dump(s, open(f"{R}/gate0.json", "w"), indent=1)
print(json.dumps({k: v for k, v in s.items() if k != "per_arm"}, indent=1))
for k, v in s["per_arm"].items():
    print(f"{k:58s} right {v['right']:3d} blocked {v['right_blocked']}  ·  not-right {v['not_right_delivered']:3d} blocked {v['not_right_blocked']:3d}")
