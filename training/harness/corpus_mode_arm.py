"""Milestone 7, arm 0b — the fluids expert, served for once the way its corpus taught.

THE QUESTION (one unknown: the serving path). `fluids-full` scored 11 of 90 through
`tool_calls` / `role: "tool"` **[ran]** P41, and read where it happens 74 of its 79 failures
hold a number that came from nowhere and 75 leave a tool result unused
(`training/physics/result_use.py`). Its corpus taught the result *inline* —
`<calc>…</calc>= 4.2305` — and that other path costs `email-full` 0.992 → 0.808 **[ran]** P55.
Same adapter (sha 825abeb8…), same 90 cases, corpus mode. Is the expert that "cannot reason"
an expert that was never shown its results the way it was taught to read them?

WHY IT IS BOUGHT BEFORE ANY KNOWLEDGE BASE. A base of knowledge delivers what it retrieves
into the same channel. If a 3B does not use an inline result either, reading is the wall and
milestone 7's arm 1 is predicted to fail; if it does, the wall was the harness, the region
measured to fail may not be one, and a knowledge base has a channel that works.

THE MATHEMATICS (docs/FOUNDATIONS.md §9.2): paired by case id against the recorded run, exact
two-sided sign test on discordant pairs, p = 2·Σ_{k≤min(b,c)} C(b+c,k)·2^-(b+c). And beside the
score, the failure measured where it happens: results used, results ignored, numbers from nowhere.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from training.harness import suites
from training.harness.accept_rank import draft_arm, serve, stop, summarise, wait_ready
from training.harness.release_gate import pair
from training.harness.verify_substrate import identity
from training.physics import result_use, tools


def reading(records: list[dict], cases: dict) -> dict:
    """The arm-0 instrument over this arm's own chains."""
    s = {"failed": 0, "failed_with_a_result_never_used": 0, "failed_with_a_number_from_nowhere": 0,
         "results_used": 0, "results_ignored": 0, "tool_errors_while_replaying": 0}
    for r in records:
        if r.get("correct") or "error" in r:
            continue
        c = cases[r["id"]]
        got = result_use.read_chain(r.get("text", ""), c.user.split("Solve the problem")[0], c.ctx, tools.answer)
        s["failed"] += 1
        s["failed_with_a_result_never_used"] += got["ignored"] > 0
        s["failed_with_a_number_from_nowhere"] += got["invented_steps"] > 0
        s["results_used"] += got["used"]; s["results_ignored"] += got["ignored"]
        s["tool_errors_while_replaying"] += got["tool_errors"]
    return s


def verdict(rec: dict) -> dict:
    applied = bool(rec.get("G1", {}).get("applied"))
    pr = (rec.get("pairs") or [{}])[0]
    state, new, old = pr.get("state"), pr.get("a_total"), pr.get("b_total")
    out = {"G1": applied, "state": state, "corpus_mode": new, "tool_calls": old}
    if not applied:
        out["reading"] = "VOID: the adapter is not applied — nothing here is about the expert"
    elif state == "improvement":
        out["reading"] = (f"THE PATH WAS PART OF IT: {new} in corpus mode against {old} through tool_calls, "
                          "paired. Read `reading` for how much of the unused-result failure went with it")
    elif state == "tie":
        out["reading"] = (f"THE PATH WAS NOT IT: {new} against {old}, a tie. The expert does not use an inline "
                          "result either — reading is the wall a knowledge base will meet")
    else:
        out["reading"] = f"corpus mode is WORSE: {new} against {old} — read the chains before anything else"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--member", default="fluids-full")
    ap.add_argument("--path", default="adapters/fluids-full")
    ap.add_argument("--recorded", default="results/P41-routing-20260915/pool_results.json")
    ap.add_argument("--max-tokens", type=int, default=200)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default="corpus_mode.json")
    a = ap.parse_args()
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    rec = json.loads(out.read_text()) if out.exists() else {}
    rec.update(base=a.base, member=a.member, started=rec.get("started") or time.strftime("%Y-%m-%dT%H:%M:%S"))
    rec.setdefault("arms", {})

    def save():
        out.write_text(json.dumps(rec, indent=1))

    save()
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(a.base)
    suite = suites.load("fluids")
    cases = suite.cases(suite.eval_n, suite.eval_seed)
    old = json.loads(Path(a.recorded).read_text())["arms"][a.member]["records"]
    old = old if isinstance(old, list) else list(old.values())
    # THE RECORDED ARM, UNDER THIS RUN'S RULE. P41 stored `passed`; the pair needs `correct`, and
    # it is recomputed from the stored answer with the same tolerance this suite verifies with,
    # so the two arms are scored by one rule — and the recomputation has to reproduce P41's total.
    by_id = {c.id: c for c in cases}
    recorded = [{"id": r["id"], "correct": bool(by_id[r["id"]].verify(r.get("got")))} for r in old]
    rec["recorded"] = {"path": a.recorded, "n": len(recorded), "correct": sum(r["correct"] for r in recorded),
                       "as_stored": sum(bool(r.get("passed")) for r in old)}
    print(f"[arm] recorded {rec['recorded']['correct']}/{len(recorded)} under this rule "
          f"(stored: {rec['recorded']['as_stored']})", flush=True)
    save()

    p = serve(a.base, ["--max-model-len", "8192", "--gpu-memory-utilization", "0.90", "--enable-lora",
                       "--max-lora-rank", "16", "--lora-modules", f"{a.member}={a.path}"])
    try:
        if not wait_ready(p):
            rec["stopped"] = "the base never came up"; rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S"); save(); return 1
        rec["G1"] = identity(a.base, a.member, tok)
        print(f"[arm] G1 {a.member}: {'applied' if rec['G1']['applied'] else 'NOT APPLIED'}", flush=True)
        save()
        if rec["G1"]["applied"]:
            arm = rec["arms"].setdefault(a.member, {"model": a.member, "records": {}})
            recs = draft_arm(a.member, tok, suite, cases, a.max_tokens, a.concurrency, arm["records"], save)
            arm.update(summarise(recs))
            print(f"[arm] {a.member} corpus mode: {arm['correct']}/{arm['n']} errors {arm['errors']} "
                  f"calls {arm.get('calls')} refused {arm.get('refused')}", flush=True)
            rec["reading"] = reading(recs, by_id)
            rec["pairs"] = [pair(recs, recorded, "corpus mode vs tool_calls")]
            save()
    finally:
        stop(p)
    rec["verdict"] = verdict(rec)
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"[arm] {rec['verdict']['reading']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
