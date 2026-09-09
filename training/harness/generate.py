"""Protocol without domain: the corpus `harness.lora` is trained on.

WHAT THE ARCHITECTURE CLAIMS, AND WHAT WE ACTUALLY MEASURED.
`ARCHITECTURE.md` §4: the kernel owns **how to act** — action tokens, tool
syntax, state — and a domain adapter owns **what is true** in its region. They
must stay separate, because merging them "would make every domain adapter
re-learn the protocol, which is the cost this design exists to remove".

P7 measured the merged case: one adapter that learned fluid mechanics AND the
`<calc>` syntax together, scoring 40/40 **[ran]**. That is
`TECHNICAL-REFERENCE.md` §5's option 3 — the one listed in order to be rejected.
The claim that has never been tested is the separation itself.

SO THIS CORPUS CONTAINS NO PHYSICS. No pipes, no fluids, no Reynolds, no
formulas from any domain the expert knows. It teaches four things and nothing
else:

  * the syntax of a call, and that a value comes back;
  * that a computed number must come FROM a call, never from the model;
  * how to carry a returned value into the next call;
  * what an error looks like and that the answer is to fix the expression.

If a kernel trained only on this can make a physics expert — one that never saw a
`<calc>` tag — start calling the tool, then the protocol lives in the weights
separately from the domain, and the architecture's layer 3 is real. If it cannot,
the merged adapter is what works and §4 is wrong.

    python3 -m training.harness.generate --n 600
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random

from training.protocol import SYSTEM, user_prompt

from training.physics.calc import evaluate




def _chain(steps: list[tuple[str, str]]) -> tuple[str, float]:
    """steps are (label, expression); the expression may use {prev}."""
    out, prev = [], None
    for i, (label, expr) in enumerate(steps, 1):
        e = expr.format(prev=f"{prev:.6g}") if prev is not None else expr
        v = evaluate(e)
        out.append(f"{i}. {label}: <calc>{e}</calc>= {v:.6g}")
        prev = v
    return "\n".join(out) + f'\n\n{{"answer": {prev:.6g}}}', prev


# -- generic tasks, chosen so that none of them teaches a domain ---------------

def receipt(rng):
    n, price = rng.randint(3, 19), round(rng.uniform(1.2, 40.0), 2)
    disc, tax = rng.choice([5, 10, 15, 20]), rng.choice([8, 10, 21])
    steps = [("subtotal", f"{n} * {price}"),
             (f"after a {disc}% discount", f"{{prev}} * (1 - {disc}/100)"),
             (f"with {tax}% tax", f"{{prev}} * (1 + {tax}/100)")]
    return (f"A shop sells {n} items at {price} each. A {disc}% discount is "
            f"applied to the subtotal, then {tax}% tax is added to the "
            f"discounted amount. What is the final total?"), steps


def average_then_scale(rng):
    vals = [round(rng.uniform(2, 200), 2) for _ in range(rng.randint(3, 6))]
    k = round(rng.uniform(1.1, 9.9), 2)
    steps = [("sum of the values", " + ".join(str(v) for v in vals)),
             ("mean", f"{{prev}} / {len(vals)}"),
             (f"scaled by {k}", f"{{prev}} * {k}")]
    return (f"Take the numbers {', '.join(str(v) for v in vals)}. Compute their "
            f"mean and then multiply it by {k}."), steps


def compound_growth(rng):
    p, r, t = round(rng.uniform(100, 9000), 2), round(rng.uniform(1.5, 12.0), 2), rng.randint(2, 25)
    steps = [("growth factor per period", f"1 + {r}/100"),
             (f"compounded over {t} periods", f"{{prev}} ** {t}"),
             ("final amount", f"{p} * {{prev}}")]
    return (f"An amount of {p} grows by {r}% per period, compounding, for {t} "
            f"periods. What is the final amount?"), steps


def two_stage_rate(rng):
    d1, s1 = round(rng.uniform(5, 300), 1), round(rng.uniform(2, 90), 1)
    d2, s2 = round(rng.uniform(5, 300), 1), round(rng.uniform(2, 90), 1)
    steps = [("time for the first leg", f"{d1} / {s1}"),
             ("plus time for the second leg", f"{{prev}} + {d2}/{s2}"),
             ("average rate over the whole trip", f"({d1} + {d2}) / {{prev}}")]
    return (f"A journey covers {d1} units at a rate of {s1} per unit time, then "
            f"{d2} units at {s2} per unit time. What is the average rate over "
            f"the whole journey?"), steps


def geometric_solid(rng):
    r, h = round(rng.uniform(0.2, 9.0), 2), round(rng.uniform(0.5, 20.0), 2)
    steps = [("base area", f"pi * {r}**2"),
             ("volume of the cylinder", f"{{prev}} * {h}"),
             ("volume of a cone of the same base and height", f"{{prev}} / 3")]
    return (f"A cylinder has radius {r} and height {h}. Compute the volume of a "
            f"cone that shares its base and height."), steps


def root_and_log(rng):
    a, b = round(rng.uniform(2, 900), 2), round(rng.uniform(1.2, 60), 2)
    steps = [("sum", f"{a} + {b}"), ("square root", f"sqrt({{prev}})"),
             ("base-10 logarithm of the result", f"log10({{prev}})")]
    return (f"Add {a} and {b}, take the square root of the sum, then take the "
            f"base-10 logarithm of that."), steps


TASKS = [receipt, average_then_scale, compound_growth, two_stage_rate,
         geometric_solid, root_and_log]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=99021)
    ap.add_argument("--out", default="training/harness/data/train.jsonl")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows = []
    for i in range(args.n):
        stmt, steps = TASKS[i % len(TASKS)](rng)
        chain, _ = _chain(steps)
        rows.append({"case_id": f"harn-{i:04d}", "task": TASKS[i % len(TASKS)].__name__,
                     "calc_calls": chain.count("<calc>"),
                     "messages": [{"role": "system", "content": SYSTEM},
                                  {"role": "user", "content": user_prompt(stmt)},
                                  {"role": "assistant", "content": chain}]})
    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    from collections import Counter
    print(json.dumps({"written": len(rows), "path": str(p),
                      "calls_per_example": round(sum(r["calc_calls"] for r in rows) / len(rows), 2),
                      "by_task": dict(Counter(r["task"] for r in rows)),
                      "contains_physics": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
