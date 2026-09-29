r"""H2 — the workflow harness on long sessions: the team tracker (Jira + Confluence-like), four and five turns per session.
Pre-registered in results/H2-tracker-harness-20260929/BRIEF.md; the suite is examples/tracker/generate_sessions.py.

    python -m examples.tracker.session_arm --train-seed 0 --out train.json         # one L4: tr-s0 on train_harness
    python -m examples.tracker.session_arm --arms base-history,harness,harness-noblock --out h2.json

Arms: `base-history` — the bare base, the conversation in the prompt (a new domain has no member: this is what serving
it would be today); `harness` / `harness-noblock` — `tr-s0` with the operational memory and the role's workflow, with and
without the tool block. Per turn: right iff the gateway's calls include the call the turn needs (`turn_right`).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = "google/gemma-4-E4B-it"
DATA = Path("examples/tracker/data_sessions")
MEMBER, ADAPTER = "tr-s0", "adapters/tracker-wf-s0"
ARM_SPEC = {"base-history": (None, {"history": True}), "harness": (MEMBER, {"harness": True}),
            "harness-noblock": (MEMBER, {"harness": True, "tool_block": False})}
DEP_MIN, NOBLOCK_MAX_LOST, FLAT = 0.9, 8, 1.1


def summarise(records: list[dict]) -> dict:
    turns = [(i, t) for s in records for i, t in enumerate(s["turns"]) if "error" not in t]
    first = [t for i, t in turns if i == 0]
    dep = [t for i, t in turns if i > 0 and t["depends"]]
    ind = [t for i, t in turns if i > 0 and not t["depends"]]
    by_pos: dict[int, list[int]] = {}
    for i, t in turns:
        by_pos.setdefault(i + 1, []).append(t["prompt_tokens"])
    frac = lambda xs: f"{sum(x['right'] for x in xs)}/{len(xs)}"
    return {"first": frac(first), "dependent": frac(dep), "independent": frac(ind),
            "errors": sum("error" in t for s in records for t in s["turns"]),
            "prompt_tokens_by_turn": {p: round(sum(v) / len(v)) for p, v in sorted(by_pos.items())}}


def reading(rec: dict) -> dict:
    r"""Written first (BRIEF). **A VOID is per arm** (H1's lesson: one arm's first turns under 90 % void that arm, not the
    run). H2 PASSED iff `harness` gets ≥ 90 % of the dependent turns AND beats `base-history` on them (exact paired sign
    test, $p < 0.05$) AND its per-turn prompt is flat, $\bar p_5 \le 1.1\,\bar p_1$. `harness-noblock` passes iff it loses no
    more than 8 of the dependent turns to `harness` (5 %)."""
    from training.harness.release_gate import pair
    arms = rec.get("arms", {})
    s = {a: summarise(list(v.values())) for a, v in arms.items()}
    num = lambda x: tuple(int(v) for v in x.split("/"))
    void = {a for a in s if num(s[a]["first"])[1] and num(s[a]["first"])[0] < 0.9 * num(s[a]["first"])[1]}
    out = {"summary": s, "void_arms": sorted(void)}
    if "harness" not in arms or "harness" in void:
        out["reading"] = "VOID: the harness arm is void or missing"
        return out

    def dep(a):
        return {(sid, i): t for sid, x in arms[a].items() for i, t in enumerate(x["turns"]) if i > 0 and t.get("depends") and "error" not in t}
    H = dep("harness")
    r, n = num(s["harness"]["dependent"])
    toks = s["harness"]["prompt_tokens_by_turn"]
    last = max(toks)
    flat = toks[last] <= FLAT * toks[1]
    beats = None
    if "base-history" in arms and "base-history" not in void:
        B = dep("base-history")
        ids = sorted(H.keys() & B.keys())
        p = pair([{"id": str(i), "correct": H[i]["right"]} for i in ids], [{"id": str(i), "correct": B[i]["right"]} for i in ids],
                 "harness vs base-history")
        out["pair"], beats = p, p["state"] == "improvement"
    ok = r >= DEP_MIN * n and beats is not False and flat
    out.update(harness_dependent=f"{r}/{n}", flat=flat, tokens=toks,
               reading=(f"PASSED: {r}/{n} dependent, flat ({toks[1]} → {toks[last]})" + ("" if beats is None else ", beats base-history")
                        if ok and beats is not None else
                        f"FALSIFIED: {r}/{n} dependent (bar {DEP_MIN:.0%}), flat={flat}, beats base-history={beats}"))
    if "harness-noblock" in arms and "harness-noblock" not in void:
        N = dep("harness-noblock")
        nl = sum(H[i]["right"] and not N[i]["right"] for i in H if i in N)
        out["noblock"] = {"lost_to_harness": nl, "reading": "PASSED" if nl <= NOBLOCK_MAX_LOST else "FALSIFIED",
                          "tokens": s["harness-noblock"]["prompt_tokens_by_turn"]}
    elif "harness-noblock" in void:
        out["noblock"] = {"reading": "VOID (first turns under 90 %)"}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--train-seed", type=int, default=None)
    ap.add_argument("--arms", default="base-history,harness,harness-noblock")
    ap.add_argument("--out", default="h2.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.setdefault("arms", {})
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    if a.train_seed is not None:
        import hashlib
        from training.harness.release_gate import RECIPE
        corpus = DATA / "train_harness.jsonl"
        print(f"[tracker] training {ADAPTER} on {a.base} from {corpus}", flush=True)
        rc = subprocess.call([sys.executable, "-m", "training.harness.train_one", "--base", a.base, "--train", str(corpus),
                              "--out-dir", ADAPTER, "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                              "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"]), "--seed", str(a.train_seed)])
        if rc != 0:
            rec["stopped"] = f"training failed rc={rc}"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
            return 1
        rec["member"] = {"adapter": ADAPTER, "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
                         "adapter_sha256": hashlib.sha256(Path(ADAPTER, "adapter_model.safetensors").read_bytes()).hexdigest()}
        subprocess.call(["tar", "czf", "adapters_out.tgz", ADAPTER])
        rec["trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
        print("[tracker] trained and packed — stopping before serving, as asked", flush=True)
        return 0
    sessions = [json.loads(l) for l in (DATA / "eval.jsonl").read_text().splitlines() if l.strip()]
    arms = [x for x in a.arms.split(",") if x]
    from transformers import AutoTokenizer
    from examples.school.gateway import vllm_generator
    from examples.tracker import generate_sessions as gs
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    lora = ["--enable-lora", "--max-lora-rank", "16", "--max-loras", "1", "--lora-modules", f"{MEMBER}={ADAPTER}"] \
        if any(ARM_SPEC[x][0] for x in arms) else []
    srv = ar.serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", *lora])
    try:
        if not ar.wait_ready(srv, minutes=20):
            rec["stopped"] = "the server never came up"; save(); return 1
        if lora:
            rec["G1"] = identity(a.base, MEMBER, tok)
            print(f"[tracker] G1 {MEMBER}: {'applied' if rec['G1']['applied'] else 'NOT APPLIED'}", flush=True)
            save()
            if not rec["G1"]["applied"]:
                rec["stopped"] = "G1: the member is not applied"; save(); return 1
        for arm in arms:
            member, kw = ARM_SPEC[arm]
            gen = vllm_generator(member or a.base, tok)
            slot = rec["arms"].setdefault(arm, {})
            for i, s in enumerate(sessions, 1):
                if s["session_id"] in slot:
                    continue
                slot[s["session_id"]] = {"kind": s["kind"], "turns": gs.play(s, gen, **kw)}
                if i % 10 == 0 or i == len(sessions):
                    save()
                    sm = summarise(list(slot.values()))
                    print(f"[tracker] {arm} {i}/{len(sessions)} · first {sm['first']} · dependent {sm['dependent']} · "
                          f"independent {sm['independent']} · tokens {sm['prompt_tokens_by_turn']}", flush=True)
    finally:
        ar.stop(srv)
    rec["reading"] = reading(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[tracker] {rec['reading']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
