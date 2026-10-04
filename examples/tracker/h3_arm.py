r"""H3 — the tracker member's second corpus against its first: `tr-s1` (wording widened in every role, a block-less third of
EACH role) against `tr-s0` (H2's member), both served with the operational memory, on a FRESH held-out suite. Pre-registered
in results/H3-tracker-corpus-v2-20260929/BRIEF.md; the suite is `examples.tracker.generate_sessions --suite h3`.

    python -m examples.tracker.h3_arm --train-seed 0 --out train_tr_s1.json            # one L4: tr-s1 on the h3 corpus
    python -m examples.tracker.h3_arm --arms s0-harness,s1-harness,s1-noblock --out h3.json

The baseline is our own previous member, never the bare base (H2 measured that one: 4/160). Per turn: right iff the
gateway's calls include the call the turn needs — `turn_right_h3`, which also counts a page read that returned the
statement asked for (fixed here, before the run, not after it).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from examples.tracker.session_arm import summarise

BASE = "google/gemma-4-E4B-it"
DATA = Path("examples/tracker/data_sessions_h3")
MEMBERS = {"tr-s0": "adapters/tracker-wf-s0", "tr-s1": "adapters/tracker-wf-s1"}
ARM_SPEC = {"s0-harness": ("tr-s0", {"harness": True}), "s1-harness": ("tr-s1", {"harness": True}),
            "s1-noblock": ("tr-s1", {"harness": True, "tool_block": False})}
DEP_MIN, FIRST_MIN, CEILING, MAX_LOST, NOBLOCK_MAX_LOST, FLAT = 0.9, 0.9, 0.95, 3, 8, 1.1


def reading(rec: dict) -> dict:
    r"""Written first (BRIEF). Every arm here is a TRAINED member, so the per-arm VOID applies to each (first turns under
    90 % — the member is broken, not the conversation); it is never asked of an untrained baseline (H2's lesson).

    H3a, the corpus: HEADROOM if `s0-harness` gets under 95 % of the dependent turns, else NO HEADROOM (reported, never a
    pass). With headroom, PASSED iff `s1-harness` ≥ 90 % AND the pair against `s0-harness` is an improvement (exact sign
    test, $p < 0.05$) AND it loses at most 3 turns `s0` got right AND its prompt is flat, $\bar p_5 \le 1.1\,\bar p_1$.
    H3b, block-less: PASSED iff `s1-noblock` loses at most 8 of the dependent turns `s1-harness` gets right (5 %), in
    EVERY role — H2's no-block learned only the role its rows came from."""
    from training.harness.release_gate import pair
    arms = rec.get("arms", {})
    s = {a: summarise(list(v.values())) for a, v in arms.items()}
    num = lambda x: tuple(int(v) for v in x.split("/"))
    void = sorted(a for a in s if num(s[a]["first"])[1] == 0 or num(s[a]["first"])[0] < FIRST_MIN * num(s[a]["first"])[1])
    out: dict = {"summary": s, "void_arms": void}

    def dep(a):
        return {(sid, i): (x["kind"], t) for sid, x in arms[a].items() for i, t in enumerate(x["turns"])
                if i > 0 and t.get("depends") and "error" not in t}
    if not {"s0-harness", "s1-harness"} <= arms.keys() or {"s0-harness", "s1-harness"} & set(void):
        out["h3a"] = "VOID: an arm of the pair is void or missing"
    else:
        S0, S1 = dep("s0-harness"), dep("s1-harness")
        ids = sorted(S0.keys() & S1.keys())
        r0, r1 = sum(S0[i][1]["right"] for i in ids), sum(S1[i][1]["right"] for i in ids)
        lost = sum(S0[i][1]["right"] and not S1[i][1]["right"] for i in ids)
        p = pair([{"id": str(i), "correct": S1[i][1]["right"]} for i in ids], [{"id": str(i), "correct": S0[i][1]["right"]} for i in ids],
                 "tr-s1 vs tr-s0")
        toks = s["s1-harness"]["prompt_tokens_by_turn"]
        flat = bool(toks) and toks[max(toks)] <= FLAT * toks[min(toks)]
        out.update(pair=p, s0_dependent=f"{r0}/{len(ids)}", s1_dependent=f"{r1}/{len(ids)}", lost=lost, flat=flat, tokens=toks)
        if r0 >= CEILING * len(ids):
            out["h3a"] = f"NO HEADROOM: tr-s0 already gets {r0}/{len(ids)} on the fresh suite"
        else:
            ok = r1 >= DEP_MIN * len(ids) and p["state"] == "improvement" and lost <= MAX_LOST and flat
            out["h3a"] = (f"{'PASSED' if ok else 'FALSIFIED'}: tr-s1 {r1}/{len(ids)} against tr-s0 {r0}/{len(ids)} "
                          f"({p['only_a']}:{p['only_b']}, p={p['p_value']}), lost {lost}, flat={flat}")
    if "s1-noblock" in arms and "s1-harness" in arms and not {"s1-noblock", "s1-harness"} & set(void):
        H, N = dep("s1-harness"), dep("s1-noblock")
        by_kind: dict[str, int] = {}
        for i in H:
            if i in N and H[i][1]["right"] and not N[i][1]["right"]:
                by_kind[H[i][0]] = by_kind.get(H[i][0], 0) + 1
        nl = sum(by_kind.values())
        right_by_kind = {k: f"{sum(N[i][1]['right'] for i in N if N[i][0] == k)}/{sum(N[i][0] == k for i in N)}"
                         for k in sorted({v[0] for v in N.values()})}
        out["h3b"] = (f"{'PASSED' if nl <= NOBLOCK_MAX_LOST else 'FALSIFIED'}: block-less loses {nl} to the block "
                      f"(bar {NOBLOCK_MAX_LOST}); by role {right_by_kind}")
    elif "s1-noblock" in void:
        out["h3b"] = "VOID: s1-noblock's first turns under 90 %"
    out["reading"] = f"H3a {out['h3a']} · H3b {out.get('h3b', 'not run')}"
    return out


def main(argv=None, *, doc=__doc__, data=None, members=None, arm_spec=None, read=None, train_member="tr-s1",
         default_arms="s0-harness,s1-harness,s1-noblock", default_out="h3.json", tag="tracker3",
         corpus_file="train_harness.jsonl", eval_data=None, scorer=None) -> int:
    """H3's runner; H4 (examples/tracker/h4_arm.py) calls it with its own suite, members, arms and reading."""
    data, members, arm_spec, read = data or DATA, members or MEMBERS, arm_spec or ARM_SPEC, read or reading
    ap = argparse.ArgumentParser(description=doc, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--train-seed", type=int, default=None)
    ap.add_argument("--arms", default=default_arms)
    ap.add_argument("--out", default=default_out)
    a = ap.parse_args(argv)
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.setdefault("arms", {})
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    if a.train_seed is not None:
        import hashlib
        from training.harness.release_gate import RECIPE
        corpus, adapter = data / corpus_file, members[train_member]
        print(f"[{tag}] training {adapter} on {a.base} from {corpus}", flush=True)
        rc = subprocess.call([sys.executable, "-m", "training.harness.train_one", "--base", a.base, "--train", str(corpus),
                              "--out-dir", adapter, "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                              "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"]), "--seed", str(a.train_seed)])
        if rc != 0:
            rec["stopped"] = f"training failed rc={rc}"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
            return 1
        rec["member"] = {"adapter": adapter, "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
                         "adapter_sha256": hashlib.sha256(Path(adapter, "adapter_model.safetensors").read_bytes()).hexdigest()}
        subprocess.call(["tar", "czf", "adapters_out.tgz", adapter])
        rec["trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
        print(f"[{tag}] trained and packed — stopping before serving, as asked", flush=True)
        return 0
    sessions = [json.loads(l) for l in ((eval_data or data) / "eval.jsonl").read_text().splitlines() if l.strip()]
    arms = [x for x in a.arms.split(",") if x]
    from transformers import AutoTokenizer
    from examples.school.gateway import vllm_generator
    from examples.tracker import generate_sessions as gs
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    served = {m: members[m] for m in dict.fromkeys(arm_spec[x][0] for x in arms)}
    srv = ar.serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", "--enable-lora", "--max-lora-rank", "16",
                            "--max-loras", str(len(served)), "--lora-modules", *[f"{m}={d}" for m, d in served.items()]])
    try:
        if not ar.wait_ready(srv, minutes=20):
            rec["stopped"] = "the server never came up"; save(); return 1
        rec["G1s"] = {m: identity(a.base, m, tok) for m in served}
        print(f"[{tag}] G1 {({m: g['applied'] for m, g in rec['G1s'].items()})}", flush=True)
        save()
        if not all(g["applied"] for g in rec["G1s"].values()):
            rec["stopped"] = "G1: a member is not applied"; save(); return 1
        for arm in arms:
            member, kw = arm_spec[arm]
            gen = vllm_generator(member, tok)
            slot = rec["arms"].setdefault(arm, {})
            for i, s in enumerate(sessions, 1):
                if s["session_id"] in slot and not any("error" in x for x in slot[s["session_id"]]["turns"]):
                    continue                                 # resumed: a session with a transport error is played again
                slot[s["session_id"]] = {"kind": s["kind"], **({"out": s["out"]} if s.get("out") else {}),
                                         "turns": gs.play(s, gen, scorer=scorer or gs.turn_right_h3, **kw)}
                if i % 10 == 0 or i == len(sessions):
                    save()
                    sm = summarise(list(slot.values()))
                    print(f"[{tag}] {arm} {i}/{len(sessions)} · first {sm['first']} · dependent {sm['dependent']} · "
                          f"independent {sm['independent']} · errors {sm['errors']} · tokens {sm['prompt_tokens_by_turn']}", flush=True)
    finally:
        ar.stop(srv)
    rec["reading"] = read(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[{tag}] {rec['reading']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
