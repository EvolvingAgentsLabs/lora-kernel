"""A difficulty ladder for the fluids suite, 1 to 4 steps.

WHY THIS EXISTS. Every number this project has about a small expert on fluids was
measured on a suite whose oracle solutions are **6, 7 or 9 steps long** — and each
family is pinned at exactly one length, so there is no difficulty axis at all
**[ran]** 2026-09-15, `results/P41-routing-20260915/` re-read. The experiment could
therefore only ever ask *can a 3B solve a 6-to-9-step multi-tool chain*. It could
not ask *is a small expert sufficient for the easy end of its own domain*, because
the easy end was never generated.

THAT IS A HEADROOM FAILURE UPSIDE DOWN. This repository's standing rule is to check
the ceiling first: if the baseline already passes everything, every arm ties and the
tie reads as success. The mirror failure has no rule and cost us a conclusion —
**if every task sits above the treatment's floor, every arm fails and the failure
reads as "the approach does not work."** A suite with one difficulty cannot tell
*this expert is too weak* apart from *this suite is too hard*.

SO THE LADDER IS THE INSTRUMENT, NOT A NEW DOMAIN. Same fluids, same three tools,
same per-case handbook that cannot be memorised — only the number of steps changes,
1 → 2 → 3 → 4, below the 6 → 9 the suite already had. What it makes askable is
where a small expert stops being sufficient, with the difficulty set by the problem
rather than by what a frontier model happens to find easy.

THE GATE ON THIS LADDER IS NOT THE FRONTIER'S SCORE. A frontier model answering a
one-step lookup correctly says nothing about whether our expert is usable; the
question is whether the expert clears an **absolute** standard for work at that
level. The frontier is still run, as a **ceiling check** — a rung it does not
itself pass is a broken rung, not a hard one.
"""

from __future__ import annotations


from training.physics.calc import evaluate
from training.physics.multitool import (
    G,
    LEN_UNITS,
    _fluid,
    _si,
    handbook_for,
)

# --------------------------------------------------------------------------
# Each rung returns (statement, answer, unit, chain, handbook), the same shape
# `multitool.generate` already consumes — so the ladder runs through the existing
# runner and scorer, and is not a second instrument to keep honest.
# --------------------------------------------------------------------------


def rung1_property(rng):
    """One step. A single lookup, with nothing to compute.

    It is not trivial only because the fluid is invented per case: the value was
    not in training and is not in the question, so the call has to happen. What it
    tests is whether the expert asks at all, and asks for the right property.
    """
    name, t, rho, mu = _fluid(rng)
    want = rng.choice(["density", "viscosity"])
    unit = "kg/m^3" if want == "density" else "Pa s"
    ans = rho if want == "density" else mu
    stmt = rng.choice([
        f"What is the {want} of {name} at {t} C?",
        f"Report the {want} of {name} held at {t} C.",
        f"A tank holds {name} at {t} C. State its {want}.",
    ])
    chain = [(f"{want.capitalize()} of the fluid", "lookup",
              f"fluid={name}; property={want}; T={t}")]
    return stmt, ans, unit, chain, handbook_for(name, t, rho, mu)


def rung2_pressure(rng):
    """Two steps. Lookup, then one formula: p = rho g h, depth already in metres."""
    name, t, rho, mu = _fluid(rng)
    h = round(rng.uniform(0.6, 12.0), 2)
    p = rho * G * h
    stmt = rng.choice([
        f"Find the gauge pressure {h} m below the surface of {name} at {t} C.",
        f"A tank of {name} at {t} C stands open. What is the gauge "
        f"pressure at a depth of {h} m?",
        f"How much gauge pressure acts at {h} m depth in {name} held at {t} C?",
    ])
    chain = [
        ("Density of the fluid", "lookup", f"fluid={name}; property=density; T={t}"),
        ("Pressure p = rho g h", "calc", f"{rho} * {G} * {h}"),
    ]
    return stmt, p, "Pa", chain, handbook_for(name, t, rho, mu)


def rung3_pressure_converted(rng):
    """Three steps. The same physics, with the depth in a unit that needs converting.

    The one thing it adds over rung 2 is choosing to convert — which is the decision
    `harness.lora` was built for and the smallest place it can be seen.
    """
    name, t, rho, mu = _fluid(rng)
    lu = rng.choice([u for u in LEN_UNITS if u != "m"])
    h_raw = round(rng.uniform(300, 4000), 1) if lu == "mm" else round(rng.uniform(30, 400), 1)
    h = _si(h_raw, lu)
    p = rho * G * h
    stmt = rng.choice([
        f"Find the gauge pressure {h_raw} {lu} below the surface of {name} at {t} C.",
        f"A column of {name} at {t} C is {h_raw} {lu} deep. What gauge pressure "
        f"acts at its base?",
        f"What is the gauge pressure at the bottom of a {h_raw} {lu} depth of "
        f"{name} held at {t} C?",
    ])
    chain = [
        ("Depth", "convert", f"value={h_raw}; from={lu}; to=m"),
        ("Density of the fluid", "lookup", f"fluid={name}; property=density; T={t}"),
        ("Pressure p = rho g h", "calc", f"{rho} * {G} * {h:.6g}"),
    ]
    return stmt, p, "Pa", chain, handbook_for(name, t, rho, mu)


def rung4_force_on_base(rng):
    """Four steps. Convert, look up, pressure, then force on a horizontal base.

    The rung directly below the suite's existing floor of six. A flat base means
    the pressure is uniform, so no centroid is involved — the step the six-step
    `hydrostatic_force` family adds on top of this one.
    """
    name, t, rho, mu = _fluid(rng)
    lu = rng.choice([u for u in LEN_UNITS if u != "m"])
    h_raw = round(rng.uniform(400, 3500), 1) if lu == "mm" else round(rng.uniform(40, 350), 1)
    d = round(rng.uniform(0.4, 3.2), 2)
    h = _si(h_raw, lu)
    p = rho * G * h
    # THE ANSWER IS WHAT THE CHAIN COMPUTES, not a parallel calculation that agrees
    # with it to six figures. The chain writes the pressure as `%.6g` and the force
    # is built from that string, so `f` is the tool's own output — P38's rule, that
    # a corpus must CALL the thing it teaches rather than copy what it prints,
    # applied to the oracle. The first draft computed `f = rho*G*h * pi/4*d**2`
    # directly and disagreed with its own solution by 1.3e-6, which the ladder's
    # test caught **[ran]**.
    _force_expr = f"{p:.6g} * pi/4 * {d}**2"
    f = evaluate(_force_expr)
    stmt = rng.choice([
        f"A cylindrical tank {d} m in diameter holds {name} at {t} C to a depth of "
        f"{h_raw} {lu}. What force does the liquid exert on the flat base?",
        f"Find the total force on the horizontal floor of a {d} m diameter tank "
        f"filled with {name} ({t} C) to {h_raw} {lu}.",
        f"A round tank of diameter {d} m is filled with {name} at {t} C up to "
        f"{h_raw} {lu}. Compute the load carried by its flat bottom.",
    ])
    chain = [
        ("Depth", "convert", f"value={h_raw}; from={lu}; to=m"),
        ("Density of the fluid", "lookup", f"fluid={name}; property=density; T={t}"),
        ("Pressure at the base p = rho g h", "calc", f"{rho} * {G} * {h:.6g}"),
        ("Force F = p A", "calc", _force_expr),
    ]
    return stmt, f, "N", chain, handbook_for(name, t, rho, mu)


LADDER = {
    "L1_property": rung1_property,
    "L2_pressure": rung2_pressure,
    "L3_pressure_converted": rung3_pressure_converted,
    "L4_force_on_base": rung4_force_on_base,
}

# The rung each family sits on, so a sweep can report accuracy against depth
# rather than against a name. The existing families are included because the
# point of the ladder is that they are the top of it, not a different suite.
STEPS = {"L1_property": 1, "L2_pressure": 2, "L3_pressure_converted": 3,
         "L4_force_on_base": 4, "hydrostatic_force": 6, "manning_channel": 6,
         "venturi_flow": 7, "pipe_head_loss": 9}


def full_ladder() -> dict:
    """Every rung, 1 to 9, as one family table."""
    from training.physics.multitool import FAMILIES

    return {**LADDER, **FAMILIES}
