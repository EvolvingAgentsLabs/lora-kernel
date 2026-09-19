r"""A region measured to fail, back through the gate — on the base the pool now runs on.

`fluids-full` is `serve: out` in `route.REGIONS` on 11 of 90 **[ran]** P41, and that number was the
serving path: inline, as its corpus taught, the same adapter is 90 of 90 **[ran]** M7 arm 0b. The
mark changes when the member is back through a gate, and the pool has moved to `Qwen3.5-4B` since
**[ran]** M1 — so the member that is released is the one retrained there, from the same corpus with
the same recipe, and scored in corpus mode on the same 90 cases.

Three pairs, each an exact two-sided sign test on discordant pairs (`bar.compare`, FOUNDATIONS §7.1),
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$:

    new vs recorded   the 4B member against the 3B member's 90/90 — must not lose
    new vs base       the 4B member against the bare 4B — must win, or the corpus bought nothing
    new vs frontier   against the frontier's recorded 66/90 — the ceiling check, must not lose

A SESSION LIVES SIXTY MINUTES, so this runs as `pool_base` does: `--stop-after-training` ends the
first session with the adapter packed and said so; the next one carries it in and scores.
The proxy is NOT in this run (one unknown): its per-member call cap and the region's mark are what
change after a RELEASED verdict, and they are measured then.
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
from training.harness.release_gate import RECIPE, pair, sha256
from training.harness.verify_substrate import identity

REGIONS = {
    "fluids-full": {"corpus": "training/physics/data_ff/train.jsonl", "suite": "fluids",
                    "recorded": ("results/M7-arm0b-corpus-mode-20260919/corpus_mode.json", "fluids-full"),
                    "frontier": "results/P41-routing-20260915/frontier_fluids.json"},
}


def verdict(rec: dict) -> dict:
    applied = bool(rec.get("G1", {}).get("applied"))
    prs = {p["pair"]: p.get("state") for p in rec.get("pairs", [])}
    holds = (prs.get("new vs recorded") in ("tie", "improvement")
             and prs.get("new vs base") == "improvement"
             and prs.get("new vs frontier") in ("tie", "improvement"))
    out = {"G1": applied, "pairs": prs, "released": bool(applied and holds)}
    if not rec.get("G1"):
        out["reading"] = "NOTHING SERVED: no gate was reached"
    elif not applied:
        out["reading"] = "VOID: the adapter is not applied — nothing here is about the member"
    elif out["released"]:
        out["reading"] = "RELEASED: holds its recorded run, beats its bare base, does not lose to the frontier"
    else:
        ok = {"new vs recorded": ("tie", "improvement"), "new vs base": ("improvement",),
              "new vs frontier": ("tie", "improvement")}
        out["reading"] = "NOT RELEASED: " + ", ".join(f"{k} is {prs.get(k)}" for k, v in ok.items()
                                                       if prs.get(k) not in v)
    return out


def rescored(records: list[dict], by_id: dict) -> list[dict]:
    """A recorded arm under this run's rule: P41 stored `passed`, the pair needs `correct`."""
    return [{"id": r["id"], "correct": bool(r["correct"]) if "correct" in r
             else bool(by_id[r["id"]].verify(r.get("got")))} for r in records]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--member", default="fluids-full", choices=sorted(REGIONS))
    ap.add_argument("--base", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--tag", default="q35")
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--stop-after-training", dest="train_only", action="store_true")
    ap.add_argument("--out", default="region_release.json")
    a = ap.parse_args()
    spec, out = REGIONS[a.member], Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(member=a.member, base=a.base, recipe=RECIPE, corpus=spec["corpus"],
               corpus_sha256=sha256(Path(spec["corpus"])),
               started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    rec.setdefault("arms", {})

    def save():
        out.write_text(json.dumps(rec, indent=1))

    def end(why: str | None = None) -> int:
        if why:
            rec["stopped"] = why
        rec["verdict"] = verdict(rec)
        rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        print(f"[pool] {rec['verdict']['reading']}", flush=True)
        return 0 if rec["verdict"]["released"] else 1

    save()
    path = f"adapters/{a.member}-{a.tag}"
    if not Path(path, "adapter_model.safetensors").exists():
        print(f"[pool] training {a.member} on {a.base} from {spec['corpus']}", flush=True)
        rc = subprocess.call([sys.executable, "-m", "training.harness.train_one", "--base", a.base,
                              "--train", spec["corpus"], "--out-dir", path,
                              "--epochs", str(RECIPE["epochs"]), "--r", str(RECIPE["r"]),
                              "--alpha", str(RECIPE["lora_alpha"]), "--lr", str(RECIPE["lr"])])
        if rc != 0:
            return end(f"training {a.member} failed rc={rc}")
    rec["adapter"] = path
    rec["adapter_sha256"] = sha256(Path(path, "adapter_model.safetensors"))
    note = Path(path, "rekey.json")
    rec["named_for_serving"] = json.loads(note.read_text()) if note.exists() else None
    subprocess.call(["tar", "czf", "adapters_out.tgz", path])
    rec["packed"] = 1
    save()
    if a.train_only:
        rec["trained_only"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
        print("[pool] trained and packed 1 — stopping before serving, as asked", flush=True)
        return 0

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.base)
    suite = suites.load(spec["suite"])
    cases = suite.cases(suite.eval_n, suite.eval_seed)
    by_id = {c.id: c for c in cases}
    p = serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", "--enable-lora",
                       "--max-lora-rank", "16", "--lora-modules", f"{a.member}={path}"])
    try:
        if not wait_ready(p):
            return end("the base never came up")
        rec["G1"] = identity(a.base, a.member, tok)
        print(f"[pool] G1 {a.member}: {'applied' if rec['G1']['applied'] else 'NOT APPLIED'}", flush=True)
        save()
        if not rec["G1"]["applied"]:
            return end("G1: the member is not applied")
        for arm, model in (("base", a.base), (a.member, a.member)):
            r = rec["arms"].setdefault(arm, {"model": model, "records": {}})
            recs = draft_arm(model, tok, suite, cases, a.max_tokens, a.concurrency, r["records"], save)
            r.update(summarise(recs))
            print(f"[pool] arm {arm}: {r['correct']}/{r['n']} errors {r['errors']} "
                  f"calls {r.get('calls')} refused {r.get('refused')}", flush=True)
            save()
    finally:
        stop(p)

    new = list(rec["arms"][a.member]["records"].values())
    rpath, rname = spec["recorded"]
    old = json.loads(Path(rpath).read_text())["arms"][rname]["records"]
    old = rescored(old if isinstance(old, list) else list(old.values()), by_id)
    frontier = rescored(json.loads(Path(spec["frontier"]).read_text())["records"], by_id)
    rec["pairs"] = [pair(new, old, "new vs recorded"),
                    pair(new, list(rec["arms"]["base"]["records"].values()), "new vs base"),
                    pair(new, frontier, "new vs frontier")]
    for pr in rec["pairs"]:
        print(f"[pool] {a.member} · {pr['pair']}: {pr['state']} ({pr['only_a']}:{pr['only_b']}, "
              f"p={pr['p_value']})", flush=True)
    return end()


if __name__ == "__main__":
    raise SystemExit(main())
