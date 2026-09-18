"""Milestone 5, synthetic — the second useful member, released and co-resident.

WHY THIS IS THE MILESTONE. "Pool" has meant one useful member since P40: the fluids
expert followed its protocol and got the physics wrong 78 times in 90. The desk's
`commitment` region has a trained expert that scores 240/240 (P55b `g600`) — and its
weights were never brought back from the card. So the second member enters through
the same door as the first (Phase 1): trained from its corpus with the released
recipe, scored on its suite, paired against the recorded run, and only then served
beside `email-full` on one base, routed by the question it answers.

WHAT ONE SESSION MEASURES, IN ORDER, EACH PERSISTED AS IT LANDS:

    train      `desk-commitment` from `data_desk/train.jsonl` (release_gate.RECIPE)
    serve      base + email-full + desk-commitment in one vLLM
    G1         identity for both members (verify_substrate.identity, empty-arm rule)
    G2         tools reachable through the proxy for both (`--prune --member-prompt`)
    G2'        `auto` routes a desk prompt to desk-commitment and a listing to email-full —
               the three-region router, live, read off the reply's `model`
    score      desk suite, 240 cases: base and desk-commitment in corpus mode
    pairs      desk-commitment vs recorded g600 (must tie, §9.2); vs base (must win)
    manifest   releases/desk-commitment@v1.json when every gate passes

PRE-REGISTERED. `released` iff G1 and G2 pass for both members, G2' routes both
prompts to the right member, the new arm ties the recorded 240/240 ($p \ge 0.05$ on
discordant pairs) and beats the base ($p < 0.05$). Written first: a tie with the base
or a loss to the recorded run means the training chain does not reproduce this region
and the member is not released.

    python3 -m training.harness.pool_second --email adapters/email-full \
        --recorded results/P55b-desk-ranking-20260917/p55b.json --recorded-arm g600
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from training.harness import bar, suites
from training.harness.accept_rank import draft_arm, serve, stop, summarise, wait_ready
from training.harness.release_gate import RECIPE, pair, sha256
from training.harness.verify_substrate import identity, tools_reachable

OUT = Path("pool_second.json")
NAME = "desk-commitment"


def route_live(proxy: str, prompt: str) -> dict:
    """One `auto` request through the proxy; the member vLLM served is the reply's `model`."""
    payload = {"model": "auto", "temperature": 0, "max_tokens": 8,
               "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(proxy + "/v1/chat/completions", method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
        return {"served": out.get("model"), "ok": True}
    except urllib.error.HTTPError as e:
        return {"served": None, "ok": False, "http": e.code}
    except Exception as e:
        return {"served": None, "ok": False, "error": repr(e)[:120]}


def verdict(rec: dict) -> dict:
    g1 = all(v.get("applied") for v in rec.get("G1", {}).values()) and len(rec.get("G1", {})) == 2
    g2 = all(v.get("reachable") for v in rec.get("G2", {}).values()) and len(rec.get("G2", {})) == 2
    routes = rec.get("G2_auto", {})
    g2a = (routes.get("desk", {}).get("served") == NAME
           and routes.get("email", {}).get("served") == "email-full")
    pairs = {p["pair"]: p for p in rec.get("pairs", [])}
    ties = pairs.get("new vs recorded", {}).get("state") == "tie"
    beats = (pairs.get("new vs base", {}).get("state") == "improvement")
    out = {"G1": g1, "G2": g2, "auto_routes": g2a, "ties_recorded": ties, "beats_base": beats,
           "released": bool(g1 and g2 and g2a and ties and beats)}
    failed = [k for k, v in out.items() if k != "released" and not v]
    out["reading"] = ("RELEASED: a second useful member, co-resident and routed by its question"
                      if out["released"] else f"NOT RELEASED: failed {failed}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--email", default="adapters/email-full")
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--corpus", default="training/harness/data_desk/train.jsonl")
    ap.add_argument("--recorded", default="results/P55b-desk-ranking-20260917/p55b.json")
    ap.add_argument("--recorded-arm", dest="recorded_arm", default="g600")
    ap.add_argument("--suite", default="desk")
    ap.add_argument("--n", type=int, default=0, help="desks to generate; 0 = the suite's eval_n "
                    "(960 desks → 240 commitment cases). Attempt 1 passed 240 and scored 60 [ran]")
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(name=NAME, base=args.base, recipe=RECIPE, corpus=args.corpus,
               corpus_sha256=sha256(Path(args.corpus)),
               started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    rec.setdefault("arms", {}); rec.setdefault("G1", {}); rec.setdefault("G2", {})

    def save():
        out.write_text(json.dumps(rec, indent=1))

    save()
    new = f"adapters/{NAME}"
    if not Path(new, "adapter_model.safetensors").exists():
        print(f"[pool] training {NAME} from {args.corpus}", flush=True)
        rc = subprocess.call([sys.executable, "-m", "training.code.train_one", "--base", args.base,
                              "--train", args.corpus, "--out-dir", new,
                              "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                              "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"])])
        if rc != 0:
            rec["stopped"] = f"training failed rc={rc}"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); return 1
    rec["adapter_sha256"] = sha256(Path(new, "adapter_model.safetensors"))
    save()

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.base)
    suite = suites.load(args.suite)
    cases = suite.cases(args.n or suite.eval_n, suite.eval_seed)
    print(f"[pool] {len(cases)} cases from {args.n or suite.eval_n} desks (seed {suite.eval_seed})", flush=True)
    recorded = json.loads(Path(args.recorded).read_text())["arms"][args.recorded_arm]["records"]
    recorded = recorded if isinstance(recorded, list) else list(recorded.values())
    rec["recorded"] = {"path": args.recorded, "arm": args.recorded_arm, "n": len(recorded),
                       "correct": sum(bool(r.get("correct")) for r in recorded)}

    adapters = {"email-full": args.email, NAME: new}
    p = serve(args.base, ["--max-model-len", str(args.max_model_len), "--gpu-memory-utilization", "0.90",
                          "--enable-lora", "--max-lora-rank", "16", "--max-loras", "2",
                          "--lora-modules", *[f"{k}={v}" for k, v in adapters.items()]])
    proxy = None
    try:
        if not wait_ready(p):
            rec["stopped"] = "the base never came up"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); return 1
        for m in adapters:
            rec["G1"][m] = identity(args.base, m, tok)
            print(f"[pool] G1 {m}: {rec['G1'][m]['differs']}/{rec['G1'][m]['probed']} differ → "
                  f"{'applied' if rec['G1'][m]['applied'] else 'NOT APPLIED'}", flush=True)
            save()
        proxy = subprocess.Popen([sys.executable, "-m", "training.harness.openai_proxy", "--upstream",
                                  "http://127.0.0.1:8000", "--port", "8001", "--prune", "--member-prompt",
                                  "--auto", "auto"], stdout=open("proxy.log", "a"), stderr=subprocess.STDOUT)
        time.sleep(4)
        for m in adapters:
            rec["G2"][m] = tools_reachable("http://127.0.0.1:8001", m)
            print(f"[pool] G2 {m}: {rec['G2'][m]}", flush=True)
        desk_prompt = cases[0].user
        email_prompt = ("Message msg-000 in thread thr-000\nFrom: A <a@x.com>\nSubject: hello\n"
                        "Preview: (waiting)\n\nIs this important?")
        rec["G2_auto"] = {"desk": route_live("http://127.0.0.1:8001", desk_prompt),
                          "email": route_live("http://127.0.0.1:8001", email_prompt)}
        print(f"[pool] G2' auto: desk -> {rec['G2_auto']['desk'].get('served')}, "
              f"listing -> {rec['G2_auto']['email'].get('served')}", flush=True)
        save()
        for name, model in [("base", args.base), (NAME, NAME)]:
            arm = rec["arms"].setdefault(name, {"model": model, "records": {}})
            recs = draft_arm(model, tok, suite, cases, args.max_tokens, args.concurrency, arm["records"], save)
            arm.update(summarise(recs))
            print(f"[pool] arm {name}: {arm['correct']}/{arm['n']} errors {arm['errors']}", flush=True)
            save()
    finally:
        if proxy is not None:
            proxy.terminate()
        stop(p)

    new_recs = list(rec["arms"][NAME]["records"].values())
    base_recs = list(rec["arms"]["base"]["records"].values())
    rec["pairs"] = [pair(new_recs, recorded, "new vs recorded"), pair(new_recs, base_recs, "new vs base")]
    for pr in rec["pairs"]:
        print(f"[pool] {pr['pair']}: {pr['state']} ({pr['only_a']}:{pr['only_b']}, p={pr['p_value']})", flush=True)
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[pool] {rec['verdict']['reading']}", flush=True)
    if rec["verdict"]["released"]:
        man = Path("releases") / f"{NAME}@v1.json"
        man.parent.mkdir(exist_ok=True)
        man.write_text(json.dumps({
            "name": NAME, "version": 1, "base": args.base, "recipe": RECIPE,
            "corpus": args.corpus, "corpus_sha256": rec["corpus_sha256"],
            "adapter_sha256": rec["adapter_sha256"],
            "prompt_sha": new_recs[0].get("prompt_sha") if new_recs else None,
            "suite": suite.name, "n": len(cases),
            "score": {"correct": rec["arms"][NAME]["correct"], "human_correct": rec["arms"][NAME]["human_correct"]},
            "recorded": rec["recorded"], "pairs": rec["pairs"], "run": str(out)}, indent=2))
        print(f"[pool] manifest written: {man}", flush=True)
    # THE WEIGHTS COME HOME OR THE RELEASE IS A NUMBER. Attempt 1 released a member
    # whose adapter stayed on the card and the chain stopped the session [ran] — the
    # same way P55b's grades were lost. The chain downloads `adapters_out.tgz`.
    subprocess.call(["tar", "czf", "adapters_out.tgz", new] + (
        [f"releases/{NAME}@v1.json"] if rec["verdict"]["released"] else []))
    print("[pool] adapters packed: adapters_out.tgz", flush=True)
    return 0 if rec["verdict"]["released"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
