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

# THE OUTPUT NAME FOLLOWS THE CHAIN'S. It was hardcoded, and the chain downloads
# whatever RESULTS_NAME says — so the pool-cost run wrote `serve_results.json` on the
# VM while the chain asked for `serve_pool_cost.json` and came home empty. Twice. Both
# runs' numbers survive only in a log [ran] 2026-09-14.
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
        body = r.read()
    # `/health` ANSWERS 200 WITH AN EMPTY BODY. Parsing it raised JSONDecodeError —
    # not in the readiness loop's except clause — so this crashed at the exact
    # moment the server became healthy, which is the one moment it looked like the
    # server had failed [ran] 2026-09-13.
    return json.loads(body) if body.strip() else {}


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
        except Exception:
            # Anything at all means not-ready-yet. A readiness probe that is choosy
            # about how it fails is a readiness probe that reports the wrong thing.
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
    ap.add_argument("--gate-only", dest="gate_only", action="store_true",
                    help="P29: serve, ask the identity question, and stop. Nothing "
                         "is trained and nothing is scored.")
    ap.add_argument("--cost-only", dest="cost_only", action="store_true",
                    help="skip the accuracy arm and measure only what a pool costs")
    ap.add_argument("--out", default=None,
                    help="results file; must match the chain's RESULTS_NAME")
    ap.add_argument("--repeats", type=int, default=3,
                    help="timed rounds; the order alternates so neither arm is "
                         "always first")
    args = ap.parse_args()

    global OUT
    if args.out:
        OUT = Path(args.out)

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
           # `--disable-log-requests` was removed in vLLM 0.29.0 and the server
           # exits 2 on it — argparse, before a single weight is loaded [ran]
           # 2026-09-13. Quieter logs are not worth a flag that pins a version.
           "--lora-modules",
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
            try:
                t = chat(name, probe, SYSTEM, 120)
            except Exception as e:
                # REFUSED OUT LOUD IS NOT THE SAME AS SILENTLY IGNORED. P29 serves a
                # deliberately foreign adapter; a shape or rank complaint is an
                # inconclusive result, not a negative one, and it must not be
                # recorded as "does not differ".
                gate[name] = {"differs_from_base": None, "refused": repr(e)[:200]}
                print(f"[gate] {name}: REFUSED — {e}"[:200], flush=True)
                continue
            gate[name] = {"differs_from_base": t.strip() != base_text.strip(),
                          "base_head": base_text[:110], "lora_head": t[:110]}
            print(f"[gate] {name}: "
                  + ("applied" if gate[name]["differs_from_base"]
                     else "IDENTICAL TO BASE — not applied"), flush=True)

        results["arms"]["serving identity"] = gate
        OUT.write_text(json.dumps(results, indent=2))
        if args.gate_only:
            # THE WHOLE EXPERIMENT. P3 spent an A100 discovering that throughput
            # measured on an unverified stack is worth nothing; this asks the
            # verification question alone and pays for nothing else.
            # THREE OUTCOMES, NOT TWO. `all(...)` over a None reads as False and
            # would file an explicit shape complaint under "not applied" — which is
            # the one reading this brief forbids, because a foreign adapter being
            # refused says nothing about whether a native one would apply.
            vals = [g["differs_from_base"] for g in gate.values()]
            if any(v is None for v in vals):
                verdict = "inconclusive: the adapter was refused out loud"
            elif all(vals):
                verdict = "applied"
            else:
                verdict = "not applied: served text is identical to the base"
            print(f"[gate-only] {verdict}", flush=True)
            results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            results["gate_verdict"] = verdict
            OUT.write_text(json.dumps(results, indent=2))
            return 0
        if not all(g["differs_from_base"] for g in gate.values()):
            print("[gate] STOPPED. An adapter that does not change the output is "
                  "not being served, whatever the throughput says. This is C18 and "
                  "it is why nothing below this line is measured.", flush=True)
            results["stopped_at_gate"] = True
            OUT.write_text(json.dumps(results, indent=2))
            return 0

        # ARM 2 — do the numbers survive the serving stack? It is skipped under
        # --cost-only because P26 established it cannot answer that question as
        # built: a single-turn endpoint gives the kernel no answer to its calls and
        # the domain cannot do arithmetic, so both zeros are about the harness [ran].
        for name in ([] if args.cost_only else pool):
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
        pure = lambda i: first
        mixed = lambda i: names_cycle[i % len(names_cycle)]

        # A WARM-UP BURST, AND AN ALTERNATING ORDER. P26 ran pure then mixed, once
        # each, and mixed came out FASTER — which is not a finding, it is the first
        # arm paying whatever warm-up exists [ran]. The discarded burst absorbs it
        # and the order flips each round so neither arm is always first.
        print("[cost] warm-up burst, discarded", flush=True)
        burst(pure)
        rounds = []
        for r in range(args.repeats):
            if r % 2 == 0:
                a = burst(pure); b = burst(mixed)
            else:
                b = burst(mixed); a = burst(pure)
            rounds.append({"round": r, "pure_first": r % 2 == 0,
                           "pure": a["prompts_per_second"],
                           "mixed": b["prompts_per_second"]})
            print(f"  [cost] round {r}: pure {a['prompts_per_second']} · "
                  f"mixed {b['prompts_per_second']}"
                  + ("  (pure first)" if r % 2 == 0 else "  (mixed first)"),
                  flush=True)
            results["arms"]["concurrency"] = {"rounds": rounds}
            OUT.write_text(json.dumps(results, indent=2))

        ps = sorted(x["pure"] for x in rounds)
        ms = sorted(x["mixed"] for x in rounds)
        med = lambda v: v[len(v) // 2]
        p, m = med(ps), med(ms)
        results["arms"]["concurrency"].update({
            "pure_median": p, "mixed_median": m,
            "pure_range": [ps[0], ps[-1]], "mixed_range": [ms[0], ms[-1]],
            "pool_cost": round(1 - m / max(p, 1e-9), 4)})
        print(f"\npure {p} prompts/s (spread {ps[0]}–{ps[-1]}) · "
              f"mixed {m} (spread {ms[0]}–{ms[-1]}) · "
              f"the pool costs {1 - m / max(p, 1e-9):.1%}", flush=True)
        print("A difference smaller than either spread is not a difference.",
              flush=True)
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
