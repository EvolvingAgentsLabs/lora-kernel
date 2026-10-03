"""ROUTE0's scoring and verdict, as the brief fixed it (written before the sets exist). Zero GPU, no model.

    PYTHONPATH=. python results/ROUTE0-factored-router-20261002/read.py
"""
import json
from pathlib import Path

from training.harness import route
from training.harness.embed_router import corpora_from_pool
from training.harness.factored_router import FactoredRouter
from training.harness.router_sets import score

R = Path("results/ROUTE0-factored-router-20261002")
sets = {k: [tuple(x) for x in v] for k, v in json.loads((R / "sets.json").read_text()).items()}
router = FactoredRouter(corpora_from_pool())
def dictionary(text):
    """The proxy's default today: the region whose keys occur most (a fluids hit on foreign text is a misroute too)."""
    return route.classify(text) or "out"


res = {"factored": score(router.decide, sets), "dictionary": score(dictionary, sets)}
foreign = [s for s in ("E3", "E4", "I3", "C3", "D3") if s in sets]
f = res["factored"]
mis = sum(f[s]["misrouted_to_local"] for s in foreign)
n_foreign = sum(f[s]["n"] for s in foreign)
mis_dict = sum(res["dictionary"][s]["misrouted_to_local"] for s in foreign)
safe = (n_foreign - mis) / n_foreign >= 0.95 and mis <= mis_dict and f["A3"]["misrouted_to_local"] == 0
keeps = f["A3"]["lost_local"] <= 0.01 * f["A3"]["n"] and all(f[s]["lost_local"] <= 0.05 * f[s]["n"] for s in ("F3", "G3", "H3"))
reading = ("PASSES" if safe and keeps else "NOT SAFE" if not safe else "SAFE AND LOSES REAL-LOOKING TRAFFIC")
out = {"reading": reading, "foreign_misrouted": f"{mis}/{n_foreign}", "dictionary_foreign_misrouted": f"{mis_dict}/{n_foreign}",
       "lost": {s: f"{f[s]['lost_local']}/{f[s]['n']}" for s in ("A3", "F3", "G3", "H3") if s in f},
       "B3_recovered": f"{f['B3']['local_right_member']}/{f['B3']['n']}" if "B3" in f else None, "per_set": res}
print(json.dumps({k: v for k, v in out.items() if k != "per_set"}, indent=1))
for s in sets:
    print(f"{s:4s} factored {f[s]}  ·  dictionary {res['dictionary'][s]}")
json.dump(out, open(R / "verdict.json", "w"), indent=1)
