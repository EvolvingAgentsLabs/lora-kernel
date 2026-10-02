"""CITE0's verdict, mechanically, as the brief fixed it (written before the run). Zero GPU.

    python results/CITE0-runtime-check-20261002/read.py [cite0.json]
"""
import json
import math
import sys
from collections import Counter

R = "results/CITE0-runtime-check-20261002"
BASE, TREAT = "withlib-s0+page", "withlib-s0+page+check"


def sign_p(a: int, b: int) -> float:
    n, k = a + b, min(a, b)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


rec = json.load(open(sys.argv[1] if len(sys.argv) > 1 else f"{R}/cite0.json"))
rows = {json.loads(l)["case_id"]: json.loads(l) for l in open(f"{R}/questions.jsonl")}
b, t = rec["arms"][BASE], rec["arms"][TREAT]
ok = lambda x: "error" not in x
lost = [i for i in rows if i not in b or i not in t or not ok(b[i]) or not ok(t[i])]
fired = {i: x for i, x in t.items() if ok(x) and x.get("pre_check")}
conv = [i for i, x in fired.items() if x["pre_check"]["state"] != "right" and x["state"] == "right"]
broke = [i for i, x in fired.items() if x["pre_check"]["state"] == "right" and x["state"] != "right"]
why = Counter(x["pre_check"]["line"] and x.get("text", "").split("= ERROR: citation — ")[-1].split(";")[0].split(" ")[0]
              for x in fired.values())
keep = [i for i in rows if i not in lost]
wins = sum(t[i]["credit"] and not b[i]["credit"] for i in keep)
losses = sum(b[i]["credit"] and not t[i]["credit"] for i in keep)
none = [i for i in keep if rows[i]["check"]["kind"] == "none"]
head = [i for i in keep if rows[i]["hops"] >= 2]
one = [i for i in keep if rows[i]["hops"] == 1]
cnt = lambda arm, ids: sum(bool(arm[i]["credit"]) for i in ids)
p_within, p_arms = sign_p(len(conv), len(broke)), sign_p(wins, losses)
arm_loss = losses > wins and p_arms < 0.05
refusals_drop = cnt(b, none) - cnt(t, none)
if len(lost) > 3:
    reading = f"VOID: {len(lost)} rows lost to transport"
elif len(fired) < 5:
    reading = f"NOT ENOUGH FIRES ({len(fired)})"
elif len(conv) > len(broke) and p_within < 0.05 and not arm_loss and refusals_drop <= 1:
    reading = "CHECK WORKS"
elif len(conv) > len(broke):
    reading = "CHECK HELPS"
else:
    reading = "FALSIFIED"
out = {"reading": reading, "fired": len(fired), "fired_by_reason": dict(why), "converted": len(conv), "broken": len(broke),
       "within_p": round(p_within, 4), "arms_paired": f"{wins}:{losses}", "arms_p": round(p_arms, 4),
       "all": {BASE: f"{cnt(b, keep)}/{len(keep)}", TREAT: f"{cnt(t, keep)}/{len(keep)}"},
       "headline": {BASE: f"{cnt(b, head)}/{len(head)}", TREAT: f"{cnt(t, head)}/{len(head)}"},
       "one_hop": {BASE: f"{cnt(b, one)}/{len(one)}", TREAT: f"{cnt(t, one)}/{len(one)}"},
       "refusals": {BASE: f"{cnt(b, none)}/{len(none)}", TREAT: f"{cnt(t, none)}/{len(none)}"},
       "lost": lost, "converted_ids": conv, "broken_ids": broke}
print(json.dumps(out, indent=1))
json.dump(out, open(f"{R}/verdict.json", "w"), indent=1)
