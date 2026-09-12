"""Problems whose statements do not contain the numbers needed to solve them.

WHAT IS DIFFERENT FROM THE ORIGINAL SUITE, AND WHY. There, every constant a chain
needed was printed in the statement, in SI, ready to be copied into an expression.
That is why a learned protocol lost to twenty lines of `re` in P13: with one tool
and every number already written down, asking for the tool *is* copying.

Here a statement says "water at 20 C" and "45 L/s". The density is in a table the
model must query, and the flow is in a unit it must convert. So a chain has to:

    choose WHICH tool        `convert`, `lookup` or `calc`
    build keyed ARGUMENTS    `fluid=water; property=density; T=20`
    out of PROSE             "water at 20 C"

and one family, `manning_channel`, needs no fluid property at all — so a model
that has learned to always look something up is punished by the same suite that
rewards looking up elsewhere.

THE STEP LABELS DO NOT NAME THE TOOL. An earlier draft wrote "Flow rate in SI
units", which hands the choice of `convert` to anything that can read. The labels
say what quantity is wanted — "Flow rate", "Density of the fluid", "Inlet area" —
and which tool that requires is left to be worked out. Otherwise the experiment
measures argument formatting only, and calls that the choice of tool.

THREE PHRASINGS PER FAMILY, ON PURPOSE. The competitor this material exists to
test against is a hand-written rule, and a rule beats a single template every
time. Two of this project's measurements have already died on material that
announced its own answer in its wording; a third would be a pattern rather than an
accident.

    python3 -m training.physics.multitool --n 40 --split eval
"""

from __future__ import annotations

import argparse
import json
import math
import random

from training.physics.tools import FLUIDS, UNITS

G = 9.80665

FLOW_UNITS = ["L/s", "m^3/h", "L/min"]
LEN_UNITS = ["mm", "cm"]
PRESSURE_UNITS = ["kPa", "bar", "mbar"]
LIQUIDS = [("water", 10), ("water", 20), ("water", 40), ("water", 60),
           ("seawater", 20), ("ethanol", 20), ("glycerin", 20)]


def _si(value: float, unit: str) -> float:
    return value * UNITS[unit][1]


# INVENTED NAMES AND VALUES DRAWN PER CASE. A fixed table of seven fluids is
# fourteen numbers, and an expert trained on 600 examples learns them and beats
# every arm that queries — 27/30 against 10/30 [ran] `results/P15-…`. A fluid
# called XJ-7 whose density exists only in this problem cannot be recalled, so a
# step that needs it has to ask. What an expert can still learn is WHICH property
# the step needs, which is the physics and is what an expert is for.
CODES = "ABCDEFGHJKLMNPQRSTVWXYZ"


def _fluid(rng) -> tuple[str, int, float, float]:
    name = f"{rng.choice(CODES)}{rng.choice(CODES)}-{rng.randrange(2, 99)}"
    t = rng.choice([10, 20, 25, 40, 60, 80])
    density = round(rng.uniform(620.0, 1480.0), 1)
    viscosity = float(f"{rng.uniform(2.4e-4, 1.9):.3g}")
    return name, t, density, viscosity


def handbook_for(name: str, t: int, density: float, viscosity: float) -> dict:
    """The table this one problem carries — held by the TOOL, never printed.

    A FIRST DRAFT PRINTED IT IN THE STATEMENT AND THAT REPEATED P15'S FAULT WITH A
    NEW FACE. If the density is in the prompt, a model copies it and the lookup is
    decoration again: P15 failed because the value could be remembered, and a
    printed handbook fails because it can be read. Naming the fluid and keeping its
    properties inside the tool is what makes the call necessary — the value was not
    in training, and it is not in the question.

    Both properties are stored even when one is unused, so a step has to name which
    one it wants rather than take the only number available.
    """
    return {(name.lower(), t): {"density": density, "viscosity": viscosity}}


def _friction(re_: float, eps: float, d: float) -> float:
    if re_ < 2300:
        return 64 / re_
    return 0.25 / math.log10(eps / (3.7 * d) + 5.74 / re_ ** 0.9) ** 2


# --------------------------------------------------------------------------
# Each family returns (statement, answer, unit, chain) where `chain` is the
# oracle's own solution as tool calls, with nothing computed in prose.
# --------------------------------------------------------------------------

def pipe_head_loss(rng):
    name, t, rho, mu = _fluid(rng)
    qu, du = rng.choice(FLOW_UNITS), rng.choice(LEN_UNITS)
    q_raw = round(rng.uniform(5, 90), 1)
    d_raw = round(rng.uniform(60, 400), 1) if du == "mm" else round(rng.uniform(6, 40), 1)
    L = round(rng.uniform(20, 400), 1)
    eps = round(rng.uniform(2e-5, 3e-4), 6)
    q, d = _si(q_raw, qu), _si(d_raw, du)
    a = math.pi / 4 * d ** 2
    v = q / a
    re_ = rho * v * d / mu
    f = _friction(re_, eps, d)
    h = f * (L / d) * v ** 2 / (2 * G)
    phrasing = rng.randrange(3)
    if phrasing == 0:
        stmt = (f"{name.capitalize()} at {t} C is pumped at {q_raw} {qu} along a "
                f"straight pipe of internal diameter {d_raw} {du} and length {L} m. "
                f"The pipe roughness is {eps} m. Find the head loss.")
    elif phrasing == 1:
        stmt = (f"A {L} m run of pipe, {d_raw} {du} across, carries {q_raw} {qu} of "
                f"{name} held at {t} C. Taking the wall roughness as {eps} m, what "
                f"head is lost to friction?")
    else:
        stmt = (f"Determine the friction head loss when {q_raw} {qu} of {name} "
                f"({t} C) travels {L} m through a {d_raw} {du} bore whose roughness "
                f"is {eps} m.")
    chain = [
        ("Flow rate", "convert", f"value={q_raw}; from={qu}; to=m^3/s"),
        ("Pipe diameter", "convert", f"value={d_raw}; from={du}; to=m"),
        ("Density of the fluid", "lookup", f"fluid={name}; property=density; T={t}"),
        ("Dynamic viscosity", "lookup", f"fluid={name}; property=viscosity; T={t}"),
        ("Cross-sectional area", "calc", f"pi/4 * {d:.6g}**2"),
        ("Velocity v = Q/A", "calc", f"{q:.6g} / {a:.6g}"),
        ("Reynolds number", "calc", f"{rho} * {v:.6g} * {d:.6g} / {mu}"),
        ("Friction factor",
         "calc", (f"64 / {re_:.6g}" if re_ < 2300 else
                  f"0.25 / (log10({eps}/(3.7*{d:.6g}) + 5.74/{re_:.6g}**0.9))**2")),
        ("Head loss h = f (L/D) v^2 / (2g)",
         "calc", f"{f:.6g} * ({L}/{d:.6g}) * {v:.6g}**2 / (2*{G})"),
    ]
    book = handbook_for(name, t, rho, mu)
    return stmt, h, "m", chain, book


def hydrostatic_force(rng):
    name, t, rho, mu = _fluid(rng)
    lu = rng.choice(LEN_UNITS)
    w_raw = round(rng.uniform(300, 2500), 1) if lu == "mm" else round(rng.uniform(30, 250), 1)
    h_raw = round(rng.uniform(300, 2000), 1) if lu == "mm" else round(rng.uniform(30, 200), 1)
    top = round(rng.uniform(0.5, 4.0), 2)
    w, hh = _si(w_raw, lu), _si(h_raw, lu)
    hc = top + hh / 2
    f = rho * G * hc * (w * hh)
    phrasing = rng.randrange(3)
    if phrasing == 0:
        stmt = (f"A vertical rectangular gate {w_raw} {lu} wide and {h_raw} {lu} tall "
                f"is submerged in {name} at {t} C, its top edge {top} m below the "
                f"surface. Compute the resultant force on one face.")
    elif phrasing == 1:
        stmt = (f"In a tank of {name} held at {t} C, a flat gate measuring "
                f"{w_raw} {lu} by {h_raw} {lu} hangs vertically with {top} m of "
                f"liquid above its upper edge. What force does the liquid exert on it?")
    else:
        stmt = (f"Find the hydrostatic thrust on a vertical plate {h_raw} {lu} high "
                f"and {w_raw} {lu} wide, its top {top} m beneath the free surface of "
                f"{name} at {t} C.")
    chain = [
        ("Gate width", "convert", f"value={w_raw}; from={lu}; to=m"),
        ("Gate height", "convert", f"value={h_raw}; from={lu}; to=m"),
        ("Density of the fluid", "lookup", f"fluid={name}; property=density; T={t}"),
        ("Depth of the centroid", "calc", f"{top} + {hh:.6g}/2"),
        ("Area of the gate", "calc", f"{w:.6g} * {hh:.6g}"),
        ("Resultant force F = rho g h_c A",
         "calc", f"{rho} * {G} * {hc:.6g} * {w * hh:.6g}"),
    ]
    book = handbook_for(name, t, rho, mu)
    return stmt, f, "N", chain, book


def venturi_flow(rng):
    name, t, rho, mu = _fluid(rng)
    lu, pu = rng.choice(LEN_UNITS), rng.choice(PRESSURE_UNITS)
    d1_raw = round(rng.uniform(80, 400), 1) if lu == "mm" else round(rng.uniform(8, 40), 1)
    ratio = rng.uniform(0.35, 0.7)
    d2_raw = round(d1_raw * ratio, 1)
    dp_raw = round(rng.uniform(3, 90), 2) if pu == "kPa" else (
        round(rng.uniform(0.03, 0.9), 3) if pu == "bar" else round(rng.uniform(30, 900), 1))
    d1, d2, dp = _si(d1_raw, lu), _si(d2_raw, lu), _si(dp_raw, pu)
    a1, a2 = math.pi / 4 * d1 ** 2, math.pi / 4 * d2 ** 2
    q = a2 * math.sqrt(2 * dp / (rho * (1 - (a2 / a1) ** 2)))
    phrasing = rng.randrange(3)
    if phrasing == 0:
        stmt = (f"A venturi meter with an inlet of {d1_raw} {lu} and a throat of "
                f"{d2_raw} {lu} carries {name} at {t} C. The pressure drop between "
                f"inlet and throat is {dp_raw} {pu}. Find the volumetric flow rate.")
    elif phrasing == 1:
        stmt = (f"{name.capitalize()} at {t} C passes through a venturi whose bore "
                f"narrows from {d1_raw} {lu} to {d2_raw} {lu}. A drop of {dp_raw} {pu} "
                f"is measured across the contraction. What flow does this imply?")
    else:
        stmt = (f"Compute the discharge through a venturi ({d1_raw} {lu} inlet, "
                f"{d2_raw} {lu} throat) metering {name} at {t} C when the pressure "
                f"falls by {dp_raw} {pu}.")
    chain = [
        ("Inlet diameter", "convert", f"value={d1_raw}; from={lu}; to=m"),
        ("Throat diameter", "convert", f"value={d2_raw}; from={lu}; to=m"),
        ("Pressure drop", "convert", f"value={dp_raw}; from={pu}; to=Pa"),
        ("Density of the fluid", "lookup", f"fluid={name}; property=density; T={t}"),
        ("Inlet area", "calc", f"pi/4 * {d1:.6g}**2"),
        ("Throat area", "calc", f"pi/4 * {d2:.6g}**2"),
        ("Flow Q = A2 sqrt(2 dp / (rho (1 - (A2/A1)^2)))",
         "calc", f"{a2:.6g} * sqrt(2*{dp:.6g} / ({rho} * (1 - ({a2:.6g}/{a1:.6g})**2)))"),
    ]
    book = handbook_for(name, t, rho, mu)
    return stmt, q, "m^3/s", chain, book


def manning_channel(rng):
    """The family that needs NO lookup. A model that always queries the table
    pays for it here, which is the point of including it."""
    lu = rng.choice(LEN_UNITS)
    b_raw = round(rng.uniform(80, 400), 1) if lu == "cm" else round(rng.uniform(800, 4000), 1)
    y_raw = round(rng.uniform(20, 150), 1) if lu == "cm" else round(rng.uniform(200, 1500), 1)
    n = round(rng.uniform(0.011, 0.035), 3)
    s = round(rng.uniform(0.0005, 0.02), 5)
    b, y = _si(b_raw, lu), _si(y_raw, lu)
    a = b * y
    per = b + 2 * y
    r = a / per
    q = (1 / n) * a * r ** (2 / 3) * math.sqrt(s)
    phrasing = rng.randrange(3)
    if phrasing == 0:
        stmt = (f"A rectangular channel {b_raw} {lu} wide runs {y_raw} {lu} deep on a "
                f"bed slope of {s}. Manning's n is {n}. Find the discharge.")
    elif phrasing == 1:
        stmt = (f"Water flows uniformly in an open rectangular channel of width "
                f"{b_raw} {lu} at a depth of {y_raw} {lu}. The slope is {s} and the "
                f"roughness coefficient is {n}. What volume passes per second?")
    else:
        stmt = (f"Using Manning's equation with n = {n}, compute the flow in a "
                f"{b_raw} {lu} wide rectangular channel carrying a depth of "
                f"{y_raw} {lu} down a gradient of {s}.")
    chain = [
        ("Channel width", "convert", f"value={b_raw}; from={lu}; to=m"),
        ("Flow depth", "convert", f"value={y_raw}; from={lu}; to=m"),
        ("Flow area", "calc", f"{b:.6g} * {y:.6g}"),
        ("Wetted perimeter", "calc", f"{b:.6g} + 2*{y:.6g}"),
        ("Hydraulic radius R = A/P", "calc", f"{a:.6g} / {per:.6g}"),
        ("Discharge Q = (1/n) A R^(2/3) sqrt(S)",
         "calc", f"(1/{n}) * {a:.6g} * {r:.6g}**(2/3) * sqrt({s})"),
    ]
    return stmt, q, "m^3/s", chain, {}


FAMILIES = {"pipe_head_loss": pipe_head_loss, "hydrostatic_force": hydrostatic_force,
            "venturi_flow": venturi_flow, "manning_channel": manning_channel}

INSTRUCTION = (
    "Solve the problem. Work in SI units. Show your working as a short numbered "
    "chain of steps, each with its intermediate value. Then, on the final line, "
    'give the answer as one JSON object: {"answer": <number>}, where <number> is '
    "the numeric value in %s."
)


def render(chain: list[tuple[str, str, str]]) -> str:
    """The oracle's chain as calls, with no value written by hand."""
    return "\n".join(f"{i}. {label}: <{tool}>{body}</{tool}>"
                     for i, (label, tool, body) in enumerate(chain, 1))


def generate(n: int, seed: int, families: dict | None = None) -> list[dict]:
    fams = families or FAMILIES
    rng = random.Random(seed)
    names = sorted(fams)
    out = []
    for i in range(n):
        name = names[i % len(names)]
        stmt, ans, unit, chain, book = fams[name](rng)
        out.append({"case_id": f"mt-{i:04d}", "family": name,
                    "handbook": [[list(k), v] for k, v in book.items()],
                    "prompt": f"{stmt}\n\n{INSTRUCTION % unit}",
                    "answer": ans, "unit": unit, "chain": chain,
                    "tools_needed": sorted({t for _, t, _ in chain})})
    return out


def domain_chain(chain, handbook=None) -> str:
    """The same solution with the PROTOCOL removed and the physics kept.

    A tool step becomes `3. Density of the fluid: 998.2` — the label and the value
    that came back, with no call. A calc step keeps its expression, because the
    expression is the physics and the physics is the expert's. What the expert
    never sees is a tag.

    THE TABLE VALUES ARE VISIBLE HERE AND THAT IS A KNOWN COST. An expert trained
    on this can memorise that water at 20 C is 998.2 and skip the lookup at serving
    time. It is not hidden: P15's third arm removes the tool layer entirely and
    measures exactly how far memory alone gets, so the leak is priced rather than
    assumed away.
    """
    from training.physics.tools import answer
    lines, last = [], 0.0
    for i, (label, tool, body) in enumerate(chain, 1):
        last = answer(tool, body, handbook)
        if tool == "calc":
            lines.append(f"{i}. {label}: {body} = {last:.6g}")
        else:
            lines.append(f"{i}. {label}: {last:.6g}")
    return "\n".join(lines) + f'\n\n{{"answer": {last:.6g}}}'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20260910)
    ap.add_argument("--split", default="eval", choices=["train", "eval"])
    ap.add_argument("--out", default="")
    ap.add_argument("--corpus", default="", choices=["", "domain"],
                    help="domain writes a training corpus with the protocol removed")
    args = ap.parse_args()
    rows = generate(args.n, args.seed + (0 if args.split == "eval" else 7717))
    if args.corpus == "domain":
        from training.protocol import SYSTEM
        rows = [{"case_id": r["case_id"], "family": r["family"],
                 "answer": r["answer"], "unit": r["unit"],
                 "messages": [{"role": "system", "content": SYSTEM},
                              {"role": "user", "content": r["prompt"]},
                              {"role": "assistant", "content": domain_chain(r["chain"], {tuple(k): v for k, v in r["handbook"]})}]}
                for r in rows]
    text = "\n".join(json.dumps(r) for r in rows) + "\n"
    if args.out:
        open(args.out, "w").write(text)
        print(f"{len(rows)} cases -> {args.out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
