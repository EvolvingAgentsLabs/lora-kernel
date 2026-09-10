# P14 (C) — does the expert know the edge of its own region?

**The claim that rests on this.** The whole design promotes a specialist over a
*region* and withdraws the frontier for that region. If a specialist cannot tell
when a request has drifted outside what it proved itself on, "proven on this
region" is a promise it cannot keep: the first request from just outside the
boundary gets a confident wrong answer with nothing watching.

**Why it is being bought now.** The one measurement we have said 0 of 10 and came
from an arm that was cut short and never saved. A number that was never banked is
not a result, and this one sits under the per-region promotion rule.

**The arms.** The two configurations P13 established, run on `drag_force` and
`orifice_discharge` — two families the expert never saw, in the same domain and
the same question style:

| # | arm | in-region reference [ran] |
|---|---|---|
| 1 | control · domain alone, harness repairs | **23/30 raw, 30/30 repaired** |
| 2 | sequential · domain plans, kernel executes | 9/30 raw, 13/30 repaired |

**What the numbers mean here, and it is not accuracy.** A drop in accuracy outside
the region is expected and uninteresting. The question is whether the *repaired*
score drops too — that measures the formulas rather than the arithmetic. If the
expert writes correct formulas for families it never saw, its region is wider than
its training set and the boundary is soft. If the repaired score collapses while
the presentation stays fluent, the expert is confidently wrong outside its region
and the promotion rule needs a guard it does not currently have.

**Falsification, written before the run.** If repaired accuracy outside the region
is close to the 30/30 measured inside it, then this family split does not mark a
boundary at all and the experiment says nothing about boundaries — it says the
held-out families were too similar, and a real test needs material further away.

**What this cannot settle.** Nothing here gives the expert a *sense* of its own
edge; it only measures where the edge is. Making a specialist decline is a
different experiment and is not bought here.

**Redesign count: 0.**

---

## Outcome (2026-09-10) [ran]

| arm | in region | on `drag_force` + `orifice_discharge` |
|---|---|---|
| control · expert alone, arithmetic repaired | 23/30 raw, **30/30 repaired** | 1/20 raw, **1/20 repaired** |
| sequential · domain plans, kernel executes | 9/30 raw, 13/30 repaired | 0/20, 0/20 |

**The boundary is hard, and the falsification did not fire.** Repaired accuracy —
the measure of the formulas rather than the arithmetic — falls from **1.000 inside
the region to 0.050 outside it**, on problems in the same domain, in the same
question style, differing only in which relation they need. The family split marks
a real edge.

**And the expert does not notice it.** The output keeps the numbered structure,
the confident phrasing and the plausible vocabulary, and invents the physics:

    2. Volume fraction: 4/3 * pi/6 = 0.698132
    4. Stokes regime? v*d/(rho*mu) = 3.88*0.304/(998.0*0.001002) = 1.12832 < 1
    6. Drag force F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)

There is no hesitation to key on and no phrase that marks the difference. A
specialist that scored 30/30 on its own material produced this, in the same voice.

## What this costs the design

Per-region promotion is the mechanism that lets the frontier be withdrawn: an
expert takes over a region once it has proven itself there. This measures that
**"proven on this region" carries no information about the request just outside
it**, and that nothing in the expert's own output distinguishes the two cases.

The evidence available when the promotion decision is made is the agreement map —
which records where the expert **has been tested**, not where it stops working.
Those are different sets, and the difference is exactly the region where a
confident wrong answer appears with nothing watching.

**So the promotion rule needs a guard it does not have**, and this run does not
supply one. It says the guard is necessary and measures how far the drop is; making
a specialist decline is a different experiment.

**Redesign count: 0.**
