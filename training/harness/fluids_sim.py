"""The fluids expert, driven the same way the email one is: OpenAI over HTTP.

WHY IT HAD TO BE WRITTEN. `multitool_run` runs the model **in process** with PEFT
(`peft_model.set_adapter`). That is fine for measuring an adapter and useless for
measuring a *pool*: the thesis is that the agentic system is QLoRAs over **one
resident base, selected by the `model` field of a request**, and two adapters scored
in two different processes demonstrate two adapters, not a pool.

So this is `agent_sim` for fluid mechanics — same shape, same protocol, a different
domain and a different oracle. It speaks only OpenAI: a base URL, a model name,
`tools`, `tool_calls`, `role: "tool"`.

**The converter stays domain-free and this file does not change it.** P27 measured
`tool_calls.py` at 0 of 38 lines naming a tool or a domain; the one thing a client
must own is its own schema, so the positional-argument shim lives here exactly as it
does in `agent_sim`.

SEVEN CALLS DEEP, NOT THREE. A hydrostatic-force case converts two lengths, looks up
a density and computes three values, so `--max-turns` defaults well above the email
loop's. A run that silently ran out of turns would look like a model that could not
finish the physics.

    python3 -m training.harness.fluids_sim --base-url http://127.0.0.1:8001/v1 \\
        --model fluids-full --n 90
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error

from training.harness.agent_sim import chat
from training.physics import multitool as mod
from training.physics.headroom import correct, parse_answer
from training.physics.tools import SCHEMA, ToolError, answer

SCORER_RTOL = 0.02


def _param_name(tool: str) -> str:
    for t in SCHEMA:
        fn = t["function"]
        if fn["name"] == tool:
            req = fn["parameters"].get("required") or sorted(fn["parameters"]["properties"])
            return req[0]
    return "expression"


def _body(tool: str, arguments) -> str:
    """`tool_calls` arguments back into the string the tool reads.

    `calc` takes one required parameter, so P28's arity convention renders it
    positionally and the shim hands back `{"_": "..."}`. Mapping `_` onto the real
    name needs the schema, and the client owns the schema.
    """
    a = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
    if list(a) == ["_"]:
        name = _param_name(tool)
        # `calc` reads its expression raw, not as `expression=...`
        return str(a["_"]) if tool == "calc" else f"{name}={a['_']}"
    if tool == "calc":
        return str(next(iter(a.values())))
    return "; ".join(f"{k}={v}" for k, v in a.items())


def solve_one(base_url, key, model, case, max_turns, max_tokens):
    """One problem, as many tool turns as the model asks for."""
    book = {tuple(k): v for k, v in case["handbook"]}
    messages = [{"role": "user", "content": case["prompt"]}]
    calls = refused = 0
    asked: list[dict] = []
    for _ in range(max_turns):
        try:
            out = chat(base_url, key, {"model": model, "messages": messages,
                                       "tools": SCHEMA, "temperature": 0,
                                       "max_tokens": max_tokens})
        except Exception as e:
            return {"id": case["case_id"], "family": case["family"], "got": None,
                    "passed": False, "calls": calls, "refused": refused,
                    "asked": asked, "error": repr(e)[:160], "text": ""}

        m = (out.get("choices") or [{}])[0].get("message") or {}
        tcs = m.get("tool_calls") or []
        messages.append({k: v for k, v in m.items()
                         if k in ("role", "content", "tool_calls")} or
                        {"role": "assistant", "content": ""})
        if not tcs:
            text = m.get("content") or ""
            got = parse_answer(text)
            return {"id": case["case_id"], "family": case["family"], "got": got,
                    "passed": bool(correct(got, case["answer"], SCORER_RTOL)),
                    "calls": calls, "refused": refused, "asked": asked,
                    "text": text[:300]}
        for tc in tcs:
            fn = tc["function"]
            calls += 1
            try:
                # THE HANDBOOK TRAVELS WITH THE CASE. A fixed table would let the
                # expert answer from memory — P15 measured 27/30 that way [ran].
                result = f"{answer(fn['name'], _body(fn['name'], fn['arguments']), book):.6g}"
            except ToolError as e:
                refused += 1
                asked.append({"name": fn["name"],
                              "args": str(fn.get("arguments"))[:120],
                              "error": str(e)[:120]})
                result = f"ERROR: {e}"
            messages.append({"role": "tool", "tool_call_id": tc.get("id"),
                             "name": fn["name"], "content": result})
    # RUNNING OUT OF TURNS IS ITS OWN OUTCOME, and it must not read as wrong physics.
    return {"id": case["case_id"], "family": case["family"], "got": None,
            "passed": False, "calls": calls, "refused": refused, "asked": asked,
            "text": "(ran out of turns)", "out_of_turns": True}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--model", default="fluids-full")
    ap.add_argument("--n", type=int, default=90)
    ap.add_argument("--seed", type=int, default=616161)
    ap.add_argument("--max-turns", type=int, default=14)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--out", default="fluids_results.json")
    args = ap.parse_args()

    cases = mod.generate(args.n, args.seed, mod.FAMILIES)
    recs, t0 = [], time.time()
    for i, case in enumerate(cases, 1):
        recs.append(solve_one(args.base_url, args.api_key, args.model, case,
                              args.max_turns, args.max_tokens))
        if i % 10 == 0 or i == len(cases):
            ok = sum(r["passed"] for r in recs)
            print(f"[fluids] {i}/{len(cases)} passed {ok} "
                  f"calls {sum(r['calls'] for r in recs)} "
                  f"refused {sum(r['refused'] for r in recs)}", flush=True)

    from collections import Counter
    out = {"model": args.model, "n": len(recs),
           "passed": sum(r["passed"] for r in recs),
           "accuracy": round(sum(r["passed"] for r in recs) / max(len(recs), 1), 4),
           "calls": sum(r["calls"] for r in recs),
           "refused": sum(r["refused"] for r in recs),
           "out_of_turns": sum(bool(r.get("out_of_turns")) for r in recs),
           "by_family": {k: v for k, v in
                         Counter(r["family"] for r in recs if r["passed"]).items()},
           "seconds": round(time.time() - t0, 1), "records": recs}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n{out['passed']}/{out['n']} = {out['accuracy']:.3f} · "
          f"{out['calls']} calls, {out['refused']} refused, "
          f"{out['out_of_turns']} ran out of turns", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
