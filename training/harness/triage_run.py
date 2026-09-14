"""P31 — the killing arm: can the base do this job at all, with tools?

WHY IT IS BOUGHT FIRST. `docs/CASE-TRIAGE.md` puts this before every other phase for
a reason this project has paid for twice. A baseline sitting at the ceiling makes
every arm tie and the tie reads as success; **a baseline sitting at the floor is the
same expense in the other direction** — no adapter placed over it can move anything,
and the training run that discovers this costs a day.

So: the base model, no adapter, against the triage suite, through the real proxy and
the real agent loop. If it cannot beat the majority class, the next purchase is a
different base rather than a training run.

IT BRINGS UP THE WHOLE PATH ITSELF because that is the path being tested: vLLM, the
proxy, and an OpenAI client that sends `tools=[…]` and executes what comes back.
Anything that only works when a piece is stubbed is not a result about the system.

    python3 -m training.harness.triage_run --base Qwen/Qwen2.5-3B-Instruct --n 30
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

OUT = Path("triage_results.json")


def _wait(url: str, minutes: int, proc=None) -> bool:
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            print(f"[run] {url} exited with {proc.returncode}", flush=True)
            return False
        try:
            urllib.request.urlopen(url, timeout=5).read()
            return True
        except Exception:
            time.sleep(5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", action="append", default=[],
                    help="name=path; omit entirely for the base-only arm")
    ap.add_argument("--arms", default="base",
                    help="comma-separated model names to score; `base` means the "
                         "base model under its own name")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=717171)
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    pool = dict(a.split("=", 1) for a in args.adapter)
    missing = [n for n, p in pool.items()
               if not (Path(p) / "adapter_model.safetensors").exists()]
    if missing:
        print(f"[run] no weights for {missing}")
        return 1

    cmd = ["vllm", "serve", args.base, "--dtype", "bfloat16"]
    if pool:
        cmd += ["--enable-lora", "--max-lora-rank", "16",
                "--max-loras", str(len(pool)), "--lora-modules",
                *[f"{n}={p}" for n, p in pool.items()]]
    print("[run] " + " ".join(cmd), flush=True)
    vlog = open("vllm.log", "w")
    v = subprocess.Popen(cmd, stdout=vlog, stderr=subprocess.STDOUT)

    px = None
    results = {"base": args.base, "pool": list(pool), "arms": {}}
    if OUT.exists():
        try:
            results["arms"] = json.loads(OUT.read_text()).get("arms", {})
            print(f"[resume] arms on disk: {list(results['arms'])}", flush=True)
        except json.JSONDecodeError:
            pass

    try:
        if not _wait("http://127.0.0.1:8000/health", 15, v):
            results["arms"]["server"] = {"status": "never came up"}
            OUT.write_text(json.dumps(results, indent=2))
            return 1
        print("[run] vllm up", flush=True)

        px = subprocess.Popen([sys.executable, "-u", "-m",
                               "training.harness.openai_proxy",
                               "--upstream", "http://127.0.0.1:8000", "--port", "8001"],
                              stdout=open("proxy.log", "w"), stderr=subprocess.STDOUT)
        if not _wait("http://127.0.0.1:8001/v1/models", 2, px):
            results["arms"]["proxy"] = {"status": "never came up"}
            OUT.write_text(json.dumps(results, indent=2))
            return 1
        print("[run] proxy up", flush=True)

        for arm in [a.strip() for a in args.arms.split(",") if a.strip()]:
            model = args.base if arm == "base" else arm
            if (results["arms"].get(arm) or {}).get("n"):
                print(f"[arm] {arm} already scored", flush=True)
                continue
            print(f"[arm] {arm} -> {model}", flush=True)
            r = subprocess.run(
                [sys.executable, "-u", "-m", "training.harness.agent_sim",
                 "--base-url", "http://127.0.0.1:8001/v1", "--model", model,
                 "--n", str(args.n), "--seed", str(args.seed),
                 "--max-turns", str(args.max_turns),
                 "--max-tokens", str(args.max_tokens),
                 "--out", f"arm_{arm}.json"], capture_output=True, text=True)
            print(r.stdout[-1200:], flush=True)
            p = Path(f"arm_{arm}.json")
            if p.exists():
                results["arms"][arm] = json.loads(p.read_text())
            else:
                results["arms"][arm] = {"status": "produced nothing",
                                        "stderr": r.stderr[-400:]}
            OUT.write_text(json.dumps(results, indent=2))

        print(f"\n{'arm':<16}{'human':>12}{'bar':>8}{'calls':>8}{'refused':>9}"
              f"{'undecided':>11}")
        for arm, v_ in results["arms"].items():
            if "human_accuracy" not in v_:
                continue
            print(f"{arm:<16}{v_['human_correct']}/{v_['human_n']:<8}"
                  f"{v_['human_majority_class_bar']:>8.3f}{v_['calls']:>8}"
                  f"{v_['refused']:>9}{v_['undecided']:>11}")
        print("\nThe number that decides this phase is the human-message accuracy "
              "against its bar.\nBelow it, an adapter over this base cannot help and "
              "the next purchase is a different base.")
        results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        OUT.write_text(json.dumps(results, indent=2))
    finally:
        for p_ in (px, v):
            if p_ is None:
                continue
            p_.terminate()
            try:
                p_.wait(timeout=30)
            except subprocess.TimeoutExpired:
                p_.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
