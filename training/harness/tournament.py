"""S7 — does a grade the loop cannot influence pick the better variant?

P17 gave the tournament a judge, and the useful half of that result was that
**judging is easier than solving**: the same peer model solves this material at
0.467 and judges it at 0.82 [ran]. So `w₁` can come from something that could not
have done the work, which is the only way a tournament survives the frontier being
withdrawn.

It did not give the tournament **selection**. A judge right 82% of the time can
still rank two variants the wrong way round if its mistakes lean one way, and
ordering — not per-item accuracy — is what the fitness function actually needs.

    fitness = w1 * (fraction the judge calls correct) - w3 * (tokens, normalised)

`w₂·α` is dropped: it needs a frontier, and the point of S7 is the phase after the
frontier is gone.

THE CANDIDATES ARE NOT BRED BY A LOOP, AND THAT IS THE LIMIT OF THIS RUN. They are
the arms of P13, P14 and P15 — configurations that already exist, each with outputs
on disk and a true accuracy known from the oracle. Enough to ask whether selection
works; not enough to call it evolution.

    python3 -m training.harness.tournament
"""

from __future__ import annotations

import argparse
import json
import re
from itertools import combinations
from pathlib import Path

SOURCES = [
    ("results/P13-sequential-20260910/sequential_results.json", "P13 in-region"),
    ("results/P14-held-out-20260910/sequential_results_heldout.json", "P14 held-out"),
    ("results/P15-multitool-20260910/multitool_results.json", "P15 multi-tool"),
]
VERDICTS = Path("results/P19-tournament-20260911/verdicts.json")


def candidates() -> list[dict]:
    """Every arm with outputs on disk, grouped by the eval set it was scored on."""
    out = []
    for path, pool in SOURCES:
        p = Path(path)
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        for arm, v in d["arms"].items():
            recs = [r for r in v.get("records", []) if r.get("raw")]
            if len(recs) < 10:
                continue
            out.append({"pool": pool, "name": arm.split("·")[0].strip(),
                        "true_accuracy": sum(r["passed"] for r in recs) / len(recs),
                        "tokens": sum(len(r["raw"]) for r in recs) / len(recs),
                        "records": recs})
    return out


def judge_all(cands, tag: str, cache: dict) -> dict:
    """The peer judge over every candidate's outputs, cached between runs."""
    from training.harness.judges import PROMPT, SYSTEM, judge_model
    from training.physics.generate import (HELD_OUT_FAMILIES, TRAIN_FAMILIES,
                                           generate)
    from training.physics.multitool import FAMILIES as MT_FAMILIES
    from training.physics.multitool import generate as mt_generate

    problems: dict[str, str] = {}
    for c in cands:
        if c["pool"].startswith("P15"):
            rows = mt_generate(30, 616161, MT_FAMILIES)
        else:
            fams = HELD_OUT_FAMILIES if "held-out" in c["pool"] else TRAIN_FAMILIES
            rows = generate(30, 515151, fams, style="working")
        problems.update({r["case_id"]: r["prompt"].split("\n\n")[0] for r in rows})

    for c in cands:
        key = f"{c['pool']}::{c['name']}"
        todo = [r for r in c["records"] if f"{key}::{r['case_id']}" not in cache]
        if todo:
            print(f"[judge] {key} — {len(todo)} to score", flush=True)
            rows = [{"problem": problems.get(r["case_id"], ""), "chain": r["raw"]}
                    for r in todo]
            for r, v in zip(todo, judge_model(tag, rows)):
                cache[f"{key}::{r['case_id']}"] = v
            VERDICTS.write_text(json.dumps(cache, indent=2))
        said = [cache.get(f"{key}::{r['case_id']}") for r in c["records"]]
        seen = [s for s in said if s is not None]
        c["judge_accuracy"] = sum(seen) / len(seen) if seen else 0.0
        c["judged"] = len(seen)
    return cache


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--judge", default="ollama:qwen3.5:4b")
    ap.add_argument("--w3", type=float, default=0.1,
                    help="the token penalty, reported with and without")
    args = ap.parse_args()

    cands = candidates()
    cache = json.loads(VERDICTS.read_text()) if VERDICTS.exists() else {}
    VERDICTS.parent.mkdir(parents=True, exist_ok=True)
    judge_all(cands, args.judge, cache)

    longest = max(c["tokens"] for c in cands) or 1.0
    for c in cands:
        c["fitness"] = c["judge_accuracy"]
        c["fitness_taxed"] = c["judge_accuracy"] - args.w3 * (c["tokens"] / longest)

    print(f"\n{'candidate':<46}{'true':>8}{'judge':>8}{'taxed':>8}{'judged':>8}")
    for c in sorted(cands, key=lambda c: (c["pool"], -c["true_accuracy"])):
        print(f"{c['pool'] + ' · ' + c['name']:<46}{c['true_accuracy']:>8.3f}"
              f"{c['fitness']:>8.3f}{c['fitness_taxed']:>8.3f}{c['judged']:>8}")

    # ONLY WITHIN A POOL. Two arms scored on different problems are not candidates
    # for the same tournament, and ranking them together would be comparing
    # difficulty rather than variants.
    print(f"\n{'pair':<60}{'oracle says':>14}{'judge says':>13}{'taxed':>9}")
    agree = taxed_agree = total = 0
    for a, b in combinations(cands, 2):
        if a["pool"] != b["pool"] or a["true_accuracy"] == b["true_accuracy"]:
            continue
        total += 1
        better = a if a["true_accuracy"] > b["true_accuracy"] else b
        pick = a if a["fitness"] > b["fitness"] else b
        pick_t = a if a["fitness_taxed"] > b["fitness_taxed"] else b
        agree += pick is better
        taxed_agree += pick_t is better
        print(f"{a['name'] + ' vs ' + b['name'] + '  [' + a['pool'] + ']':<60}"
              f"{better['name'][:13]:>14}{pick['name'][:12]:>13}"
              f"{('=' if pick_t is pick else pick_t['name'][:8]):>9}")

    if total:
        print(f"\nthe judge orders {agree}/{total} comparable pairs the way the "
              f"oracle does; with the token penalty, {taxed_agree}/{total}.")
    print("Selection is what a tournament needs — a judge accurate per item can "
          "still rank two variants the wrong way round. And these candidates were "
          "not bred by a loop, so this is a selection test and not evolution.")
    Path("results/P19-tournament-20260911/tournament.json").write_text(json.dumps(
        {"w3": args.w3, "pairs": total, "agree": agree, "agree_taxed": taxed_agree,
         "candidates": [{k: v for k, v in c.items() if k != "records"}
                        for c in cands]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
