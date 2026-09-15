"""Two experts, one resident base, selected by the `model` field. The pool claim.

WHAT IS AND IS NOT ALREADY MEASURED. P26 showed two adapters registering as separate
model names and producing different text **[ran]**. That is two personalities. P36
showed one adapter clearing a real gate on its own subdomain **[ran]**. That is one
expert. **Neither is a pool**, and the thesis is specifically that the agentic system
is a pool of QLoRAs over one resident base.

So: `email-full` and `fluids-full` loaded into **one** vLLM, each scored on its own
suite through its own client and its own oracle, each against its own gate — and the
only thing that selects between them is the `model` field of an HTTP request.

THE TWO DOMAINS SHARE NOTHING BUT THE BASE. Different tools, different verifiers,
different bars: email is a binary verdict against a majority class, fluids is a
number against a mechanical oracle and a hand-written competitor. Sharing a gate
would have been easier and would have measured a suite rather than a pool.

EVERY ADAPTER IS GATED BEFORE IT IS SCORED. vLLM accepts a LoRA, logs that it loaded
it, and can serve the base anyway — measured on a named class in P33 **[ran]**. A
pool whose members were silently the same model would produce two respectable
numbers and mean nothing.

    python3 -m training.harness.pool_run --base Qwen/Qwen2.5-3B-Instruct \\
        --adapter email-full=adapters/email-full \\
        --adapter fluids-full=adapters/fluids-full
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from training.harness.bar import compare, verdict

OUT = Path("pool_results.json")


def _wait(url: str, minutes: int, proc=None) -> bool:
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            print(f"[pool] {url} exited with {proc.returncode}", flush=True)
            return False
        try:
            urllib.request.urlopen(url, timeout=5).read()
            return True
        except Exception:
            time.sleep(5)
    return False


def _probe(model: str, port: int = 8001) -> str | None:
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 24,
                       "messages": [{"role": "user",
                                     "content": "In one sentence, what are you?"}]})
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 data=body.encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return (json.loads(r.read())["choices"][0]["message"].get("content") or "")
    except Exception as e:
        print(f"[pool] probe of {model} failed: {e!r}"[:160], flush=True)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", action="append", default=[], help="name=path")
    ap.add_argument("--n-email", type=int, default=150)
    ap.add_argument("--n-fluids", type=int, default=90)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    pool = dict(a.split("=", 1) for a in args.adapter)
    missing = [n for n, p in pool.items()
               if not (Path(p) / "adapter_model.safetensors").exists()]
    if missing:
        print(f"[pool] no weights for {missing}")
        return 1

    cmd = ["vllm", "serve", args.base, "--dtype", "bfloat16", "--enable-lora",
           "--max-lora-rank", "16", "--max-loras", str(len(pool)), "--lora-modules",
           *[f"{n}={p}" for n, p in pool.items()]]
    print("[pool] " + " ".join(cmd), flush=True)
    v = subprocess.Popen(cmd, stdout=open("vllm.log", "w"),
                         stderr=subprocess.STDOUT)
    px = None
    results = {"base": args.base, "pool": list(pool), "arms": {}}

    try:
        if not _wait("http://127.0.0.1:8000/health", 20, v):
            results["arms"]["server"] = {"status": "never came up"}
            OUT.write_text(json.dumps(results, indent=2)); return 1
        print("[pool] vllm up", flush=True)
        px = subprocess.Popen([sys.executable, "-u", "-m",
                               "training.harness.openai_proxy",
                               "--upstream", "http://127.0.0.1:8000",
                               "--port", "8001"],
                              stdout=open("proxy.log", "w"),
                              stderr=subprocess.STDOUT)
        if not _wait("http://127.0.0.1:8001/v1/models", 3, px):
            results["arms"]["proxy"] = {"status": "never came up"}
            OUT.write_text(json.dumps(results, indent=2)); return 1
        print("[pool] proxy up", flush=True)

        # THE MEMBERS MUST DIFFER FROM THE BASE **AND FROM EACH OTHER**. Two names
        # over one silently-unapplied adapter would score twice and mean nothing;
        # two names over the SAME adapter would look like a pool and be one expert.
        base_text = _probe(args.base)
        texts = {n: _probe(n) for n in pool}
        gate = {n: {"differs_from_base": None if t is None
                    else t.strip() != (base_text or "").strip()}
                for n, t in texts.items()}
        names = list(pool)
        distinct = (len(names) < 2 or
                    len({(texts[n] or "").strip() for n in names}) == len(names))
        for n in names:
            print(f"[pool] gate {n}: "
                  + ("applied" if gate[n]["differs_from_base"]
                     else "IDENTICAL TO BASE — not applied"), flush=True)
        print(f"[pool] members differ from each other: {distinct}", flush=True)
        results["identity_gate"] = gate
        results["members_are_distinct"] = distinct
        OUT.write_text(json.dumps(results, indent=2))
        if not all(g["differs_from_base"] for g in gate.values()) or not distinct:
            print("[pool] STOPPED. Every number after this would measure something "
                  "other than a pool.", flush=True)
            results["stopped_at_gate"] = True
            OUT.write_text(json.dumps(results, indent=2)); return 1

        for name in pool:
            mod, extra = (("training.harness.agent_sim", ["--n", str(args.n_email)])
                          if "email" in name else
                          ("training.harness.fluids_sim", ["--n", str(args.n_fluids)]))
            print(f"[pool] scoring {name} with {mod.rsplit('.', 1)[-1]}", flush=True)
            r = subprocess.run([sys.executable, "-u", "-m", mod,
                                "--base-url", "http://127.0.0.1:8001/v1",
                                "--model", name, "--max-tokens", str(args.max_tokens),
                                *extra, "--out", f"arm_{name}.json"],
                               capture_output=True, text=True)
            print(r.stdout[-900:], flush=True)
            p = Path(f"arm_{name}.json")
            results["arms"][name] = (json.loads(p.read_text()) if p.exists()
                                     else {"status": "produced nothing",
                                           "stderr": r.stderr[-400:]})
            OUT.write_text(json.dumps(results, indent=2))

        print(f"\n{'member':<14}{'score':>12}{'gate':>10}{'calls':>8}{'refused':>9}")
        for name, a in results["arms"].items():
            if "human_correct" in a:            # email: a majority-class bar
                d = verdict(a["human_correct"], a["human_n"],
                            a["human_majority_class_bar"])
            elif "passed" in a:                 # fluids: a number against an oracle
                d = {"beats_the_bar": None, "accuracy": a["accuracy"]}
            else:
                continue
            a["gate"] = d
            score = (f"{a.get('human_correct', a.get('passed'))}/"
                     f"{a.get('human_n', a.get('n'))}")
            mark = {True: "clears", False: "no", None: "see brief"}[d["beats_the_bar"]]
            print(f"{name:<14}{score:>12}{mark:>10}"
                  f"{a.get('calls', 0):>8}{a.get('refused', 0):>9}")
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
