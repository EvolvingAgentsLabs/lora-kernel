"""Three tools, so that asking for one is a decision rather than a copy.

WHY THIS EXISTS. P13 measured that a learned protocol adapter scores 9/30 where
twenty lines of `re` score 23/30 **[ran]** `results/P13-sequential-20260910/`.
That is not a defeat for `harness.lora` so much as a statement about the suite: it
has exactly one tool, and asking for it means copying an expression the expert has
already written. Copying is what ordinary code is for, and a learned protocol
cannot beat a regular expression at it.

So the suite gains what it was missing. A statement now names its fluid instead of
handing over a density, and gives quantities in whatever unit a person would write
— litres per second, millimetres, kilopascals. Solving it means:

    choosing WHICH tool          convert? look up? compute?
    building keyed ARGUMENTS     `fluid=water; property=density; T=20`
    from PROSE                   "water at 20 C"

None of that is in the transcript to be copied, and a hand-written rule has to
parse the statement to do it — which is exactly the competitor `harness.lora` has
to beat, written and given a fair try rather than assumed away.

THE TOOLS ANSWER, THEY DO NOT GUESS. A lookup for a fluid or temperature that is
not in the table is an error, not an interpolation, and a conversion between
incompatible units is an error, not a silent pass-through. A tool that quietly
returns something plausible turns a model's mistake into a number nobody can see.
"""

from __future__ import annotations

import re

from training.physics.calc import CalcError, evaluate

# Values at 1 atm, from standard engineering tables, rounded to the precision a
# handbook prints. Density in kg/m^3, dynamic viscosity in Pa s.
FLUIDS: dict[tuple[str, int], dict[str, float]] = {
    ("water", 10): {"density": 999.7, "viscosity": 1.307e-3},
    ("water", 20): {"density": 998.2, "viscosity": 1.002e-3},
    ("water", 40): {"density": 992.2, "viscosity": 6.53e-4},
    ("water", 60): {"density": 983.2, "viscosity": 4.67e-4},
    ("air", 20): {"density": 1.204, "viscosity": 1.825e-5},
    ("glycerin", 20): {"density": 1260.0, "viscosity": 1.412},
    ("ethanol", 20): {"density": 789.0, "viscosity": 1.20e-3},
    ("seawater", 20): {"density": 1025.0, "viscosity": 1.07e-3},
    ("sae30 oil", 20): {"density": 891.0, "viscosity": 0.29},
}

# to SI, by dimension. A conversion across dimensions is an error.
UNITS: dict[str, tuple[str, float]] = {
    "m^3/s": ("flow", 1.0), "L/s": ("flow", 1e-3), "m^3/h": ("flow", 1 / 3600),
    "L/min": ("flow", 1e-3 / 60), "gpm": ("flow", 6.30902e-5),
    "m": ("length", 1.0), "mm": ("length", 1e-3), "cm": ("length", 1e-2),
    "in": ("length", 0.0254), "ft": ("length", 0.3048),
    "Pa": ("pressure", 1.0), "kPa": ("pressure", 1e3), "bar": ("pressure", 1e5),
    "psi": ("pressure", 6894.757), "mbar": ("pressure", 100.0),
}

# P25's second domain lives in the same table ON PURPOSE, and it is a concession to
# the competitor rather than to the treatment. The hand-written rule reads `UNITS`,
# so keeping the materials units in a separate module would have handed it a defeat
# it did not earn — it would fail to convert GPa because the table it was given is
# incomplete, not because its 144 lines are suite-specific. The claim P25 tests is
# about vocabulary and labels; the unit table is given away for free.
UNITS.update({
    "MPa": ("pressure", 1e6), "GPa": ("pressure", 1e9),
    "m^2": ("area", 1.0), "mm^2": ("area", 1e-6), "cm^2": ("area", 1e-4),
    "N": ("load", 1.0), "kN": ("load", 1e3), "MN": ("load", 1e6),
    "kg": ("mass", 1.0), "g": ("mass", 1e-3), "t": ("mass", 1e3),
    "K": ("interval", 1.0), "degC": ("interval", 1.0),
})

TOOLS = ("calc", "lookup", "convert")
CALL = re.compile(rf"<({'|'.join(TOOLS)})>(.*?)</\1>", re.S)


class ToolError(ValueError):
    pass


def _args(text: str) -> dict[str, str]:
    """`fluid=water; property=density; T=20` -> a dict, or a ToolError.

    Commas are accepted as well as semicolons, because a model that separates
    arguments the other way has made a formatting choice and not a mistake about
    what it wants — and refusing it would measure punctuation.
    """
    out = {}
    for part in re.split(r"[;,]", text):
        if not part.strip():
            continue
        if "=" not in part:
            raise ToolError(f"argument {part.strip()!r} is not key=value")
        k, _, v = part.partition("=")
        out[k.strip().lower()] = v.strip()
    if not out:
        raise ToolError("no arguments")
    return out


def lookup(text: str, handbook: dict | None = None) -> float:
    """A property, from the handbook this problem carries or the fixed table.

    THE HANDBOOK IS WHY THIS TOOL CAN BE NEEDED AT ALL. With a fixed table of
    fourteen numbers, an expert trained on 600 examples memorises it and beats
    every arm that bothers to query — measured at 27/30 against 10/30 [ran]
    `results/P15-multitool-20260910/`. A handbook drawn per case cannot be
    memorised, because the value did not exist when the expert was trained.
    """
    table = handbook if handbook is not None else FLUIDS
    a = _args(text)
    # `material` is the same argument under the name P25's domain uses for it. The
    # tool's interface does not change between domains — that is what makes P25 a
    # test of subject transfer rather than interface transfer — but refusing a
    # metal called `material=` would be measuring a noun.
    if "material" in a and "fluid" not in a:
        a["fluid"] = a.pop("material")
    missing = {"fluid", "property"} - set(a)
    if missing:
        raise ToolError(f"lookup needs {sorted(missing)}")
    fluid = a["fluid"].lower().replace("_", " ")
    prop = a["property"].lower()
    try:
        t = int(round(float(a.get("t", "20"))))
    except ValueError:
        raise ToolError(f"temperature {a.get('t')!r} is not a number") from None
    if (fluid, t) not in table:
        named = sorted({f for f, _ in table})
        raise ToolError(f"no entry for {fluid} at {t} C; this handbook lists {named}")
    row = table[(fluid, t)]
    if prop not in row:
        # NAMING WHAT IS AVAILABLE, as the not-found branch above already does. An
        # adapter meeting a new domain has to derive the property key from the step
        # label, and refusing it without saying what the keys are measures whether
        # it guessed the noun rather than whether it followed the protocol.
        raise ToolError(f"{fluid} has no property {prop!r}; "
                        f"it has {sorted(row)}")
    return row[prop]


def convert(text: str) -> float:
    a = _args(text)
    missing = {"value", "from", "to"} - set(a)
    if missing:
        raise ToolError(f"convert needs {sorted(missing)}")
    try:
        v = float(a["value"])
    except ValueError:
        raise ToolError(f"value {a['value']!r} is not a number") from None
    src, dst = a["from"], a["to"]
    if src not in UNITS:
        raise ToolError(f"unknown unit {src!r}")
    if dst not in UNITS:
        raise ToolError(f"unknown unit {dst!r}")
    if UNITS[src][0] != UNITS[dst][0]:
        raise ToolError(f"{src} is a {UNITS[src][0]}, {dst} is a {UNITS[dst][0]}")
    return v * UNITS[src][1] / UNITS[dst][1]


def calc(text: str) -> float:
    try:
        return evaluate(text)
    except CalcError as e:
        raise ToolError(str(e)) from e


HANDLERS = {"calc": calc, "lookup": lookup, "convert": convert}


def answer(name: str, body: str, handbook: dict | None = None) -> float:
    if name not in HANDLERS:
        raise ToolError(f"no tool named {name!r}")
    if name == "lookup":
        return lookup(body, handbook)
    return HANDLERS[name](body)


def fill(text: str, handbook: dict | None = None) -> tuple[str, int, int]:
    """Answer every call in a finished chain. Used on the oracle's own chains."""
    calls = fails = 0

    def one(m):
        nonlocal calls, fails
        calls += 1
        try:
            return f"{m.group(0)}= {answer(m.group(1), m.group(2), handbook):.6g}"
        except ToolError:
            fails += 1
            return m.group(0)

    return CALL.sub(one, text), calls, fails
