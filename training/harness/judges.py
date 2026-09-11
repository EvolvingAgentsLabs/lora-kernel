"""Can anything grade this work without the answer key that made it trustworthy?

Every number in this project is trustworthy because the problems were generated
from closed-form formulas. Real work has no such key, and the tournament needs a
grade that the loop it grades cannot influence. So the oracle is turned on the
judges: 100 chains whose correctness is already known, scored by candidates that
never see the answer.

THE BAR IS THE MAJORITY CLASS. 67 of the 100 chains are wrong, so answering
"incorrect" every time scores 0.67 and is not a judge. Accuracy alone would hide
that, which is why recall on the CORRECT class is reported beside it: a grader used
in a loop that never recognises good work throws the good work away.

    python3 -m training.harness.judges
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from training.physics.repair import repair
from training.physics.tools import CALL as TOOLCALL
from training.physics.tools import ToolError, answer


def _resolve(chain: str) -> str | None:
    """Every tool call re-executed and replaced by the value it returns.

    A CHAIN IS MIXED, AND THAT IS THE WHOLE POINT OF THE DESIGN. The query steps
    carry tags because a tool answered them; the arithmetic steps do not, because
    the expert wrote them and the harness evaluated them. A check that reads only
    the tagged half compares the final answer against the last *lookup* and rejects
    a chain that was right [ran] 2026-09-11. Resolving the calls first leaves one
    uniform chain of `expression = value` lines for the ordinary walk to score.

    Returns None when a call is refused or carried a value the tool disagrees with,
    because either is a defect the chain cannot be right despite.
    """
    out, last = [], 0
    for m in TOOLCALL.finditer(chain):
        try:
            value = answer(m.group(1), m.group(2))
        except ToolError:
            return None
        tail = chain[m.end():].lstrip()
        claimed = re.match(r"=\s*(-?\d+\.?\d*(?:[eE][-+]?\d+)?)", tail)
        if claimed:
            if abs(float(claimed.group(1)) - value) > 1e-3 * max(abs(value), 1):
                return None
            skip = len(chain[m.end():]) - len(tail) + claimed.end()
        else:
            skip = 0
        out.append(chain[last:m.start()] + f"{value:.6g}")
        last = m.end() + skip
    return "".join(out) + chain[last:]


SOURCES = [("results/P13-sequential-20260910/sequential_results.json", "in"),
           ("results/P14-held-out-20260910/sequential_results_heldout.json", "out")]

SYSTEM = ("You are grading a worked solution to an engineering problem. You are "
          "NOT given the correct answer. Decide whether the solution is right.")
PROMPT = ("Problem:\n{problem}\n\nSubmitted solution:\n{chain}\n\n"
          "Is the submitted solution correct? Consider whether the relations used "
          "are the right ones for this problem and whether the steps follow from "
          'each other. Reply with exactly one word: CORRECT or INCORRECT.')


def pool() -> list[dict]:
    from training.physics.generate import TRAIN_FAMILIES, HELD_OUT_FAMILIES, generate
    rows = []
    for path, tag in SOURCES:
        d = json.loads(Path(path).read_text())
        fams = HELD_OUT_FAMILIES if d.get("held_out") else TRAIN_FAMILIES
        n = max(v["n"] for v in d["arms"].values())
        seed = 515151
        cases = {c["case_id"]: c for c in generate(n, seed, fams, style="working")}
        for arm, v in d["arms"].items():
            for r in v["records"]:
                c = cases.get(r["case_id"])
                if c is None or not r.get("raw"):
                    continue
                rows.append({"id": f"{tag}:{arm.split('·')[0].strip()}:{r['case_id']}",
                             "problem": c["prompt"].split("\n\n")[0],
                             "chain": r["raw"], "truth": bool(r["passed"])})
    return rows


def judge_procedural(row) -> bool:
    """No model is asked anything, so no model can flatter it.

    Re-executes every step and accepts the solution only if the number it finishes
    on is the number its own chain implies. It is blind to a wrong formula by
    construction — that blindness is the measurement.

    IT HAS TO READ EVERY TOOL, NOT ONLY THE CALCULATOR. A first version knew only
    `<calc>`, so on a multi-tool chain it found nothing evaluable and returned
    False for both arms of a pair — a tie at zero, broken arbitrarily, that read
    as "the procedural check does not help" [ran] 2026-09-11. A chain that queries
    a table is re-queried; a chain that converts a unit is re-converted.
    """
    chain = _resolve(row["chain"])
    if chain is None:
        return False
    value, ok, bad = repair(chain)
    if value is None or ok == 0:
        return False
    m = re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", chain.replace(",", ""))
    if not m:
        return False
    claimed = float(m[-1])
    return bad == 0 and abs(claimed - value) <= 0.02 * max(abs(value), 1e-9)


def judge_model(tag: str, rows, max_tokens: int = 400) -> list[bool]:
    """400, not 8.

    A one-word verdict looks like it needs eight tokens. It does not: a reasoning
    model spends the budget in its thinking channel and returns an EMPTY answer
    channel, so the frontier judge abstained on 100 of 100 cases and read as
    "cannot judge" [ran] 2026-09-10. It answers correctly with room. Both judges
    get the same budget, or the comparison is between token allowances.
    """
    from alpha.backends import BackendError, build
    model = build(tag)
    out = []
    for i, row in enumerate(rows, 1):
        try:
            r = model.chat([{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": PROMPT.format(**row)}],
                           max_tokens=max_tokens)
            said = (r.text or "").strip().upper()
        except BackendError as e:
            print(f"  [{tag}] {row['id']} backend error: {e}", flush=True)
            said = ""
        # A REPLY THAT IS NEITHER WORD IS NOT A VERDICT. Counting it as INCORRECT
        # would hand the judge the majority class for free.
        out.append(True if "CORRECT" in said and "INCORRECT" not in said else
                   False if "INCORRECT" in said else None)
        if i % 20 == 0:
            print(f"  [{tag}] {i}/{len(rows)}", flush=True)
    return out


def score(name: str, verdicts, truths) -> dict:
    pairs = [(v, t) for v, t in zip(verdicts, truths) if v is not None]
    n = len(pairs)
    acc = sum(v == t for v, t in pairs) / n if n else 0.0
    correct = [(v, t) for v, t in pairs if t]
    wrong = [(v, t) for v, t in pairs if not t]
    return {"judge": name, "scored": n, "abstained": len(truths) - n,
            "accuracy": round(acc, 4),
            "recall_correct": round(sum(v for v, _ in correct) / len(correct), 4) if correct else 0.0,
            "recall_incorrect": round(sum(not v for v, _ in wrong) / len(wrong), 4) if wrong else 0.0,
            "said_correct": sum(v for v, _ in pairs)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--frontier", default="openai:google/gemini-3.8-flash")
    ap.add_argument("--peer", default="ollama:qwen3.5:4b")
    ap.add_argument("--out", default="results/P17-judges-20260910/judges.json")
    args = ap.parse_args()

    rows = pool()
    truths = [r["truth"] for r in rows]
    base = max(sum(truths), len(truths) - sum(truths)) / len(truths)
    print(f"[pool] {len(rows)} chains · {sum(truths)} correct · "
          f"{len(truths)-sum(truths)} incorrect · majority-class bar {base:.2f}\n",
          flush=True)

    results = [score("always INCORRECT", [False] * len(rows), truths),
               score("procedural (no model)", [judge_procedural(r) for r in rows], truths)]
    Path(args.out).write_text(json.dumps({"bar": base, "judges": results}, indent=2))

    for tag in (args.peer, args.frontier):
        if not tag:
            continue
        print(f"[judge] {tag}", flush=True)
        results.append(score(tag, judge_model(tag, rows), truths))
        Path(args.out).write_text(json.dumps({"bar": base, "judges": results}, indent=2))

    print(f"\n{'judge':<34}{'accuracy':>10}{'finds right':>13}{'finds wrong':>13}{'abstained':>11}")
    for r in results:
        print(f"{r['judge']:<34}{r['accuracy']:>10.2f}{r['recall_correct']:>13.2f}"
              f"{r['recall_incorrect']:>13.2f}{r['abstained']:>11}")
    print(f"\nThe bar is {base:.2f} — answering INCORRECT every time. A judge that "
          "does not beat it is not a judge, and one that never finds the correct "
          "work would throw good work away in a loop.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
