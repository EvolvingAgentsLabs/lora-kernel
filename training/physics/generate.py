"""Multi-step fluid mechanics whose answer is computed, never judged.

WHY THIS DOMAIN EXISTS. The clinical suite cannot show a frontier advantage, and
the reason is structural rather than bad luck: its difficulty is three
**unpublished** rules that "can only be discovered from experience" — the
benchmark's own words. A model that never saw the training split cannot know
them, so no amount of general capability helps and every frontier arm ties or
loses. **[read]** `../verified-runtime/domains/clinical_learning/generate.py`.

Here the difficulty is the opposite kind. Everything needed is in the statement
and in physics; what a small model lacks is the ability to carry a chain:

    Q and D  ->  Reynolds  ->  choose the regime  ->  the right friction
             ->  head loss  ->  pump power

That chain is where a 3B drops a link and a large model does not — which is the
precondition Phase A needs and has never had.

THE ORACLE IS ARITHMETIC. Every family below computes its own answer in closed
form. There is no judge, no rubric and no rater: a float, compared within a
stated relative tolerance.

FAMILIES ARE THE GENERALISATION PROBE. Training uses some families and evaluation
holds others out entirely, the way `delta` holds out an inverted rule. An adapter
that learned the templates scores well on seen families and collapses on unseen
ones; an adapter that learned to carry a chain does not. That gap is this
domain's false-promotion number.

    python3 -m training.physics.generate --n 40 --split eval
"""

from __future__ import annotations

import argparse
import json
import math
import random

G = 9.80665


# -- the families -------------------------------------------------------------
# Each returns (statement, answer, unit, workings). `workings` is never shown to
# a model; it exists so a human can check the oracle by hand, which is the only
# way an oracle stops being a claim.

def _reynolds(rho, v, d, mu):
    return rho * v * d / mu


def _friction(re, eps, d):
    """Laminar exact; turbulent by Swamee-Jain, the explicit Colebrook fit."""
    if re < 2300:
        return 64.0 / re
    return 0.25 / (math.log10(eps / (3.7 * d) + 5.74 / re ** 0.9)) ** 2


def pipe_head_loss(rng):
    # Velocity is sampled and the flow rate derived from it, not the other way
    # round. Sampling Q and D independently produced 17.8 m/s in a 37 mm pipe and
    # a head loss of 2706 m over 296 m of pipe — arithmetically correct and
    # physically absurd, which invites a capable model to argue with the question
    # instead of answering it.
    d = round(rng.uniform(0.05, 0.30), 3)           # m
    v_target = rng.uniform(0.4, 3.5)                # m/s, engineering range
    q = round(v_target * math.pi * d ** 2 / 4, 5)   # m^3/s
    L = round(rng.uniform(20, 400), 1)              # m
    rho = rng.choice([998.0, 1025.0, 880.0])        # kg/m^3
    mu = rng.choice([1.002e-3, 1.5e-3, 8.0e-4])     # Pa.s
    eps = rng.choice([1.5e-6, 4.5e-5, 2.6e-4])      # m
    a = math.pi * d ** 2 / 4
    v = q / a
    re = _reynolds(rho, v, d, mu)
    f = _friction(re, eps, d)
    h = f * (L / d) * v ** 2 / (2 * G)
    return (
        f"Water-like fluid of density {rho} kg/m^3 and dynamic viscosity {mu} Pa.s "
        f"flows at {q} m^3/s through a circular pipe of internal diameter {d} m and "
        f"length {L} m. The pipe wall roughness is {eps} m. Using the Darcy-Weisbach "
        f"equation, with f = 64/Re for Re < 2300 and the Swamee-Jain correlation "
        f"otherwise, compute the head loss along the pipe.",
        h, "m",
        {"area": a, "velocity": v, "reynolds": re, "friction_factor": f},
    )


def pump_power(rng):
    stmt, h, _, w = pipe_head_loss(rng)
    q = w["velocity"] * w["area"]
    rho = float(stmt.split("density ")[1].split(" ")[0])
    eta = round(rng.uniform(0.55, 0.85), 2)
    p = rho * G * q * h / eta
    return (
        stmt + f" Then, given a pump of overall efficiency {eta}, compute the "
               f"shaft power the pump must deliver to overcome that head loss.",
        p, "W", {**w, "head_loss": h, "efficiency": eta},
    )


def terminal_velocity(rng):
    # Parameters constrained so Stokes is ACTUALLY valid, Re < 1. The first
    # version sampled up to 3 mm and 7800 kg/m^3, which gives 33 m/s under a
    # formula that assumes creeping flow — and then penalised a model for
    # noticing. A statement that says "assume Stokes" about a case where Stokes
    # cannot hold is a trap, not a problem. [ran] 2026-09-08
    # Rejection sampling rather than a narrower guess. Tightening the range by
    # eye still produced Re = 1.34 on another seed, which the test caught: the
    # constraint belongs in the sampler, not in the reviewer's judgement.
    for _ in range(200):
        d = round(rng.uniform(2e-5, 2.5e-4), 7)
        rho_s = round(rng.uniform(1100, 2600), 1)
        rho_f = rng.choice([998.0, 1025.0])
        mu = rng.choice([1.002e-3, 1.5e-3, 5.0e-3])
        v = (rho_s - rho_f) * G * d ** 2 / (18 * mu)
        re = _reynolds(rho_f, v, d, mu)
        if re < 0.8:          # margin below 1, so rounding cannot cross it
            break
    else:
        raise RuntimeError("could not sample a case inside the Stokes regime")
    return (
        f"A solid sphere of diameter {d} m and density {rho_s} kg/m^3 settles in a "
        f"quiescent fluid of density {rho_f} kg/m^3 and dynamic viscosity {mu} Pa.s. "
        f"Assuming Stokes flow, compute the terminal settling velocity.",
        v, "m/s", {"reynolds": re, "stokes_valid": re < 1.0},
    )


def venturi_flow(rng):
    d1 = round(rng.uniform(0.08, 0.30), 3)
    beta = round(rng.uniform(0.35, 0.7), 3)
    d2 = round(d1 * beta, 4)
    dp = round(rng.uniform(2000, 60000), 1)
    rho = rng.choice([998.0, 1025.0, 880.0])
    a1 = math.pi * d1 ** 2 / 4
    a2 = math.pi * d2 ** 2 / 4
    q = a2 * math.sqrt(2 * dp / (rho * (1 - (a2 / a1) ** 2)))
    return (
        f"A horizontal venturi meter has an inlet diameter of {d1} m and a throat "
        f"diameter of {d2} m. The fluid density is {rho} kg/m^3 and the measured "
        f"pressure drop between inlet and throat is {dp} Pa. Assuming ideal, "
        f"incompressible, frictionless flow, compute the volumetric flow rate.",
        q, "m^3/s", {"a1": a1, "a2": a2},
    )


def manning_channel(rng):
    b = round(rng.uniform(0.5, 4.0), 2)
    y = round(rng.uniform(0.2, 2.0), 2)
    s = round(rng.uniform(0.0005, 0.02), 5)
    n = rng.choice([0.012, 0.015, 0.022, 0.030])
    a = b * y
    p = b + 2 * y
    r = a / p
    q = (1.0 / n) * a * r ** (2 / 3) * math.sqrt(s)
    return (
        f"A rectangular open channel of bed width {b} m carries a uniform flow at a "
        f"depth of {y} m. The bed slope is {s} and Manning's roughness coefficient "
        f"is {n}. Using Manning's equation in SI units, compute the discharge.",
        q, "m^3/s", {"area": a, "wetted_perimeter": p, "hydraulic_radius": r},
    )


def hydrostatic_force(rng):
    h_top = round(rng.uniform(0.0, 3.0), 2)
    height = round(rng.uniform(0.5, 4.0), 2)
    width = round(rng.uniform(0.5, 5.0), 2)
    rho = rng.choice([998.0, 1025.0, 880.0])
    h_c = h_top + height / 2
    f = rho * G * h_c * width * height
    return (
        f"A vertical rectangular gate {width} m wide and {height} m tall is submerged "
        f"in a fluid of density {rho} kg/m^3, with its top edge {h_top} m below the "
        f"free surface. Compute the magnitude of the resultant hydrostatic force on "
        f"one face of the gate.",
        f, "N", {"centroid_depth": h_c},
    )


# -- held out from training on purpose ----------------------------------------

def drag_force(rng):
    d = round(rng.uniform(0.01, 0.4), 3)
    v = round(rng.uniform(0.5, 25.0), 2)
    rho = rng.choice([1.225, 998.0])
    mu = 1.81e-5 if rho == 1.225 else 1.002e-3
    re = _reynolds(rho, v, d, mu)
    cd = 24 / re if re < 1 else (24 / re) * (1 + 0.15 * re ** 0.687) if re < 1000 else 0.44
    a = math.pi * d ** 2 / 4
    f = 0.5 * rho * v ** 2 * cd * a
    return (
        f"A sphere of diameter {d} m moves at {v} m/s through a fluid of density "
        f"{rho} kg/m^3 and dynamic viscosity {mu} Pa.s. Using Cd = 24/Re for Re < 1, "
        f"Cd = (24/Re)(1 + 0.15 Re^0.687) for 1 <= Re < 1000, and Cd = 0.44 above "
        f"that, compute the drag force on the sphere.",
        f, "N", {"reynolds": re, "cd": cd, "area": a},
    )


def orifice_discharge(rng):
    d = round(rng.uniform(0.01, 0.12), 4)
    h = round(rng.uniform(0.4, 8.0), 2)
    cd = rng.choice([0.60, 0.62, 0.65])
    a = math.pi * d ** 2 / 4
    q = cd * a * math.sqrt(2 * G * h)
    return (
        f"A sharp-edged circular orifice of diameter {d} m is located in the side of "
        f"a large tank, with the free surface {h} m above the orifice centreline. The "
        f"discharge coefficient is {cd}. Compute the volumetric flow rate through the "
        f"orifice.",
        q, "m^3/s", {"area": a},
    )


TRAIN_FAMILIES = {
    "pipe_head_loss": pipe_head_loss,
    "pump_power": pump_power,
    "terminal_velocity": terminal_velocity,
    "venturi_flow": venturi_flow,
    "manning_channel": manning_channel,
    "hydrostatic_force": hydrostatic_force,
}
# Never trained on. The generalisation probe, and this domain's equivalent of the
# clinical suite's inverted-rule split.
HELD_OUT_FAMILIES = {
    "drag_force": drag_force,
    "orifice_discharge": orifice_discharge,
}

INSTRUCTION = (
    "Solve the problem. Work in SI units. Reply with one JSON object and nothing "
    'else: {"answer": <number>}, where <number> is the numeric value in %s.'
)

# THE INSTRUCTION THE DISTILLATION USES, and why it is different.
# The teacher spends about seven hundred characters of reasoning per problem and
# the small model spends none [ran]. Training on the final number alone would ask
# a 3B to guess the result of a five-step chain; the chain is the thing worth
# distilling. So both the corpus and the arms that will be compared against it
# use this instruction, and the baseline is re-measured under it rather than
# borrowed from the JSON-only run.
INSTRUCTION_WORKING = (
    "Solve the problem. Work in SI units. Show your working as a short numbered "
    "chain of steps, each with its intermediate value. Then, on the final line, "
    'give the answer as one JSON object: {"answer": <number>}, where <number> is '
    "the numeric value in %s."
)


def generate(n: int, seed: int, families: dict, style: str = "json") -> list[dict]:
    rng = random.Random(seed)
    names = sorted(families)
    out = []
    for i in range(n):
        name = names[i % len(names)]
        stmt, ans, unit, workings = families[name](rng)
        out.append({
            "case_id": f"phys-{i:04d}", "family": name,
            "prompt": f"{stmt}\n\n"
                      f"{(INSTRUCTION_WORKING if style == 'working' else INSTRUCTION) % unit}",
            "answer": ans, "unit": unit, "workings": workings,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20260908)
    ap.add_argument("--split", default="eval", choices=["train", "eval", "held_out"])
    ap.add_argument("--style", default="json", choices=["json", "working"])
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    fams = HELD_OUT_FAMILIES if args.split == "held_out" else TRAIN_FAMILIES
    rows = generate(args.n, args.seed + hash(args.split) % 1000, fams, args.style)
    text = "\n".join(json.dumps(r) for r in rows) + "\n"
    if args.out:
        open(args.out, "w").write(text)
        print(f"{len(rows)} cases -> {args.out}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
