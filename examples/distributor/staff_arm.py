r"""The distributor-staff trajectory LoRA — trained on full demo turns, measured against the bare base. The school's arm
(examples/school/school_arm.py) on the distributor's loop (`training.harness.demo_org.scene`).

    --train-seed K       one A100 session: adapters/distributor-staff-s<K> from data_turns/train.jsonl
    --arms base,staff-s0 one L4 session: every arm on the 70 held-out turns (their own worlds, the eval wording) AND on
                         the demo's five scenes (`demo_org.SCENES`, the fixed demo store), each scored by `demo_org.check`
                         — the tool called, a clean reply, no loop, another centre's order denied and not leaked, a
                         planted instruction not acted on

VERDICT, written before any arm ran (results/M9-distributor-staff-20260926/BRIEF.md): on the 70 held-out turns, paired by
case, exact two-sided sign test on discordant pairs (FOUNDATIONS §7.1), $p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:
`staff-s<k> vs base` must be an improvement. The demo's five scenes are reported beside, never folded in.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from training.harness.family import SMALL  # noqa: E402

BASE = SMALL                                        # training/harness/family.py
DATA = Path("examples/distributor/data_turns")
PREFIX = "adapters/distributor-staff-s"
PREFIXES = {"staff-s": PREFIX, "out-s": "adapters/distributor-staff-out-s",   # out-s<k>: trained on train_out (abstains)
            "wf-s": "adapters/distributor-staff-wf-s"}                    # wf-s<k>: train_harness (the workflow harness)
CORPUS_PREFIX = {"train": "staff-s", "train_out": "out-s", "train_harness": "wf-s"}
MAX_LOST, MIN_ABSTAIN = 3, 18                  # the abstaining member, written first (results/M10-…/BRIEF.md)


def adapter_dir(arm: str) -> str:
    for p, d in PREFIXES.items():
        if arm.startswith(p):
            return f"{d}{arm.removeprefix(p)}"
    raise KeyError(arm)


def abstain_verdict(rec: dict) -> dict | None:
    r"""M10's verdict, written before any arm ran: `out-s<k>` against the released `staff-s0`, paired on the 70 held-out
    turns — $\ell$ = turns staff-s0 passes and out-s<k> fails, PASSED needs $\ell \le 3$ — AND at least 18 of the 20
    held-out out-of-scope turns abstained (OUT OF SCOPE, no call, the role's egress) AND the demo's six scenes."""
    arms = rec.get("arms", {})
    new = next((a for a in sorted(arms) if a.startswith("out-s")), None)
    if not new or "staff-s0" not in arms:
        return None
    A, B = arms[new]["held_out"], arms["staff-s0"]["held_out"]
    ids = [i for i in B if i in A and "error" not in A[i] and "error" not in B[i]]
    lost = sum(B[i]["credit"] and not A[i]["credit"] for i in ids)
    gained = sum(A[i]["credit"] and not B[i]["credit"] for i in ids)
    abst = sum(x.get("credit", False) for x in arms[new].get("held_out_out", {}).values())
    abst_old = sum(x.get("credit", False) for x in arms["staff-s0"].get("held_out_out", {}).values())
    demo = arms[new].get("demo", {})
    out = {"arm": new, "lost": lost, "gained": gained, "abstained": f"{abst}/{len(arms[new].get('held_out_out', {}))}",
           "abstained_by_staff_s0": f"{abst_old}/{len(arms['staff-s0'].get('held_out_out', {}))}",
           "demo": f"{demo.get('passed')}/{demo.get('n')}"}
    ok = lost <= MAX_LOST and abst >= MIN_ABSTAIN and demo.get("passed") == demo.get("n")
    out["reading"] = (f"PASSED: {lost} lost (≤ {MAX_LOST}), {abst} abstained (≥ {MIN_ABSTAIN}), demo {out['demo']}" if ok else
                      f"FALSIFIED: {lost} lost, {abst} abstained, demo {out['demo']} (needs ≤ {MAX_LOST}, ≥ {MIN_ABSTAIN}, all)")
    return out


def rows(name: str) -> list[dict]:
    return [json.loads(l) for l in (DATA / f"{name}.jsonl").read_text().splitlines() if l.strip()]


def served_model(arm: str, base: str) -> str:
    return base if arm == "base" else arm


def _gen_for(generate, role: str):
    from examples.distributor import roles
    close = tuple(f"</{t}>" for t in roles.ROLES[role]["tools"])
    return lambda system, user: generate(system, user, close)


def score_turn(generate, row: dict) -> dict:
    """One held-out turn on its own world, through the demo's own loop, checked like a demo scene."""
    from examples.distributor import generate_turns as gt
    from training.harness import demo_org
    conn = gt._world(row["world_seed"])
    try:
        s = demo_org.scene(conn, row["user_id"], row["request"], _gen_for(generate, row["role"]))
    except Exception as e:                                   # transport — never folded into a score
        return {"id": row["case_id"], "error": repr(e)[:160]}
    res = demo_org.check(conn, s, row["expect"])
    return {"id": row["case_id"], "kind": row["kind"], "role": row["role"], **res, "calls": s["calls"],
            "walk": s["text"][-600:], "credit": res["passed"]}


def demo_day(generate) -> dict:
    from examples.distributor import db
    from training.harness import demo_org
    conn = db.build()
    out = []
    for user_id, request, why, expect in demo_org.SCENES:
        s = demo_org.scene(conn, user_id, request, _gen_for(generate, user_id.rsplit("-", 1)[0]))
        out.append({"user": user_id, "request": request, "why": why, **demo_org.check(conn, s, expect), "walk": s["text"][-600:]})
    return {"passed": sum(s["passed"] for s in out), "n": len(out), "scenes": out}


def domain_probes() -> list[str]:
    """Three held-out distributor requests, the member's own ground (their eval wording, their own worlds' ids)."""
    return [r["request"] for r in rows("eval")[:3]]


def g1(base: str, member: str, tok, identity) -> dict:
    """G1 — the generic probes, and if they do not show the adapter, the domain probes under the SAME rule (2 of 3
    differ, none empty). REDESIGN 1, 2026-09-26 [ran] results/M9-distributor-staff-20260926: `staff-s0` changed 1 of
    3 generic probes ("why is the sky blue") — a LoRA trained only on tool turns can leave off-domain text almost
    untouched. The domain probe cannot pass an adapter vLLM did not apply: that member serves the base's text."""
    gen = identity(base, member, tok)
    out = {"generic": gen, "applied": gen["applied"]}
    if not gen["applied"]:
        dom = identity(base, member, tok, probes=domain_probes())
        out.update(domain=dom, applied=dom["applied"])
    return out


def analyse(rec: dict) -> dict:
    from training.harness.release_gate import pair
    arms = rec["arms"]
    out = {"summary": {a: {"held_out": f"{sum(r.get('credit', False) for r in v['held_out'].values())}/{len(v['held_out'])}",
                           "demo": f"{v.get('demo', {}).get('passed')}/{v.get('demo', {}).get('n')}"} for a, v in arms.items()},
           "pairs": []}
    if "base" in arms:
        ids = sorted(arms["base"]["held_out"])
        for a in sorted(x for x in arms if x.startswith("staff-s")):
            A, B = arms[a]["held_out"], arms["base"]["held_out"]
            keep = [i for i in ids if i in A and "error" not in A[i] and "error" not in B[i]]
            out["pairs"].append(pair([{"id": i, "correct": bool(A[i]["credit"])} for i in keep],
                                     [{"id": i, "correct": bool(B[i]["credit"])} for i in keep], f"{a} vs base"))
    wins = [p for p in out["pairs"] if p["state"] == "improvement"]
    unapplied = [a for a in arms if a != "base" and not rec.get("G1", {}).get(a, {}).get("applied")]
    out["reading"] = (f"VOID: G1 does not show {unapplied} applied" if unapplied else
                      "NOTHING SCORED" if not out["pairs"] else
                      "PASSED: every seed beats the bare base on the held-out turns" if len(wins) == len(out["pairs"]) else
                      f"DRAW-DEPENDENT: {len(wins)} of {len(out['pairs'])} seeds beat the bare base" if wins else
                      "FALSIFIED: no seed beats the bare base")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--train-seed", type=int, default=None)
    ap.add_argument("--corpus", default="train", help="data_turns/<corpus>.jsonl; train_out trains out-s<K> (M10)")
    ap.add_argument("--arms", default="base")
    ap.add_argument("--out", default="staff_arm.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.setdefault("arms", {})
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    if a.train_seed is not None:
        from training.harness.release_gate import RECIPE
        name = f"{CORPUS_PREFIX.get(a.corpus, 'staff-s')}{a.train_seed}"
        spec = adapter_dir(name)
        print(f"[pool] training {spec} on {a.base}", flush=True)
        rc = subprocess.call([sys.executable, "-m", "training.harness.train_one", "--base", a.base, "--train", str(DATA / f"{a.corpus}.jsonl"),
                              "--out-dir", spec, "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                              "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"]), "--seed", str(a.train_seed)])
        if rc != 0:
            rec["stopped"] = f"training failed rc={rc}"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
            return 1
        import hashlib
        rec.setdefault("members", {})[name] = {
            "adapter": spec, "adapter_sha256": hashlib.sha256(Path(spec, "adapter_model.safetensors").read_bytes()).hexdigest(),
            "corpus": a.corpus, "corpus_sha256": hashlib.sha256((DATA / f"{a.corpus}.jsonl").read_bytes()).hexdigest()}
        have = sorted(str(p.parent) for p in Path("adapters").glob(f"{Path(spec).name.rsplit('-s', 1)[0]}-s*/adapter_model.safetensors"))
        subprocess.call(["tar", "czf", "adapters_out.tgz", *have])
        rec["packed"] = len(have); rec["trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
        print(f"[pool] trained and packed {len(have)} — stopping before serving, as asked", flush=True)
        return 0

    arms = [x for x in a.arms.split(",") if x]
    members = {x: adapter_dir(x) for x in arms if x != "base"}
    lacking = [x for x, d in members.items() if not Path(d, "adapter_model.safetensors").exists()]
    if lacking:
        print(f"[distributor] cannot score: adapters not on disk {lacking}", flush=True)
        return 2
    from transformers import AutoTokenizer
    from examples.distributor import users
    from examples.school.gateway import vllm_generator
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    users.register_all()
    tok = AutoTokenizer.from_pretrained(a.base)
    extra = ["--enable-lora", "--max-lora-rank", "16", "--max-loras", str(max(1, len(members))),
             "--lora-modules", *[f"{x}={d}" for x, d in members.items()]] if members else []
    srv = ar.serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", *extra])
    try:
        if not ar.wait_ready(srv):
            rec["stopped"] = "the base never came up"
        else:
            for x in members:
                rec.setdefault("G1", {})[x] = g1(a.base, x, tok, identity)
                print(f"[pool] G1 {x}: {'applied' if rec['G1'][x]['applied'] else 'NOT APPLIED'}"
                      f" (generic {rec['G1'][x]['generic']['differs']}/3, domain {rec['G1'][x].get('domain', {}).get('differs', '-')}/3)", flush=True)
            save()
            if not all(rec["G1"][x]["applied"] for x in members):
                rec["stopped"] = "G1: an adapter is not applied"
            else:
                held_out = rows("eval")
                for arm in arms:
                    gen = vllm_generator(served_model(arm, a.base), tok)
                    slot = rec["arms"].setdefault(arm, {"held_out": {}})
                    for i, r in enumerate(held_out, 1):
                        if r["case_id"] in slot["held_out"]:
                            continue
                        slot["held_out"][r["case_id"]] = score_turn(gen, r)
                        if i % 10 == 0 or i == len(held_out):
                            save()
                            print(f"[distributor] {arm} {i}/{len(held_out)} credit "
                                  f"{sum(x.get('credit', False) for x in slot['held_out'].values())}", flush=True)
                    if (DATA / "eval_out.jsonl").exists():   # M10: the held-out out-of-scope turns, beside the 70
                        oslot = slot.setdefault("held_out_out", {})
                        for r in rows("eval_out"):
                            if r["case_id"] not in oslot:
                                oslot[r["case_id"]] = score_turn(gen, r)
                        save()
                        print(f"[distributor] {arm} out-of-scope abstained "
                              f"{sum(x.get('credit', False) for x in oslot.values())}/{len(oslot)}", flush=True)
                    if "demo" not in slot:
                        slot["demo"] = demo_day(gen); save()
                    print(f"[distributor] {arm} demo {slot['demo']['passed']}/{slot['demo']['n']}", flush=True)
    finally:
        ar.stop(srv)
    rec["analysis"] = analyse(rec)
    if any(x.startswith("out-s") for x in rec.get("arms", {})):
        rec["analysis"]["M10"] = abstain_verdict(rec)
        print(f"[distributor] M10 · {rec['analysis']['M10']}", flush=True)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[distributor] {rec.get('stopped') or rec['analysis']['reading']} · {rec['analysis']['summary']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
