"""Distil the teacher into an adapter, withdraw the teacher, measure what falls.

THE WITHDRAWAL GAP IS THE PROJECT. `ARCHITECTURE.md`: "the verified task score
after withdrawal, minus the score it had while the frontier was there. Making
that gap small IS the project." Until now it could not be measured, because on
the clinical suite no frontier was ever ahead. Here the teacher scores 40/40 and
the small model 1/40, so there is something to fall from.

FOUR ARMS, AND EACH ANSWERS ONE THING.

  base            what the student can do alone. The floor.
  teacher         what the frontier does. The ceiling, and the thing withdrawn.
  adapter         the student after distillation, on the SAME families.
  adapter · held  the same adapter on `drag_force` and `orifice_discharge`,
                  which appear nowhere in the corpus. This is the probe that
                  separates "learned to carry a chain" from "learned six
                  templates", and a gain reported without it is not a result.

THE ORACLE GRADES EVERY ARM. Same closed-form answers, same 2 % tolerance, same
parser. A teacher and a student scored by different code are not comparable.

    python3 -m training.physics.train_expert --base Qwen/Qwen2.5-3B-Instruct
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from training.physics.generate import HELD_OUT_FAMILIES, TRAIN_FAMILIES, generate
from training.physics.headroom import SYSTEM, correct, parse_answer

RESULTS = Path("physics_results.json")


def load_corpus(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def score(gen_fn, rows: list[dict], rtol: float, label: str) -> dict:
    passed, unparsed, recs = 0, 0, []
    for i, row in enumerate(rows, 1):
        text = gen_fn(SYSTEM, row["prompt"])
        got = parse_answer(text)
        ok = correct(got, row["answer"], rtol)
        passed += ok
        unparsed += got is None
        recs.append({"case_id": row["case_id"], "family": row["family"],
                     "want": row["answer"], "got": got, "passed": bool(ok),
                     "raw": text[:400]})
        if i % 10 == 0:
            print(f"  [{label}] {i}/{len(rows)} passed {passed}", flush=True)
    return {"label": label, "n": len(rows), "passed": passed,
            "accuracy": round(passed / len(rows), 4), "unparsed": unparsed,
            "records": recs}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--corpus", default="training/physics/data/train.jsonl")
    ap.add_argument("--n-eval", type=int, default=40)
    ap.add_argument("--n-held", type=int, default=20)
    ap.add_argument("--eval-seed", type=int, default=515151)
    ap.add_argument("--rtol", type=float, default=0.02)
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-seq", type=int, default=1536)
    ap.add_argument("--max-new-tokens", type=int, default=900)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--targets",
                    default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    ap.add_argument("--four-bit", dest="four_bit", action="store_true")
    args = ap.parse_args()

    # Imported here so the module can be read without a GPU stack present.
    from training.s4_train import free, load_base, make_generate, train_adapter

    # The eval seed differs from the corpus seed, so no evaluated case was
    # generated for training. Same families, different draws.
    ev = generate(args.n_eval, args.eval_seed, TRAIN_FAMILIES, style="working")
    held = generate(args.n_held, args.eval_seed + 7, HELD_OUT_FAMILIES, style="working")
    corpus = load_corpus(args.corpus)
    print(f"[corpus] {len(corpus)} verified examples | eval {len(ev)} | "
          f"held-out families {len(held)}", flush=True)

    summary = {"base": args.base, "corpus_n": len(corpus),
               "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "rtol": args.rtol, "arms": {}}

    def save():
        RESULTS.write_text(json.dumps(summary, indent=2))

    model, tok = load_base(args.base, args.four_bit)
    gen = make_generate(model, tok, args.max_new_tokens)
    summary["arms"]["base"] = score(gen, ev, args.rtol, "base")
    save()
    summary["arms"]["base · held-out families"] = score(
        gen, held, args.rtol, "base · held")
    save()
    gen = model = tok = None
    free()

    expert, tok = train_adapter(args.base, corpus, "adapters/physics", args)
    gen = make_generate(expert, tok, args.max_new_tokens)
    summary["arms"]["adapter"] = score(gen, ev, args.rtol, "adapter")
    save()
    summary["arms"]["adapter · held-out families"] = score(
        gen, held, args.rtol, "adapter · held")
    save()

    b = summary["arms"]["base"]["accuracy"]
    a = summary["arms"]["adapter"]["accuracy"]
    bh = summary["arms"]["base · held-out families"]["accuracy"]
    ah = summary["arms"]["adapter · held-out families"]["accuracy"]
    summary["gain"] = round(a - b, 4)
    summary["gain_held_out"] = round(ah - bh, 4)
    summary["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    save()
    print(f"\n{'arm':<32}{'passed':>10}{'accuracy':>11}")
    for k, v in summary["arms"].items():
        print(f"{k:<32}{str(v['passed'])+'/'+str(v['n']):>10}{v['accuracy']:>11.3f}")
    print(f"\ngain on trained families {summary['gain']:+.3f}   "
          f"on held-out families {summary['gain_held_out']:+.3f}")
    print("The teacher scored 1.000 on this domain. The withdrawal gap is that "
          "minus the adapter's accuracy, and it is the number the project is for.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
