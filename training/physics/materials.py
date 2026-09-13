"""A second domain with the same three tools and none of this suite's vocabulary.

WHY IT EXISTS. P21 ended in a tie between a learned protocol and a hand-written
rule. The rule is **144 lines that know fluid mechanics** — its label table keys on
`throat diameter` and `gate width`, its unit table holds litres per second and
millibars, its name matcher expects handbook codes shaped `XJ-7`. The adapter
learned from a corpus containing none of the evaluation families. A tie between
those two is not a tie in kind, and nothing in this repository has measured that.

SO NOTHING HERE LOOKS LIKE FLUID MECHANICS. The substances are alloys and
polymers, the quantities are moduli and coefficients, the units are gigapascals
and square millimetres, the handbook codes are shaped `4419-K`. A rule that scores
here was never suite-specific; a rule that collapses tells us how much of a
hand-written harness is the harness and how much was the suite.

THE TOOLS ARE THE SAME THREE, ON PURPOSE. This measures whether a protocol survives
a change of **subject**, not a change of **interface**. An adapter asked to use
tools with names it was never trained on would be asked to invent, and that is a
different experiment — named as unbought in the brief rather than smuggled in here.

THE STATEMENT CARRIES ITS OWN FORMULA, so no subject expertise is needed from any
arm and the protocol is the only thing being measured.
"""

from __future__ import annotations

import random

# Deliberately unlike `XJ-7`: digits first, one trailing letter. The rule's code
# matcher is `[A-Za-z]{2}-\d{1,2}` and will not see these, which is the point —
# recognising a name is the part of a hand-written harness that is suite-specific.
GRADES = "KLMNPRSTVWZ"

# to SI. None of these units exist in `tools.UNITS`, which is what the rule reads.
UNITS: dict[str, tuple[str, float]] = {
    "Pa": ("stress", 1.0), "kPa": ("stress", 1e3), "MPa": ("stress", 1e6),
    "GPa": ("stress", 1e9),
    "m^2": ("area", 1.0), "mm^2": ("area", 1e-6), "cm^2": ("area", 1e-4),
    "m": ("span", 1.0), "mm": ("span", 1e-3), "cm": ("span", 1e-2),
    "N": ("load", 1.0), "kN": ("load", 1e3), "MN": ("load", 1e6),
    "K": ("interval", 1.0), "degC": ("interval", 1.0),
    "kg": ("mass", 1.0), "g": ("mass", 1e-3), "t": ("mass", 1e3),
}

PROPERTIES = ("modulus", "expansion", "resistivity", "heat_capacity")


def _si(value: float, unit: str) -> float:
    return value * UNITS[unit][1]


def _grade(rng) -> tuple[str, int, dict[str, float]]:
    """A material code and the properties only this problem knows."""
    name = f"{rng.randrange(1000, 9999)}-{rng.choice(GRADES)}"
    t = rng.choice([20, 60, 120, 200, 300])
    props = {
        "modulus": round(rng.uniform(45e9, 410e9), -6),          # Pa
        "expansion": float(f"{rng.uniform(4.1e-6, 2.6e-5):.3g}"),  # 1/K
        "resistivity": float(f"{rng.uniform(1.5e-8, 1.4e-6):.3g}"),  # ohm m
        "heat_capacity": round(rng.uniform(130.0, 1180.0), 1),   # J/(kg K)
    }
    return name, t, props


def handbook_for(name: str, t: int, props: dict) -> dict:
    """Held by the tool, never printed — the same contract P21 settled on."""
    return {(name.lower(), t): dict(props)}


# --------------------------------------------------------------------------
# Each family returns (statement, answer, unit, chain, handbook).
# --------------------------------------------------------------------------

def bar_elongation(rng):
    """dL = F L / (A E). Needs the modulus, a load and an area conversion."""
    name, t, p = _grade(rng)
    lu = rng.choice(["kN", "MN", "N"])
    au = rng.choice(["mm^2", "cm^2", "m^2"])
    f = round(rng.uniform(3, 90), 1)
    area = round(rng.uniform(40, 900), 1) if au != "m^2" else round(rng.uniform(0.002, 0.05), 4)
    span = round(rng.uniform(0.4, 7.5), 2)
    chain = []
    if lu != "N":
        chain.append(("Applied load", "convert", f"value={f}; from={lu}; to=N"))
    if au != "m^2":
        chain.append(("Cross-sectional area", "convert", f"value={area}; from={au}; to=m^2"))
    chain.append(("Elastic modulus of the material", "lookup",
                  f"material={name}; property=modulus; T={t}"))
    chain.append(("Elongation", "calc",
                  f"{_si(f, lu):.6g} * {span} / ({_si(area, au):.6g} * {p['modulus']:.6g})"))
    ans = _si(f, lu) * span / (_si(area, au) * p["modulus"])
    stmt = (f"Elongation equals load times length divided by the product of "
            f"cross-sectional area and elastic modulus. A bar of material {name} "
            f"held at {t} degC is {span} m long with a cross-section of {area} {au}, "
            f"and carries {f} {lu}. Find the elongation.")
    return stmt, ans, "m", chain, handbook_for(name, t, p)


def thermal_growth(rng):
    """dL = alpha L dT. Needs the expansion coefficient and a span conversion."""
    name, t, p = _grade(rng)
    su = rng.choice(["mm", "cm", "m"])
    span = round(rng.uniform(80, 4000), 1) if su != "m" else round(rng.uniform(0.3, 9.0), 2)
    rise = round(rng.uniform(15, 240), 1)
    chain = []
    if su != "m":
        chain.append(("Original span", "convert", f"value={span}; from={su}; to=m"))
    chain.append(("Coefficient of thermal expansion", "lookup",
                  f"material={name}; property=expansion; T={t}"))
    chain.append(("Change in length", "calc",
                  f"{p['expansion']:.6g} * {_si(span, su):.6g} * {rise}"))
    ans = p["expansion"] * _si(span, su) * rise
    stmt = (f"The change in length of a heated member is its expansion coefficient "
            f"times its original span times the temperature rise. A member of "
            f"material {name}, rated at {t} degC, spans {span} {su} and is warmed "
            f"by {rise} K. How much longer does it get?")
    return stmt, ans, "m", chain, handbook_for(name, t, p)


def conductor_resistance(rng):
    """R = rho L / A. Needs resistivity and two conversions."""
    name, t, p = _grade(rng)
    au = rng.choice(["mm^2", "cm^2"])
    su = rng.choice(["m", "cm"])
    area = round(rng.uniform(0.8, 240), 2)
    span = round(rng.uniform(2, 800), 1) if su == "cm" else round(rng.uniform(1.5, 90), 2)
    chain = [("Conductor cross-section", "convert", f"value={area}; from={au}; to=m^2")]
    if su != "m":
        chain.append(("Conductor run", "convert", f"value={span}; from={su}; to=m"))
    chain.append(("Resistivity of the material", "lookup",
                  f"material={name}; property=resistivity; T={t}"))
    chain.append(("Resistance", "calc",
                  f"{p['resistivity']:.6g} * {_si(span, su):.6g} / {_si(area, au):.6g}"))
    ans = p["resistivity"] * _si(span, su) / _si(area, au)
    stmt = (f"Resistance equals resistivity times run length divided by "
            f"cross-sectional area. A conductor of material {name} at {t} degC has "
            f"a cross-section of {area} {au} and runs {span} {su}. What is its "
            f"resistance?")
    return stmt, ans, "ohm", chain, handbook_for(name, t, p)


def heat_to_raise(rng):
    """Q = m c dT. The family with a mass conversion and no length at all."""
    name, t, p = _grade(rng)
    mu = rng.choice(["g", "t", "kg"])
    mass = round(rng.uniform(120, 9000), 1) if mu == "g" else round(rng.uniform(0.4, 18), 2)
    rise = round(rng.uniform(8, 310), 1)
    chain = []
    if mu != "kg":
        chain.append(("Mass of the part", "convert", f"value={mass}; from={mu}; to=kg"))
    chain.append(("Specific heat capacity", "lookup",
                  f"material={name}; property=heat_capacity; T={t}"))
    chain.append(("Heat required", "calc",
                  f"{_si(mass, mu):.6g} * {p['heat_capacity']:.6g} * {rise}"))
    ans = _si(mass, mu) * p["heat_capacity"] * rise
    stmt = (f"The heat needed to warm a part is its mass times its specific heat "
            f"capacity times the temperature rise. A part of material {name}, "
            f"characterised at {t} degC, weighs {mass} {mu} and must be warmed by "
            f"{rise} K. How much heat is needed?")
    return stmt, ans, "J", chain, handbook_for(name, t, p)


FAMILIES = {"bar_elongation": bar_elongation, "thermal_growth": thermal_growth,
            "conductor_resistance": conductor_resistance,
            "heat_to_raise": heat_to_raise}

INSTRUCTION = (
    "Solve the problem. Work in SI units. Show your working as a short numbered "
    "chain of steps, each with its intermediate value. Then, on the final line, "
    'give the answer as one JSON object: {"answer": <number>}, where <number> is '
    "the numeric value in %s."
)


def generate(n: int, seed: int, families: dict | None = None) -> list[dict]:
    fams = families or FAMILIES
    rng = random.Random(seed)
    names = sorted(fams)
    out = []
    for i in range(n):
        name = names[i % len(names)]
        stmt, ans, unit, chain, book = fams[name](rng)
        out.append({"case_id": f"mat-{i:04d}", "family": name,
                    "handbook": [[list(k), v] for k, v in book.items()],
                    "prompt": f"{stmt}\n\n{INSTRUCTION % unit}",
                    "answer": ans, "unit": unit, "chain": chain,
                    "tools_needed": sorted({t for _, t, _ in chain})})
    return out
