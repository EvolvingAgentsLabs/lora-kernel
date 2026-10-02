"""PAGE0's verdict, as the brief fixed it (written before the run). Zero GPU.

    PYTHONPATH=. python results/PAGE0-page-top-20261002/read.py
"""
import json
import math
from pathlib import Path

from memory.notes import Library
from memory.runtime import Conversation

R = Path("results/PAGE0-page-top-20261002")
BASE, TREAT = "withlib-s0+page", "withlib-s0+page+top8"


def sign_p(a, b):
    n, k = a + b, min(a, b)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


lib = Library.load("knowledge/hazwaste-regs")
rows = {json.loads(l)["case_id"]: json.loads(l) for l in open(R / "questions.jsonl")}
rec = json.load(open(R / "page0.json"))
b, t = rec["arms"][BASE], rec["arms"][TREAT]
ok = lambda x: "error" not in x
lost = [i for i in rows if i not in b or i not in t or not ok(b[i]) or not ok(t[i])]
keep = [i for i in rows if i not in lost]
ans = [i for i in keep if rows[i]["check"]["kind"] != "none"]
none = [i for i in keep if rows[i]["check"]["kind"] == "none"]
wins = sum(bool(t[i]["credit"]) and not b[i]["credit"] for i in ans)
losses = sum(bool(b[i]["credit"]) and not t[i]["credit"] for i in ans)
p = sign_p(wins, losses)
cnt = lambda arm, ids: sum(bool(arm[i]["credit"]) for i in ids)


def same_page_wrong(arm):
    return sum(1 for i in ans if not arm[i]["credit"] and isinstance(arm[i].get("cited"), list)
               and arm[i]["cited"][0] == rows[i]["support"][0])


hidden = 0
for i in ans:
    q = rows[i]
    conv = Conversation(lib, page_text=True, page_top=8, first_query=q["question"])
    need = [(s[1], s[2]) for s in q["plan"] if s[0] == "open" and len(s) == 3]
    hidden += any(a not in conv._page_selection(lib[pg]) for pg, a in need)
refusal_drop = cnt(b, none) - cnt(t, none)
if len(lost) > 3:
    reading = f"VOID: {len(lost)} rows lost to transport"
elif wins > losses and p < 0.05 and refusal_drop <= 1:
    reading = "PAGE TOP WORKS"
elif wins > losses:
    reading = "PAGE TOP HELPS"
else:
    reading = "FALSIFIED"
multi = [i for i in ans if rows[i]["hops"] > 1]
one = [i for i in ans if rows[i]["hops"] == 1]
out = {"reading": reading, "paired": f"{wins}:{losses}", "p": round(p, 4),
       "answerable": {BASE: f"{cnt(b, ans)}/{len(ans)}", TREAT: f"{cnt(t, ans)}/{len(ans)}"},
       "multi_hop": {BASE: f"{cnt(b, multi)}/{len(multi)}", TREAT: f"{cnt(t, multi)}/{len(multi)}"},
       "one_hop": {BASE: f"{cnt(b, one)}/{len(one)}", TREAT: f"{cnt(t, one)}/{len(one)}"},
       "refusals": {BASE: f"{cnt(b, none)}/{len(none)}", TREAT: f"{cnt(t, none)}/{len(none)}"},
       "same_page_wrong_statement": {BASE: same_page_wrong(b), TREAT: same_page_wrong(t)},
       "rows_whose_needed_statement_top8_hides": hidden, "lost": lost}
print(json.dumps(out, indent=1))
json.dump(out, open(R / "verdict.json", "w"), indent=1)
