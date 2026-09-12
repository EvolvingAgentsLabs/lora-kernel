"""A protocol corpus for three tools, containing no derivation to be learned.

WHAT THE KERNEL IS ALLOWED TO KNOW. `ARCHITECTURE.md` §4 gives it *how to act* and
nothing else, so every task here **states its own formula**:

    Mass flow equals density times volumetric flow. Water at 20 C is delivered at
    45 L/s. Compute the mass flow.

There is no physics to absorb — the relation is in the prompt. What has to be
learned is the protocol: that a quantity in the wrong unit becomes a `convert`,
that a named substance becomes a `lookup`, that arithmetic becomes a `calc`, and
that each of the three takes different arguments in a different shape.

WHAT IT MUST NOT CONTAIN, AND THIS IS CHECKED. None of the four evaluation
families. No Reynolds number, no friction factor, no Manning equation, no venturi,
no hydrostatic gate. A kernel that had seen those would be an expert wearing a
kernel's name, and P15 would measure nothing.

THE HARD CASE IS DELIBERATELY OVER-REPRESENTED: tasks that give a quantity already
in SI, where the right move is to **not** call `convert`. A protocol that has
learned "always convert" is as wrong as one that never does, and only a corpus
containing both teaches the difference.

    python3 -m training.harness.generate_multitool --out training/harness/data_mt/train.jsonl
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random

from training.physics.multitool import INSTRUCTION
from training.physics.multitool import _fluid, handbook_for
from training.physics.tools import UNITS, answer
from training.protocol import SYSTEM

# THE KERNEL CORPUS USES INVENTED FLUIDS TOO. If it trained against the fixed
# table it would learn those fourteen numbers and stop querying, which is the
# behaviour P15 measured and this material exists to remove [ran].
FLOW = ["L/s", "m^3/h", "L/min", "m^3/s"]        # m^3/s is the trap: no convert
LENGTH = ["mm", "cm", "m", "in"]                 # m is the trap
PRESSURE = ["kPa", "bar", "mbar", "Pa"]          # Pa is the trap


def _si(v: float, u: str) -> float:
    return v * UNITS[u][1]


def mass_flow(rng):
    name, t, rho, mu = _fluid(rng)
    u = rng.choice(FLOW)
    q = round(rng.uniform(2, 90), 1)
    chain = []
    if u != "m^3/s":
        chain.append(("Volumetric flow", "convert", f"value={q}; from={u}; to=m^3/s"))
    chain.append(("Density of the fluid", "lookup",
                  f"fluid={name}; property=density; T={t}"))
    chain.append(("Mass flow", "calc", f"{rho} * {_si(q, u):.6g}"))
    stmt = (f"Mass flow equals density times volumetric flow. {name} "
            f"at {t} C is delivered at {q} {u}. Compute the mass flow.")
    return stmt, "kg/s", chain, handbook_for(name, t, rho, mu)


def column_pressure(rng):
    name, t, rho, mu = _fluid(rng)
    u = rng.choice(LENGTH)
    h = round(rng.uniform(50, 900), 1) if u in ("mm", "cm") else round(rng.uniform(1, 9), 2)
    chain = []
    if u != "m":
        chain.append(("Column height", "convert", f"value={h}; from={u}; to=m"))
    chain.append(("Density of the fluid", "lookup",
                  f"fluid={name}; property=density; T={t}"))
    chain.append(("Pressure", "calc", f"{rho} * 9.80665 * {_si(h, u):.6g}"))
    stmt = (f"The pressure under a still column of liquid is density times 9.80665 "
            f"times height. A column of {name} at {t} C stands {h} {u} tall. What "
            f"is the pressure at its base?")
    return stmt, "Pa", chain, handbook_for(name, t, rho, mu)


def kinematic_viscosity(rng):
    name, t, rho, mu = _fluid(rng)
    chain = [("Dynamic viscosity", "lookup", f"fluid={name}; property=viscosity; T={t}"),
             ("Density of the fluid", "lookup", f"fluid={name}; property=density; T={t}"),
             ("Kinematic viscosity", "calc", f"{mu} / {rho}")]
    stmt = (f"Kinematic viscosity is dynamic viscosity divided by density. Give it "
            f"for {name} at {t} C.")
    return stmt, "m^2/s", chain, handbook_for(name, t, rho, mu)


def force_from_pressure(rng):
    pu, lu = rng.choice(PRESSURE), rng.choice(LENGTH)
    p = round(rng.uniform(5, 400), 1) if pu != "bar" else round(rng.uniform(0.05, 4), 3)
    a_side = round(rng.uniform(20, 800), 1) if lu in ("mm", "cm") else round(rng.uniform(0.2, 8), 2)
    chain = []
    if pu != "Pa":
        chain.append(("Applied pressure", "convert", f"value={p}; from={pu}; to=Pa"))
    if lu != "m":
        chain.append(("Plate side", "convert", f"value={a_side}; from={lu}; to=m"))
    chain.append(("Area of the square plate", "calc", f"{_si(a_side, lu):.6g}**2"))
    chain.append(("Force", "calc",
                  f"{_si(p, pu):.6g} * {_si(a_side, lu) ** 2:.6g}"))
    stmt = (f"Force equals pressure times area. A square plate of side {a_side} {lu} "
            f"has {p} {pu} acting uniformly on it. Find the force.")
    return stmt, "N", chain, {}


def flow_ratio(rng):
    """No lookup at all — the family that punishes always querying the table."""
    u1, u2 = rng.sample([u for u in FLOW if u != "m^3/s"], 2)
    a = round(rng.uniform(3, 80), 1)
    b = round(rng.uniform(3, 80), 1)
    chain = [("First flow", "convert", f"value={a}; from={u1}; to=m^3/s"),
             ("Second flow", "convert", f"value={b}; from={u2}; to=m^3/s"),
             ("Ratio", "calc", f"{_si(a, u1):.6g} / {_si(b, u2):.6g}")]
    stmt = (f"One line carries {a} {u1} and another carries {b} {u2}. How many "
            f"times larger is the first flow than the second?")
    return stmt, "dimensionless", chain, {}


TASKS = [mass_flow, column_pressure, kinematic_viscosity, force_from_pressure,
         flow_ratio]

FORBIDDEN = ("reynolds", "friction factor", "manning", "venturi", "throat",
             "hydraulic radius", "wetted perimeter", "head loss", "hydrostatic",
             "gate", "swamee")


def render(chain, handbook=None) -> tuple[str, float]:
    """The chain with every call answered, and the value it ends on."""
    lines, last = [], 0.0
    for i, (label, tool, body) in enumerate(chain, 1):
        last = answer(tool, body, handbook)
        lines.append(f"{i}. {label}: <{tool}>{body}</{tool}>= {last:.6g}")
    return "\n".join(lines) + f'\n\n{{"answer": {last:.6g}}}', last


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=445533)
    ap.add_argument("--out", default="training/harness/data_mt/train.jsonl")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    rows, no_convert = [], 0
    for i in range(args.n):
        task = TASKS[i % len(TASKS)]
        stmt, unit, chain, book = task(rng)
        body, _ = render(chain, book)
        tools = sorted({t for _, t, _ in chain})
        no_convert += "convert" not in tools
        rows.append({"case_id": f"mtk-{i:04d}", "task": task.__name__,
                     "calls": len(chain), "tools": tools,
                     "messages": [{"role": "system", "content": SYSTEM},
                                  {"role": "user",
                                   "content": f"{stmt}\n\n{INSTRUCTION % unit}"},
                                  {"role": "assistant", "content": body}]})

    blob = json.dumps(rows).lower()
    leaked = [w for w in FORBIDDEN if w in blob]
    assert not leaked, f"the kernel corpus contains the evaluation domain: {leaked}"

    p = pathlib.Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    from collections import Counter
    print(json.dumps({
        "written": len(rows), "path": str(p),
        "calls_per_example": round(sum(r["calls"] for r in rows) / len(rows), 2),
        "by_task": dict(Counter(r["task"] for r in rows)),
        "examples_needing_no_convert": no_convert,
        "contains_evaluation_domain": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
