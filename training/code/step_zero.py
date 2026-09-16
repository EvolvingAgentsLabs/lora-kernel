"""Step zero — does a base model with the right LoRA complete these programs better?

THE SMALLEST THING THAT SHOWS THE IDEA WORKS OR DOES NOT. One language, one adapter,
one paired comparison on held-out programs the adapter never saw. If the answer is no,
nothing downstream is worth buying — not a pool, not acceptance, not ranking. If it is
yes, all of that becomes buyable and this is the rung everything stands on.

IT TRAINS AND SCORES IN ONE SESSION, WHICH IS UNUSUAL HERE AND DELIBERATE. P26's brief
says retraining inside a serving run puts forty minutes and a second source of variance
into a question about HTTP — but this question is not about HTTP. It is *did the
training do anything*, and splitting it across two rented sessions would add a tarball
round-trip to a run whose whole point is the delta between two arms on one card.

PAIRED, BECAUSE THE ARMS SHARE FIXTURES. Both arms answer the same 180 held-out cases,
so the comparison is a paired sign test rather than two independent proportions —
`bar.compare`. Reporting two accuracies side by side and eyeballing the gap is how a
run-to-run spread gets read as an effect: the same adapter on the same cases at
temperature 0 scored 84, 81 and 82 across three runs **[ran]** P36/P38/P40.

C18 FIRST. vLLM loads a LoRA, logs that it did, and can serve the base anyway. Without
that gate the two arms would be one model and the sign test would report a tie as
truthfully as it would report anything.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from training.code.suite import verify_against
from training.harness.bar import compare, resolvable

OUT = Path("step_zero.json")

#: Pre-registered. An adapter that cannot beat the base by this much on held-out
#: programs has not learned the shape, and the pool has nothing to be built from.
MIN_EFFECT = 0.10


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


def _probe(model: str, port: int = 8000) -> str | None:
    body = json.dumps({"model": model, "max_tokens": 32, "temperature": 0,
                       "messages": [{"role": "user",
                                     "content": "Reply with one short sentence "
                                                "about sorting."}]}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["choices"][0]["message"]["content"]
    except Exception:
        return None


def complete(model: str, prompt: str, max_tokens: int, port: int = 8000,
             timeout: int = 240) -> dict:
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
                                 body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"text": json.load(r)["choices"][0]["message"]["content"] or ""}
    except Exception as e:
        return {"text": None, "error": repr(e)[:180]}


def score_arm(model: str, cases: list[dict], max_tokens: int, out: Path,
              every: int = 20) -> list[dict]:
    done: dict[str, dict] = {}
    if out.exists():
        try:
            done = {r["id"]: r for r in json.loads(out.read_text()).get("records", [])}
        except Exception as e:
            print(f"[zero] could not reuse {out}: {e!r}", flush=True)
    if done:
        print(f"[zero] resuming {model} — {len(done)} scored", flush=True)
    recs = []
    for i, c in enumerate(cases, 1):
        if c["case_id"] in done:
            recs.append(done[c["case_id"]])
            continue
        r = complete(model, c["prompt"], max_tokens)
        if r.get("error"):
            rec = {"correct": False, "why": "transport", "error": r["error"]}
        else:
            rec = verify_against(c["prefix"], c["region"], c["answer"],
                                 r["text"])
        rec |= {"id": c["case_id"], "family": c["family"], "depth": c["depth"],
                "completion": (r.get("text") or "")[:400]}
        recs.append(rec)
        if len(recs) % every == 0 or i == len(cases):
            ok = sum(x["correct"] for x in recs)
            out.write_text(json.dumps({"model": model, "n": len(recs), "correct": ok,
                                       "partial": i < len(cases),
                                       "records": recs}, indent=2))
            print(f"[zero] {model} {i}/{len(cases)} correct {ok} "
                  f"(did not run {sum(bool(x.get('why')) and x.get('why') not in ('', 'output differs', 'transport') for x in recs)})",
                  flush=True)
    return recs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter-name", default="code-python")
    ap.add_argument("--adapter-path", default="adapters/code-python")
    ap.add_argument("--train", default="training/code/data/train.python.jsonl")
    ap.add_argument("--eval", default="training/code/data/eval.python.jsonl")
    ap.add_argument("--max-tokens", type=int, default=700)
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    cases = [json.loads(line) for line in open(args.eval) if line.strip()]
    results = {"base": args.base, "adapter": args.adapter_name, "n": len(cases),
               "min_effect": MIN_EFFECT, "arms": {}}

    # HEADROOM, BEFORE THE TREATMENT EXISTS. If 180 cases cannot resolve a +0.10
    # improvement over a plausible baseline, the arm is unbuyable and saying so now
    # costs nothing — P42 bought one that could not and found out afterwards.
    results["power"] = resolvable(len(cases), baseline=0.30, effect=MIN_EFFECT)
    print(f"[zero] {results['power']['why']}", flush=True)
    OUT.write_text(json.dumps(results, indent=2))

    if not (Path(args.adapter_path) / "adapter_model.safetensors").exists():
        rows = [json.loads(l) for l in open(args.train) if l.strip()]
        print(f"[zero] training {args.adapter_path} on {len(rows)} examples",
              flush=True)
        from types import SimpleNamespace

        from training.s4_train import free, train_adapter
        train_adapter(args.base, rows, args.adapter_path, SimpleNamespace(
            epochs=args.epochs, r=16, alpha=32, lr=2e-4, batch=2, accum=8,
            max_seq=1536, seed=0, four_bit=False,
            targets="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj"))
        free()
        print("[zero] trained", flush=True)

    v = subprocess.Popen(
        ["vllm", "serve", args.base, "--dtype", "bfloat16", "--enable-lora",
         "--max-lora-rank", "16", "--max-loras", "1", "--max-model-len",
         str(args.max_model_len), "--gpu-memory-utilization", "0.90",
         "--lora-modules", f"{args.adapter_name}={args.adapter_path}"],
        stdout=open("vllm.log", "w"), stderr=subprocess.STDOUT)
    try:
        if not _wait("http://127.0.0.1:8000/health", 25, v):
            results["arms"]["server"] = {"status": "never came up"}
            OUT.write_text(json.dumps(results, indent=2)); return 1
        print("[zero] vllm up", flush=True)

        applied = ((_probe(args.adapter_name) or "").strip()
                   != (_probe(args.base) or "").strip())
        results["identity_gate"] = {"differs_from_base": applied}
        print(f"[zero] gate {args.adapter_name}: "
              + ("applied" if applied else "IDENTICAL TO BASE"), flush=True)
        OUT.write_text(json.dumps(results, indent=2))
        if not applied:
            print("[zero] STOPPED. Both arms would be the base.", flush=True)
            results["stopped_at_gate"] = True
            OUT.write_text(json.dumps(results, indent=2)); return 1

        arms = {}
        for arm, model in (("base", args.base), ("adapter", args.adapter_name)):
            recs = score_arm(model, cases, args.max_tokens, Path(f"arm_{arm}.json"))
            arms[arm] = recs
            results["arms"][arm] = {
                "model": model, "n": len(recs),
                "correct": sum(r["correct"] for r in recs),
                "accuracy": round(sum(r["correct"] for r in recs) / len(recs), 4),
                "records": recs}
            OUT.write_text(json.dumps(results, indent=2))

        by_id = {r["id"]: r for r in arms["base"]}
        only_a = sum(1 for r in arms["adapter"]
                     if r["correct"] and not by_id[r["id"]]["correct"])
        only_b = sum(1 for r in arms["adapter"]
                     if not r["correct"] and by_id[r["id"]]["correct"])
        results["paired"] = compare(only_a, only_b)
        a = results["arms"]["adapter"]["accuracy"]
        b = results["arms"]["base"]["accuracy"]
        results["verdict"] = {
            "adapter": a, "base": b, "delta": round(a - b, 4),
            "bought": (a - b) >= MIN_EFFECT and results["paired"]["different"],
            "reading": (
                f"the adapter wins {only_a} cases the base loses and loses {only_b} "
                f"it wins; p = {results['paired']['p_value']:.4g}")}
        print(f"\nbase {b:.3f} · adapter {a:.3f} · delta {a - b:+.3f}")
        print(results["verdict"]["reading"])
        print("STEP ZERO " + ("PASSES" if results["verdict"]["bought"] else "FAILS"))
        results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        OUT.write_text(json.dumps(results, indent=2))
    finally:
        v.terminate()
        try:
            v.wait(timeout=60)
        except subprocess.TimeoutExpired:
            v.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
