r"""The school-staff trajectory LoRA — trained on full gateway turns, measured against the bare base.

    --train-seed K       one A100 session: adapters/school-staff-s<K> from data_turns/train.jsonl
    --arms base,school-s0[,school-s1]   one L4 session: every arm on the 70 held-out turns (their own worlds,
                         the eval wording) AND on the demo's scripted day (examples/school/demo_run.SCENES,
                         the fixed demo school), each scored by `demo_run.check` — call, denial, hold, route,
                         a clean reply, no loop, a grounded answer

VERDICT, written before any arm ran (results/M8-school-staff-20260925/BRIEF.md): on the 70 held-out turns,
paired by case, exact two-sided sign test on discordant pairs (FOUNDATIONS §7.1),
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:  `school-s<k> vs base` must be an improvement for EVERY
seed trained — PASSED; for some — DRAW-DEPENDENT; none — FALSIFIED. The demo day is reported beside, never
folded in: eight scenes are a demonstration, not a sample.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from examples.common import tokens

from training.harness.family import SMALL  # noqa: E402

BASE = SMALL                                        # training/harness/family.py
DATA = Path("examples/school/data_turns")


def rows(name: str) -> list[dict]:
    return [json.loads(l) for l in (DATA / f"{name}.jsonl").read_text().splitlines() if l.strip()]


def adapter_dir(arm: str) -> str:
    """`school-s<k>` — the full member (M8); `upper-s<k>` — E6, the same recipe on the upper half of the layers."""
    if arm.startswith("upper-s"):
        return f"adapters/school-upper-s{arm.removeprefix('upper-s')}"
    return f"adapters/school-staff-s{arm.removeprefix('school-s')}"


def served_model(arm: str, base: str) -> str:
    return base if arm == "base" else arm


def score_turn(generate, row: dict) -> dict:
    """One held-out turn on its own world, through the gateway, checked like a demo scene."""
    from examples.school import generate_turns as gt
    from examples.school.demo_run import check
    from examples.school.gateway import Gateway
    g = Gateway(gt._world(row["world_seed"]), generate)
    try:
        out = g.turn(tokens.issue(row["user_id"], row["role"], "northgate"), [{"role": "user", "content": row["request"]}])
    except Exception as e:                                   # transport — never folded into a score
        return {"id": row["case_id"], "error": repr(e)[:160]}
    res = check(row["expect"], {"x_route": out["route"], "x_calls": out["event"]["calls"],
                                "choices": [{"message": {"content": out["reply"] if out["route"] == "local" else out["walk"]}}]})
    return {"id": row["case_id"], "kind": row["kind"], "role": row["role"], **res, "walk": out["walk"][-600:], "credit": res["passed"]}


def demo_day(generate) -> dict:
    from examples.school import db
    from examples.school.demo_run import SCENES, check, token_for
    from examples.school.gateway import Gateway
    g = Gateway(db.build(), generate)
    out = []
    for who, text, expect in SCENES:
        o = g.turn(token_for(who), [{"role": "user", "content": text}])
        res = check(expect, {"x_route": o["route"], "x_calls": o["event"]["calls"],
                             "choices": [{"message": {"content": o["reply"] if o["route"] == "local" else o["walk"]}}]})
        out.append({"who": who, "request": text, **res, "walk": o["walk"][-600:]})
    return {"passed": sum(s["passed"] for s in out), "n": len(out), "scenes": out}


def analyse(rec: dict) -> dict:
    from training.harness.release_gate import pair
    arms = rec["arms"]
    out = {"summary": {a: {"held_out": f"{sum(r.get('credit', False) for r in v['held_out'].values())}/{len(v['held_out'])}",
                           "demo_day": f"{v.get('demo', {}).get('passed')}/{v.get('demo', {}).get('n')}"} for a, v in arms.items()},
           "pairs": []}
    if "base" in arms:
        ids = sorted(arms["base"]["held_out"])
        for a in sorted(x for x in arms if x.startswith("school-s")):
            A, B = arms[a]["held_out"], arms["base"]["held_out"]
            keep = [i for i in ids if i in A and "error" not in A[i] and "error" not in B[i]]
            out["pairs"].append(pair([{"id": i, "correct": bool(A[i]["credit"])} for i in keep],
                                     [{"id": i, "correct": bool(B[i]["credit"])} for i in keep], f"{a} vs base"))
    if any(x.startswith("upper-s") for x in arms):
        out["E6"] = e6(rec)
    wins = [p for p in out["pairs"] if p["state"] == "improvement"]
    unapplied = [a for a in arms if a != "base" and not rec.get("G1", {}).get(a, {}).get("applied")]
    out["reading"] = (f"VOID: G1 does not show {unapplied} applied" if unapplied else
                      "NOTHING SCORED" if not out["pairs"] else
                      "PASSED: every seed beats the bare base on the held-out turns" if len(wins) == len(out["pairs"]) else
                      f"DRAW-DEPENDENT: {len(wins)} of {len(out['pairs'])} seeds beat the bare base" if wins else
                      "FALSIFIED: no seed beats the bare base")
    return out


E6_MAX_LOST = 3                                     # docs/review/00-thesis-review.md §5, written before the run


def e6(rec: dict) -> dict:
    r"""E6's verdict, written first (results/E6-upper-layers-20260927/BRIEF.md). Paired against the full member on the 70
    held-out turns: $\ell$ = turns the full member passes and the upper-half member fails; PASSED needs $\ell\le 3$
    AND the lower layers bit-identical to the base (`train_one.lower_layers_identical`, read from the adapter directory).
    A base-vs-base control that differs, or an adapter that does not move layer $k$, makes the identity unreadable: VOID."""
    from training.harness.release_gate import pair
    arms, res = rec["arms"], {}
    full = next((x for x in sorted(arms) if x.startswith("school-s")), None)
    for up in sorted(x for x in arms if x.startswith("upper-s")):
        low = rec.get("lower_identity", {}).get(up) or {}
        r = {"lower_identity": low}
        if full:
            A, B = arms[up]["held_out"], arms[full]["held_out"]
            keep = [i for i in sorted(B) if i in A and "error" not in A[i] and "error" not in B[i]]
            r["pair"] = pair([{"id": i, "correct": bool(A[i]["credit"])} for i in keep],
                             [{"id": i, "correct": bool(B[i]["credit"])} for i in keep], f"{up} vs {full}")
            r["lost"] = r["pair"]["only_b"]
        identical = low.get("inputs_identical") and low.get("kv_identical") is not False and not low.get("file_layers_below_k")
        r["reading"] = ("VOID: no full member scored beside it" if not full else
                        "VOID: G1 does not show it applied" if not rec.get("G1", {}).get(up, {}).get("applied") else
                        "VOID: no lower-layer check in the adapter directory" if not low else
                        "VOID: base against base is not bit-identical — the engine, not the adapter" if not low.get("control_identical") else
                        "VOID: the adapter does not move layer k" if not low.get("adapted_moves") else
                        "FALSIFIED: the layers below k are not the base's" if not identical else
                        f"PASSED: {r['lost']} of {len(keep)} turns lost (≤ {E6_MAX_LOST}), lower layers bit-identical"
                        if r["lost"] <= E6_MAX_LOST else
                        f"FALSIFIED: {r['lost']} turns lost against the full member (> {E6_MAX_LOST})")
        res[up] = r
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--train-seed", type=int, default=None)
    ap.add_argument("--layers-from", default=None, help="E6: train `upper-s<K>` on decoder layers k…N-1 only ('half')")
    ap.add_argument("--arms", default="base")
    ap.add_argument("--combine", default=None, help="zero GPU: add this file's arms to --out's and re-read the verdict")
    ap.add_argument("--out", default="school_arm.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.setdefault("arms", {})
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    if a.combine:
        more = json.loads(Path(a.combine).read_text())
        rec["arms"].update(more["arms"]); rec["G1"] = {**rec.get("G1", {}), **more.get("G1", {})}
        rec["analysis"] = analyse(rec); save()
        print(f"[school] {rec['analysis']['reading']} · {rec['analysis']['summary']}", flush=True)
        return 0
    if a.train_seed is not None:
        from training.harness.release_gate import RECIPE
        name = f"upper-s{a.train_seed}" if a.layers_from else f"school-s{a.train_seed}"
        spec = adapter_dir(name)
        print(f"[pool] training {spec} on {a.base}{f' (layers from {a.layers_from})' if a.layers_from else ''}", flush=True)
        rc = subprocess.call([sys.executable, "-m", "training.harness.train_one", "--base", a.base, "--train", str(DATA / "train.jsonl"),
                              "--out-dir", spec, "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                              "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"]), "--seed", str(a.train_seed),
                              *(["--layers-from", a.layers_from] if a.layers_from else [])])
        if rc != 0:
            rec["stopped"] = f"training failed rc={rc}"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
            return 1
        import hashlib
        rec.setdefault("members", {})[name] = {
            "adapter": spec, "adapter_sha256": hashlib.sha256(Path(spec, "adapter_model.safetensors").read_bytes()).hexdigest()}
        if Path(spec, "lower_identity.json").exists():
            rec["members"][name]["lower_identity"] = json.loads(Path(spec, "lower_identity.json").read_text())
        have = sorted(str(p.parent) for p in Path("adapters").glob(f"{Path(spec).name.rsplit('-s', 1)[0]}-s*/adapter_model.safetensors"))
        subprocess.call(["tar", "czf", "adapters_out.tgz", *have])
        rec["packed"] = len(have); rec["trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
        print(f"[pool] trained and packed {len(have)} — stopping before serving, as asked", flush=True)
        return 0

    arms = [x for x in a.arms.split(",") if x]
    members = {x: adapter_dir(x) for x in arms if x != "base"}
    lacking = [x for x, d in members.items() if not Path(d, "adapter_model.safetensors").exists()]
    if lacking:
        print(f"[school] cannot score: adapters not on disk {lacking}", flush=True)
        return 2
    for x, d in members.items():                      # E6: the lower-layer check travels with the adapter
        if Path(d, "lower_identity.json").exists():
            rec.setdefault("lower_identity", {})[x] = json.loads(Path(d, "lower_identity.json").read_text())
    from transformers import AutoTokenizer
    from examples.school.gateway import vllm_generator
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    extra = ["--enable-lora", "--max-lora-rank", "16", "--max-loras", str(max(1, len(members))),
             "--lora-modules", *[f"{x}={d}" for x, d in members.items()]] if members else []
    srv = ar.serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", *extra])
    try:
        if not ar.wait_ready(srv):
            rec["stopped"] = "the base never came up"
        else:
            for x in members:
                rec.setdefault("G1", {})[x] = identity(a.base, x, tok)
                print(f"[pool] G1 {x}: {'applied' if rec['G1'][x]['applied'] else 'NOT APPLIED'}", flush=True)
            save()
            if not all(rec["G1"][x]["applied"] for x in members):
                rec["stopped"] = "G1: an adapter is not applied"
            else:
                held_out = rows("eval")
                for arm in arms:
                    gen = vllm_generator(served_model(arm, a.base), tok)
                    slot = rec["arms"].setdefault(arm, {"held_out": {}})
                    for i, r in enumerate(held_out, 1):
                        if r["case_id"] in slot["held_out"] and "error" not in slot["held_out"][r["case_id"]]:
                            continue                         # resumed across sessions: a scored turn is not re-scored
                        slot["held_out"][r["case_id"]] = score_turn(gen, r)
                        if i % 10 == 0 or i == len(held_out):
                            save()
                            print(f"[school] {arm} {i}/{len(held_out)} credit {sum(x.get('credit', False) for x in slot['held_out'].values())}", flush=True)
                    if "demo" not in slot:
                        slot["demo"] = demo_day(gen); save()
                    print(f"[school] {arm} demo day {slot['demo']['passed']}/{slot['demo']['n']}", flush=True)
    finally:
        ar.stop(srv)
    rec["analysis"] = analyse(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[school] {rec.get('stopped') or rec['analysis']['reading']} · {rec['analysis']['summary']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
