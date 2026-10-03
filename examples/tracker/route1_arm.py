r"""ROUTE1 — the tracker's member learns to abstain (M10's recipe): `tr-out-s0` against `tr-s1` on H3's held-out suite
(no in-scope turn lost) and on 30 held-out out-of-scope turns (abstained). Pre-registered in
results/ROUTE1-tracker-abstain-20261003/BRIEF.md; the corpus is `generate_sessions --suite h3 --out-turns`.

    python -m examples.tracker.route1_arm --train-seed 0 --out train_tr_out.json       # tr-out-s0 on train_harness_out
    python -m examples.tracker.route1_arm --arms s1-harness,out-harness --out route1.json
"""
from __future__ import annotations

from pathlib import Path

from examples.tracker import generate_sessions as gs
from examples.tracker.h3_arm import DATA, main as h3_main
from examples.tracker.session_arm import summarise

MEMBERS = {"tr-s1": "adapters/tracker-wf-s1", "tr-out": "adapters/tracker-out-s0"}
ARM_SPEC = {"s1-harness": ("tr-s1", {"harness": True}), "out-harness": ("tr-out", {"harness": True})}
EVAL = Path("examples/tracker/data_sessions_route1")
ABSTAIN_MIN, MAX_LOST = 27, 3


def split(arm: dict) -> tuple[list, list]:
    ins = [v for v in arm.values() if not v.get("out")]
    outs = [v for v in arm.values() if v.get("out")]
    return ins, outs


def abstained(v: dict) -> bool:
    t = v["turns"][0]
    return "error" not in t and t.get("route") in ("frontier", "person") and not t.get("calls")


def reading(rec: dict) -> dict:
    r"""Written first (BRIEF): ABSTAINS iff `out-harness` abstains (route ≠ local, no call) on ≥ 27 of 30 held-out
    out-of-scope turns AND loses at most 3 dependent turns `s1-harness` gets right on H3's suite AND abstains on no more
    in-scope turns than `s1-harness`; COSTS if it abstains but loses more; FALSIFIED under 27/30."""
    arms = rec.get("arms", {})
    if not {"s1-harness", "out-harness"} <= set(arms):
        return {"reading": "NOTHING SCORED"}
    out = {}
    for name, arm in arms.items():
        ins, outs = split(arm)
        sm = summarise(ins)
        out[name] = {"in_scope": sm, "abstained_out": f"{sum(abstained(v) for v in outs)}/{len(outs)}",
                     "abstained_out_by_kind": {k: f"{sum(abstained(v) for v in outs if v['out'] == k)}/{sum(v['out'] == k for v in outs)}"
                                               for k in ("outside-tracker", "outside-role")},
                     "abstained_in_scope": sum(t.get("route") in ("frontier", "person") for v in ins for t in v["turns"])}
    b, t = arms["s1-harness"], arms["out-harness"]
    lost = 0
    for sid, v in b.items():
        if v.get("out") or sid not in t:
            continue
        for tb, tt in zip(v["turns"], t[sid]["turns"]):
            lost += bool(tb.get("depends")) and bool(tb.get("right")) and not tt.get("right")
    n_abs = sum(abstained(v) for v in split(t)[1])
    more_in_abst = out["out-harness"]["abstained_in_scope"] > out["s1-harness"]["abstained_in_scope"]
    reading = ("ABSTAINS" if n_abs >= ABSTAIN_MIN and lost <= MAX_LOST and not more_in_abst else
               "COSTS" if n_abs >= ABSTAIN_MIN else "FALSIFIED")
    return {"reading": reading, "abstained_out": f"{n_abs}/{len(split(t)[1])}", "dependent_lost": lost,
            "abstains_more_in_scope": more_in_abst, "arms": out}


def main(argv=None) -> int:
    return h3_main(argv, doc=__doc__, data=DATA, members=MEMBERS, arm_spec=ARM_SPEC, read=reading, train_member="tr-out",
                   default_arms="s1-harness,out-harness", default_out="route1.json", tag="route1",
                   corpus_file="train_harness_out.jsonl", eval_data=EVAL, scorer=gs.turn_right_out)


if __name__ == "__main__":
    raise SystemExit(main())
