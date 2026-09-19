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

THE TEXT GATE ALONE COULD NOT READ ATTEMPT 2. The engine loaded the adapter, used the
Punica GPU wrapper, and one probe of three changed one word at T=0 — a 60-step toy
adapter over a 32B moves an argmax rarely, and G1 counts argmax flips. So a second gate
measures the mechanism where it lives: the per-token log-probabilities of a fixed
continuation under the base, under the base again (the determinism control), and
under the member. With $\ell_m(t)$ the member's logprob of token $t$ and $\ell_b(t)$
the base's, the adapter is applied iff

    mean_t |ℓ_m(t) − ℓ_b(t)|  >  RATIO · max(mean_t |ℓ_b(t) − ℓ_b'(t)|, FLOOR)

on at least NEED of the probes — a difference the base does not produce against itself
(FOUNDATIONS §3.4). The text gate is kept and reported beside it.

WHAT THE LOG SAYS IS RECORDED TOO. Every `lora`/`Punica` line vLLM prints is kept in
the verdict, so a `not applied` comes with the engine's own account of what it
skipped — the reading D2 needs, taken while the log is in hand.

    BASE=Qwen/Qwen2.5-32B-Instruct-AWQ … MODULE=training.harness.awq_lora_gate
    python3 -m training.harness.awq_lora_gate --base Qwen/Qwen2.5-32B-Instruct-AWQ --out results/P60-deep-window-20260917/awq_gate.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from training.harness.accept_rank import post, serve, stop, wait_ready
from training.harness.verify_substrate import PROBES, identity

OUT = Path("awq_gate.json")
CONTINUATION = " It depends on several things, and the first of them is"
RATIO = 10.0        # member-vs-base must exceed this many times base-vs-base
FLOOR = 1e-4        # nats; below this the control is float noise, not a difference
NEED = 2            # of 3 probes


def token_logprobs(model: str, text: str, ids: list[int]) -> list[float]:
    r = post("/v1/completions", {"model": model, "prompt": text, "max_tokens": 1,
                                 "temperature": 0, "prompt_logprobs": 1})
    pl = r["choices"][0].get("prompt_logprobs") or []
    out = []
    for i, tid in enumerate(ids):
        d = (pl[i] if i < len(pl) else None) or {}
        e = d.get(tid) or d.get(str(tid))
        out.append(float(e["logprob"]) if e and e.get("logprob") is not None else float("nan"))
    return out


def mean_abs_delta(a: list[float], b: list[float], start: int) -> float:
    pairs = [(x, y) for x, y in zip(a[start:], b[start:]) if x == x and y == y]
    return sum(abs(x - y) for x, y in pairs) / len(pairs) if pairs else float("nan")


def logprob_verdict(rows: list[dict], ratio: float = RATIO, floor: float = FLOOR,
                    need: int = NEED) -> dict:
    """rows: [{"member_vs_base": Δ, "base_vs_base": Δ'}]. Applied iff Δ > ratio·max(Δ', floor)
    on ≥ need probes. A NaN on either side is not a difference."""
    hits = 0
    for r in rows:
        d, c = r["member_vs_base"], r["base_vs_base"]
        r["applied"] = bool(d == d and c == c and d > ratio * max(c, floor))
        hits += r["applied"]
    return {"probes": len(rows), "differ": hits, "need": need, "applied": hits >= need}


def logprob_gate(base: str, member: str, tok, probes=PROBES) -> dict:
    rows = []
    for p in probes:
        prefix = tok.apply_chat_template([{"role": "user", "content": p}],
                                         tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False)
        text = prefix + CONTINUATION
        ids = tok(text)["input_ids"]
        start = len(tok(prefix)["input_ids"]) - 1          # the BPE seam is scored too
        b1 = token_logprobs(base, text, ids)
        b2 = token_logprobs(base, text, ids)
        m = token_logprobs(member, text, ids)
        rows.append({"probe": p[:40], "tokens": len(ids) - start,
                     "member_vs_base": mean_abs_delta(m, b1, start),
                     "base_vs_base": mean_abs_delta(b1, b2, start)})
        print(f"[awq] Δlogprob {p[:32]!r}: member-base {rows[-1]['member_vs_base']:.5f} "
              f"base-base {rows[-1]['base_vs_base']:.5f}", flush=True)
    v = logprob_verdict(rows); v["rows"] = rows
    return v


def lora_spec(tiny: str) -> str:
    """What vLLM is handed: exactly one `name=path`. A path carrying `=` is refused here
    rather than by vLLM's argparse a minute after the 32B trained."""
    if "=" in tiny or not tiny:
        raise SystemExit(f"[awq] refusing the toy adapter path {tiny!r}: must be a bare path")
    return f"tiny32={tiny}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train-base", default="Qwen/Qwen2.5-32B-Instruct")
    # `--base` IS WHAT THE CHAIN PASSES TO EVERY RUNNER (chain_serve.sh: `--base $BASE`);
    # here it is the base the adapter is served over. The first launch died on
    # `unrecognized arguments: --base` nine times before anything trained.
    ap.add_argument("--base", "--serve-base", dest="serve_base",
                    default="Qwen/Qwen2.5-32B-Instruct-AWQ")
    # THE CHAIN'S `MARGS=""` FALLS BACK TO ITS DEFAULT `--adapter kernel=… --adapter
    # domain=…` (`${MARGS:-…}` treats empty as unset), and a runner whose own flag is
    # `--adapter` gets the last of those as its toy adapter path: attempt 1 asked vLLM for
    # `tiny32=domain=adapters/domain-mt`. So the pool's flag is accepted and ignored,
    # and the toy adapter has a flag of its own.
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored here)")
    ap.add_argument("--tiny", default="adapters/tiny32", help="where the toy adapter is trained")
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    print(f"[awq] lora spec: {lora_spec(args.tiny)}", flush=True)
    rec = {"train_base": args.train_base, "serve_base": args.serve_base, "lora": lora_spec(args.tiny),
           "started": time.strftime("%Y-%m-%dT%H:%M:%S")}

    def save():
        out.write_text(json.dumps(rec, indent=2))

    save()
    if not Path(args.tiny, "adapter_model.safetensors").exists():
        print(f"[awq] training a toy adapter on {args.train_base} in 4-bit", flush=True)
        rc = subprocess.call([sys.executable, "-m", "training.harness.tiny_adapter",
                              "--base", args.train_base, "--out", args.tiny,
                              "--steps", str(args.steps), "--four-bit"])
        rec["train_rc"] = rc; save()
        if rc != 0:
            rec["verdict"] = {"applied": None, "reading": f"toy adapter did not train (rc={rc})"}
            rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); return 1

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.serve_base)
    p = serve(args.serve_base, ["--max-model-len", "4096", "--gpu-memory-utilization", "0.90",
                                "--enable-lora", "--max-lora-rank", "16", "--max-loras", "1",
                                "--lora-modules", lora_spec(args.tiny)])
    try:
        if not wait_ready(p, minutes=30):
            rec["verdict"] = {"applied": None, "reading": "the AWQ base never came up with the adapter"}
            rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); return 1
        rec["G1"] = identity(args.serve_base, "tiny32", tok)
        print(f"[awq] G1 text: {rec['G1']['differs']}/{rec['G1']['probed']} differ, "
              f"{rec['G1']['empty']} empty → "
              f"{'applied' if rec['G1']['applied'] else 'not applied'}", flush=True)
        save()
        rec["G1_logprob"] = logprob_gate(args.serve_base, "tiny32", tok)
        print(f"[awq] G1 logprob: {rec['G1_logprob']['differ']}/{rec['G1_logprob']['probes']} "
              f"beyond {RATIO}× the base's own noise → "
              f"{'applied' if rec['G1_logprob']['applied'] else 'not applied'}", flush=True)
    finally:
        stop(p)
    try:
        log = Path("vllm.log").read_text(errors="replace")
        rec["engine_lora_lines"] = [l.strip()[:220] for l in log.splitlines()
                                    if re.search(r"lora|Punica|punica", l, re.I)][-40:]
    except Exception:
        rec["engine_lora_lines"] = []
    g, lp = rec["G1"], rec["G1_logprob"]
    applied = lp["applied"]
    rec["verdict"] = {"applied": applied, "text_gate": g["applied"], "logprob_gate": lp["applied"],
                      "reading": (f"APPLIED: the member's logprobs differ from the base's beyond {RATIO}× "
                                  f"the base's own noise on {lp['differ']}/{lp['probes']} probes "
                                  f"(text gate {g['differs']}/{g['probed']}) — option A can be served"
                                  if applied else
                                  f"NOT APPLIED over the AWQ 32B: logprobs {lp['differ']}/{lp['probes']}, "
                                  f"text {g['differs']}/{g['probed']}, {g['empty']} empty — option A "
                                  "cannot be served this way; the engine's own lora lines are in the record")}
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save()
    print(f"[awq] {rec['verdict']['reading']}", flush=True)
    return 0 if applied else 1


if __name__ == "__main__":
    raise SystemExit(main())
