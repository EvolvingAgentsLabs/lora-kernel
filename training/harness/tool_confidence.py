"""P47 — serve one expert and read the confidence at the END of its tool chain.

WHY THIS ARM AND NOT THE TYPED ADAPTER. P44 measured the confidence `email-full`
attaches to its answers **without tools** and found an AURC gap of 0.400, read as
room for a typed head. P46 then computed the ceiling: on the full inbox both arms
are already at it — room 0.030 and 0.007 — and on the human subset the best possible
listing-only predictor is a **constant**, one group, not rankable **[ran]**. A
constant confidence routes nothing, so that arm was cancelled before the GPU.

**With the tools the ceiling collapses.** `thread_history` answers *did I write in
this thread*, `sender_stats` answers *is this a frequent counterpart* — the two facts
the definition needs and the listing withholds by construction. Every fact becomes
recoverable, the truth becomes decidable, and the ceiling falls to the oracle floor,
so **the whole of whatever gap is measured here is claimable**.

Nobody has measured it. P43 established accuracy in this exact configuration —
260/351 = 0.741, exact p = 0.00036 **[ran]** — and never looked at the confidence,
because `triage_one` could not ask for logprobs until 2026-09-16.

ONE ARM. The base is not run: P44 already has it tool-free, and a base that makes one
call per case and refuses 85 of 140 is a different configuration rather than a
comparison. Arms are bought in sequence.

NOTHING IS TRAINED. The adapter is carried in.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from training.harness.stream import run_streaming

OUT = Path("tool_confidence.json")

#: The gate, pre-registered in `results/P47-tool-confidence-20260916/BRIEF.md`
#: before the run. Written here so the decision is code rather than a reading.
BUYS = 0.10
CANCELS = 0.05
MIN_READ_RATE = 0.80


def arm_verdict(gap: float | None, read_rate: float) -> str:
    """What this run decides about the typed arm, from the numbers alone.

    THE MIDDLE ROW IS THE ONE THAT MATTERS. A confidence that is miscalibrated but
    *rankable* is repaired by temperature scaling, which costs no training at all —
    naming that outcome in advance is what stops a bad ECE being spent on a model.
    P44 wrote the same row and it is what made its result readable.
    """
    if read_rate < MIN_READ_RATE:
        return ("VOID: the first token was not the decision often enough "
                f"({read_rate:.2f} read)")
    if gap is None:
        return "VOID: no confidence was read"
    if gap > BUYS:
        return "typed arm BOUGHT: the gap is real room and the ceiling is the floor"
    if gap < CANCELS:
        return "typed arm CANCELLED: the expert already orders its own errors"
    return "temperature scaling, NOT a typed head — rankable but miscalibrated"


def _wait(url: str, minutes: int, proc=None) -> bool:
    for _ in range(minutes * 12):
        if proc is not None and proc.poll() is not None:
            return False
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except Exception:
            time.sleep(5)
    return False


def _probe(model: str, port: int = 8001) -> str | None:
    body = json.dumps({"model": model, "max_tokens": 24, "temperature": 0,
                       "messages": [{"role": "user",
                                     "content": "Reply with one short sentence "
                                                "about email."}]}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["choices"][0]["message"]["content"]
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", default="email-full=adapters/email-full")
    ap.add_argument("--n", type=int, default=475)
    ap.add_argument("--seed", type=int, default=717171)
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--top-logprobs", type=int, default=20)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    name, path = args.adapter.split("=", 1)
    if not (Path(path) / "adapter_model.safetensors").exists():
        print(f"[conf] no weights at {path}")
        return 1

    cmd = ["vllm", "serve", args.base, "--dtype", "bfloat16", "--enable-lora",
           "--max-lora-rank", "16", "--max-loras", "1",
           "--lora-modules", f"{name}={path}"]
    print("[conf] " + " ".join(cmd), flush=True)
    v = subprocess.Popen(cmd, stdout=open("vllm.log", "w"),
                         stderr=subprocess.STDOUT)
    px = None
    results = {"base": args.base, "adapter": name, "n": args.n, "seed": args.seed,
               "top_logprobs": args.top_logprobs, "arms": {}}

    def save():
        OUT.write_text(json.dumps(results, indent=2))

    try:
        if not _wait("http://127.0.0.1:8000/health", 20, v):
            results["arms"]["server"] = {"status": "never came up"}
            save(); return 1
        print("[conf] vllm up", flush=True)
        px = subprocess.Popen([sys.executable, "-u", "-m",
                               "training.harness.openai_proxy",
                               "--upstream", "http://127.0.0.1:8000",
                               "--port", "8001"],
                              stdout=open("proxy.log", "w"),
                              stderr=subprocess.STDOUT)
        if not _wait("http://127.0.0.1:8001/v1/models", 3, px):
            results["arms"]["proxy"] = {"status": "never came up"}
            save(); return 1
        print("[conf] proxy up", flush=True)

        # C18. An adapter vLLM logs as loaded and does not apply would make this the
        # base's calibration published under the expert's name.
        applied = ((_probe(name) or "").strip()
                   != (_probe(args.base) or "").strip())
        results["identity_gate"] = {"differs_from_base": applied}
        print(f"[conf] gate {name}: "
              + ("applied" if applied else "IDENTICAL TO BASE — not applied"),
              flush=True)
        save()
        if not applied:
            print("[conf] STOPPED. This would be the base's number.", flush=True)
            results["stopped_at_gate"] = True
            save(); return 1

        rc, tail = run_streaming([sys.executable, "-u", "-m",
                                  "training.harness.agent_sim",
                                  "--base-url", "http://127.0.0.1:8001/v1",
                                  "--model", name, "--n", str(args.n),
                                  "--seed", str(args.seed),
                                  "--max-turns", str(args.max_turns),
                                  "--max-tokens", str(args.max_tokens),
                                  "--logprobs", str(args.top_logprobs),
                                  "--out", "arm_tools.json"])
        p = Path("arm_tools.json")
        results["arms"]["email-full-with-tools"] = (
            json.loads(p.read_text()) if p.exists()
            else {"status": "produced nothing", "returncode": rc,
                  "output": tail[-1200:]})
        results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        save()
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
