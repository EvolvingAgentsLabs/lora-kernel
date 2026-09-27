r"""The school demo through a REAL agent runtime — OpenClaw, one profile per role, each holding that role's signed token —
against a gateway already serving (`python -m examples.school.gateway …`). Runs on the user's machine: OpenClaw and the
gateway run no model; the model is wherever `--upstream` points (a rented card through `serve_tunnel`).

For each of `demo_run.SCENES`: the scene's user gets an OpenClaw profile `school-<user>` patched with the file the gateway
wrote (`~/.config/lora-kernel/openclaw/<user>.json5`), the request is sent with `openclaw agent --local -m`, the reply is
what OpenClaw printed, and the route and tool calls are the gateway's own event for that turn. Scored by
`demo_run.check` — the same checks as the scripted demo, so the difference between the two runs is the runtime.

    python -m examples.school.live_openclaw --out results/<run>/live.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

OPENCLAW = Path.home() / ".openclaw/bin/openclaw"
_LOG = re.compile(r"^\s*(\x1b\[[0-9;]*m)*\[[a-z0-9/_-]+\]")


def reply_of(stdout: str) -> str:
    """What OpenClaw showed the person: its output with its own `[tag] …` log lines removed."""
    lines = [l for l in stdout.splitlines() if l.strip() and not _LOG.match(l)]
    return "\n".join(lines).strip()


def main() -> int:
    from examples.school.demo_run import SCENES, check
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--patches", default=str(Path.home() / ".config/lora-kernel/openclaw"))
    ap.add_argument("--events", default="examples/school/events.jsonl", help="the gateway's --log")
    ap.add_argument("--openclaw", default=str(OPENCLAW))
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--out", default="live_openclaw.json")
    a = ap.parse_args()
    events = Path(a.events)
    rec = {"runtime": subprocess.run([a.openclaw, "--version"], capture_output=True, text=True).stdout.strip(),
           "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "scenes": []}
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    for who, text, expect in SCENES:
        profile = f"school-{who}"
        subprocess.run([a.openclaw, "--profile", profile, "config", "patch", "--file", str(Path(a.patches) / f"{who}.json5")],
                       capture_output=True, text=True, check=True)
        seen = len(events.read_text().splitlines()) if events.exists() else 0
        t0 = time.time()
        p = subprocess.run([a.openclaw, "--profile", profile, "agent", "--local", "-m", text],
                           capture_output=True, text=True, timeout=a.timeout)
        new = [json.loads(l) for l in events.read_text().splitlines()[seen:]] if events.exists() else []
        ev = new[-1] if new else {}
        reply = reply_of(p.stdout)
        res = check(expect, {"x_route": ev.get("route"), "x_calls": ev.get("calls", []),
                             "choices": [{"message": {"content": reply}}]})
        rec["scenes"].append({"who": who, "request": text, "why": expect.get("why"), "reply": reply, "turns_seen": len(new),
                              "runtime_s": round(time.time() - t0, 2), "gateway_latency_s": ev.get("latency_s"),
                              "grounding": ev.get("grounding"), **res})
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(f"[live] {who}: {'PASS' if res['passed'] else 'FAIL'} {({k: v for k, v in res['ok'].items() if not v})} · {reply[:90]!r}",
              flush=True)
    rec["passed"] = sum(s["passed"] for s in rec["scenes"])
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print(f"[live] {rec['passed']}/{len(SCENES)} scenes as expected through {rec['runtime']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
