"""The gate S1 failed, asked again on a domain where capability can help.

WHAT IT DECIDES. Does a frontier model beat a small local model on multi-step
fluid mechanics by a margin a withdrawal gap could live in? On the clinical suite
the answer was no, and structurally so: its difficulty is unpublished rules that
only the training split reveals. Here everything is in the statement, and what
separates the models is whether they can carry a chain.

IF THE ANSWER IS NO AGAIN, nothing else gets built. That is the whole point of
asking before generating a corpus and training anything.

THE VERIFIER IS ARITHMETIC — the generated answer compared to the model's within
a stated relative tolerance. No judge, no rubric, no rater.

MODELS ARE ALLOWED TO THINK. The reasoning channel is read separately and never
scored; the budget is generous on purpose, because a chain the model was not
given room to carry is a measurement of the budget.

    python3 -m training.physics.headroom --small ollama:qwen3.5:4b \\
        --large openai:google/gemini-3.5-flash-lite --n 40
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path

from alpha.backends import BackendError, build
from training.physics.generate import HELD_OUT_FAMILIES, TRAIN_FAMILIES, generate

# THIS PROMPT TELLS THE MODEL NOT TO SHOW ITS WORKING, AND EVERY BASELINE IN
# P5-P8 WAS MEASURED UNDER IT while every treatment was trained to show working.
# An unmodified 3B scores 4/30 on the same suite under the neutral contract and
# 0/40 under this one [ran] `results/P9-shared-contract-20260909/`. It is kept so
# those runs stay reproducible, and `--contract shared` is how a comparison that
# means something is bought.
SYSTEM = ("You are a careful engineer. Work in SI units and show no working in "
          "the final message: reply with one JSON object only.")


def parse_answer(text: str) -> float | None:
    """`{"answer": <number>}`, or the last bare number as a fallback.

    The fallback is deliberate and it is generous to the model: a run that scored
    a correct number as wrong because of a brace would be measuring formatting,
    which is a different experiment.
    """
    m = re.search(r'"answer"\s*:\s*(-?\d+\.?\d*(?:[eE][-+]?\d+)?)', text)
    if m:
        return float(m.group(1))
    nums = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", text.replace(",", ""))
    return float(nums[-1]) if nums else None


def correct(got: float | None, want: float, rtol: float) -> bool:
    return got is not None and abs(got - want) <= rtol * abs(want)


def run_model(tag: str, rows: list[dict], rtol: float, max_tokens: int) -> dict:
    model = build(tag)
    per_family: dict[str, list[bool]] = defaultdict(list)
    records, passed, unparsed, thought = [], 0, 0, 0
    t0 = time.time()
    for i, row in enumerate(rows, 1):
        try:
            r = model.chat([{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": row["prompt"]}],
                           max_tokens=max_tokens)
            got = parse_answer(r.text)
            thought += len(r.thinking)
        except BackendError as e:
            got, r = None, None
            print(f"  [{tag}] {row['case_id']} backend error: {e}", flush=True)
        ok = correct(got, row["answer"], rtol)
        passed += ok
        unparsed += got is None
        per_family[row["family"]].append(ok)
        records.append({"case_id": row["case_id"], "family": row["family"],
                        "want": row["answer"], "got": got, "passed": bool(ok),
                        "raw": (r.text[:300] if r else "")})
        if i % 10 == 0:
            print(f"  [{tag}] {i}/{len(rows)} passed {passed}", flush=True)
    return {
        "model": tag, "n": len(rows), "passed": passed,
        "accuracy": round(passed / len(rows), 4), "unparsed": unparsed,
        "seconds": round(time.time() - t0, 1),
        "thinking_chars": thought,
        "by_family": {k: f"{sum(v)}/{len(v)}" for k, v in sorted(per_family.items())},
        "records": records,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--small", default="ollama:qwen3.5:4b")
    ap.add_argument("--large", default="openai:google/gemini-3.5-flash-lite")
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20260908)
    # 2%, not 1%. A frontier model answered a hydrostatic force within 2.0% —
    # correct physics, hand-rounded arithmetic — and a 1% window scored it wrong.
    # The tolerance has to absorb rounding or it measures decimal places.
    ap.add_argument("--rtol", type=float, default=0.02)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--style", default="json", choices=["json", "working"])
    ap.add_argument("--contract", default="legacy", choices=["legacy", "shared"],
                    help="shared uses training/protocol.py — the contract the "
                         "adapters were trained under, so the number is comparable")
    ap.add_argument("--held-out", action="store_true",
                    help="use the families kept out of training instead")
    ap.add_argument("--run-dir", default="results/P5-physics-headroom-20260908")
    args = ap.parse_args()

    fams = HELD_OUT_FAMILIES if args.held_out else TRAIN_FAMILIES
    style = args.style
    if args.contract == "shared":
        global SYSTEM
        from training.protocol import SYSTEM as SHARED
        SYSTEM = SHARED
        style = "working"
    rows = generate(args.n, args.seed, fams, style)
    out = Path(args.run_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = {"rtol": args.rtol, "n": len(rows), "style": style,
               "contract": args.contract,
               "families": sorted(fams),
               "seed": args.seed, "arms": {}}

    for tag in [t for t in (args.small, args.large) if t]:
        print(f"[headroom] {tag}", flush=True)
        summary["arms"][tag] = run_model(tag, rows, args.rtol, args.max_tokens)
        (out / "headroom.json").write_text(json.dumps(summary, indent=2))

    s, l = summary["arms"][args.small], summary["arms"][args.large]
    gap = l["accuracy"] - s["accuracy"]
    summary["gap"] = round(gap, 4)
    (out / "headroom.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{'model':<44}{'passed':>10}{'accuracy':>11}{'unparsed':>10}")
    for tag in [t for t in (args.small, args.large) if t]:
        a = summary["arms"][tag]
        print(f"{tag:<44}{str(a['passed'])+'/'+str(a['n']):>10}"
              f"{a['accuracy']:>11.3f}{a['unparsed']:>10}")
    print(f"\ngap (large - small): {gap:+.3f}")
    print("THE GATE: a withdrawal gap needs somewhere to fall from. On the "
          "clinical suite this gap was +0.05 and the project stalled there.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
