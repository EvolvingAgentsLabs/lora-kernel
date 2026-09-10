"""The hand-written rule the learned protocol has to beat.

WHY IT IS WRITTEN AT ALL. P13's verdict was that a learned protocol lost to twenty
lines of `re`, and the reason was a suite where the call was a copy. The multi-tool
suite removes the copying — but a claim that a learned protocol now wins is worth
nothing unless the rule is actually built and given a fair try. A comparison
against a competitor nobody wrote is not a comparison, and it is the failure mode
that has already cost this project two routing results.

So this is written to win. It knows the label vocabulary, it knows the unit table,
it knows the fluid names, and it gets the same input the adapter gets: the problem
statement and the label of the step being solved.

TWO ROUNDS OF IMPROVEMENT, THEN STOPPED — and the second was reverted. Round one
took it from 90.2% to 92.9% on the tool steps by learning that a keyword usually
follows its number and that "47 cm by 179 cm" names width then height. Round two
tried assigning every quantity to its own nearest keyword and scored **87.4%**, so
it was undone. The stopping condition was written before the tuning started,
because a competitor polished until it stops embarrassing the treatment is not a
competitor. **The bar is 92.9%.**

WHAT IT CANNOT DO, AND WHY THAT IS FAIR. It has no physics, so on a step that needs
an expression it returns None and the expert writes that step — exactly as it does
in the adapter arm. The two arms differ only in who produces the `convert` and
`lookup` calls, which is the part this suite exists to make hard.
"""

from __future__ import annotations

import re

from training.physics.tools import FLUIDS, UNITS

NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
FLUID_NAMES = sorted({f for f, _ in FLUIDS}, key=len, reverse=True)
FLOW = [u for u, (dim, _) in UNITS.items() if dim == "flow"]
LENGTH = [u for u, (dim, _) in UNITS.items() if dim == "length"]
PRESSURE = [u for u, (dim, _) in UNITS.items() if dim == "pressure"]

# label keyword -> (dimension, words that sit near the quantity in the statement)
NEAR = [
    ("flow rate", "flow", ()),
    ("pressure drop", "pressure", ()),
    ("inlet diameter", "length", ("inlet",)),
    ("throat diameter", "length", ("throat",)),
    ("pipe diameter", "length", ("diameter", "across", "bore")),
    ("gate width", "length", ("wide", "width")),
    ("channel width", "length", ("wide", "width")),
    ("gate height", "length", ("tall", "high")),
    ("flow depth", "length", ("deep", "depth")),
]


def _units_for(dim: str) -> list[str]:
    return {"flow": FLOW, "length": LENGTH, "pressure": PRESSURE}[dim]


def _quantities(statement: str, dim: str) -> list[tuple[float, str, int]]:
    """Every (value, unit, position) in the statement with a unit of `dim`."""
    units = sorted(_units_for(dim), key=len, reverse=True)
    pattern = rf"({NUM})\s*({'|'.join(re.escape(u) for u in units)})\b"
    return [(float(m.group(1)), m.group(2), m.start())
            for m in re.finditer(pattern, statement)]


def _fluid_and_temperature(statement: str) -> tuple[str, int] | None:
    low = statement.lower()
    name = next((f for f in FLUID_NAMES if f in low), None)
    if name is None:
        return None
    m = re.search(rf"({NUM})\s*C\b", statement)
    return name, int(round(float(m.group(1)))) if m else 20


def _pick(statement, label, qs, near):
    """Which of several quantities the label means.

    THE KEYWORD USUALLY FOLLOWS THE NUMBER, not surrounds it: "192.6 mm inlet".
    A symmetric distance picked the throat for the inlet in every venturi phrased
    that way, so a keyword sitting just after a quantity counts for much more than
    one sitting just before it.

    AND "47.1 cm by 179.4 cm" NAMES NEITHER. English convention puts width first
    and height second, and a rule written by a person would use that rather than
    give up — so it does.
    """
    low = statement.lower()
    if re.search(rf"{NUM}\s*\w+\s+by\s+{NUM}", low) and len(qs) >= 2:
        want_second = any(w in label.lower() for w in ("height", "depth", "tall"))
        return qs[1] if want_second else qs[0]

    def cost(q):
        _, _, pos = q
        best = 10 ** 6
        for w in near:
            for m in re.finditer(rf"\b{re.escape(w)}\b", low):
                d = m.start() - pos
                best = min(best, d if d >= 0 else 3 * -d)   # after >> before
        return best
    return min(qs, key=cost)


def call_for(statement: str, label: str) -> str | None:
    """The tool call this step needs, or None when only physics can write it."""
    low = label.lower()

    if "densit" in low or "viscosit" in low:
        found = _fluid_and_temperature(statement)
        if found is None:
            return None
        name, t = found
        prop = "density" if "densit" in low else "viscosity"
        return f"<lookup>fluid={name}; property={prop}; T={t}</lookup>"

    for key, dim, near in NEAR:
        if key not in low:
            continue
        qs = _quantities(statement, dim)
        if not qs:
            return None
        if len(qs) == 1:
            v, u, _ = qs[0]
        else:
            v, u, _ = _pick(statement, label, qs, near)
        target = {"flow": "m^3/s", "length": "m", "pressure": "Pa"}[dim]
        if u == target:
            return None            # already SI: nothing to convert
        return f"<convert>value={v:g}; from={u}; to={target}</convert>"

    return None                    # a calc step: the expert writes it
