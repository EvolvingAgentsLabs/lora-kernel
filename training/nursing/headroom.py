"""Milestone 5, headroom — a small base against a real procedure, closed book and open book.

Zero GPU: the model is local (Ollama). Every answer is persisted as it lands and the run resumes;
the brief and the verdict table are in results/M5-nursing-headroom-20260919/BRIEF.md.

THE MATHEMATICS (docs/FOUNDATIONS.md §9.2, §9.4). Headroom is the room under the ceiling on the
closed-book arm; the two arms answer the same questions, so they are paired — exact two-sided
sign test on discordant pairs, p = 2·Σ_{k≤min(b,c)} C(b+c,k)·2^-(b+c).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from alpha.backends import build
from training.harness import bar
from training.nursing import questions as Q
from training.nursing.source import note

SYSTEM = "You are a nursing skills tutor. Answer exactly what is asked, as briefly as asked."
RATE_NOTE = ("IV rate formulas\n- Gravity: drops per minute = volume (mL) x drop factor (gtt/mL) / time (minutes).\n"
             "- Pump: mL per hour = volume (mL) x 60 / time (minutes).")


def context(q: dict) -> str:
    if q["kind"] == "site":
        return q["site_note"]
    return RATE_NOTE if q["kind"] == "rate" else note(q["checklist"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", default="ollama:qwen3.5:4b")
    ap.add_argument("--out", default="results/M5-nursing-headroom-20260919/headroom.json")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {"model": a.model, "arms": {}}
    qs = Q.build()
    model = build(a.model)

    for arm in ("closed", "open"):
        got = rec["arms"].setdefault(arm, {})
        for i, q in enumerate(qs):
            if q["id"] in got:
                continue
            user = q["question"] if arm == "closed" else f"{context(q)}\n\n{q['question']}"
            try:
                r = model.chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}], 48)
                got[q["id"]] = {"kind": q["kind"], "reply": r.text[:200], "correct": Q.check(q, r.text),
                                "truncated": r.truncated, "thought": bool(r.thinking), "seconds": round(r.seconds, 1)}
            except Exception as e:                       # transport, never folded into a score
                got[q["id"]] = {"kind": q["kind"], "error": repr(e)[:160]}
            out.write_text(json.dumps(rec, indent=1))
            if (i + 1) % 12 == 0:
                done = [v for v in got.values() if "error" not in v]
                print(f"[m5] {arm} {i + 1}/{len(qs)} correct {sum(v['correct'] for v in done)} "
                      f"errors {len(got) - len(done)}", flush=True)

    summary = {}
    for arm, got in rec["arms"].items():
        for kind in ("order", "next", "rate", "site"):
            rows = [v for v in got.values() if v.get("kind") == kind and "error" not in v]
            summary.setdefault(arm, {})[kind] = {"n": len(rows), "correct": sum(v["correct"] for v in rows)}
        summary[arm]["errors"] = sum("error" in v for v in got.values())
        summary[arm]["truncated"] = sum(bool(v.get("truncated")) for v in got.values())
    rec["summary"] = summary
    closed = {k: bool(v.get("correct")) for k, v in rec["arms"]["closed"].items() if "error" not in v}
    opened = {k: bool(v.get("correct")) for k, v in rec["arms"]["open"].items() if "error" not in v}
    rec["pair_open_vs_closed"] = bar.compare(opened, closed)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.write_text(json.dumps(rec, indent=1))
    print(f"[m5] {json.dumps(summary)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
