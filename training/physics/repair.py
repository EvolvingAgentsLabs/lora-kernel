"""Score the physics an expert knows, separately from the arithmetic it botches.

THE MEASUREMENT THIS REPLACES. P6 established that a distilled expert reproduces
the teacher's chain step for step and still fails, because it computes
pi/4 * 0.22**2 as 0.037006 rather than 0.038013 **[ran]**. Scoring only the final
number therefore reports "does not know fluid mechanics" for a model that knows
the formula and cannot multiply. Every claim about what a domain adapter
contributes to a composition depends on telling those two apart, and P8 never
did: its domain arm emitted no chain at all, so its physics was never measured.

WHAT THIS DOES. It walks the chain in order, re-evaluates each step's expression
with the exact evaluator, and **carries the corrected value forward** — replacing
the model's own claimed value wherever a later step reuses it. What comes out is
the answer the model's formulas imply, with its arithmetic repaired. If that
lands on the oracle's answer, the physics was right and only the arithmetic was
wrong, which is precisely the failure a tool call fixes.

It is not a scoring loophole: it is applied to the arms that are NOT allowed a
tool, and reported beside their raw score, never instead of it.
"""

from __future__ import annotations

import re

from training.physics.calc import CalcError, evaluate

# `3. Hydraulic radius R = A/P: 2.4892 / 4.5 = 0.553133`
#                               ^^^^^^^^^^^^   ^^^^^^^^
# The expression is what sits between the last colon and the last `=`.
STEP = re.compile(r"^\s*\d+[.)]\s*(?P<body>.+)$", re.M)
NUM = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"


def _split(body: str) -> tuple[str, str | None] | None:
    """(expression, the value the model claimed, AS WRITTEN), or None.

    The literal matters. Reformatting the claim to `%.6g` turned a model's "2.0"
    into "2", and substituting "2" into a later "2.0 * 10" produced "2.4892.0 * 10"
    — a repair that manufactured a syntax error out of a correct chain.
    """
    if "=" not in body:
        # A STEP THAT CLAIMS NO VALUE IS STILL A FORMULA. The formula-only corpus
        # writes `3. Resultant force: 880.0 * 9.80665 * (2.58 + 1.32/2)` and stops,
        # because producing the number is the kernel's job. Scoring that as "no
        # chain" would make the expert unmeasurable on exactly the corpus written
        # to fix its behaviour.
        expr = body.rpartition(":")[2] if ":" in body else body
        expr = expr.strip().strip("*_`$ ")
        return (expr, None) if expr else None
    lhs, _, rhs = body.rpartition("=")
    m = re.match(rf"\s*({NUM})\s*[.,]?\s*$", rhs)
    if not m:
        return None
    expr = lhs.rpartition(":")[2] if ":" in lhs else lhs
    # Drop a leading `Q ` or `R = A/P` style symbolic restatement: keep the part
    # after the last `=` that still has arithmetic in it.
    if "=" in expr:
        expr = expr.rpartition("=")[2]
    expr = expr.strip().strip("*_`$ ")
    return (expr, m.group(1)) if expr else None


# A CHAIN THAT DELEGATED ALREADY HAS EXACT ARITHMETIC. `1. area: <calc>e</calc>= v`
# carries the same expression and the harness's own value, so the tags are removed
# and the line reads like any other — after which `repaired` equals the raw score
# for a tool-using arm instead of reading 0 by construction, which is what it did
# on P9's kernel arm and would have looked like a finding.
TAGS = re.compile(r"</?calc>")


def repair(text: str) -> tuple[float | None, int, int]:
    """(answer the formulas imply, steps repaired, steps the evaluator rejected).

    Returns None when no step in the chain could be evaluated at all — a model
    that writes prose without arithmetic has no formulas to score.
    """
    fixed: list[tuple[str, str]] = []      # (claimed as written, corrected)
    last: float | None = None
    ok = bad = 0
    for m in STEP.finditer(TAGS.sub("", text)):
        parsed = _split(m.group("body"))
        if parsed is None:
            continue
        expr, claimed = parsed
        # A later step that reuses an earlier value must reuse the CORRECTED one,
        # or the repair only fixes the last multiplication in the chain. The
        # boundaries stop "2" from matching inside "2.0" or "12".
        for was, now in fixed:
            if was is not None:
                expr = re.sub(rf"(?<![\d.]){re.escape(was)}(?![\d.])", now, expr)
        try:
            value = evaluate(expr)
        except CalcError:
            bad += 1
            continue
        ok += 1
        last = value
        if claimed is not None:
            fixed.append((claimed, f"{value:.6g}"))
    return (last if ok else None), ok, bad
