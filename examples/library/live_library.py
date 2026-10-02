r"""LIVE-library — REAL4's 52 questions through OpenClaw to the library endpoint (`examples.library.serve`), on the user's Mac.

Each question goes through `openclaw agent --local --session-id <fresh> -m`; the reply is what OpenClaw printed; the
grade is REAL4's, on the endpoint's own walk record (`--log`): the value and the citation, the citation checked against
the statements the walk opened (`training/wiki/grade.py`, strict). Pre-registered in the run's BRIEF.

    python -m examples.library.live_library --log results/LIVE-library-<date>/walks.jsonl --out results/LIVE-library-<date>/live.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

from examples.school.live_openclaw import OPENCLAW, reply_of

# THE HOLD IS NODE'S, AT EXIT [ran] 2026-10-02: every held `agent --local` had already logged its run ended
# (`stopReason=stop`) within 0.2 s of the reply, and `sample` found all three LIVE-library2 holds still inside
# process.exit() hours later — V8 joining its platform workers. Our endpoint's answer, delay and format play no part. The
# cause inside node is not fixed here (a V8 flag tried against it did not separate from chance on a stub, 0/12 vs 3/15);
# the driver stops waiting for an exit that may never come: once OpenClaw prints that its run ended, the reply is
# complete — the turn's whole process group is killed after a short grace, and on a timeout. The launcher re-spawns node
# with inherited stdio, so a held grandchild used to keep the pipe open and outlive the driver as an orphan.
DONE = re.compile(r"\] run \S+ ended with stopReason=")
GRACE_S = 2.0


def run_turn(argv: list[str], timeout: float, env: dict | None = None) -> tuple[str, bool]:
    """(stdout, timed_out). The turn runs in its own process group; it ends when the process exits, or GRACE_S after
    the run-ended line, or at `timeout` — the last two kill the group whole, so nothing outlives the row."""
    import threading
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, start_new_session=True,
                         env={**os.environ, "OPENCLAW_NO_RESPAWN": "1", **(env or {})})
    lines, done_at = [], []

    def read():
        for line in p.stdout:
            lines.append(line)
            if not done_at and DONE.search(line):
                done_at.append(time.time())
    t = threading.Thread(target=read, daemon=True)
    t.start()
    t0, timed_out = time.time(), False
    while p.poll() is None:
        if done_at and time.time() - done_at[0] >= GRACE_S:
            break
        if time.time() - t0 >= timeout:
            timed_out = True
            break
        time.sleep(0.1)
    if p.poll() is None:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    t.join(timeout=2)
    return "".join(lines), timed_out


def grade_walk(lib, row: dict, ev: dict) -> dict:
    """REAL4's grade on the endpoint's record: the ids it showed, the statements it opened, the statement's text."""
    from memory.runtime import Conversation
    from training.wiki import grade as gr
    conv = SimpleNamespace(shown=ev["shown"], statements={tuple(s) for s in ev["statements"]}, lib=lib,
                           _statement_text=Conversation(lib)._statement_text)
    return gr.grade(row, ev["final"], conv)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rows", default="results/REAL4-refusal-20260930/questions.jsonl")
    ap.add_argument("--library", default="knowledge/logistics-regs")
    ap.add_argument("--log", required=True, help="the endpoint's --log")
    ap.add_argument("--patch", default=str(Path.home() / ".config/lora-kernel/openclaw/library-reader.json5"))
    ap.add_argument("--openclaw", default=str(OPENCLAW))
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--out", required=True)
    ap.add_argument("--resume", action="store_true", help="keep the rows already in --out and run the rest")
    a = ap.parse_args()
    from memory.notes import Library
    lib = Library.load(a.library)
    rows = [json.loads(l) for l in Path(a.rows).read_text().splitlines() if l.strip()]
    subprocess.run([a.openclaw, "--profile", "library-reader", "config", "patch", "--file", a.patch], capture_output=True, text=True, check=True)
    log, out = Path(a.log), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rec = {"runtime": subprocess.run([a.openclaw, "--version"], capture_output=True, text=True).stdout.strip(),
           "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": []}
    if a.resume and out.exists():
        rec = json.loads(out.read_text()); rec.setdefault("resumed", []).append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    done = {x["id"] for x in rec["rows"]}
    stamp = time.strftime("%H%M%S")
    for r in rows:
        if r["case_id"] in done:
            continue
        seen = len(log.read_text().splitlines()) if log.exists() else 0
        t0 = time.time()
        # OpenClaw can hold a turn after the endpoint has answered [ran] LIVE-library2, row 32: the walk landed in 25 s and
        # the agent sat 600 s — node held in its own exit (see DONE); the row is graded on the walk, as every
        # row is, and flagged — the driver does not stop
        stdout, timed_out = run_turn([a.openclaw, "--profile", "library-reader", "agent", "--local",
                                      "--session-id", f"lib-{r['case_id']}-{stamp}", "-m", r["question"]], a.timeout)
        p = SimpleNamespace(stdout=stdout)
        new = [json.loads(l) for l in log.read_text().splitlines()[seen:]] if log.exists() else []
        ev = next((e for e in reversed(new) if e["question"].strip() == r["question"].strip()), new[-1] if new else None)
        g = grade_walk(lib, r, ev) if ev else {"state": "no-walk"}
        rec["rows"].append({"id": r["case_id"], "hops": r["hops"], "kind": r["check"]["kind"], "state": g["state"],
                            "right": g["state"] == "right", "reply": reply_of(p.stdout)[:300], "walks_seen": len(new),
                            "runtime_s": round(time.time() - t0, 2), "endpoint_latency_s": ev and ev.get("latency_s"),
                            "openclaw_timeout": timed_out})
        out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print(f"[live] {r['case_id']}: {g['state']} · {reply_of(p.stdout)[:80]!r}", flush=True)
    R = rec["rows"]
    rec.update(right=sum(x["right"] for x in R), n=len(R),
               headline=f"{sum(x['right'] for x in R if x['hops'] >= 2)}/{sum(x['hops'] >= 2 for x in R)}",
               refusals=f"{sum(x['right'] for x in R if x['kind'] == 'none')}/{sum(x['kind'] == 'none' for x in R)}",
               finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print(f"[live] {rec['right']}/{rec['n']} right · headline {rec['headline']} · refusals {rec['refusals']} through {rec['runtime']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
