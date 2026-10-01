r"""LIVE-library — REAL4's 52 questions through OpenClaw to the library endpoint (`examples.library.serve`), on the user's Mac.

Each question goes through `openclaw agent --local --session-id <fresh> -m`; the reply is what OpenClaw printed; the
grade is REAL4's, on the endpoint's own walk record (`--log`): the value and the citation, the citation checked against
the statements the walk opened (`training/wiki/grade.py`, strict). Pre-registered in the run's BRIEF.

    python -m examples.library.live_library --log results/LIVE-library-<date>/walks.jsonl --out results/LIVE-library-<date>/live.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

from examples.school.live_openclaw import OPENCLAW, reply_of


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
    a = ap.parse_args()
    from memory.notes import Library
    lib = Library.load(a.library)
    rows = [json.loads(l) for l in Path(a.rows).read_text().splitlines() if l.strip()]
    subprocess.run([a.openclaw, "--profile", "library-reader", "config", "patch", "--file", a.patch], capture_output=True, text=True, check=True)
    log, out = Path(a.log), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rec = {"runtime": subprocess.run([a.openclaw, "--version"], capture_output=True, text=True).stdout.strip(),
           "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "rows": []}
    stamp = time.strftime("%H%M%S")
    for r in rows:
        seen = len(log.read_text().splitlines()) if log.exists() else 0
        t0 = time.time()
        p = subprocess.run([a.openclaw, "--profile", "library-reader", "agent", "--local", "--session-id", f"lib-{r['case_id']}-{stamp}",
                            "-m", r["question"]], capture_output=True, text=True, timeout=a.timeout)
        new = [json.loads(l) for l in log.read_text().splitlines()[seen:]] if log.exists() else []
        ev = next((e for e in reversed(new) if e["question"].strip() == r["question"].strip()), new[-1] if new else None)
        g = grade_walk(lib, r, ev) if ev else {"state": "no-walk"}
        rec["rows"].append({"id": r["case_id"], "hops": r["hops"], "kind": r["check"]["kind"], "state": g["state"],
                            "right": g["state"] == "right", "reply": reply_of(p.stdout)[:300], "walks_seen": len(new),
                            "runtime_s": round(time.time() - t0, 2), "endpoint_latency_s": ev and ev.get("latency_s")})
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
