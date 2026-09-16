"""How well could ANY predictor rank these cases, given only what it can see?

WHY THIS EXISTS. P44 measured the confidence `email-full` attaches to its own
answers and found an AURC gap of **0.400** above the oracle floor — read, per its
pre-registered brief, as *the confidence does not order the errors, so a typed head
is bought* **[ran]**. The brief asked whether the gap was large. It did not ask **how
much of the gap is claimable**, and that turns out to be most of the answer.

On the human subset of the email suite the listing is deliberately uninformative:
whether I wrote in the thread and whether the sender is frequent live behind the
tools, the ask is not in the preview, and `Re:` is random. So the best possible
predictor reading only the listing is a **constant**, and a constant cannot rank —
its gap is **0.311** by construction, against a measured 0.400 **[ran]** 2026-09-16.

**Three quarters of the room P44 reported was a property of the suite.** That is the
ceiling rule from `CLAUDE.md` §3 applied one level up: we check whether *accuracy*
can move and had no way to ask whether *ranking* could.

WHAT THE CEILING IS. Group the cases by what a predictor can actually see. Inside a
group every case looks identical, so the best any model can output is the group's
own base rate — and the AURC of that predictor is the floor of what is achievable,
not of what is achieved. Room is `measured - ceiling`, and it can be zero or
negative; a negative one means the model ranks worse than knowing nothing.

This is cheap, needs no GPU, and it belongs before a calibration arm is bought
rather than after.
"""

from __future__ import annotations

from training.harness.bar import aurc, aurc_floor


def best_possible(groups: list, truth: list[bool]) -> dict:
    """The AURC the ideal predictor reaches when it sees only `groups`.

    `groups[i]` is the signature of everything case `i` reveals — a tuple of the
    visible features, a string, anything hashable. Cases sharing a signature are
    indistinguishable to any model, so the optimal answer is their base rate.
    """
    if len(groups) != len(truth):
        raise ValueError(f"{len(groups)} groups against {len(truth)} labels")
    if not groups:
        raise ValueError("nothing to compute a ceiling over")

    rate: dict = {}
    for g, t in zip(groups, truth):
        n, k = rate.get(g, (0, 0))
        rate[g] = (n + 1, k + bool(t))

    conf, correct = [], []
    for g, t in zip(groups, truth):
        n, k = rate[g]
        p = k / n
        # The ideal predictor answers the majority of its group and reports the
        # mass behind THAT answer, which is what a confidence is.
        said = p > 0.5
        conf.append(p if said else 1 - p)
        correct.append(said == bool(t))

    a, floor = aurc(conf, correct), aurc_floor(correct)
    return {
        "n": len(truth),
        "distinct_groups": len(rate),
        "accuracy": round(sum(correct) / len(correct), 4),
        "aurc": round(a, 4),
        "aurc_floor": round(floor, 4),
        # THE NUMBER THIS MODULE EXISTS FOR.
        "ceiling_gap": round(a - floor, 4),
        # A suite where every case looks the same to the model cannot be ranked at
        # all, and saying so is the point — it is not a small ceiling, it is none.
        "rankable": len(rate) > 1,
    }


def room(measured_gap: float, ceiling_gap: float) -> dict:
    """How much of a measured AURC gap a better model could actually take."""
    # LOWER IS BETTER FOR AN AURC GAP, so `measured - ceiling` is what a better
    # model could still take. The first draft of this reading had the sign
    # backwards and called a model that BEAT the ceiling "worse than knowing
    # nothing" — caught by running it rather than by reading it.
    left = measured_gap - ceiling_gap
    return {
        "measured_gap": round(measured_gap, 4),
        "ceiling_gap": round(ceiling_gap, 4),
        "room": round(left, 4),
        "share_irreducible": (round(min(ceiling_gap / measured_gap, 1.0), 4)
                              if measured_gap > 0 else 1.0),
        "reading": (
            # A model cannot beat the best predictor of what it can see. If it
            # appears to, the GROUPING is wrong — something visible was left out of
            # it — and the ceiling, not the model, is what needs another look.
            "below the ceiling: the grouping omits something the model can see, "
            "so this ceiling is not the right one"
            if left < 0 else
            "at the ceiling — no room for a better model on this input" if left < 0.05
            else f"{left:.3f} of the gap is claimable"),
    }
