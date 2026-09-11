# P21 — a suite where a tool call cannot be remembered

**What P15 proved about itself.** A learned protocol beat a hand-written rule
94.8% to 91.7% where the call is not a copy — and a control with **no tool layer at
all** beat both at **27/30 while asking nothing** **[ran]**. The domain corpus shows
the property table, seven fluids times two properties is fourteen numbers, and 600
examples is far more than enough to memorise them. **A suite whose tool calls can
be recalled cannot price a tool layer**, whoever writes the calls.

**The fix is one line of the material's design.** Each problem carries **its own
handbook**, with the properties drawn per case and printed nowhere the model has
seen before:

    Handbook entry — fluid XJ-7: density 1043.9 kg/m^3, viscosity 2.71e-3 Pa s.

    A gate 47 cm wide and 179 cm tall is submerged in XJ-7, its top edge 1.78 m
    below the surface. Compute the resultant force.

The fluid has a made-up name and values that exist only in this problem. An expert
can still learn **which** property a step needs — that is the physics, and it is
what an expert is for — but it cannot learn **what the value is**, because the
value did not exist during training. Memory is removed by construction rather than
by hoping the table is large.

**The tool changes with it**: `lookup` reads the handbook supplied with the case
rather than a fixed table, and refuses a fluid the handbook does not name.

## The arms, and the killing one is bought first

`CLAUDE.md` says to buy the arm that can kill the experiment first, and P15 is what
ignoring that costs: two arms paid for before learning the material could not
support them.

| # | arm | why it is first |
|---|---|---|
| 1 | **no tool layer at all** | **if this still scores well, the material is still memorisable and the other two are not bought** |
| 2 | hand-written rule writes the calls | the competitor |
| 3 | kernel adapter writes the calls | the claim |

## Falsification, written before the run

**If arm 1 scores anywhere near P15's 27/30, the redesign failed** and the problem
is deeper than a fixed table — the expert would be reconstructing values some other
way, and this whole line of measurement needs rethinking rather than another arm.

**If arm 1 collapses**, the material finally makes tools necessary, and arms 2 and
3 measure what P15 could not: whether a learned protocol is worth its weights when
the answer genuinely is not in the weights.

**Redesign count: 0.** This is a new experiment on new material, not P15 retuned —
P15's numbers stand as published.
