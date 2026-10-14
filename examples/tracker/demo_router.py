r"""The router demo: one developer session on the user's Mac — two turns the local member serves with its tools, one it
abstains on and the role's egress forwards to the frontier. Plain HTTP against a gateway already serving the tracker
(see `live_tracker.py` for the server lines), printed for a terminal recording and saved whole:

    python -m examples.tracker.demo_router --out results/DEMO-router-mac-20261013/demo.json

The in-scope turns are LIVE-tracker's developer session (`live_tracker.sessions`, the issue the served store holds); the
out-of-scope turn is a held-out ROUTE1 request `tr-out-s0` sent to the egress [ran], sent as the first turn of\na session of its own, as ROUTE1 measured it. Nothing printed is edited.
"""

from __future__ import annotations

import argparse
import json
import textwrap
import time
import urllib.request
from pathlib import Path

from examples.common import tokens
from examples.tracker.live_tracker import sessions

OUT_OF_SCOPE = "How do you say 'deadline' in French?"
DIM, BOLD, GREEN, ORANGE, RESET = "\033[2m", "\033[1m", "\033[32m", "\033[33m", "\033[0m"


def post(url: str, token: str, sid: str, text: str) -> dict:
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", method="POST",
                                 data=json.dumps({"model": "auto", "messages": [{"role": "user", "content": text}]}).encode(),
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}",
                                          "X-Session-Id": sid})
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gateway", default="http://127.0.0.1:8765")
    ap.add_argument("--out", required=True)
    ap.add_argument("--pause", type=float, default=1.5, help="seconds between turns, for the recording")
    a = ap.parse_args()
    dev = next(s for s in sessions(time.strftime("%H%M%S")) if s["user_id"].startswith("developer"))
    token = tokens.issue(dev["user_id"], "developer", dev["org"])
    requests = [t["request"] for t in dev["turns"][:2]] + [OUT_OF_SCOPE]
    rec = {"started": time.strftime("%Y-%m-%dT%H:%M:%S"), "user": dev["user_id"], "turns": []}
    print(f"{DIM}developer · {dev['org']} · Gemma 4 E4B Q8_0 + tr-out-s0 on llama.cpp, this laptop{RESET}\n")
    for i, text in enumerate(requests):
        # the out-of-scope request opens its own session: ROUTE1 taught and measured abstention only as a session's first
        # turn, and mid-session it was not shown (attempt 1, results/DEMO-router-mac-20261013/BRIEF.md)
        sid = dev["session_id"] if text != OUT_OF_SCOPE else dev["session_id"] + "-new"
        if text == OUT_OF_SCOPE:
            print(f"{DIM}new session{RESET}")
        print(f"{BOLD}> {text}{RESET}", flush=True)
        t0 = time.time()
        res = post(a.gateway, token, sid, text)
        wall = round(time.time() - t0, 2)
        route, calls = res.get("x_route"), res.get("x_calls") or []
        reply = res["choices"][0]["message"]["content"]
        for c in calls:
            args = ", ".join(f"{k}={v}" for k, v in (c.get("args") or {}).items())
            res_ = str(c.get("result", c.get("error", c.get("held", ""))))
            print(f"{DIM}  tool  {c.get('tool')}({args}) → {textwrap.shorten(res_, 70)}{RESET}")
        tag = f"{GREEN}local · this laptop{RESET}" if route == "local" else f"{ORANGE}{route} · OUT OF SCOPE for this member{RESET}"
        print(f"  route {tag} {DIM}· {wall} s{RESET}")
        print(textwrap.indent(textwrap.fill(reply, 96), "  "), "\n", flush=True)
        rec["turns"].append({"session": sid, "request": text, "route": route, "calls": calls, "reply": reply, "wall_s": wall})
        time.sleep(a.pause)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
