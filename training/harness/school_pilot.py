"""The first LoRA trained on `examples/school`'s generated corpus (results/M7-school-pilot-*).

WHY THIS ARM, NAMED BEFORE ANY NUMBER OF IT EXISTS. `examples/` was built to validate this
architecture against a reference organisation, code-only, "before any adapter"
(`examples/README.md`). Its biggest pure-code step — a corpus generator that drives the tool
layer and rolls back its own writes — is done (`examples/school/generate_corpus.py`). This is
the next, GPU-requiring step named in `docs/FRAMEWORK.md`'s gap table: does a member trained on
that corpus actually learn to reach for its own tool, the way `email-full`/`desk-commitment` did
on the email domain? One role, one tool, held-out students — the cheapest version of that
question, not all seven roles at once.

ONE UNKNOWN. What is measured is tool-call fidelity only — did the model write the right tag
with the right argument for a held-out student — not full corpus-mode serving with a live tool
result spliced back in and a continuation graded. That is a second, larger question
(`docs/RECORD.md`'s own lesson: "serve an expert the way its corpus taught it, and suspect the
path before the model") and is not conflated with this one. The grader never executes a tool: the
truth for each case is already known from the case's own `tool` and `entity_id` fields, so a
live tool call cannot leak into what "correct" means.

HEADROOM FIRST. The bare base is evaluated on the held-out set before any training exists,
recorded in the same file, so a base that already reaches for `agenda_read` correctly (the
system prompt states its name and argument) would make an adapter here undecidable. `A FRESH
BASE PER ADAPTER` — `training.s4_train.train_adapter` reloads the base rather than reusing the
one the headroom pass mutated (`../../CLAUDE.md`: "prepare_model_for_kbit_training mutates the
model it is given").

    python -m training.harness.school_pilot --out school_pilot.json
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

TAG = re.compile(r"<agenda_read>\s*(\d+)\s*</agenda_read>")


def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def truth_of(row: dict) -> tuple[str, int]:
    return row["tool"], row["entity_id"]


def parse_call(text: str) -> tuple[str, int] | None:
    m = TAG.search(text)
    return ("agenda_read", int(m.group(1))) if m else None


def evaluate(generate_fn, rows: list[dict], name: str = "") -> dict:
    """`generate_fn(system, user) -> str`. Greedy decoding is the caller's job — the same
    contract `training/evaluate.py`'s `evaluate` uses, so a base and an adapter here are graded
    by the same code the rest of this repository already holds to that rule with."""
    records = []
    correct = 0
    for i, row in enumerate(rows, 1):
        system, user = row["messages"][0]["content"], row["messages"][1]["content"]
        try:
            out = generate_fn(system, user)
            got = parse_call(out)
        except Exception as e:                    # a raise here is infrastructure, not a miss
            out, got = f"<generation failed: {type(e).__name__}: {e}>", None
        want = truth_of(row)
        ok = got == want
        correct += ok
        records.append({"case_id": row["case_id"], "passed": bool(ok),
                        "got": list(got) if got else None, "want": list(want),
                        "out": out[:160]})
        print(f"[school] {name} {i}/{len(rows)} {'ok' if ok else 'miss'}", flush=True)
    n = len(rows)
    return {"n": n, "correct": correct, "accuracy": round(correct / n, 4) if n else 0.0,
           "records": records}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--role", default="educador")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max-seq", type=int, default=768, dest="max_seq")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--targets",
                    default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
    ap.add_argument("--four-bit", dest="four_bit", action="store_true", default=True)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--out", default="school_pilot.json")
    a = ap.parse_args()

    from training.harness.bar import compare
    from training.s4_train import free, load_base, make_generate, train_adapter

    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    train_rows = load_jsonl(f"examples/school/data_corpus/{a.role}_train.jsonl")
    eval_rows = load_jsonl(f"examples/school/data_corpus/{a.role}_eval.jsonl")
    rec = {"base": a.base, "role": a.role, "train_n": len(train_rows), "eval_n": len(eval_rows),
          "lora": {"r": a.r, "alpha": a.alpha, "epochs": a.epochs, "lr": a.lr},
          "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out.write_text(json.dumps(rec, indent=1))
    print(f"[school] {a.role}: {len(train_rows)} train, {len(eval_rows)} eval", flush=True)

    # -- headroom, recorded before the treatment exists --------------------------------
    model, tok = load_base(a.base, a.four_bit)
    gen = make_generate(model, tok, 32)
    rec["base_eval"] = evaluate(gen, eval_rows, "base")
    out.write_text(json.dumps(rec, indent=1))
    print(f"[school] base {rec['base_eval']['correct']}/{rec['base_eval']['n']}", flush=True)
    model = tok = gen = None
    free()

    # -- the adapter, a fresh base -------------------------------------------------------
    expert, tok = train_adapter(a.base, train_rows, f"adapters/school-{a.role}", a)
    gen = make_generate(expert, tok, 32)
    rec["adapter_eval"] = evaluate(gen, eval_rows, "adapter")
    out.write_text(json.dumps(rec, indent=1))
    print(f"[school] adapter {rec['adapter_eval']['correct']}/{rec['adapter_eval']['n']}",
         flush=True)
    expert = tok = gen = None
    free()

    a_map = {r["case_id"]: r["passed"] for r in rec["base_eval"]["records"]}
    b_map = {r["case_id"]: r["passed"] for r in rec["adapter_eval"]["records"]}
    rec["paired"] = compare(a_map, b_map)

    passes = (rec["adapter_eval"]["accuracy"] >= 0.90
             and rec["adapter_eval"]["correct"] > rec["base_eval"]["correct"]
             and rec["paired"]["different"])
    rec["verdict"] = {
        "passes": passes,
        "reading": (f"PASSED: {rec['adapter_eval']['correct']}/{rec['adapter_eval']['n']} "
                   f"against the base's {rec['base_eval']['correct']}/{rec['base_eval']['n']}, "
                   f"{rec['paired']['reading']}" if passes else
                   f"NOT PASSED: adapter {rec['adapter_eval']['correct']}/{rec['adapter_eval']['n']} "
                   f"vs base {rec['base_eval']['correct']}/{rec['base_eval']['n']} — "
                   f"{rec['paired']['reading']}"),
    }
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.write_text(json.dumps(rec, indent=1))
    print(f"[school] {rec['verdict']['reading']}", flush=True)
    return 0 if passes else 1


if __name__ == "__main__":
    raise SystemExit(main())
