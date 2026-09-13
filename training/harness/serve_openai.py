"""P26 — the adapter pool behind vLLM's OpenAI-compatible server.

WHAT THIS ANSWERS. Everything measured so far ran through `transformers` or vLLM's
offline `LLM` class. An agent runtime calls `POST /v1/chat/completions` with a
`model` name, and vLLM registers each adapter as its own model name — which is the
shape the architecture needs and which nobody here has run.

THE GATE COMES BEFORE THE NUMBERS, AND IT IS NOT THROUGHPUT. vLLM 0.28.0 accepted a
valid LoRARequest on `Qwen3.5-2B` and served the base model with no error, no
warning and byte-identical output **[ran]** `results/P3-vllm-20260908/`. Had that
step measured only throughput it would have reported three adapters at 90 prompts/s
and called the substrate proven. So: the same prompt to the base and to an adapter
must produce DIFFERENT text before anything else is recorded.

    python3 -m training.harness.serve_openai --base Qwen/Qwen2.5-3B-Instruct \\
        --adapter kernel=adapters/kernel-mt --adapter domain=adapters/domain-mt
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path("serve_results.json")
HOST = "http://127.0.0.1:8000"


def post(path: str, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(HOST + path, method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def get(path: str, timeout: int = 10) -> dict:
    with urllib.request.urlopen(HOST + path, timeout=timeout) as r:
        return json.load(r)


def chat(model: str, prompt: str, system: str, max_tokens: int) -> str:
    body = post("/v1/chat/completions", {
        "model": model, "temperature": 0.0, "max_tokens": max_tokens,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": prompt}]})
    return body["choices"][0]["message"]["content"] or ""


def wait_ready(proc, minutes: int = 12) -> bool:
    """A server that never comes up is not a result — it is a run that did not start."""
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        if proc.poll() is not None:
            print(f"[serve] the server exited with {proc.returncode} before it "
                  "answered /health", flush=True)
            return False
        try:
            get("/health", timeout=5)
            return True
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(5)
    print("[serve] the server never answered /health", flush=True)
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", action="append", default=[],
                    help="name=path, repeatable — each becomes its own model name")
    ap.add_argument("--n-eval", type=int, default=30)
    ap.add_argument("--eval-seed", type=int, default=616161)
    ap.add_argument("--rtol", type=float, default=0.02)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--max-lora-rank", type=int, default=16)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    from training.physics.headroom import correct, parse_answer
    from training.physics.multitool import FAMILIES, generate
    from training.protocol import SYSTEM

    pool = dict(a.split("=", 1) for a in args.adapter)
    missing = [n for n, p in pool.items()
               if not (Path(p) / "adapter_model.safetensors").exists()]
    if missing:
        # A DIRECTORY IS NOT AN ADAPTER — the same check the training runner needed.
        print(f"[serve] no weights for {missing}; nothing to serve")
        return 1

    cmd = ["vllm", "serve", args.base, "--enable-lora",
           "--max-lora-rank", str(args.max_lora_rank),
           "--max-loras", str(max(len(pool), 1)), "--dtype", "bfloat16",
           "--disable-log-requests", "--lora-modules",
           *[f"{n}={p}" for n, p in pool.items()]]
    print("[serve] " + " ".join(cmd), flush=True)
    log = open("vllm.log", "w")
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    results = {"base": args.base, "pool": list(pool), "arms": {}}

    try:
        if not wait_ready(proc):
            results["arms"]["server"] = {"status": "never came up"}
            OUT.write_text(json.dumps(results, indent=2))
            return 1

        names = [m["id"] for m in get("/v1/models")["data"]]
        print(f"[serve] /v1/models -> {names}", flush=True)
        results["models_endpoint"] = names

        rows = generate(args.n_eval, args.eval_seed, FAMILIES)
        probe = rows[0]["prompt"]

        # ARM 1 — THE C18 GATE. Identical text means the adapter was not applied.
        base_text = chat(args.base, probe, SYSTEM, 120)
        gate = {}
        for name in pool:
            t = chat(name, probe, SYSTEM, 120)
            gate[name] = {"differs_from_base": t.strip() != base_text.strip(),
                          "base_head": base_text[:110], "lora_head": t[:110]}
            print(f"[gate] {name}: "
                  + ("applied" if gate[name]["differs_from_base"]
                     else "IDENTICAL TO BASE — not applied"), flush=True)
        results["arms"]["serving identity"] = gate
        OUT.write_text(json.dumps(results, indent=2))
        if not all(g["differs_from_base"] for g in gate.values()):
            print("[gate] STOPPED. An adapter that does not change the output is "
                  "not being served, whatever the throughput says. This is C18 and "
                  "it is why nothing below this line is measured.", flush=True)
            results["stopped_at_gate"] = True
            OUT.write_text(json.dumps(results, indent=2))
            return 0

        # ARM 2 — do the numbers survive the serving stack?
        for name in pool:
            recs, passed = [], 0
            t0 = time.time()
            for i, row in enumerate(rows, 1):
                text = chat(name, row["prompt"], SYSTEM, args.max_tokens)
                got = parse_answer(text)
                ok = bool(correct(got, row["answer"], args.rtol))
                passed += ok
                recs.append({"case_id": row["case_id"], "family": row["family"],
                             "want": row["answer"], "got": got, "passed": ok,
                             "chars": len(text), "raw": text[:300]})
                if i % 10 == 0:
                    print(f"  [{name}] {i}/{len(rows)} passed {passed}", flush=True)
            results["arms"][f"served · {name}"] = {
                "passed": passed, "n": len(rows),
                "accuracy": round(passed / len(rows), 4),
                "seconds": round(time.time() - t0, 1), "records": recs}
            OUT.write_text(json.dumps(results, indent=2))

        # ARM 3 — what a pool costs, INSIDE one scheduling pass. P3's serial loop
        # measured round-trips and reported a 20x penalty that was not there.
        def burst(model_for):
            t0 = time.time()
            with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
                list(ex.map(lambda a: chat(model_for(a[0]), a[1]["prompt"],
                                           SYSTEM, args.max_tokens),
                            list(enumerate(rows))))
            dt = time.time() - t0
            return {"seconds": round(dt, 2),
                    "prompts_per_second": round(len(rows) / dt, 2)}

        first = list(pool)[0]
        names_cycle = list(pool)
        results["arms"]["concurrency · pure"] = burst(lambda i: first)
        results["arms"]["concurrency · mixed"] = burst(
            lambda i: names_cycle[i % len(names_cycle)])
        OUT.write_text(json.dumps(results, indent=2))
        p = results["arms"]["concurrency · pure"]["prompts_per_second"]
        m = results["arms"]["concurrency · mixed"]["prompts_per_second"]
        print(f"\npure {p} prompts/s · mixed {m} prompts/s · "
              f"the pool costs {1 - m / max(p, 1e-9):.1%}", flush=True)
        results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        OUT.write_text(json.dumps(results, indent=2))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
