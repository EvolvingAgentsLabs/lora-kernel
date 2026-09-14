"""P27 arm 3 — an OpenAI client with `tools=[…]` against the served pool.

THE QUESTION. P27 proved the *serializer* is free: tags become `tool_calls` with no
line that knows a domain, 604 round trips out of 604 **[ran]**. The half it named as
not free is the other direction — rendering a client's `tools=[…]` schema into the
tag surface the adapter was trained on. This measures that half.

TWO ARMS, SAME CASES, SAME ADAPTER, ONE DIFFERENCE:

    trained instruction   the protocol prompt the adapter saw during training
    OpenAI schema         the same three tools, described by `tools=[…]` and
                          rendered through `tools_to_instruction`

If the second matches the first, the shim is transparent and an agent runtime can
speak its own language to this pool. If it collapses, **the schema rendering is the
expensive half and the claim belongs to the shim, not to the weights.**

THE SHIM RUNS CLIENT-SIDE, and that is the honest architecture. vLLM will not emit
`tool_calls` for an adapter that writes tags; nothing here asks it to. The client
sends tools, this translates them into the surface, the model writes tags, and
`to_tool_calls` turns the reply into what an OpenAI client reads.

    python3 -m training.harness.serve_tools --base Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from training.harness.serve_openai import HOST, chat, get, post, wait_ready
from training.harness.tool_calls import to_tool_calls, tools_to_instruction

OUT = Path("serve_tools_results.json")

# The same three tools an OpenAI client would declare. Nothing here is read by the
# adapter directly — it is rendered into the tag surface by the shim.
TOOLS = [
    {"type": "function", "function": {
        "name": "lookup", "description": "a property of a named substance",
        "parameters": {"type": "object", "properties": {
            "fluid": {"type": "string"}, "property": {"type": "string"},
            "T": {"type": "number"}}}}},
    {"type": "function", "function": {
        "name": "convert", "description": "a quantity from one unit to another",
        "parameters": {"type": "object", "properties": {
            "value": {"type": "number"}, "from": {"type": "string"},
            "to": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "calc", "description": "evaluate an arithmetic expression",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string"}}}}},
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", default="adapters/kernel-mt")
    ap.add_argument("--name", default="kernel")
    ap.add_argument("--n-eval", type=int, default=30)
    ap.add_argument("--eval-seed", type=int, default=616161)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--max-lora-rank", type=int, default=16)
    ap.add_argument("--out", default=None,
                    help="results file; must match the chain's RESULTS_NAME")
    args = ap.parse_args()

    global OUT
    if args.out:
        OUT = Path(args.out)

    from training.physics.multitool import FAMILIES, INSTRUCTION, generate
    from training.physics.tools import ToolError, answer
    from training.protocol import SYSTEM

    if not (Path(args.adapter) / "adapter_model.safetensors").exists():
        print(f"[serve] no weights at {args.adapter}")
        return 1

    cmd = ["vllm", "serve", args.base, "--enable-lora",
           "--max-lora-rank", str(args.max_lora_rank), "--max-loras", "1",
           "--dtype", "bfloat16", "--lora-modules", f"{args.name}={args.adapter}"]
    print("[serve] " + " ".join(cmd), flush=True)
    log = open("vllm.log", "w")
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    results = {"base": args.base, "adapter": args.adapter, "arms": {}}

    try:
        if not wait_ready(proc):
            results["arms"]["server"] = {"status": "never came up"}
            OUT.write_text(json.dumps(results, indent=2))
            return 1
        print(f"[serve] /v1/models -> {[m['id'] for m in get('/v1/models')['data']]}",
              flush=True)

        rows = generate(args.n_eval, args.eval_seed, FAMILIES)
        schema_block = tools_to_instruction(TOOLS)
        print(f"[shim] the schema renders as:\n{schema_block}\n", flush=True)

        for arm, suffix in (("trained instruction", None),
                            ("OpenAI schema", schema_block)):
            recs = {"calls": 0, "malformed": 0, "matched": 0, "wanted": 0,
                    "cases_with_a_call": 0, "records": []}
            t0 = time.time()
            for i, row in enumerate(rows, 1):
                stmt = row["prompt"].split("\n\n")[0]
                unit = row["unit"]
                prompt = (f"{stmt}\n\n{suffix}\n\n{INSTRUCTION % unit}" if suffix
                          else row["prompt"])
                text = chat(args.name, prompt, SYSTEM, args.max_tokens)
                tcs = to_tool_calls(text)
                book = {tuple(k): v for k, v in row["handbook"]}
                want = [answer(t, b, book) for _, t, b in row["chain"]
                        if t in ("lookup", "convert")]
                got = []
                for tc in tcs:
                    fn = tc["function"]
                    a = json.loads(fn["arguments"])
                    body = (a["_"] if list(a) == ["_"]
                            else "; ".join(f"{k}={v}" for k, v in a.items()))
                    try:
                        got.append(answer(fn["name"], body, book))
                    except ToolError:
                        recs["malformed"] += 1
                pool = list(want)
                m = 0
                for v in got:
                    hit = next((w for w in pool
                                if abs(v - w) <= 1e-6 * max(abs(w), 1)), None)
                    if hit is not None:
                        pool.remove(hit); m += 1
                recs["calls"] += len(tcs)
                recs["matched"] += m
                recs["wanted"] += len(want)
                recs["cases_with_a_call"] += bool(tcs)
                recs["records"].append({"case_id": row["case_id"],
                                        "tool_calls": len(tcs), "matched": m,
                                        "wanted": len(want), "raw": text[:300]})
                if i % 10 == 0:
                    print(f"  [{arm}] {i}/{len(rows)} calls {recs['calls']} "
                          f"tools {recs['matched']}/{recs['wanted']}", flush=True)
            recs["seconds"] = round(time.time() - t0, 1)
            results["arms"][arm] = recs
            OUT.write_text(json.dumps(results, indent=2))
            print(f"[arm] {arm}: {recs['matched']}/{recs['wanted']} oracle values, "
                  f"{recs['calls']} calls, {recs['malformed']} refused, "
                  f"{recs['cases_with_a_call']}/{len(rows)} cases produced a call",
                  flush=True)

        a = results["arms"]["trained instruction"]
        b = results["arms"]["OpenAI schema"]
        ra = a["matched"] / max(a["wanted"], 1)
        rb = b["matched"] / max(b["wanted"], 1)
        print(f"\ntrained {ra:.3f} · schema {rb:.3f} · the shim costs "
              f"{ra - rb:+.3f}", flush=True)
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
