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
# H1 (docs/review/harness-workflow-kv.md §5): the harness member, served with the operational memory and its workflow
HARNESS, HARNESS_ADAPTER = "wf-s0", "adapters/distributor-staff-wf-s0"
ARM_SPEC = {"last": (MEMBER, {}), "history": (MEMBER, {"history": True}),
            "harness": (HARNESS, {"harness": True}), "harness-noblock": (HARNESS, {"harness": True, "tool_block": False})}
MAX_LOST, FLAT = 3, 1.1


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


def h1_reading(rec: dict) -> dict:
    r"""H1, written first (the design's §5). Paired per dependent turn against `history`: $\ell$ = turns history gets
    right and the harness wrong, PASSED needs $\ell \le 3$; the harness's prompt tokens flat, $\bar p_3 \le 1.1\,\bar p_1$;
    first turns ≥ 90 % in every arm (else VOID); every dependent turn the harness gets right fetched its key (`get`).
    `harness-noblock` passes if it loses no more than 3 dependent turns to `harness`."""
    arms = rec.get("arms", {})
    if not {"history", "harness"} <= arms.keys():
        return {"reading": "NOTHING SCORED"}
    def dep(arm):
        return {(sid, i): t for sid, s in arms[arm].items() for i, t in enumerate(s["turns"]) if i > 0 and t.get("depends") and "error" not in t}
    def first(arm):
        ts = [s["turns"][0] for s in arms[arm].values() if s["turns"] and "error" not in s["turns"][0]]
        return sum(t["right"] for t in ts), len(ts)
    out = {}
    for arm in arms:
        r, n = first(arm)
        if n and r < 0.9 * n:
            return {"reading": f"VOID: {arm} gets {r}/{n} first turns"}
    H, B = dep("harness"), dep("history")
    ids = sorted(H.keys() & B.keys())
    lost = sum(B[i]["right"] and not H[i]["right"] for i in ids)
    gained = sum(H[i]["right"] and not B[i]["right"] for i in ids)
    fetched = sum(any(c["tool"] == "get" and "result" in c for c in H[i]["calls"]) for i in ids if H[i]["right"])
    toks = summarise(list(arms["harness"].values()))["prompt_tokens_by_turn"]
    flat = toks.get(3, toks.get("3")) is None or toks.get(3, toks.get("3")) <= FLAT * toks.get(1, toks.get("1"))
    out.update(harness_dependent=f"{sum(H[i]['right'] for i in ids)}/{len(ids)}", history_dependent=f"{sum(B[i]['right'] for i in ids)}/{len(ids)}",
               lost=lost, gained=gained, right_turns_that_fetched=f"{fetched}/{sum(H[i]['right'] for i in ids)}", tokens=toks, flat=flat)
    ok = lost <= MAX_LOST and flat and fetched == sum(H[i]["right"] for i in ids)
    out["reading"] = (f"PASSED: {lost} lost, {gained} gained against history, tokens flat" if ok else
                      f"FALSIFIED: {lost} lost, flat={flat}, fetched {out['right_turns_that_fetched']}")
    if "harness-noblock" in arms:
        N = dep("harness-noblock")
        nl = sum(H[i]["right"] and not N[i]["right"] for i in ids if i in N)
        out["noblock"] = {"lost_to_harness": nl, "reading": "PASSED" if nl <= MAX_LOST else "FALSIFIED",
                          "tokens": summarise(list(arms["harness-noblock"].values()))["prompt_tokens_by_turn"]}
    return out


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
    arms = [x for x in a.arms.split(",") if x]
    served = {MEMBER: ADAPTER, **({HARNESS: HARNESS_ADAPTER} if any(ARM_SPEC[x][0] == HARNESS for x in arms) else {})}
    srv = ar.serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", "--enable-lora",
                            "--max-lora-rank", "16", "--max-loras", str(len(served)),
                            "--lora-modules", *[f"{m}={d}" for m, d in served.items()]])
    try:
        if not ar.wait_ready(srv, minutes=20):
            rec["stopped"] = "the server never came up"; save(); return 1
        rec["G1s"] = {m: staff_arm.g1(a.base, m, tok, identity) for m in served}
        rec["G1"] = rec["G1s"][MEMBER]
        print(f"[session] G1 {({m: g['applied'] for m, g in rec['G1s'].items()})}", flush=True)
        save()
        if not all(g["applied"] for g in rec["G1s"].values()):
            rec["stopped"] = "G1: a member is not applied"; save(); return 1
        for arm in arms:
            member, kw = ARM_SPEC[arm]
            gen = vllm_generator(member, tok)
            slot = rec["arms"].setdefault(arm, {})
            for i, s in enumerate(sessions, 1):
                if s["session_id"] in slot:
                    continue
                slot[s["session_id"]] = {"kind": s["kind"], "turns": gs.play(s, gen, **kw)}
                if i % 10 == 0 or i == len(sessions):
                    save()
                    sm = summarise(list(slot.values()))
                    print(f"[session] {arm} {i}/{len(sessions)} · first {sm['first']} · dependent {sm['dependent']} · "
                          f"independent {sm['independent']} · tokens {sm['prompt_tokens_by_turn']}", flush=True)
    finally:
        ar.stop(srv)
    rec["summary"] = {arm: summarise(list(v.values())) for arm, v in rec["arms"].items()}
    rec["reading"] = reading(rec) if not any(x.startswith("harness") for x in rec["arms"]) else h1_reading(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[session] {rec['reading']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
