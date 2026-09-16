"""P49 — does a larger model write better drafts than the bare base?

WHY THIS RUNS BEFORE THREE CORPORA ARE BUILT. The close-experts design selects
drafting experts by **acceptance against a larger target**. If the target is not
better than the base, acceptance against it ranks nothing and all three arms tie —
which is exactly how P42's third-party adapter scored **0.825** against a base
already at **0.815** **[ran]**. Checking the ceiling first is the cheapest run there
is, and this one trains nothing.

THE DELIBERATE SIMPLIFICATION, STATED RATHER THAN HIDDEN. Both models are handed the
thread **inline**; neither calls a tool. The product configuration reads the thread
through `thread_history`, and adding that here would put a second skill — operating
the protocol — inside a question about writing. **If the target is not better with
the facts handed to it, it is certainly not better having to fetch them**, so the
simplification can only make the gate easier to clear, which is the conservative
direction for a headroom check.

MEASURED WITHOUT A JUDGE. There is no rule that says a draft is good — that is the
whole reason the design reaches for acceptance. What is mechanical is whether the
draft carries the facts the reply depends on: the reference, the date, the amount.
`drafting.carries()` is that check. It is a **floor, not a quality score**, and it
catches the failure acceptance alone cannot see — fluent nothing.

THE ARMS RUN ONE AT A TIME, on one card, because a 19.3 GB AWQ target and a 3B base
resident together would need memory tuning to answer a question that does not need
them simultaneous.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from training.email.drafting import carries, generate

OUT = Path("draft_headroom.json")

#: Pre-registered in `results/P49-draft-headroom-20260916/BRIEF.md` before the run.
#: A margin below this on the fact-carrying floor means the target is not enough
#: better for acceptance against it to rank anything.
MIN_MARGIN = 0.10


def _wait(url: str, minutes: int, proc=None) -> bool:
    for _ in range(minutes * 12):
        if proc is not None and proc.poll() is not None:
            return False
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except Exception:
            time.sleep(5)
    return False


def thread_inline(inbox: dict, case: dict) -> str:
    """The thread as text, so neither arm needs a tool to see it."""
    lines = []
    for m in inbox["threads"][case["thread_id"]]:
        who = "me" if m["from"] == inbox["me"] else case["from_name"]
        lines.append(f"{who}: {m['preview']}")
    return "\n".join(lines)


def draft_one(base_url: str, model: str, inbox: dict, case: dict,
              max_tokens: int, timeout: int = 240) -> dict:
    prompt = (f"{case['prompt']}\n\nThe thread so far:\n"
              f"{thread_inline(inbox, case)}\n\nWrite the reply.")
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions", body,
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = json.load(r)["choices"][0]["message"]["content"] or ""
    except Exception as e:
        return {"id": case["case_id"], "topic": case["topic"], "error": repr(e)[:160],
                "found": 0, "needed": len(case["must_carry"]), "complete": False}
    c = carries(text, case["must_carry"])
    return {"id": case["case_id"], "topic": case["topic"], "draft": text[:600], **c}


def summarise(records: list[dict]) -> dict:
    n = len(records)
    if not n:
        return {"n": 0}
    found = sum(r["found"] for r in records)
    needed = sum(r["needed"] for r in records)
    by_topic: dict[str, dict] = {}
    for r in records:
        row = by_topic.setdefault(r["topic"], {"n": 0, "complete": 0})
        row["n"] += 1
        row["complete"] += bool(r["complete"])
    for row in by_topic.values():
        row["rate"] = round(row["complete"] / row["n"], 4)
    return {
        "n": n,
        # THE HEADLINE IS PER-DRAFT, NOT PER-FACT. A model that names two of three
        # facts has still written a reply somebody has to fix.
        "complete": sum(r["complete"] for r in records),
        "complete_rate": round(sum(r["complete"] for r in records) / n, 4),
        # And the per-fact rate beside it, because a floor that moves from 0.1 to
        # 0.9 facts while completeness stays at 0 is a different situation.
        "facts_found": found, "facts_needed": needed,
        "fact_rate": round(found / needed, 4) if needed else 0.0,
        "errors": sum("error" in r for r in records),
        "by_topic": dict(sorted(by_topic.items())),
    }


def verdict(target: dict, base: dict) -> dict:
    if not target.get("n") or not base.get("n"):
        return {"readable": False, "why": "an arm produced nothing"}
    # ROUNDED BEFORE IT IS COMPARED. `0.50 - 0.40` is 0.09999999999999998, so a
    # result exactly at the pre-registered threshold fell on the wrong side of it —
    # a gate decided by float noise rather than by the number that was written down
    # **[ran]** 2026-09-16, caught by the boundary test.
    margin = round(target["complete_rate"] - base["complete_rate"], 4)
    return {
        "readable": True,
        "target_complete_rate": target["complete_rate"],
        "base_complete_rate": base["complete_rate"],
        "margin": margin,
        "min_margin": MIN_MARGIN,
        "bought": margin >= MIN_MARGIN,
        "reading": (
            f"BOUGHT: the target carries the facts {margin:.3f} more often, so "
            "acceptance against it has something to rank"
            if margin >= MIN_MARGIN else
            "UNBOUGHT: the target is not enough better than the base — acceptance "
            "against it would rank nothing and all three experts would tie"),
    }


def serve(model: str, port: int, extra: list[str]) -> subprocess.Popen:
    cmd = ["vllm", "serve", model, "--port", str(port), *extra]
    print(f"[draft] {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, stdout=open(f"vllm-{port}.log", "w"),
                            stderr=subprocess.STDOUT)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--target", default="Qwen/Qwen2.5-32B-Instruct-AWQ")
    ap.add_argument("--n", type=int, default=90)
    ap.add_argument("--seed", type=int, default=606060)
    ap.add_argument("--max-tokens", type=int, default=300)
    ap.add_argument("--max-model-len", type=int, default=4096)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.out:
        globals()["OUT"] = Path(args.out)

    inbox = generate(args.n, args.seed)
    results = {"base": args.base, "target": args.target, "n": args.n,
               "seed": args.seed, "min_margin": MIN_MARGIN, "arms": {}}

    def save():
        OUT.write_text(json.dumps(results, indent=2))

    save()
    # THE TARGET FIRST. It is the arm that can make the second unnecessary: a target
    # that cannot carry the facts itself ends the design without the base being run.
    for arm, model in (("target", args.target), ("base", args.base)):
        extra = ["--max-model-len", str(args.max_model_len),
                 "--gpu-memory-utilization", "0.90"]
        p = serve(model, 8000, extra)
        try:
            if not _wait("http://127.0.0.1:8000/health", 25, p):
                results["arms"][arm] = {"status": "never came up"}
                save()
                return 1
            print(f"[draft] {arm} up", flush=True)
            recs = []
            for i, case in enumerate(inbox["cases"], 1):
                recs.append(draft_one("http://127.0.0.1:8000/v1", model, inbox,
                                      case, args.max_tokens))
                # Persisted as it lands. P47 was lost twice for want of this.
                if i % 10 == 0 or i == args.n:
                    results["arms"][arm] = {**summarise(recs), "records": recs,
                                            "partial": i < args.n}
                    save()
                    s = summarise(recs)
                    print(f"[draft] {arm} {i}/{args.n} complete {s['complete']} "
                          f"facts {s['fact_rate']:.3f}", flush=True)
            results["arms"][arm] = {**summarise(recs), "records": recs,
                                    "partial": False}
            save()
        finally:
            p.terminate()
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill()

    results["verdict"] = verdict(results["arms"].get("target", {}),
                                 results["arms"].get("base", {}))
    print(f"\n{'arm':8}{'complete':>10}{'facts':>9}")
    for arm in ("target", "base"):
        a = results["arms"].get(arm, {})
        print(f"{arm:8}{a.get('complete_rate', float('nan')):>10.3f}"
              f"{a.get('fact_rate', float('nan')):>9.3f}")
    print("\n" + results["verdict"]["reading"], flush=True)
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
