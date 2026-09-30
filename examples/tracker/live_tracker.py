r"""The tracker's long sessions through a REAL agent runtime — OpenClaw, one profile per user, each holding that user's
signed token — against a gateway already serving the tracker with the operational memory and without the tool block:

    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-tracker-wf-s1-f16.gguf --port 8792 -c 8192 -ngl 99
    python -m examples.school.gateway --org tracker --member tr-s1 --upstream http://127.0.0.1:8792 \
        --tokenizer google/gemma-4-E4B-it --memory --no-tool-block --max-calls 6 --port 8765
    python -m examples.tracker.live_tracker --out results/LIVE-tracker-openclaw-<date>/live.json

One session per role (developer, lead, qa), four and five turns each, on the gateway's own store (`db.build()`, the demo
team) with H3's held-out wording. Every turn goes through `openclaw agent --local --session-id <session> -m`, so OpenClaw
keeps the conversation and the gateway reads only the last request and the memory's one line. A turn is scored on the
gateway's own event for it, by H3's scorer (`turn_right_h3`) — the same check as the measurement, so the difference
between H3 and this run is the runtime (OpenClaw, llama.cpp Q8_0 on the user's machine). Pre-registered in the run's BRIEF.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from examples.school.live_openclaw import OPENCLAW, reply_of
from examples.tracker import db
from examples.tracker import generate_sessions as gs


def sessions(run: str = "") -> list[dict]:
    """One session per role on the demo team's world: H3's fresh wording, the plan computed on `db.build()` itself, so the
    key the lead's bug will get and the issues the developer and QA open are the ones the served store holds. Order:
    lead first (it creates the next key), then developer, then QA — none touches another's issue."""
    out = []
    for kind in ("lead", "developer", "qa"):
        s = gs.session(db.DEMO_SEED, "eval", kind, "h3")
        if s is None:
            raise SystemExit(f"the demo world has no issue for a {kind} session")
        # a fresh OpenClaw session per run: OpenClaw keeps a session's conversation, and a rerun must not inherit it
        out.append({**s, "session_id": f"live-{kind}-{s['org']}" + (f"-{run}" if run else "")})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--openclaw", default=str(OPENCLAW))
    ap.add_argument("--patches", default=str(Path.home() / ".config/lora-kernel/openclaw"))
    ap.add_argument("--events", default="examples/tracker/events.jsonl", help="the gateway's --log")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    events = Path(a.events)
    rec = {"org": "tracker", "runtime": subprocess.run([a.openclaw, "--version"], capture_output=True, text=True).stdout.strip(),
           "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "sessions": []}
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    for s in sessions(time.strftime("%H%M%S")):
        profile = f"tracker-{s['user_id']}"
        subprocess.run([a.openclaw, "--profile", profile, "config", "patch", "--file", str(Path(a.patches) / f"{s['user_id']}.json5")],
                       capture_output=True, text=True, check=True)
        turns = []
        for t in s["turns"]:
            seen = len(events.read_text().splitlines()) if events.exists() else 0
            t0 = time.time()
            p = subprocess.run([a.openclaw, "--profile", profile, "agent", "--local", "--session-id", s["session_id"], "-m", t["request"]],
                               capture_output=True, text=True, timeout=a.timeout)
            new = [json.loads(l) for l in events.read_text().splitlines()[seen:]] if events.exists() else []
            ev = new[-1] if new else {}
            right = bool(ev) and gs.turn_right_h3(ev.get("calls", []), t)
            reply = reply_of(p.stdout)
            turns.append({"request": t["request"], "tool": t["tool"], "depends": t["depends"], "right": right,
                          "calls": ev.get("calls", []), "route": ev.get("route"), "reply": reply, "turns_seen": len(new),
                          "runtime_s": round(time.time() - t0, 2), "gateway_latency_s": ev.get("latency_s"),
                          "prompt_tokens": ev.get("prompt_tokens")})
            print(f"[live] {s['kind']} t{len(turns)}: {'PASS' if right else 'FAIL'} {t['tool']} · {reply[:90]!r}", flush=True)
            rec_s = {"session_id": s["session_id"], "kind": s["kind"], "user": s["user_id"], "turns": turns}
            out.write_text(json.dumps({**rec, "sessions": rec["sessions"] + [rec_s]}, indent=1, ensure_ascii=False))
        rec["sessions"].append(rec_s)
    allt = [t for s in rec["sessions"] for t in s["turns"]]
    rec.update(passed=sum(t["right"] for t in allt), turns=len(allt),
               dependent=f"{sum(t['right'] for t in allt if t['depends'])}/{sum(t['depends'] for t in allt)}",
               finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print(f"[live] {rec['passed']}/{rec['turns']} turns right (dependent {rec['dependent']}) through {rec['runtime']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
