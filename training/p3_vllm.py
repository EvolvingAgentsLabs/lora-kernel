"""P3 — the substrate: many adapters, one resident base, served by vLLM.

WHAT THIS IS FOR. `ARCHITECTURE.md` layer 1 is "one GPU, one resident base model,
multi-LoRA serving, adapters batched per request". Every result this project has
produced so far came from `transformers` loading one adapter at a time, which is
not that. Until this runs, the architecture's substrate is a claim.

THE THREE THINGS IT HAS TO SHOW, in order of how much they matter:

  1. THE POOL IS SERVABLE. Three adapters resident over one base, each answering
     its own requests.
  2. THE SAME NUMBERS COME OUT. An adapter scored through vLLM must match what
     `transformers` measured, or one of the two implementations is wrong and
     every earlier number is in question.
  3. A MIXED BATCH COSTS WHAT A PURE ONE COSTS — or it does not, and the
     difference is the price of the pool. This is the economic claim underneath
     "swap adapters per request", and nobody has measured it here.

WHAT TO WATCH FOR. These adapters target all seven projections, `q_proj` and
`k_proj` included. Qwen3 applies QK-norm, and adapting those two is reported to
produce shape-incompatible tensors in some serving kernels **[read]**. It did not
bite in training **[ran]**. If it bites here, that is a finding about what the
pool may adapt, not a bug to route around.

    python3 -m training.p3_vllm --base Qwen/Qwen3.5-2B --pool ./pool
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from training.evaluate import evaluate, load_jsonl, parse_answer

OUT = Path("p3_results.json")


def build_prompts(tok, rows):
    out = []
    for r in rows:
        msgs = [{"role": "system", "content": r["messages"][0]["content"]},
                {"role": "user", "content": r["messages"][1]["content"]}]
        out.append(tok.apply_chat_template(msgs, tokenize=False,
                                           add_generation_prompt=True))
    return out


def score(texts, rows) -> dict:
    """The same exact verifier as every other arm — set equality, nothing else."""
    passed = unparseable = 0
    for text, row in zip(texts, rows):
        got, want = parse_answer(text), parse_answer(row["messages"][-1]["content"])
        unparseable += got is None
        passed += got is not None and got == want
    return {"passed": passed, "n": len(rows),
            "accuracy": round(passed / len(rows), 4), "unparseable": unparseable}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--pool", default="./pool")
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--max-lora-rank", type=int, default=16)
    args = ap.parse_args()

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    pool = {p.name: str(p) for p in sorted(Path(args.pool).iterdir()) if p.is_dir()}
    print(f"[pool] {list(pool)}", flush=True)

    rows = load_jsonl("training/data/val.jsonl")[:args.n]
    tok = AutoTokenizer.from_pretrained(args.base)
    prompts = build_prompts(tok, rows)
    # Greedy, like every other number in this repository.
    sp = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=64)

    llm = LLM(model=args.base, enable_lora=True, max_loras=len(pool),
              max_lora_rank=args.max_lora_rank, dtype="bfloat16",
              gpu_memory_utilization=0.85, max_model_len=2048)
    requests = {name: LoRARequest(name, i + 1, path)
                for i, (name, path) in enumerate(pool.items())}

    results = {"base": args.base, "pool": list(pool), "n": len(rows), "arms": {}}

    def timed(label, lora=None):
        t0 = time.time()
        outs = llm.generate(prompts, sp, lora_request=lora)
        dt = time.time() - t0
        texts = [o.outputs[0].text for o in outs]
        s = score(texts, rows)
        s["seconds"] = round(dt, 2)
        s["prompts_per_second"] = round(len(prompts) / dt, 2)
        results["arms"][label] = s
        print(f"[{label}] {s['passed']}/{s['n']} = {s['accuracy']:.3f}  "
              f"{s['seconds']}s  {s['prompts_per_second']}/s", flush=True)
        OUT.write_text(json.dumps(results, indent=2))
        return s

    timed("base (no adapter)")
    for name, req in requests.items():
        timed(f"pure batch · {name}", req)

    # THE MIXED BATCH. Each request carries its own adapter, interleaved, so the
    # server has to hold three deltas over one base at once. If this costs what a
    # pure batch costs, the pool is free to serve; if not, the difference IS the
    # price of the architecture.
    t0 = time.time()
    names = list(requests)
    outs = [llm.generate([p], sp, lora_request=requests[names[i % len(names)]])[0]
            for i, p in enumerate(prompts)]
    dt = time.time() - t0
    results["arms"]["mixed batch · round-robin"] = {
        "n": len(prompts), "seconds": round(dt, 2),
        "prompts_per_second": round(len(prompts) / dt, 2),
        "note": "one adapter per request, cycled — accuracy is meaningless here "
                "because two of the three adapters are wrong for any given case; "
                "this arm measures the COST of holding a pool, not its quality",
    }
    OUT.write_text(json.dumps(results, indent=2))
    print(f"[mixed] {dt:.2f}s  {len(prompts) / dt:.2f}/s", flush=True)
    print(json.dumps(results["arms"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
