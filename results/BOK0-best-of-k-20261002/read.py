"""BOK0's verdict, as the brief fixed it (written before the run). Zero GPU.

    python results/BOK0-best-of-k-20261002/read.py
"""
import json
import math
from pathlib import Path

R = Path("results/BOK0-best-of-k-20261002")
ARM = "withlib-s0+page+k4"


def sign_p(a, b):
    n, k = a + b, min(a, b)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


out, tot = {}, {"gain": 0, "new_wrong": 0, "resampled": 0, "extra_walks": 0, "right_before": 0, "right_after": 0,
                "delivered_before": 0, "delivered_after": 0, "lost": 0}
for name in ("cite0", "real4"):
    f = R / f"bok0_{name}.json"
    if not f.exists():
        continue
    recs = json.load(open(f))["arms"].get(ARM, {})
    s = {k: 0 for k in tot}
    for cid, x in recs.items():
        if "error" in x or "bok" not in x:
            s["lost"] += 1
            continue
        w, sel = x["bok"]["walks"], x["bok"]["selected"]
        w1_delivered = w[0]["gated"] is None
        s["right_before"] += w1_delivered and w[0]["state"] == "right"
        s["delivered_before"] += w1_delivered
        s["delivered_after"] += sel is not None
        s["right_after"] += sel is not None and w[sel]["state"] == "right"
        if len(w) > 1:
            s["resampled"] += 1
            s["extra_walks"] += len(w) - 1
            if sel is not None and w[sel]["state"] == "right":
                s["gain"] += 1
            elif sel is not None:
                s["new_wrong"] += 1
    out[name] = s
    for k in tot:
        tot[k] += s[k]
p = sign_p(tot["gain"], tot["new_wrong"])
if tot["resampled"] < 5:
    reading = f"NOT ENOUGH RESAMPLES ({tot['resampled']})"
elif tot["gain"] > tot["new_wrong"] and p < 0.05 and tot["gain"] >= 5:
    reading = "BOK WORKS"
elif tot["gain"] > tot["new_wrong"]:
    reading = "BOK HELPS"
else:
    reading = "FALSIFIED"
res = {"reading": reading, "sign_p": round(p, 4), "pooled": tot, "per_set": out}
print(json.dumps(res, indent=1))
json.dump(res, open(R / "verdict.json", "w"), indent=1)
