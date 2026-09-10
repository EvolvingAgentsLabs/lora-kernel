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
