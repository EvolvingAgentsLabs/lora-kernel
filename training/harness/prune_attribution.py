"""Phase 5, first buy — does pruning the tool surface turn zero calls into calls?

THE NUMBER THIS BUYS. P43 ran the pool inside a real agent and the agent turn made
**no tool calls at all**: OpenClaw offered **54 tools** to an expert trained on three,
and the three it knew arrived under a namespaced name **[ran]**. `openai_proxy
--prune` was built to fix exactly that (#190) and has never been measured against the
surface that caused it. This is the attribution arm: the same expert, the same 475
cases, the same client, **the real 54-tool surface** — with `--prune` off and on.

THE MATHEMATICS (docs/FOUNDATIONS.md §4.4, §9.2). The adapter learned
p(x_t | x_<t) for prefixes carrying a three-line tool block; served a 54-line block it
is extrapolating, and P25 priced an unknown surface at 27 of 63. Pruning restores the
trained prefix byte for byte (`tests/test_prune.py`). The two arms are compared on the
same cases by the exact two-sided sign test on discordant pairs; the pre-registered
reading is in the brief.

WHY THROUGH THE PROXY AND `tool_calls`, NOT CORPUS MODE. This is the product path —
the one an agent runtime actually takes — and the number P43 reported (0.741) was
taken on it. Corpus mode is the instrument's path and scores 0.989; the gap between
them is the serving drift (§8.1), already measured and not the question here.

    python3 -m training.harness.prune_attribution --adapter email-full=adapters/email-full \\
        --tools results/P59-prune-attribution-20260917/openclaw_tools.json \\
        --out results/P59-prune-attribution-20260917/attribution.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from training.harness import bar
from training.harness.accept_rank import HOST, serve, stop, wait_ready

OUT = Path("attribution.json")


def proxy(prune: bool, port: int = 8001) -> subprocess.Popen:
    cmd = [sys.executable, "-m", "training.harness.openai_proxy", "--upstream", HOST,
           "--port", str(port)] + (["--prune"] if prune else [])
    print(f"[attr] {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, stdout=open("proxy.log", "a"), stderr=subprocess.STDOUT)


def sim(model: str, n: int, tools_json: str, out: Path, port: int = 8001,
        max_turns: int = 6) -> dict:
    cmd = [sys.executable, "-u", "-m", "training.harness.agent_sim",
           "--base-url", f"http://127.0.0.1:{port}/v1", "--model", model, "--n", str(n),
           "--max-turns", str(max_turns), "--tools-json", tools_json, "--out", str(out)]
    print(f"[attr] {' '.join(cmd)}", flush=True)
    subprocess.call(cmd)
    return json.loads(out.read_text())


def _map(arm: dict) -> dict:
    """{case: correct} over the records that actually ran. An errored record is not
    a wrong answer: P59's first attempt had all 475 `--prune off` requests fail with
    "maximum context length is 4096" — the 54-tool block does not fit — and a map
    that counted them as incorrect produced PRUNING PAYS 385 : 0 over an arm that had
    never reached the model **[ran]** 2026-09-17."""
    return {r["id"]: bool(r.get("correct")) for r in arm.get("records", [])
            if "id" in r and not r.get("error")}


def errors(arm: dict) -> int:
    return sum(1 for r in arm.get("records", []) if r.get("error"))


def compare(off: dict, on: dict) -> dict:
    e_off, e_on = errors(off), errors(on)
    calls_off = off.get("calls", 0); calls_on = on.get("calls", 0)
    # AN ARM WITH ERRORS VOIDS THE VERDICT. A broken run must not be able to look like
    # a floor; the count is reported and the comparison is not made.
    if e_off or e_on:
        return {"state": "VOID", "errors_off": e_off, "errors_on": e_on,
                "calls_off": calls_off, "calls_on": calls_on,
                "reading": (f"VOID: transport errors — off {e_off}, on {e_on} of "
                            f"{len(off.get('records', []))}; nothing is compared")}
    c = bar.compare(_map(on), _map(off))
    state = ("PRUNING PAYS" if c["different"] and c["only_a"] > c["only_b"] else
             "PRUNING HURTS" if c["different"] else "a tie")
    return {**c, "errors_off": 0, "errors_on": 0, "calls_off": calls_off, "calls_on": calls_on,
            "human_off": off.get("human_accuracy"), "human_on": on.get("human_accuracy"),
            "state": state,
            "reading": (f"{state}: --prune off {off.get('human_accuracy')} vs on "
                        f"{on.get('human_accuracy')} on human messages, paired "
                        f"{c['only_a']}:{c['only_b']} p={c['p_value']}; calls {calls_off} → {calls_on}")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", action="append", default=[], help="name=path")
    ap.add_argument("--model", default="email-full")
    ap.add_argument("--tools", required=True, help="JSON list of the tool schemas a runtime sends")
    ap.add_argument("--n", type=int, default=475)
    # THE 54-TOOL BLOCK NEEDS ROOM. Rendered, it is several thousand tokens on its
    # own; at 4096 every `--prune off` request was refused before reaching the model
    # **[ran]** P59 attempt 1. The runtime that sent it (OpenClaw, P43) got an answer,
    # because vLLM was serving at its default length there.
    ap.add_argument("--max-model-len", type=int, default=16384)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    tools = json.loads(Path(args.tools).read_text())
    result = {"base": args.base, "model": args.model, "n": args.n, "tools_offered": len(tools),
              "tool_names": [t["function"]["name"] for t in tools][:60],
              "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "arms": {}}

    def save():
        out.write_text(json.dumps(result, indent=2))

    save()
    adapters = dict(a.split("=", 1) for a in args.adapter)
    extra = ["--max-model-len", str(args.max_model_len), "--gpu-memory-utilization", "0.90",
             "--enable-lora", "--max-lora-rank", "16", "--max-loras", str(len(adapters)),
             "--lora-modules", *[f"{k}={v}" for k, v in adapters.items()]]
    v = serve(args.base, extra)
    try:
        if not wait_ready(v):
            result["stopped"] = "the base never came up"; save(); return 1
        # THE ARM THAT REPRODUCES P43 FIRST. If `--prune off` does not reproduce the
        # zero-call turn, the surface replayed here is not the one that caused it.
        for name, prune in (("off", False), ("on", True)):
            px = proxy(prune)
            time.sleep(4)
            try:
                arm_out = out.parent / f"arm_prune_{name}.json"
                result["arms"][name] = sim(args.model, args.n, args.tools, arm_out)
                a = result["arms"][name]
                print(f"[attr] arm prune={name}: human {a.get('human_accuracy')} "
                      f"calls {a.get('calls')} errors {errors(a)}", flush=True)
                save()
            finally:
                stop(px)
    finally:
        stop(v)
    try:
        result["verdict"] = compare(result["arms"]["off"], result["arms"]["on"])
    except Exception as e:
        result["verdict"] = {"state": "unreadable", "reading": repr(e)[:160]}
    result["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[attr] {result['verdict']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
