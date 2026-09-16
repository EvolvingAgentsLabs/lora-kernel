"""One desk question, one conversation, as many tool turns as the model asks for.

The same shape as `agent_sim`, over the regenerated suite and its four-tool surface.
What it adds is that the case carries its own inbox, so every question is asked about
a desk drawn for it and nothing can be memorised across cases.

IT KEEPS THE TRANSCRIPT. P40 stored `{"answer": 35584.2}` and the question the pool
exists to answer — which expert to trust, per case — was not computable from a
finished run **[ran]**. A ranking experiment needs the chain even more than a scoring
one does.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from training.email.desk import correct, generate, tools_needed
from training.email.desk_tools import SCHEMA, ToolError, answer

SYSTEM = (
    "You are a desk assistant for one person's inbox. Use the tools to find what you "
    "need before answering — the listing does not carry it. Answer with the value "
    "asked for and nothing else: a name, a date, a message id, or yes/no."
)


def _param(tool: str) -> str:
    for t in SCHEMA:
        fn = t["function"]
        if fn["name"] == tool:
            req = fn["parameters"].get("required") or sorted(
                fn["parameters"]["properties"])
            return req[0] if req else ""
    return ""


def _body(tool: str, arguments) -> str:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except Exception:
            return arguments
    if not isinstance(arguments, dict):
        return str(arguments)
    return "; ".join(f"{k}={v}" for k, v in arguments.items())


def chat(base_url: str, key: str | None, payload: dict, timeout: int = 300) -> dict:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
                                 json.dumps(payload).encode(), headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def ask_one(base_url, key, model, case, max_turns, max_tokens):
    desk = case["desk"]
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": case["prompt"]}]
    calls = refused = 0
    asked: list[dict] = []
    for _ in range(max_turns):
        try:
            out = chat(base_url, key, {"model": model, "messages": messages,
                                       "tools": SCHEMA, "temperature": 0,
                                       "max_tokens": max_tokens})
        except urllib.error.HTTPError as e:
            return {"said": None, "error": e.read()[:160].decode("utf-8", "replace"),
                    "calls": calls, "refused": refused}
        except Exception as e:
            return {"said": None, "error": repr(e)[:160], "calls": calls,
                    "refused": refused}
        m = (out.get("choices") or [{}])[0].get("message") or {}
        tcs = m.get("tool_calls") or []
        messages.append({k: v for k, v in m.items()
                         if k in ("role", "content", "tool_calls")}
                        or {"role": "assistant", "content": ""})
        if not tcs:
            said = (m.get("content") or "").strip()
            return {"said": said, "calls": calls, "refused": refused,
                    "turns": len(messages), "asked": asked,
                    "transcript": [{"role": x.get("role"),
                                    "content": (x.get("content") or "")[:400],
                                    "tool": x.get("name")} for x in messages]}
        for tc in tcs:
            fn = tc["function"]
            calls += 1
            try:
                result = answer(desk, fn["name"], _body(fn["name"], fn["arguments"]))
            except ToolError as e:
                refused += 1
                asked.append({"name": fn["name"],
                              "args": str(fn.get("arguments"))[:120],
                              "error": str(e)[:120]})
                result = f"ERROR: {e}"
            messages.append({"role": "tool", "tool_call_id": tc.get("id"),
                             "name": fn["name"], "content": result})
    return {"said": None, "calls": calls, "refused": refused,
            "turns": len(messages), "asked": asked, "out_of_turns": True}


def summarise(records: list[dict]) -> dict:
    n = len(records)
    if not n:
        return {"n": 0}
    cells: dict[str, dict] = {}
    for r in records:
        key = f"{r['region']}@{r['depth']}"
        row = cells.setdefault(key, {"n": 0, "correct": 0})
        row["n"] += 1
        row["correct"] += bool(r["correct"])
    for row in cells.values():
        row["rate"] = round(row["correct"] / row["n"], 4)
    by_region: dict[str, dict] = {}
    for r in records:
        row = by_region.setdefault(r["region"], {"n": 0, "correct": 0})
        row["n"] += 1
        row["correct"] += bool(r["correct"])
    for row in by_region.values():
        row["rate"] = round(row["correct"] / row["n"], 4)
    return {"n": n, "correct": sum(r["correct"] for r in records),
            "accuracy": round(sum(r["correct"] for r in records) / n, 4),
            "calls": sum(r.get("calls", 0) for r in records),
            "refused": sum(r.get("refused", 0) for r in records),
            "errors": sum("error" in r for r in records),
            "out_of_turns": sum(bool(r.get("out_of_turns")) for r in records),
            "by_cell": dict(sorted(cells.items())),
            "by_region": dict(sorted(by_region.items()))}


def run(base_url, key, model, cases, max_turns, max_tokens, out: Path,
        every: int = 20) -> list[dict]:
    """Score every case, checkpointing as it goes. P47 was lost twice without this."""
    done: dict[str, dict] = {}
    if out.exists():
        try:
            done = {r["id"]: r for r in json.loads(out.read_text()).get("records", [])}
        except Exception as e:
            print(f"[desk] could not reuse {out}: {e!r}", flush=True)
    if done:
        print(f"[desk] resuming — {len(done)} already scored", flush=True)
    recs: list[dict] = []
    t0 = time.time()
    for i, case in enumerate(cases, 1):
        if case["case_id"] in done:
            recs.append(done[case["case_id"]])
            continue
        r = ask_one(base_url, key, model, case, max_turns, max_tokens)
        r |= {"id": case["case_id"], "region": case["region"],
              "depth": case["depth"], "answer": case["answer"],
              "tools_needed": tools_needed(case),
              "correct": correct(case, r.get("said"))}
        recs.append(r)
        if len(recs) % every == 0 or i == len(cases):
            out.write_text(json.dumps({**summarise(recs), "model": model,
                                       "partial": i < len(cases),
                                       "seconds": round(time.time() - t0, 1),
                                       "records": recs}, indent=2))
            s = summarise(recs)
            print(f"[desk] {model} {i}/{len(cases)} correct {s['correct']} "
                  f"calls {s['calls']} refused {s['refused']}", flush=True)
    return recs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8001/v1")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--n", type=int, default=240)
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=250)
    ap.add_argument("--out", default="desk_results.json")
    args = ap.parse_args()
    cases = generate(args.n, args.seed)["cases"]
    recs = run(args.base_url, args.api_key, args.model, cases, args.max_turns,
               args.max_tokens, Path(args.out))
    s = summarise(recs)
    print(f"\n{s['correct']}/{s['n']} = {s['accuracy']:.3f}")
    for k, v in s["by_region"].items():
        print(f"  {k:12} {v['correct']:3d}/{v['n']:<3d} = {v['rate']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
