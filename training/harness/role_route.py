"""The role as the route, measured with no model: results/F2-role-as-route-20260920/BRIEF.md.

Three arms on text that already exists — the dictionary (today), the TRUE role attached, the WRONG
role attached — under the two policies `route.decide` declares. Two instruments: `route.replay`'s
delivered accuracy on P41's 240 cases, and `router_sets.score` on the eight router sets, whose zero
term is a request served by a member it does not belong to (FOUNDATIONS §8.4):

    misrouted_to_local = |{ x : decide(x) is a member and decide(x) != truth(x) }|

The verdict is written by `verdict()` from the falsifier the brief fixed before any number.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from training.harness import route, router_sets

ROLE_OF = {member: role for role, member in route.ROLES.items()}
OTHER = {"email-full": "desk-commitment", "desk-commitment": "email-full"}


def _decider(policy: str | None, role_for):
    def d(text: str, truth: str, src: str | None) -> str:
        role = role_for(truth, src)
        got = route.decide({"messages": [{"role": "user", "content": text}]}, role=role, policy=policy)
        return got[1] if got[0] == "local" else "out"
    return d


def _score(rows, decide) -> dict:
    right = wrong = lost = kept = 0
    for text, truth, src in rows:
        got = decide(text, truth, src)
        if truth == "out":
            wrong += got != "out"; kept += got == "out"
        else:
            right += got == truth; lost += got == "out"; wrong += got not in (truth, "out")
    return {"n": len(rows), "local_right_member": right, "misrouted_to_local": wrong,
            "lost_local": lost, "abstained": kept}


def sourced_sets() -> dict[str, list[tuple[str, str, str | None]]]:
    """Every row with the member whose listing it was built from — the agent it would arrive at.
    E and E2 are a member's own listing followed by another task; the source is recovered by
    matching the listing (everything before the final question line) against set A, and a listing
    both members could have produced is an error, not a guess."""
    sets = {**router_sets.build(), **router_sets.build_fresh()}
    head = lambda t: t.rstrip().rsplit("\n", 1)[0].rstrip()
    owner: dict[str, set[str]] = {}
    for t, m in sets["A"]:
        owner.setdefault(head(t), set()).add(m)
    out = {}
    for name, rows in sets.items():
        if name.startswith("_"):
            continue
        if name in ("E", "E2"):
            built = []
            for t, truth in rows:
                who = owner.get(head(t), set())
                assert len(who) == 1, f"{name}: a listing with {len(who)} possible sources"
                built.append((t, truth, next(iter(who))))
            out[name] = built
        else:
            out[name] = [(t, truth, truth if truth != "out" else None) for t, truth in rows]
    return out


def measure() -> dict:
    sets = sourced_sets()
    res = {"roles": route.ROLES, "sets": {k: len(v) for k, v in sets.items()}, "arms": {}}
    true_role = lambda truth, src: ROLE_OF.get(src) if src else None
    wrong_role = lambda truth, src: ROLE_OF.get(OTHER.get(src)) if src else None

    res["arms"]["dictionary"] = {k: _score(v, _decider(None, lambda *_: None)) for k, v in sets.items()}
    for policy in route.ROLE_POLICIES:
        arm = {}
        for k, rows in sets.items():
            if all(src is None for _, _, src in rows):
                # belongs to nobody: scored under EACH role, the worst reported
                per = {r: _score(rows, _decider(policy, lambda t, s, r=r: r)) for r in ("triage", "desk")}
                worst = max(per, key=lambda r: per[r]["misrouted_to_local"])
                arm[k] = {**per[worst], "under_role": worst, "per_role": per}
            else:
                arm[k] = _score(rows, _decider(policy, true_role))
        res["arms"][f"true_role:{policy}"] = arm
        wrong = {}
        for k in ("A", "B", "F"):
            rows = [r for r in sets[k] if r[2] in OTHER]
            s = _score(rows, _decider(policy, wrong_role))
            s["silently_served_by_the_wrong_member"] = s.pop("misrouted_to_local")
            s["caught"] = s["local_right_member"] + s["lost_local"]
            wrong[k] = s
        res["arms"][f"wrong_role:{policy}"] = wrong

    pool = json.loads(Path("results/P41-routing-20260915/pool_results.json").read_text())
    frontier = json.loads(Path("results/P41-routing-20260915/frontier_fluids.json").read_text())
    res["replay"] = {"dictionary": route.replay(pool, frontier)["by_request"]}
    for policy in route.ROLE_POLICIES:
        res["replay"][f"true_role:{policy}"] = replay_with_role(pool, frontier, policy)
    res["verdict"] = verdict(res)
    return res


def replay_with_role(pool: dict, frontier: dict, policy: str) -> dict:
    """`route.replay`, with each case carrying the role of the member it truly belongs to."""
    real = route.decide
    cases_role = {"email-full": "triage", "fluids-full": "fluids"}
    orig = route.decide
    try:
        def patched(req, regions=route.REGIONS):
            text = route.text_of(req)
            truth = "email-full" if "From:" in text and "Subject:" in text else "fluids-full"
            return real(req, regions, role=cases_role[truth], policy=policy)
        route.decide = patched
        return route.replay(pool, frontier)["by_request"]
    finally:
        route.decide = orig


def verdict(res: dict) -> dict:
    base = res["arms"]["dictionary"]
    out = {}
    for policy in route.ROLE_POLICIES:
        true, wrong = res["arms"][f"true_role:{policy}"], res["arms"][f"wrong_role:{policy}"]
        rep, rep0 = res["replay"][f"true_role:{policy}"], res["replay"]["dictionary"]
        a = rep["delivered"] < rep0["delivered"] or rep["misrouted"] > rep0["misrouted"]
        b = {k: (true[k]["misrouted_to_local"], base[k]["misrouted_to_local"]) for k in base
             if true[k]["misrouted_to_local"] > base[k]["misrouted_to_local"]}
        c = {k: v["silently_served_by_the_wrong_member"] for k, v in wrong.items()
             if v["silently_served_by_the_wrong_member"]}
        gained = {k: true[k]["local_right_member"] - base[k]["local_right_member"] for k in base
                  if true[k]["local_right_member"] != base[k]["local_right_member"]}
        out[policy] = {"a_replay_worse": a, "b_more_misroutes_than_dictionary": b,
                       "c_silently_served_under_wrong_role": c, "right_member_gained": gained,
                       "fails": bool(a or b or c)}
    out["default"] = next((p for p in route.ROLE_POLICIES if not out[p]["fails"]), None)
    out["reading"] = (f"DEFAULT: {out['default']}" if out["default"] else
                      "NEITHER POLICY PASSES: the role stays behind a flag")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="results/F2-role-as-route-20260920/role_route.json")
    a = ap.parse_args()
    res = measure()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1))
    for arm, sets in res["arms"].items():
        print(f"[route] {arm}")
        for k, v in sets.items():
            print(f"[route]   {k}: " + " · ".join(f"{a}={b}" for a, b in v.items() if a != "per_role"))
    for k, v in res["replay"].items():
        print(f"[route] replay {k}: {v}")
    print(f"[route] {res['verdict']['reading']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
