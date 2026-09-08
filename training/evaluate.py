"""Grading, identical in Colab and here, with no dependency on either.

Two rules this file exists to enforce:

  * THE VERIFIER IS EXACT AND IT IS NOT THE MODEL'S OPINION OF ITSELF. An answer
    passes when the set of documents it names equals the set the case requires.
    Not a superset, not a judge's impression. Reporting a document that is
    already filed sends a patient away for nothing.
  * THE SAME CODE GRADES EVERY ARM. A base model and an adapter graded by
    different code are not comparable, and the difference between them is the
    only number this project is trying to produce.

It reads the JSONL that `build_dataset.py` writes, so a notebook needs this file
and the data — not the whole repository, and never the sealed benchmark.

    from training.evaluate import load_jsonl, evaluate
    evaluate(generate_fn, load_jsonl("training/data/val.jsonl"))
"""

from __future__ import annotations

import json
from collections import defaultdict


def load_jsonl(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


try:  # one parser for every arm — a copy is a second thing to keep in step
    from alpha.cases import parse_answer
except ImportError:  # a notebook that has the data but not the package
    def parse_answer(text: str):
        start = text.find("{")
        if start < 0:
            return None
        depth, chunk = 0, ""
        for ch in text[start:]:
            chunk += ch
            depth += (ch == "{") - (ch == "}")
            if depth == 0:
                break
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            return None
        args = obj.get("arguments", obj)
        missing = args.get("missing")
        if not isinstance(missing, list):
            return None
        return {str(x) for x in missing}


def truth_of(row: dict) -> set[str]:
    return parse_answer(row["messages"][-1]["content"]) or set()


def evaluate(generate_fn, rows: list[dict], name: str = "") -> dict:
    """`generate_fn(system, user) -> str`. Greedy decoding is the caller's job."""
    per_clinic: dict[str, list[bool]] = defaultdict(list)
    passed = unparseable = 0
    records = []
    for i, row in enumerate(rows, 1):
        system = row["messages"][0]["content"]
        user = row["messages"][1]["content"]
        out = generate_fn(system, user)
        got, want = parse_answer(out), truth_of(row)
        ok = got is not None and got == want
        passed += ok
        unparseable += got is None
        per_clinic[row["clinic"]].append(ok)
        records.append({"case_id": row["case_id"], "clinic": row["clinic"],
                        "passed": bool(ok), "parsed": got is not None,
                        "got": sorted(got) if got else None, "want": sorted(want),
                        "raw": out[:400]})
        if i % 20 == 0:
            print(f"  [{name}] {i}/{len(rows)}  passed {passed}", flush=True)
    return {
        "name": name, "n": len(rows), "passed": passed,
        "accuracy": round(passed / len(rows), 4) if rows else 0.0,
        "unparseable": unparseable,
        "by_clinic": {c: {"n": len(v), "passed": sum(v),
                          "accuracy": round(sum(v) / len(v), 4)}
                      for c, v in sorted(per_clinic.items())},
        "records": records,
    }


def compare(base: dict, adapter: dict) -> str:
    """The only number that matters, printed so it cannot be misread."""
    d = adapter["passed"] - base["passed"]
    lines = [
        f"{'arm':<22}{'passed':>10}{'accuracy':>11}{'unparseable':>13}",
        f"{base['name']:<22}{base['passed']:>7}/{base['n']:<2}"
        f"{base['accuracy']:>11.3f}{base['unparseable']:>13}",
        f"{adapter['name']:<22}{adapter['passed']:>7}/{adapter['n']:<2}"
        f"{adapter['accuracy']:>11.3f}{adapter['unparseable']:>13}",
        "",
        f"adapter − base: {d:+d} of {base['n']}",
    ]
    if d <= 0:
        lines.append("THE ADAPTER DID NOT HELP. That is the result; report it as "
                     "the result. Do not retrain until it looks better.")
    return "\n".join(lines)
