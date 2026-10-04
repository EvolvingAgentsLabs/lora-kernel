"""EDIT0's verdict, as the brief fixed it. Zero GPU.   PYTHONPATH=. python results/EDIT0-edit-without-retraining-20261004/read.py"""
import json
import re
from pathlib import Path

R = Path("results/EDIT0-edit-without-retraining-20261004")
rows = {json.loads(l)["case_id"]: json.loads(l) for l in open(R / "questions_edit.jsonl")}
a = json.load(open(R / "edit0.json"))["arms"]["withlib-s0+page+top8"]
right = sum(bool(a[i]["credit"]) for i in rows if i in a and "error" not in a[i])
stale_rows = []
for i, r in rows.items():
    x = a.get(i, {})
    line = (x.get("final") or "").strip().splitlines()[-1] if (x.get("final") or "").strip() else ""
    nums = set(re.findall(r"\d+", re.sub(r"\[[a-z0-9]{3}§[^\]]*\]", " ", line)))
    if nums & set(r["stale"]):
        stale_rows.append(i)
lost = [i for i in rows if i not in a or "error" in a[i]]
reading = ("VOID" if lost else "EDITS HOLD" if right >= 16 and len(stale_rows) <= 1 else
           "STALE" if len(stale_rows) >= 2 else "NEITHER")
out = {"reading": reading, "right_new_value": f"{right}/{len(rows)}", "stale": stale_rows, "lost": lost,
       "misses": {i: (a[i].get("state"), (a[i].get("final") or "")[-120:]) for i in rows if i in a and not a[i]["credit"]}}
print(json.dumps(out, indent=1))
json.dump(out, open(R / "verdict.json", "w"), indent=1)
