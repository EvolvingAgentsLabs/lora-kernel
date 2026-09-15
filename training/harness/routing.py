"""What routing the failures to a frontier model would actually deliver, and cost.

THE IDEA THIS MEASURES. The pool's experts are not equally good — P40 measured one
that beats its base 8:51 and one that gets the physics wrong 78 times in 90
**[ran]**. So the frontier stops being scaffolding to withdraw and becomes a
**fallback for the regions and the cases where the local expert fails**. This module
turns that into numbers instead of a plan.

TWO POLICIES, AND THEY ARE NOT THE SAME CLAIM.

    by region   send every case of a failing subdomain away.
                Needs nothing but the two scores. Coarse and free.

    by case     send a case away when `escalate.should_escalate` says its chain has
                left its region. Needs the CHAIN, which is why P40 had to be bought
                twice — it stored the final line only.

THE FRONTIER'S RATE IS MEASURED, NOT ASSUMED. An earlier version of this arithmetic
reported `<= 0.871` on the assumption that the frontier answers everything it
receives. That is an upper bound, not a result, and it is the shape of claim this
repository exists to refuse. `--frontier` takes a real run.

WHAT IS DELIVERED IS WHAT THE USER GETS, not what either model scores alone: the
local answer where the router kept it, the frontier's where it sent it away.

    python3 -m training.harness.routing --pool results/.../pool_results.json \\
        --frontier-fluids results/.../frontier_fluids.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from training.harness.bar import compare
from training.harness.escalate import has_left_its_region, is_probably_wrong


def _load(path: str | None) -> dict | None:
    return json.loads(Path(path).read_text()) if path else None


def by_region(local_ok: int, local_n: int, frontier_ok: int | None,
              frontier_n: int | None, send_away: bool) -> dict:
    """One subdomain, all-or-nothing."""
    if not send_away:
        return {"delivered": local_ok, "n": local_n, "escalated": 0}
    if frontier_ok is None:
        return {"delivered": None, "n": local_n, "escalated": local_n,
                "why": "the frontier's rate on this suite is not measured"}
    # the frontier is scored on the same cases, so its count is what is delivered
    return {"delivered": frontier_ok, "n": frontier_n, "escalated": frontier_n}


def by_case(local_recs: list[dict], frontier_recs: list[dict], rule) -> dict:
    """Per-case escalation, with the frontier answering only what was sent away.

    A LOCAL CASE THE ROUTER KEEPS IS DELIVERED AS THE LOCAL ANSWER, right or wrong.
    That is the number a user experiences, and it is the only one worth reporting:
    a router that escalates everything scores the frontier's rate and is not a pool.
    """
    front = {r["id"]: r for r in frontier_recs}
    kept = sent = delivered = sent_and_right = kept_and_right = 0
    missing = 0
    for r in local_recs:
        chain = r.get("chain")
        if chain is None:
            missing += 1
            continue
        if rule(chain, r.get("unit", ""), r.get("statement", "")):
            sent += 1
            f = front.get(r["id"])
            if f is None:
                missing += 1
                continue
            delivered += bool(f["passed"])
            sent_and_right += bool(f["passed"])
        else:
            kept += 1
            delivered += bool(r["passed"])
            kept_and_right += bool(r["passed"])
    n = kept + sent
    return {"n": n, "kept": kept, "escalated": sent,
            "escalated_share": round(sent / n, 4) if n else None,
            "delivered": delivered,
            "delivered_accuracy": round(delivered / n, 4) if n else None,
            "kept_and_right": kept_and_right, "sent_and_right": sent_and_right,
            "records_without_a_chain": missing}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--frontier-fluids", default=None)
    ap.add_argument("--frontier-email", default=None)
    ap.add_argument("--out", default="routing.json")
    args = ap.parse_args()

    pool = _load(args.pool)["arms"]
    ff = _load(args.frontier_fluids)
    out: dict = {"policies": {}}

    em, fl = pool.get("email-full", {}), pool.get("fluids-full", {})
    em_ok, em_n = em.get("correct"), em.get("n")
    fl_ok, fl_n = fl.get("passed"), fl.get("n")
    f_ok, f_n = (ff.get("passed"), ff.get("n")) if ff else (None, None)

    print(f"local   email  {em_ok}/{em_n}   fluids {fl_ok}/{fl_n}")
    if ff:
        print(f"frontier fluids {f_ok}/{f_n} = {f_ok / f_n:.3f}"
              f"  ({ff.get('refused')} refused, {ff.get('out_of_turns')} out of turns)")
    else:
        print("frontier fluids: NOT MEASURED — region numbers below are bounds only")

    for name, send in (("everything local", False), ("fluids to the frontier", True)):
        r = by_region(fl_ok, fl_n, f_ok, f_n, send)
        tot_n = em_n + (r["n"] or 0)
        tot_d = None if r["delivered"] is None else em_ok + r["delivered"]
        out["policies"][name] = {
            "delivered": tot_d, "n": tot_n,
            "accuracy": None if tot_d is None else round(tot_d / tot_n, 4),
            "escalated": r["escalated"],
            "escalated_share": round(r["escalated"] / tot_n, 4)}
        acc = "unmeasured" if tot_d is None else f"{tot_d / tot_n:.3f}"
        print(f"  by region · {name:<24} delivered {acc}"
              f"   · {r['escalated'] / tot_n:.0%} of cases leave")

    if ff and fl.get("records") and fl["records"][0].get("chain") is not None:
        for label, rule in (("tripwire (has_left_its_region)", has_left_its_region),
                            ("quality gate (is_probably_wrong)", is_probably_wrong)):
            r = by_case(fl["records"], ff["records"], rule)
            out["policies"][f"by case · fluids · {label}"] = r
            print(f"  by case   · fluids · {label:<34} "
                  f"delivered {r['delivered_accuracy']}"
                  f" · {r['escalated_share']:.0%} leave")
    else:
        print("  by case: not computable — the local records carry no chain")

    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwritten to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
