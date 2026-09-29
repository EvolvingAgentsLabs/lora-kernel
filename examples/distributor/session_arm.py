r"""MT0 — the multi-turn baseline: the distributor's member over two- and three-turn sessions, served the way the gateway
serves it today (the last request only) and with the conversation's history in the prompt. Pre-registered in
results/MT0-multiturn-baseline-20260929/BRIEF.md; the suite is examples/distributor/generate_sessions.py.

    python -m examples.distributor.session_arm --arms last,history --out mt0.json      # one L4 session

Per arm: a turn is right iff the gateway's calls for it include the call the turn needs (tool and arguments,
`generate_sessions.turn_right`). Reported apart: the FIRST turns (self-contained, the member's ordinary job), the
DEPENDENT turns (the argument comes from an earlier turn) and the independent control; and the prompt tokens the model
read per turn, by the turn's position — the cost a longer conversation adds, $\bar p_i$ for turn $i$.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

BASE = "google/gemma-4-E4B-it"
MEMBER, ADAPTER = "out-s0", "adapters/distributor-staff-out-s0"
DATA = Path("examples/distributor/data_sessions")
ARMS = ("last", "history")


def summarise(records: list[dict]) -> dict:
    """Right counts by turn class, and mean prompt tokens by turn position."""
    turns = [(i, t) for s in records for i, t in enumerate(s["turns"]) if "error" not in t]
    first = [t for i, t in turns if i == 0]
    dep = [t for i, t in turns if i > 0 and t["depends"]]
    ind = [t for i, t in turns if i > 0 and not t["depends"]]
    by_pos: dict[int, list[int]] = {}
    for i, t in turns:
        by_pos.setdefault(i + 1, []).append(t["prompt_tokens"])
    frac = lambda xs: f"{sum(x['right'] for x in xs)}/{len(xs)}"
    return {"first": frac(first), "dependent": frac(dep), "independent": frac(ind),
            "errors": sum("error" in t for s in records for t in s["turns"]),
            "prompt_tokens_by_turn": {p: round(sum(v) / len(v)) for p, v in sorted(by_pos.items())}}


def reading(rec: dict) -> dict:
    """Written first (BRIEF). VOID if an arm's first turns are under 90 % right (the member is broken by the rendering,
    not by the conversation). Else the headline is the history arm's dependent turns: under 80 % is HEADROOM for the
    workflow harness on accuracy; at or over it the harness's case rests on context cost, reported beside."""
    s = rec.get("summary", {})
    if not {"last", "history"} <= s.keys():
        return {"reading": "NOTHING SCORED"}
    num = lambda x: tuple(int(v) for v in x.split("/"))
    for arm in ("last", "history"):
        r, n = num(s[arm]["first"])
        if n and r < 0.9 * n:
            return {"reading": f"VOID: the {arm} arm gets {r}/{n} first turns — the rendering, not the conversation"}
    r, n = num(s["history"]["dependent"])
    rl, _ = num(s["last"]["dependent"])
    head = "HEADROOM" if r < 0.8 * n else "NO ACCURACY HEADROOM"
    return {"reading": f"{head}: dependent turns {rl}/{n} with the last request only, {r}/{n} with history",
            "tokens": {a: s[a]["prompt_tokens_by_turn"] for a in ("last", "history")}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--out", default="mt0.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.setdefault("arms", {})
    save = lambda: out.write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    sessions = [json.loads(l) for l in (DATA / "eval.jsonl").read_text().splitlines() if l.strip()]
    from transformers import AutoTokenizer
    from examples.distributor import generate_sessions as gs
    from examples.distributor import staff_arm
    from examples.school.gateway import vllm_generator
    from training.harness import accept_rank as ar
    from training.harness.verify_substrate import identity
    tok = AutoTokenizer.from_pretrained(a.base)
    srv = ar.serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", "--enable-lora",
                            "--max-lora-rank", "16", "--max-loras", "1", "--lora-modules", f"{MEMBER}={ADAPTER}"])
    try:
        if not ar.wait_ready(srv, minutes=20):
            rec["stopped"] = "the server never came up"; save(); return 1
        rec["G1"] = staff_arm.g1(a.base, MEMBER, tok, identity)
        print(f"[session] G1 {MEMBER}: {'applied' if rec['G1']['applied'] else 'NOT APPLIED'}", flush=True)
        save()
        if not rec["G1"]["applied"]:
            rec["stopped"] = "G1: the member is not applied"; save(); return 1
        gen = vllm_generator(MEMBER, tok)
        for arm in [x for x in a.arms.split(",") if x]:
            slot = rec["arms"].setdefault(arm, {})
            for i, s in enumerate(sessions, 1):
                if s["session_id"] in slot:
                    continue
                slot[s["session_id"]] = {"kind": s["kind"], "turns": gs.play(s, gen, history=(arm == "history"))}
                if i % 10 == 0 or i == len(sessions):
                    save()
                    sm = summarise(list(slot.values()))
                    print(f"[session] {arm} {i}/{len(sessions)} · first {sm['first']} · dependent {sm['dependent']} · "
                          f"independent {sm['independent']} · tokens {sm['prompt_tokens_by_turn']}", flush=True)
    finally:
        ar.stop(srv)
    rec["summary"] = {arm: summarise(list(v.values())) for arm, v in rec["arms"].items()}
    rec["reading"] = reading(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[session] {rec['reading']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
