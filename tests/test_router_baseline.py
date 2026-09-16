"""The lexical baseline a learned subspecialty router has to beat.

WHY THIS IS A TEST AND NOT A NOTEBOOK. The number decides whether layer 1 is a model
or a dict, and a number that lives in a chat message cannot be re-run when the
generators change. P1 in the plan — *price the router* — has been open since
2026-09-08 for want of exactly this.

The keywords were written knowing the generators, which makes the baseline GENEROUS.
That is the conservative direction for the conclusion it supports (do not build a
router model yet), so it is stated rather than corrected.
"""

import collections

from training.email.inbox import generate as inbox_gen
from training.physics import ladder
from training.physics import multitool as mod

KEYS = {
    "pipe_head_loss": ("head loss", "friction", "roughness", "bore", "pumped"),
    "hydrostatic_force": ("gate", "plate", "thrust", "submerged", "hydrostatic",
                          "face"),
    "venturi_flow": ("venturi", "throat", "constriction", "manometer"),
    "manning_channel": ("channel", "manning", "slope", "trapezoid", "open channel"),
    "L1_property": ("what is the", "report the", "state its"),
    "L2_pressure": ("gauge pressure",),
    "L3_pressure_converted": ("gauge pressure",),
    "L4_force_on_base": ("flat base", "flat bottom", "horizontal floor", "tank"),
    "email": ("subject:", "preview:", "from:", "is this important"),
}


def guess(text: str) -> str:
    t = text.lower()
    n, fam = max((sum(t.count(k) for k in ks), f) for f, ks in KEYS.items())
    return fam if n else "?"


def _rows():
    rows = [(c["family"], c["prompt"])
            for c in mod.generate(140, 454545, ladder.full_ladder())]
    rows += [("email", f"From: {m['from_name']}\nSubject: {m['subject']}\n"
                       f"Preview: {m['preview']}\n\nIs this important?")
             for m in inbox_gen(60, 99)["messages"]]
    return rows


def test_the_coarse_route_needs_no_model_at_all():
    """Which tool surface to mount — the job layer 4 actually needs."""
    rows = _rows()
    hit = sum(("email" == f) == ("email" == guess(t)) for f, t in rows)
    assert hit / len(rows) == 1.0, (
        f"the coarse baseline moved to {hit}/{len(rows)}; if it has fallen below 1.0 "
        "a learned router becomes worth pricing again")


def test_the_fine_route_baseline_is_the_bar_a_router_model_must_beat():
    rows = _rows()
    hit = sum(guess(t) == f for f, t in rows)
    acc = hit / len(rows)
    # Recorded, not aspirational: 0.845 [ran] 2026-09-16.
    assert acc >= 0.80, f"fine baseline fell to {acc:.3f}"


def test_the_residual_confusion_is_the_depth_boundary_the_band_already_names():
    """L2 and L3 are the same physics; they differ only by a unit conversion.

    So the hard part of fine routing is depth — which is what `contract.band`
    declares and what P45 measured an expert to be locked inside.
    """
    conf = collections.Counter()
    for fam, text in _rows():
        g = guess(text)
        if g != fam:
            conf[(fam, g)] += 1
    pressure = sum(c for (a, b), c in conf.items()
                   if "pressure" in a and "pressure" in b)
    assert pressure > 0, "the L2/L3 confusion vanished — re-read the baseline"
