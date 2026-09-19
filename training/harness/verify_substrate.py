"""Phase 0 — the serving substrate, verified before anything is built on it.

THE GLOBAL RULE, APPLIED TO THE FLOOR. Nothing counts as working until it has a
preflight, a persisted artefact, a test that re-verifies it, and a failure condition
written first. The substrate — one resident base, a pool of LoRAs vLLM actually
applies, tools reachable, stop strings honoured — is the layer everything else stands
on, and it has been checked by ritual rather than by a gate. Each gate below exists
because a number already paid for it:

    P0  `/v1/models` is the source of truth for the pool's members. A hand-kept list
        lags the thing it tracks; this repository has retired four of them **[ran]**.
    G1  C18: the delta term y = xW + s(xA)B is PRESENT. vLLM 0.29.0 loaded a LoRA on
        Qwen3.5-4B, logged it, and served the base **[ran]** P33. Three probes per
        member, and a member passes when at least 2 of 3 differ from the base — at
        temperature 0 a single short prompt can coincide, and a false NOT APPLIED
        would cost a session. P55 A's gate saw 6 of 8 differ on a real adapter.
    G2  the member reaches its tools through the proxy. P51's first arm served vLLM
        without the tool-call flags: 240 of 240 requests returned HTTP 400 and the
        progress line read `correct 0 calls 0` — a broken run wearing a floor
        **[ran]**. Skipped with a notice when no proxy is given: it is a gate on the
        system, not on the server alone.
    G3  `stop` + `include_stop_str_in_output` honoured on a continuation the model
        cannot avoid — the corpus-mode loop is impossible without it, and the first
        preflight that asked the model to write a tag measured the model's phrasing
        instead **[ran]** P55 A attempt 1.

THE VERDICT IS READ FROM THE FILE, NOT THE EXIT CODE. Records are written before the
summary, in the order P47 taught; the exit code exists for CI. `verdict.json` is the
truth for people.

    python3 -m training.harness.verify_substrate --out results/P56-substrate/verdict.json \\
        --adapter email-full=adapters/email-full --adapter fluids-full=adapters/fluids-full \\
        --proxy auto
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

import subprocess
import sys

from training.harness.accept_rank import HOST, post, serve, stop, stop_check, wait_ready

PROBES = (
    "Explain in two sentences why the sky is blue.",
    "List three things a careful reader checks before answering an email.",
    "Write one line describing what a pressure drop in a pipe depends on.",
)
NEED = 2            # of 3 probes must differ from the base for G1 to pass
OUT = Path("verdict.json")


def members(host: str = HOST) -> list[str]:
    with urllib.request.urlopen(host + "/v1/models", timeout=30) as r:
        return [m["id"] for m in json.load(r).get("data", [])]


def _say(model: str, prompt: str, tok, max_tokens: int = 48) -> str:
    text = tok.apply_chat_template([{"role": "user", "content": prompt}],
                                   tokenize=False, add_generation_prompt=True, enable_thinking=False)
    r = post("/v1/completions", {"model": model, "prompt": text,
                                 "temperature": 0, "max_tokens": max_tokens})
    return r["choices"][0].get("text") or ""


def identity(base: str, member: str, tok, probes=PROBES) -> dict:
    """G1. A member vLLM did not apply serves the base's text."""
    pairs = [(_say(base, p, tok), _say(member, p, tok)) for p in probes]
    # AN EMPTY ARM IS NOT A DIFFERENCE. P58's C18 gate read `None` against text as
    # "differs" on 8 of 8 probes over an arm that had produced nothing **[ran]**, and
    # this gate would have read `""` the same way. A probe counts only when BOTH sides
    # answered; a member that answers empty is reported as an empty arm, never as
    # applied.
    readable = [(a, b) for a, b in pairs if a.strip() and b.strip()]
    empty = len(pairs) - len(readable)
    differs = sum(a != b for a, b in readable)
    return {"probed": len(readable), "empty": empty, "differs": differs,
            "applied": differs >= NEED and empty == 0,
            "samples": [{"base": a[:60], "member": b[:60]} for a, b in pairs]}


def tools_reachable(proxy: str, member: str) -> dict:
    """G2. One request with a tool, through the proxy: no HTTP error, and either a
    tool call or an answer — never a 4xx that reads as `calls 0`."""
    payload = {"model": member, "temperature": 0, "max_tokens": 120,
               "messages": [{"role": "user", "content":
                             "Message msg-000 in thread thr-000\nFrom: A <a@x.com>\n"
                             "Subject: hello\nPreview: (waiting)\n\nIs this important?"}],
               "tools": [{"type": "function", "function": {
                   "name": "thread_history",
                   "parameters": {"type": "object",
                                  "properties": {"thread_id": {"type": "string"}},
                                  "required": ["thread_id"]}}}]}
    req = urllib.request.Request(proxy + "/v1/chat/completions", method="POST",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = json.load(r)
    except urllib.error.HTTPError as e:
        return {"reachable": False, "http": e.code, "body": e.read()[:200].decode("utf-8", "replace")}
    except Exception as e:
        return {"reachable": False, "error": repr(e)[:160]}
    msg = (out.get("choices") or [{}])[0].get("message") or {}
    return {"reachable": True, "tool_calls": len(msg.get("tool_calls") or []),
            "answered": bool(msg.get("content"))}


def verdict(record: dict) -> dict:
    """The one line CI reads, and the reason a person reads."""
    g1 = {m: r["applied"] for m, r in record["G1"].items()}
    empty = [f"G1:{m} (empty arm, {r.get('empty', 0)} probes)" for m, r in record["G1"].items()
             if r.get("empty")]
    g2 = record.get("G2") or {}
    g3 = record.get("G3", {}).get("stop_included", False)
    failed = [f"G1:{m}" for m, ok in g1.items() if not ok and not any(e.startswith(f"G1:{m} ") for e in empty)] + empty
    failed += [f"G2:{m}" for m, r in g2.items() if r.get("reachable") is False]
    if not g3:
        failed.append("G3")
    return {"pass": not failed and bool(g1), "failed": failed,
            "members": sorted(g1),
            "reading": ("SUBSTRATE OK — every member applies, tools reachable, stop "
                        "honoured" if not failed and g1 else
                        "SUBSTRATE FAILS: " + ", ".join(failed) if failed else
                        "SUBSTRATE EMPTY: no member besides the base")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", action="append", default=[],
                    help="name=path; when given, this runner serves the pool itself")
    ap.add_argument("--proxy", default=None,
                    help="the OpenAI proxy for G2; `auto` starts one here; skipped if absent")
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.base)

    # THE RUNNER SERVES THE POOL WHEN ASKED TO, like every other runner the chain
    # launches — the chain starts nothing but the module.
    procs = []
    adapters = dict(a.split("=", 1) for a in args.adapter)
    if adapters:
        extra = ["--max-model-len", str(args.max_model_len),
                 "--gpu-memory-utilization", "0.90", "--enable-lora",
                 "--max-lora-rank", "16", "--max-loras", str(len(adapters)),
                 "--lora-modules", *[f"{k}={v}" for k, v in adapters.items()]]
        procs.append(serve(args.base, extra))
        if not wait_ready(procs[-1]):
            out.write_text(json.dumps({"verdict": {"pass": False, "failed": ["serve"],
                                                   "reading": "the base never came up"},
                                       "finished": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=2))
            return 1
    if args.proxy == "auto":
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "training.harness.openai_proxy", "--upstream", HOST,
             "--port", "8001", "--prune"], stdout=open("proxy.log", "a"), stderr=subprocess.STDOUT))
        args.proxy = "http://127.0.0.1:8001"
        time.sleep(3)

    record = {"base": args.base, "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "P0": {}, "G1": {}, "G2": None, "G3": {}}

    def save():
        out.write_text(json.dumps(record, indent=2))

    ids = members()
    pool = [m for m in ids if m != args.base]
    record["P0"] = {"served": ids, "members": pool}
    print(f"[substrate] P0 members from /v1/models: {pool}", flush=True)
    save()

    for m in pool:
        record["G1"][m] = identity(args.base, m, tok)
        print(f"[substrate] G1 {m}: {record['G1'][m]['differs']}/{record['G1'][m]['probed']} "
              f"differ → {'applied' if record['G1'][m]['applied'] else 'NOT APPLIED'}", flush=True)
        save()

    if args.proxy:
        record["G2"] = {m: tools_reachable(args.proxy, m) for m in pool}
        for m, r in record["G2"].items():
            print(f"[substrate] G2 {m}: {r}", flush=True)
    else:
        print("[substrate] G2 skipped — no --proxy given; this gates the system, not the server",
              flush=True)
    save()

    record["G3"] = stop_check(args.base, tok.apply_chat_template(
        [{"role": "user", "content": "Count from 1 to 6, comma separated."}],
        tokenize=False, add_generation_prompt=True, enable_thinking=False))
    print(f"[substrate] G3 stop: {record['G3']}", flush=True)
    save()

    # THE RECORDS ARE ON DISK. Only now the summary, in a try, then saved again.
    try:
        record["verdict"] = verdict(record)
    except Exception as e:
        record["verdict"] = {"pass": False, "failed": ["summary"], "reading": repr(e)[:160]}
    record["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[substrate] {record['verdict']['reading']}", flush=True)
    for pr in procs:
        stop(pr)
    return 0 if record["verdict"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
