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


def adapter_changes_output(llm, sp, prompts, req) -> tuple[bool, str, str]:
    """The gate C18 exists for: does the adapter change ANYTHING?

    vLLM 0.28.0 accepted every LoRARequest for `Qwen/Qwen3.5-2B`, emitted no
    warning, and served the base model byte for byte **[ran]** 2026-09-08. Three
    adapters at 90 prompts/s looked exactly like a working substrate. So no arm
    is measured until one prompt is shown to differ.
    """
    a = llm.generate(prompts[:1], sp)[0].outputs[0].text
    b = llm.generate(prompts[:1], sp, lora_request=req)[0].outputs[0].text
    return a != b, a, b


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen3.5-2B")
    ap.add_argument("--arch-override", default="",
                    help="force the architecture vLLM loads, e.g. "
                         "Qwen3_5ForCausalLM. `Qwen/Qwen3.5-2B` ships as "
                         "Qwen3_5ForConditionalGeneration, and only the CausalLM "
                         "class declares SupportsLoRA [read]")
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

    kw = {}
    if args.arch_override:
        kw["hf_overrides"] = {"architectures": [args.arch_override]}
        print(f"[arch] forcing {args.arch_override}", flush=True)
    llm = LLM(model=args.base, enable_lora=True, max_loras=len(pool),
              max_lora_rank=args.max_lora_rank, dtype="bfloat16",
              gpu_memory_utilization=0.85, max_model_len=2048, **kw)
    requests = {name: LoRARequest(name, i + 1, path)
                for i, (name, path) in enumerate(pool.items())}

    first = next(iter(requests.values()))
    changed, base_text, lora_text = adapter_changes_output(llm, sp, prompts, first)
    print(f"[gate] adapter changes output: {changed}", flush=True)
    if not changed:
        print("[gate] ABORT — the served text is byte-identical with and without "
              "the adapter, so every arm below would measure the base model.\n"
              f"  base: {base_text[:110]!r}\n  lora: {lora_text[:110]!r}", flush=True)
        Path("p3_results.json").write_text(json.dumps(
            {"base": args.base, "arch_override": args.arch_override,
             "gate": "FAILED — adapter does not change output", "arms": {}}, indent=2))
        return 4

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

    # THE MIXED BATCH IS NOT IMPLEMENTED, AND THE PREVIOUS ATTEMPT WAS WORSE
    # THAN NOTHING. It called `llm.generate([p], ...)` once per prompt, cycling
    # adapters — sixty sequential round-trips, which measured 3.85 prompts/s
    # against a pure batch's 77.66 and looked like a 20x penalty for holding a
    # pool [ran] 2026-09-08. It was measuring the loop, not the batching.
    #
    # Measuring it honestly needs per-request adapters INSIDE one scheduling
    # pass: the async engine, or the OpenAI-compatible server with each adapter
    # registered as its own model name and concurrent clients. Until one of those
    # is built, this arm reports nothing, because a number that measures the
    # wrong thing is worse than a gap in the table.
    results["arms"]["mixed batch"] = {
        "status": "not measured",
        "why": ("requires per-request adapters within one scheduling pass — the "
                "async engine or the OpenAI server with one model name per "
                "adapter. The serial loop that stood here measured round-trips "
                "and was voided."),
    }
    OUT.write_text(json.dumps(results, indent=2))
    print(json.dumps(results["arms"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
