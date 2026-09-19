"""Milestone 1 — the pool on another base: every released member retrained and re-released.

THE QUESTION (one unknown: the base). `email-full` and `desk-commitment` are released on
`Qwen2.5-3B-Instruct`. The family is now Qwen 3.x (docs/PLAN.md §0), and D2 **[ran]**
removed the reason it could not be: the adapter vLLM ignored was *named* for the text-only
class. Do the same corpora, under the unchanged recipe, give members on `Qwen3.5-4B` that
tie or beat their own Qwen 2.5 releases?

THE ORDER IS THE KILL ORDER, in one session:

    train both         a subprocess each, named for the class that serves them (train_one)
    G1 identity        a REAL adapter is `applied` — D2's was a 60-step toy. NOT APPLIED → stop,
                       nothing is scored: every number after it would measure the base
    G2, G2'            tools reachable through the proxy; `auto` routes each by its question
    base arm           per suite — the headroom arm on the NEW base, never inherited from 2.5
    member arm         per suite, paired against the recorded Qwen 2.5 run on the same cases

THE MATHEMATICS (docs/FOUNDATIONS.md §9.2). For a member, with $b$ cases only the new run
gets right and $c$ only the recorded one,

    p = 2 · Σ_{k ≤ min(b,c)} C(b+c, k) · 2^-(b+c)

`moved` iff every gate holds and each member **ties or beats** its recorded release
(`state` in tie / improvement) and beats the new base. A member that *loses* to its own
2.5 release keeps the pool on 2.5 for that region — written before the run, in the brief.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from training.harness import suites
from training.harness.accept_rank import draft_arm, serve, stop, summarise, wait_ready
from training.harness.pool_second import route_live
from training.harness.release_gate import RECIPE, pair, sha256
from training.harness.verify_substrate import identity, tools_reachable

MEMBERS = {
    "email-full": {"corpus": "training/harness/data_ef/train.jsonl", "suite": "email",
                   "recorded": ("results/P57-release-20260917/release.json", "email-full"),
                   "probe": ("Message msg-000 in thread thr-000\nFrom: A <a@x.com>\nSubject: hello\n"
                             "Preview: (waiting)\n\nIs this important?")},
    "desk-commitment": {"corpus": "training/harness/data_desk/train.jsonl", "suite": "desk",
                        "recorded": ("results/P64-second-member-20260918/pool_second.json",
                                     "desk-commitment"),
                        "probe": None},          # the suite's first case, read at run time
}


def verdict(rec: dict) -> dict:
    names = list(MEMBERS)
    g1 = all(rec.get("G1", {}).get(m, {}).get("applied") for m in names)
    g2 = all(rec.get("G2", {}).get(m, {}).get("reachable") for m in names)
    routes = all(rec.get("G2_auto", {}).get(m, {}).get("served") == m for m in names)
    per = {}
    for m in names:
        prs = {p["pair"]: p for p in rec.get("pairs", {}).get(m, [])}
        per[m] = {"vs_recorded": prs.get("new vs recorded", {}).get("state"),
                  "vs_base": prs.get("new vs base", {}).get("state")}
    holds = all(v["vs_recorded"] in ("tie", "improvement") and v["vs_base"] == "improvement"
                for v in per.values())
    out = {"G1": g1, "G2": g2, "auto_routes": routes, "members": per,
           "moved": bool(g1 and g2 and routes and holds)}
    if out["moved"]:
        out["reading"] = "MOVED: both members released on the new base, each holding its recorded run"
    elif not g1:
        out["reading"] = "STOPPED AT G1: a full-recipe adapter is not applied on this base"
    else:
        lost = [m for m, v in per.items() if v["vs_recorded"] == "REGRESSION"]
        out["reading"] = ("NOT MOVED: " + (f"{lost} lose to their own recorded release" if lost
                          else f"gates {[k for k in ('G2', 'auto_routes') if not out[k]]} or a member does not beat the new base"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--tag", default="q35", help="suffix of the adapter directories")
    ap.add_argument("--max-tokens", type=int, default=160)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--only", action="append", default=[],
                    help="train only this member in this session (repeatable). One member takes ~45 "
                         "minutes and a session lives sixty, so the pool is trained a member a session; "
                         "adapters carried in are never retrained")
    ap.add_argument("--stop-after-training", dest="train_only", action="store_true",
                    help="end the session once every adapter is trained, packed and said so: a Colab "
                         "session lives sixty minutes [ran] 2026-09-19 and one member takes ~45 to train")
    ap.add_argument("--out", default="pool_base.json")
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=args.base, recipe=RECIPE, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    for k in ("arms", "G1", "G2", "G2_auto", "pairs", "members"):
        rec.setdefault(k, {})

    def save():
        out.write_text(json.dumps(rec, indent=1))

    def end(why: str | None = None) -> int:
        if why:
            rec["stopped"] = why
        rec["verdict"] = verdict(rec)
        rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        print(f"[pool] {rec['verdict']['reading']}", flush=True)
        dirs = [v["adapter"] for v in rec["members"].values() if Path(v["adapter"]).exists()]
        if dirs:
            subprocess.call(["tar", "czf", "adapters_out.tgz", *dirs])
            print("[pool] adapters packed: adapters_out.tgz", flush=True)
        return 0 if rec["verdict"]["moved"] else 1

    save()
    unknown = [m for m in args.only if m not in MEMBERS]
    if unknown:
        print(f"[pool] --only {unknown} names no member of {sorted(MEMBERS)}", flush=True)
        return 2
    if args.only and not args.train_only:
        print("[pool] --only trains part of the pool, so it cannot be scored: add --stop-after-training", flush=True)
        return 2
    for m, spec in MEMBERS.items():
        if args.only and m not in args.only:
            continue
        path = f"adapters/{m}-{args.tag}"
        rec["members"][m] = {"adapter": path, "corpus": spec["corpus"],
                             "corpus_sha256": sha256(Path(spec["corpus"]))}
        if not Path(path, "adapter_model.safetensors").exists():
            print(f"[pool] training {m} on {args.base} from {spec['corpus']}", flush=True)
            rc = subprocess.call([sys.executable, "-m", "training.harness.train_one", "--base", args.base,
                                  "--train", spec["corpus"], "--out-dir", path,
                                  "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                                  "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"])])
            if rc != 0:
                return end(f"training {m} failed rc={rc}")
        rec["members"][m]["adapter_sha256"] = sha256(Path(path, "adapter_model.safetensors"))
        note = Path(path, "rekey.json")
        rec["members"][m]["named_for_serving"] = json.loads(note.read_text()) if note.exists() else None
        # EVERY ADAPTER IS PACKED THE MOMENT IT EXISTS, and the results file says so, so the
        # chain can bring it home while the session still answers. On a hybrid 3.x base a
        # member takes ~50 minutes to train on an L4 against ~6 on the 3B, and attempt 1
        # lost one to a session that ended with the weights on the card [ran] 2026-09-19.
        # Carried back in as `adapters.tgz`, the loop above skips what is already trained.
        done = [v["adapter"] for v in rec["members"].values() if Path(v["adapter"], "adapter_model.safetensors").exists()]
        subprocess.call(["tar", "czf", "adapters_out.tgz", *done])
        rec["packed"] = len(done)
        save()

    if args.train_only:
        # NOT A VERDICT, AND THE FILE MUST NOT LOOK LIKE ONE: no `finished`, no `verdict` — the chain
        # reads `"trained_only"` as the end of THIS session and the next one carries the weights in.
        rec["trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        print(f"[pool] trained and packed {rec.get('packed')} — stopping before serving, as asked", flush=True)
        return 0

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.base)
    served = {m: v["adapter"] for m, v in rec["members"].items()}
    p = serve(args.base, ["--max-model-len", str(args.max_model_len), "--gpu-memory-utilization", "0.90",
                          "--enable-lora", "--max-lora-rank", "16", "--max-loras", "2",
                          "--lora-modules", *[f"{k}={v}" for k, v in served.items()]])
    proxy = None
    try:
        if not wait_ready(p):
            return end("the base never came up")
        for m in served:
            rec["G1"][m] = identity(args.base, m, tok)
            print(f"[pool] G1 {m}: {rec['G1'][m]['differs']}/{rec['G1'][m]['probed']} differ → "
                  f"{'applied' if rec['G1'][m]['applied'] else 'NOT APPLIED'}", flush=True)
            save()
        if not all(v.get("applied") for v in rec["G1"].values()):
            return end("G1: a member is not applied — nothing after this would measure a member")

        proxy = subprocess.Popen([sys.executable, "-m", "training.harness.openai_proxy", "--upstream",
                                  "http://127.0.0.1:8000", "--port", "8001", "--prune", "--member-prompt",
                                  "--auto", "auto"], stdout=open("proxy.log", "a"), stderr=subprocess.STDOUT)
        time.sleep(4)
        loaded = {}
        for m, spec in MEMBERS.items():
            suite = suites.load(spec["suite"])
            loaded[m] = (suite, suite.cases(suite.eval_n, suite.eval_seed))
            rec["G2"][m] = tools_reachable("http://127.0.0.1:8001", m)
            probe = spec["probe"] or loaded[m][1][0].user
            rec["G2_auto"][m] = route_live("http://127.0.0.1:8001", probe)
            print(f"[pool] G2 {m}: {rec['G2'][m]} · auto -> {rec['G2_auto'][m].get('served')}", flush=True)
            save()

        for m, (suite, cases) in loaded.items():
            for arm, model in ((f"base:{suite.name}", args.base), (m, m)):
                a = rec["arms"].setdefault(arm, {"model": model, "records": {}})
                recs = draft_arm(model, tok, suite, cases, args.max_tokens, args.concurrency, a["records"], save)
                a.update(summarise(recs))
                print(f"[pool] arm {arm}: {a['correct']}/{a['n']} errors {a['errors']}", flush=True)
                save()
            path, name = MEMBERS[m]["recorded"]
            old = json.loads(Path(path).read_text())["arms"][name]["records"]
            old = old if isinstance(old, list) else list(old.values())
            new = list(rec["arms"][m]["records"].values())
            base = list(rec["arms"][f"base:{suite.name}"]["records"].values())
            rec["pairs"][m] = [pair(new, old, "new vs recorded"), pair(new, base, "new vs base")]
            for pr in rec["pairs"][m]:
                print(f"[pool] {m} · {pr['pair']}: {pr['state']} ({pr['only_a']}:{pr['only_b']}, "
                      f"p={pr['p_value']})", flush=True)
            save()
    finally:
        if proxy is not None:
            proxy.terminate()
        stop(p)
    return end()


if __name__ == "__main__":
    raise SystemExit(main())
