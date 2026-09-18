"""P60 §3b — does vLLM apply a LoRA on the AWQ 32B? The arm that decides option A.

WHY THIS RUNS BEFORE ANYTHING IS TRAINED FOR REAL. Option A — a target trained on the
task — is served, like the pool, as a LoRA over a resident base; the target's base is
`Qwen2.5-32B-Instruct-AWQ`. C18 measured vLLM loading a LoRA on one base and serving
the base anyway **[ran]** P33. If the same happens over an AWQ base, option A cannot be
served this way, and M2's closure is signed with that reason rather than an argument.

THE ADAPTER IS TRAINED ON THE bf16 32B IN 4-BIT AND SERVED OVER THE AWQ BUILD. PEFT does
not train through AWQ kernels; the delta has the 32B's shapes either way, and the
approximation (a delta learned against NF4 weights applied to AWQ weights) is the one
a deployment would make. The identity gate is `verify_substrate.identity` — three
probes, both sides non-empty, at least two differ.

WHAT THE LOG SAYS IS RECORDED TOO. Every `lora`/`Punica` line vLLM prints is kept in
the verdict, so a `not applied` comes with the engine's own account of what it
skipped — the reading D2 needs, taken while the log is in hand.

    python3 -m training.harness.awq_lora_gate --out results/P60-deep-window-20260917/awq_gate.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from training.harness.accept_rank import serve, stop, wait_ready
from training.harness.verify_substrate import identity

OUT = Path("awq_gate.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-base", default="Qwen/Qwen2.5-32B-Instruct")
    ap.add_argument("--serve-base", default="Qwen/Qwen2.5-32B-Instruct-AWQ")
    ap.add_argument("--adapter", default="adapters/tiny32")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = {"train_base": args.train_base, "serve_base": args.serve_base,
           "started": time.strftime("%Y-%m-%dT%H:%M:%S")}

    def save():
        out.write_text(json.dumps(rec, indent=2))

    save()
    if not Path(args.adapter, "adapter_model.safetensors").exists():
        print(f"[awq] training a toy adapter on {args.train_base} in 4-bit", flush=True)
        rc = subprocess.call([sys.executable, "-m", "training.harness.tiny_adapter",
                              "--base", args.train_base, "--out", args.adapter,
                              "--steps", str(args.steps), "--four-bit"])
        rec["train_rc"] = rc; save()
        if rc != 0:
            rec["verdict"] = {"applied": None, "reading": f"toy adapter did not train (rc={rc})"}
            rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); return 1

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.serve_base)
    p = serve(args.serve_base, ["--max-model-len", "4096", "--gpu-memory-utilization", "0.90",
                                "--enable-lora", "--max-lora-rank", "16", "--max-loras", "1",
                                "--lora-modules", f"tiny32={args.adapter}"])
    try:
        if not wait_ready(p, minutes=30):
            rec["verdict"] = {"applied": None, "reading": "the AWQ base never came up with the adapter"}
            rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); return 1
        rec["G1"] = identity(args.serve_base, "tiny32", tok)
        print(f"[awq] G1 tiny32 over AWQ: {rec['G1']['differs']}/{rec['G1']['probed']} differ, "
              f"{rec['G1']['empty']} empty → "
              f"{'applied' if rec['G1']['applied'] else 'NOT APPLIED'}", flush=True)
    finally:
        stop(p)
    try:
        log = Path("vllm.log").read_text(errors="replace")
        rec["engine_lora_lines"] = [l.strip()[:220] for l in log.splitlines()
                                    if re.search(r"lora|Punica|punica", l, re.I)][-40:]
    except Exception:
        rec["engine_lora_lines"] = []
    g = rec["G1"]
    rec["verdict"] = {"applied": g["applied"],
                      "reading": ("APPLIED: vLLM applies a LoRA over the AWQ 32B — option A can be served"
                                  if g["applied"] else
                                  f"NOT APPLIED over the AWQ 32B ({g['differs']}/{g['probed']} differ, "
                                  f"{g['empty']} empty) — option A cannot be served this way; the "
                                  "engine's own lora lines are in the record")}
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
    print(f"[awq] {rec['verdict']['reading']}", flush=True)
    return 0 if g["applied"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
