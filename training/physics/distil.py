"""Build the distillation corpus: the teacher solves, the oracle decides.

THIS IS PHASE A, MADE LITERAL. The architecture says you pay frontier prices and
collect a distillation signal along the way. Here the signal is not an acceptance
rate — it is the teacher's worked chain, kept only where an arithmetic oracle
confirms the answer.

WHAT MAKES THIS DIFFERENT FROM ORDINARY DISTILLATION. A teacher's output is
usually taken on trust. Here every case has a closed-form answer computed
independently, so a wrong chain is DROPPED rather than learned. The corpus cannot
teach the student a mistake the teacher made — which is the one advantage of
building a domain where the truth is calculable, and it would be careless not to
use it.

WHAT IS DELIBERATELY NOT IN THE CORPUS. The two held-out families. They are the
generalisation probe, and an adapter that has seen them proves nothing.

    python3 -m training.physics.distil --n 600 --teacher openai:google/gemini-3.8-flash
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from alpha.backends import BackendError, build
from training.physics.generate import TRAIN_FAMILIES, generate
from training.physics.headroom import SYSTEM, correct, parse_answer

OUT = Path("training/physics/data")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--teacher", default="openai:google/gemini-3.8-flash")
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=770208)
    ap.add_argument("--rtol", type=float, default=0.02)
    ap.add_argument("--max-tokens", type=int, default=4000)
    # Serial, the corpus took 8.2 s per case — eighty-two minutes for six hundred.
    # The teacher is an API and the bottleneck is waiting, so the work is spread
    # across threads. Results are collected in the generated order, so the corpus
    # is identical to the serial one for the same seed.
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    rows = generate(args.n, args.seed, TRAIN_FAMILIES, style="working")
    model = build(args.teacher)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    kept_path = out / "train.jsonl"

    kept, dropped, failed = [], 0, 0
    per_family: dict[str, list[bool]] = defaultdict(list)
    t0 = time.time()
    tok_in = tok_out = 0
    done = 0

    def solve(row):
        try:
            r = model.chat([{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": row["prompt"]}],
                           max_tokens=args.max_tokens)
        except BackendError as e:
            return row, None, str(e)
        return row, r, None

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for row, r, err in pool.map(solve, rows):
            done += 1
            if err:
                failed += 1
                print(f"  {row['case_id']} backend error: {err}", flush=True)
                continue
            tok_in += r.prompt_tokens
            tok_out += r.completion_tokens
            ok = correct(parse_answer(r.text), row["answer"], args.rtol)
            per_family[row["family"]].append(ok)
            if not ok:
                dropped += 1
                continue
            kept.append({
                "case_id": row["case_id"], "family": row["family"],
                "answer": row["answer"], "unit": row["unit"],
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": row["prompt"]},
                    {"role": "assistant", "content": r.text.strip()},
                ],
            })
            # Persisted as it lands: a run killed at case 400 keeps 400 of them.
            if done % 20 == 0 or done == len(rows):
                kept_path.write_text("\n".join(json.dumps(k) for k in kept) + "\n")
                print(f"  [{done}/{len(rows)}] kept {len(kept)} dropped {dropped} "
                      f"failed {failed}", flush=True)

    kept_path.write_text("\n".join(json.dumps(k) for k in kept) + "\n")
    summary = {
        "teacher": args.teacher, "generated": len(rows), "kept": len(kept),
        "dropped_wrong": dropped, "backend_failures": failed,
        "keep_rate": round(len(kept) / len(rows), 4) if rows else 0.0,
        "rtol": args.rtol, "seed": args.seed, "style": "working",
        "by_family": {k: f"{sum(v)}/{len(v)}" for k, v in sorted(per_family.items())},
        "tokens": {"in": tok_in, "out": tok_out},
        "usd_at_flash_pricing": round((tok_in * 0.75 + tok_out * 3.75) / 1e6, 4),
        "seconds": round(time.time() - t0, 1), "workers": args.workers,
    }
    (out / "corpus.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nEvery kept example was CONFIRMED BY THE ORACLE. A wrong chain is "
          "dropped, not learned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
