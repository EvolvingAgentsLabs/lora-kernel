"""Milestone 3 — the live OpenClaw turn, with `--prune` and `--auto`, measured.

WHAT P43 SHOWED AND DID NOT. OpenClaw → proxy → tunnel → the QLoRA answered, nothing
left the machine — and the turn made **no tool call at all**, because OpenClaw sent
its own tools and the expert answered from the listing **[ran]**. P59 then measured,
with the recorded 54-tool surface in a *simulation*, that unpruned the expert copies
tags off the block (225 of 227 calls refused) and pruned it calls its three. This runs
the real thing: OpenClaw with the inbox MCP server, the proxy pruning the surface and
routing `auto` by text, n synthetic turns, scored against the inbox's truth.

WHAT IS READ, AND FROM WHERE. Each turn is one `openclaw agent --local -m …` process.
Its stdout carries the reply; the proxy's traffic log (`--log`) carries the shapes of
every request the turn made — tools offered, tools kept, the reply text with its tags —
and the proxy's stdout carries the `[route]` decision. Nothing here reads the prompt
back out of the log: it is the synthetic listing this script wrote.

PRE-REGISTERED (CLAUDE.md §8b, milestone 3):

    routed_local == n            every turn stayed local through `auto`
    invented == 0                no call to a tool the agent was not offered
    calls_on_human ≥ 0.5         at least half the human turns called an inbox tool (P43: 0)
    human accuracy               reported against the 0.655 majority bar (§9.1) and
                                 beside P43's 0.741 (a different path) — descriptive

The failure written first: `invented > 0` means pruning did not reach the live path;
`calls_on_human < 0.5` means the live agent still answers from the listing.

    python3 -m training.harness.openclaw_live --n 40 --traffic traffic.jsonl \\
        --proxy-log proxy.log --out results/P63-openclaw-live-20260918/live.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path

from training.email.inbox import generate
from training.harness import bar
from training.harness.generate_email_full import listing

OPENCLAW = os.path.expanduser("~/.openclaw/bin/openclaw")
INBOX_TAGS = ("thread_history", "sender_stats", "message")
VERDICT = re.compile(r"\bNOT IMPORTANT\b|\bIMPORTANT\b", re.I)
TAG = re.compile(r"<([A-Za-z_][\w.:-]*)>[^<]*</\1>")


def parse_verdict(text: str):
    """The last IMPORTANT / NOT IMPORTANT the agent said; None if it said neither."""
    hits = VERDICT.findall(text or "")
    if not hits:
        return None
    return hits[-1].upper() != "NOT IMPORTANT"


def read_new_lines(path: Path, offset: int) -> tuple[list[str], int]:
    if not path.exists():
        return [], offset
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read()
    return data.decode("utf-8", "replace").splitlines(), offset + len(data)


def shapes_of(traffic_lines: list[str]) -> dict:
    """Per turn, from the proxy's shapes: requests, tools offered/kept, calls the
    expert wrote, calls to names it was never offered."""
    reqs = calls = invented = offered = kept = 0
    for l in traffic_lines:
        try:
            r = json.loads(l)
        except json.JSONDecodeError:
            continue
        reqs += 1
        tools = r.get("tools") or []
        offered = max(offered, int(r.get("tools_offered") or 0))
        kept = max(kept, len(tools))
        for name in TAG.findall(r.get("reply") or r.get("text") or ""):
            calls += 1
            if name not in tools and name.split("__")[-1] not in tools:
                invented += 1
    return {"requests": reqs, "tools_offered": offered, "tools_kept": kept,
            "calls": calls, "invented": invented}


def verdict(records: list[dict], n: int) -> dict:
    hum = [r for r in records if r.get("human") and "error" not in r]
    ok = sum(bool(r.get("correct")) for r in hum)
    with_call = sum(r["shapes"]["calls"] > 0 for r in hum)
    out = {"n": len(records), "errors": sum("error" in r for r in records),
           "routed_local": sum(r.get("route") == "local" for r in records),
           "routed_out": sum(r.get("route") == "out" for r in records),
           "invented": sum(r["shapes"]["invented"] for r in records if "shapes" in r),
           "human": {"n": len(hum), "correct": ok,
                     "accuracy": round(ok / len(hum), 4) if hum else None,
                     "with_a_call": with_call,
                     "call_share": round(with_call / len(hum), 4) if hum else None},
           "undecided": sum(r.get("verdict") is None for r in records if "error" not in r)}
    out["gate"] = bar.verdict(ok, len(hum), 0.655) if hum else None
    out["routed_local_all"] = out["routed_local"] == len(records) and out["routed_out"] == 0
    out["calls_reach_the_live_path"] = out["invented"] == 0
    out["agent_uses_the_tools"] = (out["human"]["call_share"] or 0) >= 0.5
    out["passes"] = out["routed_local_all"] and out["calls_reach_the_live_path"] and out["agent_uses_the_tools"]
    out["reading"] = (f"{'LIVE' if out['passes'] else 'NOT LIVE'}: {out['routed_local']}/{out['n']} local, "
                      f"{out['invented']} invented calls, {with_call}/{len(hum)} human turns called a tool, "
                      f"human {out['human']['accuracy']} vs bar 0.655")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--inbox-n", type=int, default=150)
    ap.add_argument("--seed", type=int, default=717171)
    ap.add_argument("--profile", default="lorakernel")
    ap.add_argument("--model", default="lorapool/auto")
    ap.add_argument("--traffic", default="traffic.jsonl")
    ap.add_argument("--proxy-log", default="proxy.log")
    ap.add_argument("--openclaw", default=OPENCLAW)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--out", default="live.json")
    args = ap.parse_args()

    msgs = generate(args.inbox_n, args.seed)["messages"][:args.n]
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(model=args.model, profile=args.profile, n=len(msgs), seed=args.seed,
               started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    done = rec.setdefault("records", {})
    traffic, plog = Path(args.traffic), Path(args.proxy_log)
    t_off = traffic.stat().st_size if traffic.exists() else 0
    p_off = plog.stat().st_size if plog.exists() else 0

    for i, m in enumerate(msgs):
        if m["id"] in done:
            continue
        prompt = listing(m) + "\nAnswer with one line: IMPORTANT or NOT IMPORTANT."
        t0 = time.time()
        try:
            run = subprocess.run([args.openclaw, "--profile", args.profile, "agent", "--local",
                                  "--model", args.model, "-m", prompt],
                                 capture_output=True, text=True, timeout=args.timeout)
            text = run.stdout + "\n" + run.stderr
        except subprocess.TimeoutExpired:
            done[m["id"]] = {"id": m["id"], "human": not m["_facts"]["automated"], "error": "timeout"}
            out.write_text(json.dumps(rec, indent=1)); continue
        tl, t_off = read_new_lines(traffic, t_off)
        pl, p_off = read_new_lines(plog, p_off)
        route = "local" if any("[route] auto -> local" in l for l in pl) else \
                "out" if any("[route] auto -> out" in l or "[route] OUT" in l for l in pl) else "none"
        said = parse_verdict(run.stdout)
        r = {"id": m["id"], "human": not m["_facts"]["automated"], "truth": m["_truth"],
             "verdict": said, "correct": said == m["_truth"], "route": route,
             "shapes": shapes_of(tl), "rc": run.returncode, "seconds": round(time.time() - t0, 1),
             "reply_tail": run.stdout.strip()[-160:]}
        done[m["id"]] = r
        out.write_text(json.dumps(rec, indent=1))
        ok = sum(bool(x.get("correct")) for x in done.values())
        print(f"[live] {len(done)}/{len(msgs)} {m['id']} route={route} calls={r['shapes']['calls']} "
              f"invented={r['shapes']['invented']} said={said} truth={m['_truth']} correct so far {ok} "
              f"{r['seconds']}s", flush=True)

    rec["verdict"] = verdict(list(done.values()), len(msgs))
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.write_text(json.dumps(rec, indent=1))
    print(f"[live] {rec['verdict']['reading']}", flush=True)
    return 0 if rec["verdict"]["passes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
