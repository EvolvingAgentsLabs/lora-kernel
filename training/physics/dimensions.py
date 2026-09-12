"""Does a chain's arithmetic produce the unit the problem asked for?

WHY THIS IS THE THIRD ATTEMPT AT A BOUNDARY GUARD. A specialist scores 30/30 on its
formulas inside its region and 1/20 outside, with nothing in its prose marking the
difference [ran] `results/P14-held-out-20260910/`. Asking the model how confident it
is was ruled out — the wrong answers read exactly like the right ones. Watching the
tool layer's failures was falsified on families it was not fitted to [ran]
`results/P18-confirm-20260910/`.

What is left is the artefact itself. Outside its region the specialist does not
fail quietly: it **invents relations**. An invented relation is unlikely to be
dimensionally consistent, and dimensional consistency needs no model, no answer and
no threshold:

    6. Drag force F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)
       kg/m^3 · (m/s)^2 / [1]  =  kg/(m·s^2)  — a pressure, where a force was asked

DIMENSIONS ARE ASSIGNED WHERE THEY ARE KNOWN, NEVER GUESSED. A number earns a
dimension from the units printed in the statement, from the handbook the tool holds,
from the SI target of a `convert` call, or from `g`. Anything else is treated as
dimensionless, which is the right reading of `2`, `pi` and `1/3` and the wrong
reading of a constant the model invented — a source of misses, reported rather than
patched around.

TWO LIMITATIONS, NEITHER ENGINEERED AROUND.

*Empirical constants carry units.* Manning's `n` is s·m^(-1/3), so its formula only
types if the statement names the constant. A domain brings its own, and a guard that
does not know them convicts correct work — this is the real cost of the method.

*Numbers are matched by value.* An intermediate that happens to equal a quantity
printed in the statement inherits that quantity's dimension. A channel 2 m wide
whose flow area is also 2 will be typed wrongly, and the guard will be confidently
mistaken about a correct chain. The alternative is symbolic tracking, which is a
different and much larger instrument.

    from training.physics.dimensions import check
    verdict = check(chain_text, expected_unit, statement, handbook)
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from fractions import Fraction

# (kg, m, s) — mass, length, time. Everything this suite touches is mechanical.
#
# EXPONENTS ARE FRACTIONS, NOT INTEGERS. Manning's discharge ends in `R**(2/3)` and
# an integer algebra cannot type it, so the guard abstained on a sixth of the work —
# and the silence was not spread evenly, it was the whole of one family. A rational
# exponent types that step exactly, and `Fraction` compares exactly, so nothing is
# lost to floating point along the way.
Dim = tuple[Fraction, Fraction, Fraction]


def D(kg=0, m=0, s=0) -> Dim:
    return (Fraction(kg), Fraction(m), Fraction(s))


NONE: Dim = D()

UNIT_DIMS: dict[str, Dim] = {
    "m": D(0, 1, 0), "mm": D(0, 1, 0), "cm": D(0, 1, 0), "in": D(0, 1, 0),
    "ft": D(0, 1, 0),
    "m^2": D(0, 2, 0), "m^3": D(0, 3, 0),
    "m/s": D(0, 1, -1), "m/s^2": D(0, 1, -2),
    "m^3/s": D(0, 3, -1), "L/s": D(0, 3, -1), "m^3/h": D(0, 3, -1),
    "L/min": D(0, 3, -1), "gpm": D(0, 3, -1),
    "Pa": D(1, -1, -2), "kPa": D(1, -1, -2), "bar": D(1, -1, -2),
    "mbar": D(1, -1, -2), "psi": D(1, -1, -2),
    "N": D(1, 1, -2), "W": D(1, 2, -3), "J": D(1, 2, -2),
    "kg": D(1, 0, 0), "kg/m^3": D(1, -3, 0), "kg/s": D(1, 0, -1),
    # EVERY SPELLING THE MATERIAL USES. The suite writes `Pa.s`, and a table
    # holding only `Pa s` matched the `Pa` prefix instead — typing a viscosity
    # as a pressure and putting the time exponent out by one, which flagged
    # twenty correct chains [ran] 2026-09-12.
    "Pa s": D(1, -1, -1), "Pa*s": D(1, -1, -1), "Pa.s": D(1, -1, -1),
    "Pa·s": D(1, -1, -1), "Pa-s": D(1, -1, -1),
    "m^2/s": D(0, 2, -1),
    "dimensionless": NONE, "units": NONE, "currency units": NONE,
    "cubic units": NONE, "units per hour": NONE, "dimensionless units": NONE,
}
PROPERTY_DIMS = {"density": D(1, -3, 0), "viscosity": D(1, -1, -1)}

# EMPIRICAL CONSTANTS CARRY UNITS, AND THIS IS THE REAL COST OF THE METHOD.
# Manning's `n` is not dimensionless — it is s·m^(-1/3), which is why
# `Q = (1/n) A R^(2/3) sqrt(S)` looks inconsistent to a naive reading and flagged
# twenty correct chains [ran] 2026-09-12. A dimensional guard for a domain needs
# that domain's constants, exactly as a person checking units by hand would. So the
# guard is not domain-free, and a new domain costs a table this size.
#
# THE STOPPING CONDITION, WRITTEN BEFORE THE ENTRY WAS ADDED: this table is filled
# once, from families already studied, and the confirmation on unseen families runs
# with NO further additions. If it needs another entry there, the approach is
# domain-specific in a way that matters and that is the finding.
NAMED_CONSTANTS = [
    (("manning", "roughness coefficient"), D(0, Fraction(-1, 3), 1)),
]
G = 9.80665

NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"
STEP = re.compile(r"^\s*\d+[.)]\s*(?P<body>.+)$", re.M)
TAGS = re.compile(r"</?(?:calc|convert|lookup)>")
TOOLCALL = re.compile(r"<(calc|convert|lookup)>(.*?)</\1>", re.S)


@dataclass
class Verdict:
    consistent: bool | None      # None: nothing could be typed, so no opinion
    got: Dim | None
    want: Dim | None
    steps_typed: int
    reason: str


def _mul(a: Dim, b: Dim) -> Dim:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _div(a: Dim, b: Dim) -> Dim:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _pow(a: Dim, n) -> Dim | None:
    """Any rational power. `R**(2/3)` of a length is a perfectly good dimension."""
    try:
        k = Fraction(n).limit_denominator(64)
    except (TypeError, ValueError):
        return None
    return (a[0] * k, a[1] * k, a[2] * k)


def known_quantities(statement: str, handbook: dict | None) -> dict[str, Dim]:
    """value-as-written -> dimension, for everything the problem actually states."""
    out: dict[str, Dim] = {f"{G:g}": D(0, 1, -2)}
    units = sorted(UNIT_DIMS, key=len, reverse=True)
    pattern = rf"({NUM})\s*({'|'.join(re.escape(u) for u in units)})\b"
    for m in re.finditer(pattern, statement):
        dim = UNIT_DIMS[m.group(2)]
        if dim != NONE:
            out.setdefault(f"{float(m.group(1)):g}", dim)
    low = statement.lower()
    for names, cdim in NAMED_CONSTANTS:
        where = min((low.index(n) for n in names if n in low), default=None)
        if where is None:
            continue
        # THE NUMBER BESIDE THE NAME, WITH REAL BOUNDARIES. A first version took the
        # first unit-less number in the sentence and matched `1.9` inside `1.96 m`,
        # typing the channel width as Manning's coefficient [ran] 2026-09-12. The
        # constant is the number that follows its own name.
        m = re.search(rf"(?<![\d.])({NUM})(?![\d]|\.\d)", statement[where:])  # a full stop may follow
        if m:
            out.setdefault(f"{float(m.group(1)):g}", cdim)

    for (_fluid, _t), props in (handbook or {}).items():
        for prop, value in props.items():
            if prop in PROPERTY_DIMS:
                out.setdefault(f"{float(value):g}", PROPERTY_DIMS[prop])
    return out


def _eval_dim(node, known: dict[str, Dim]) -> Dim | None:
    if isinstance(node, ast.Expression):
        return _eval_dim(node.body, known)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return known.get(f"{float(node.value):g}", NONE)
    if isinstance(node, ast.Name):
        return NONE                                   # pi, e
    if isinstance(node, ast.UnaryOp):
        return _eval_dim(node.operand, known)
    if isinstance(node, ast.Call):
        # sqrt halves a dimension; log/log10/exp demand a dimensionless argument
        # and a chain that feeds them anything else has already gone wrong, but
        # saying so would need a policy, so it is left untyped.
        args = [_eval_dim(a, known) for a in node.args]
        if any(a is None for a in args):
            return None
        fn = getattr(node.func, "id", "")
        if fn == "sqrt":
            return _pow(args[0], Fraction(1, 2))
        if fn in ("log", "log10", "log2", "exp"):
            return NONE
        return args[0] if args else NONE
    if isinstance(node, ast.BinOp):
        left, right = _eval_dim(node.left, known), _eval_dim(node.right, known)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Mult):
            return _mul(left, right)
        if isinstance(node.op, ast.Div):
            return _div(left, right)
        if isinstance(node.op, ast.Pow):
            # `**(2/3)` IS A DIVISION, NOT A LITERAL. `literal_eval` refuses it, so
            # the step went untyped and the guard abstained on Manning by accident
            # rather than by design [ran] 2026-09-12. Accidental correctness does
            # not survive the next edit, so the exponent is evaluated properly.
            exponent = _number(node.right)
            return _pow(left, exponent) if exponent is not None else None
        if isinstance(node.op, (ast.Add, ast.Sub)):
            # ADDING A LENGTH TO A PRESSURE IS ALREADY THE ERROR. But a chain that
            # adds a typed quantity to an untyped literal is common and innocent,
            # so only a disagreement between two TYPED sides counts.
            if left != NONE and right != NONE and left != right:
                return None
            return left if left != NONE else right
    return None


def _number(node) -> float | None:
    """A constant arithmetic expression, or None. Used only for exponents."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _number(node.operand)
        return None if v is None else (v if isinstance(node.op, ast.UAdd) else -v)
    if isinstance(node, ast.BinOp):
        a, b = _number(node.left), _number(node.right)
        if a is None or b is None:
            return None
        for op, fn in ((ast.Add, lambda x, y: x + y), (ast.Sub, lambda x, y: x - y),
                       (ast.Mult, lambda x, y: x * y),
                       (ast.Div, lambda x, y: x / y if y else None)):
            if isinstance(node.op, op):
                return fn(a, b)
    return None


def _steps(chain: str):
    """(label, expression, value) for each numbered step, tools resolved away."""
    text = TOOLCALL.sub(lambda m: m.group(2), chain)
    for m in STEP.finditer(text):
        body = m.group("body")
        if "=" not in body:
            continue
        lhs, _, rhs = body.rpartition("=")
        value = re.match(rf"\s*({NUM})\s*[.,]?\s*$", rhs)
        expr = lhs.rpartition(":")[2] if ":" in lhs else lhs
        if "=" in expr:
            expr = expr.rpartition("=")[2]
        expr = TAGS.sub("", expr).strip().strip("*_`$ ")
        if expr:
            yield body, expr, (float(value.group(1)) if value else None)


def check(chain: str, expected_unit: str, statement: str,
          handbook: dict | None = None) -> Verdict:
    """Does the last typed step carry the unit the problem asked for?"""
    want = UNIT_DIMS.get(expected_unit.strip())
    if want is None:
        return Verdict(None, None, None, 0, f"unit {expected_unit!r} not in the table")

    known = known_quantities(statement, handbook)
    final: Dim | None = None
    typed = 0
    steps = list(_steps(chain))
    for index, (_body, expr, value) in enumerate(steps):
        # A `convert` step is a definition, not a computation: whatever it returns
        # carries the SI dimension it was asked for. It is also how a millimetre
        # becomes a metre the rest of the chain can use.
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError:
            continue
        dim = _eval_dim(tree, known)
        if dim is None:
            continue
        typed += 1
        # THE VERDICT IS ABOUT THE LAST STEP, NOT THE LAST STEP THAT HAPPENED TO
        # TYPE. Falling back to an earlier one compared an intermediate against the
        # answer's unit and flagged two entire families of CORRECT oracle chains:
        # Manning ends in `R**(2/3)`, which this algebra cannot type, so the verdict
        # was being read off the hydraulic radius — a length, against a flow rate.
        # An untypeable final step is an absence of evidence, and a guard must say
        # so rather than convict [ran] 2026-09-12.
        if index == len(steps) - 1:
            final = dim
        if value is not None and dim != NONE:
            known.setdefault(f"{value:g}", dim)

    if final is None:
        return Verdict(None, None, want, typed, "the final step could not be typed")
    return Verdict(final == want, final, want, typed,
                   "consistent" if final == want else "final unit is not the one asked for")
