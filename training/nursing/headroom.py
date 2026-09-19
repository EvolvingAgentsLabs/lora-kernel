"""Milestone 5, headroom — a small base against a real procedure, closed book and open book.

RUNS ON COLAB, THROUGH THE CHAIN, SERVED BY vLLM. No model is run on the user's machine: a first
attempt went through a local Ollama build and was stopped and discarded at the user's instruction
(2026-09-19) — and a quantised local build is not the bf16 model vLLM serves, so its number would
not have been comparable with anything else here. Every answer is persisted as it lands and the run
resumes; brief and verdict table: results/M5-nursing-headroom-20260919/BRIEF.md.

THE MATHEMATICS (docs/FOUNDATIONS.md §9.2, §9.4). Headroom is the room under the ceiling on the
closed-book arm; the two arms answer the same questions, so they are paired — exact two-sided sign
test on discordant pairs, p = 2·Σ_{k≤min(b,c)} C(b+c,k)·2^-(b+c).
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from training.harness import bar
from training.harness.accept_rank import post, serve, stop, wait_ready
from training.nursing import questions as Q
from training.nursing.source import note

SYSTEM = "You are a nursing skills tutor. Answer exactly what is asked, as briefly as asked."
RATE_NOTE = ("IV rate formulas\n- Gravity: drops per minute = volume (mL) x drop factor (gtt/mL) / time (minutes).\n"
             "- Pump: mL per hour = volume (mL) x 60 / time (minutes).")


def context(q: dict) -> str:
    if q["kind"] == "site":
        return q["site_note"]
    return RATE_NOTE if q["kind"] == "rate" else note(q["checklist"])


def ask(model: str, user: str) -> dict:
    # THINKING OFF, AS FOR EVERY MEMBER ON THE 3.x LINE: left open, a bare base spends its tokens
    # thinking and the arm scores as a floor. A template without the switch ignores it.
    r = post("/v1/chat/completions", {
        "model": model, "temperature": 0, "max_tokens": 48,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]})
    c = r["choices"][0]
    return {"reply": (c["message"].get("content") or "")[:200], "truncated": c.get("finish_reason") == "length"}


def summarise(rec: dict) -> dict:
    summary = {}
    for arm, got in rec["arms"].items():
        for kind in ("order", "next", "rate", "site"):
            rows = [v for v in got.values() if v.get("kind") == kind and "error" not in v]
            summary.setdefault(arm, {})[kind] = {"n": len(rows), "correct": sum(v["correct"] for v in rows)}
        summary[arm]["errors"] = sum("error" in v for v in got.values())
        summary[arm]["truncated"] = sum(bool(v.get("truncated")) for v in got.values())
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="headroom.json")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(model=a.base, served_by="vllm", started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    rec.setdefault("arms", {})
    qs = Q.build()

    def save():
        out.write_text(json.dumps(rec, indent=1))

    save()
    p = serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90"])
    try:
        if not wait_ready(p):
            rec["stopped"] = "the base never came up"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); return 1
        # AN ARM PROVES IT CAN ANSWER BEFORE IT SCORES: one probe, checked for an error and for text.
        probe = ask(a.base, "Reply with the single letter A.")
        rec["probe"] = probe
        print(f"[arm] probe: {probe}", flush=True)
        save()
        for arm in ("closed", "open"):
            got = rec["arms"].setdefault(arm, {})
            todo = [q for q in qs if q["id"] not in got]

            def one(q, arm=arm):
                user = q["question"] if arm == "closed" else f"{context(q)}\n\n{q['question']}"
                try:
                    r = ask(a.base, user)
                    return q["id"], {"kind": q["kind"], **r, "correct": Q.check(q, r["reply"])}
                except Exception as e:                    # transport, never folded into a score
                    return q["id"], {"kind": q["kind"], "error": repr(e)[:160]}

            with ThreadPoolExecutor(a.concurrency) as ex:
                for i, (qid, row) in enumerate(ex.map(one, todo), 1):
                    got[qid] = row
                    if i % 12 == 0 or i == len(todo):
                        save()
                        ok = [v for v in got.values() if "error" not in v]
                        print(f"[arm] {arm} {len(got)}/{len(qs)} correct {sum(v['correct'] for v in ok)} "
                              f"errors {len(got) - len(ok)}", flush=True)
            save()
    finally:
        stop(p)

    rec["summary"] = summarise(rec)
    closed = {k: bool(v.get("correct")) for k, v in rec["arms"]["closed"].items() if "error" not in v}
    opened = {k: bool(v.get("correct")) for k, v in rec["arms"]["open"].items() if "error" not in v}
    rec["pair_open_vs_closed"] = bar.compare(opened, closed)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[arm] {json.dumps(rec['summary'])}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
