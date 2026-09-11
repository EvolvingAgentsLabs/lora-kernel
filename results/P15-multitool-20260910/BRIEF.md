# P15 (A) — is a learned protocol worth its weights when the call is not a copy?

**What P13 actually showed.** A learned protocol adapter scored **9/30** where a
hand-written rule scored **23/30** **[ran]**. Read carelessly that kills
`harness.lora`. Read properly it is a statement about the suite: one tool, every
constant already printed in SI, so asking for the tool means copying an expression
the expert has already written — and copying is what ordinary code is for.

**So the suite is replaced, not the adapter.** A statement now says *"water at
20 C"* and *"45 L/s"*. Nothing it needs is printed in SI, and the density is in a
table. Solving one means **choosing** between three tools, **building** keyed
arguments, and reading them out of **prose**:

    1. Flow rate:            <convert>value=45; from=L/s; to=m^3/s</convert>
    2. Density of the fluid: <lookup>fluid=water; property=density; T=20</lookup>
    5. Cross-sectional area: <calc>pi/4 * 0.22**2</calc>

Four families, seven calls per case, three phrasings each. `manning_channel` needs
no fluid property at all, so a model that learns to always look something up pays
for it in the same suite that rewards looking up elsewhere. **The step labels do
not name the tool** — an earlier draft wrote "Flow rate in SI units", which hands
the choice to anything that can read.

The oracle's own chains reach their labelled answers on **400 of 400** cases.

## The bar, measured before the treatment exists

`training/harness/rule_tools.py` is the competitor, written to win: it knows the
label vocabulary, the unit table and the fluid names, and it gets exactly what the
adapter gets — the statement and the step label. On the 1300 tool steps of 400
cases it is right **1208 times, 92.9%** **[ran]**.

**Two rounds of improvement, then stopped, and the second was reverted.** Round
one took it from 90.2% to 92.9% by learning that a keyword usually follows its
number and that "47 cm by 179 cm" names width then height. Round two tried a
different assignment rule and scored 87.4%, so it was undone. The stopping
condition was written before the tuning began, because a competitor polished until
it stops embarrassing the treatment is not a competitor.

Its remaining failures are honest ones and they are concentrated: 63 of 400 venturi
steps and 29 of 200 Manning steps, all of them phrasings where two lengths compete
for one label. `pipe_head_loss` and `hydrostatic_force` it gets perfectly.

## The arms

| # | arm | who writes the `convert` / `lookup` calls |
|---|---|---|
| 1 | **kernel adapter** | the learned protocol, from the statement and the label |
| 2 | **hand-written rule** | `rule_tools.call_for`, the 92.9% bar |
| 3 | **no tool layer** | nobody: the expert answers from memory, with only arithmetic repaired |

`calc` steps are handled identically in every arm — the expert writes the
expression — so the arms differ only in who produces the calls this suite exists
to make hard.

## Falsification, written before the run

**If the kernel adapter does not beat 92.9% on the tool steps, a learned protocol
is not worth its weights even where the call is not a copy**, and `harness.lora`
should be replaced by a rule in the architecture rather than defended.

**And arm 3 is the control that prices the tool layer itself.** If an expert
answering from memory does as well, then neither the adapter nor the rule is
buying anything here and the suite has failed to make tools necessary — which
would be a fault in this material, reported as such.

**Redesign count: 0** for the experiment. The competitor was tuned twice by
design, and both numbers are published.

---

## Outcome (2026-09-11) [ran]

| arm | accuracy | oracle's queries reproduced | queries | rejected |
|---|---|---|---|---|
| **kernel adapter** | **10/30** | **91/96 — 94.8%** | 118 | 19 |
| hand-written rule | 7/30 | 88/96 — 91.7% | 96 | 0 |
| **no tool layer at all** | **27/30** | — | **0** | 0 |

## The question this suite was built for: answered

**A learned protocol beats a hand-written rule where the call is not a copy.**
94.8% against 91.7% on reproducing the oracle's queries, and 10/30 against 7/30 on
the final answer. Both margins are narrow and they point the same way, and the
kernel pays for its lead with 19 rejected calls that the rule cannot produce
because it cannot malform one.

That reverses P13's verdict and locates it: a learned protocol loses to a regular
expression when asking for a tool means copying an expression already written, and
wins when it means choosing between three tools and building keyed arguments out of
prose. **The suite was the thing P13 measured, not the adapter.**

## The question the suite failed: whether a tool layer is worth anything

**The control with no tool layer scores 27 of 30 while asking nothing.** The expert
answers from memory and beats both tool arms by a factor of three.

The cause is the leak this brief named before the run: the domain corpus shows the
table's values, and **seven fluids times two properties is fourteen numbers**, plus
five unit conversions. Six hundred examples is far more than enough to memorise
that. So the tools were never necessary, and adding a tool layer **hurts** — the
queries introduce errors and break chains that memory would have finished.

**A suite whose tool calls are memorisable cannot price a tool layer.** The
kernel-versus-rule comparison survives — both arms ran under identical conditions —
but the headline question this material was built to answer is void.

## What I got wrong, and it is a rule of this project

**The arm that could kill the experiment was bought last.** `CLAUDE.md` says to buy
the killing arm first, and the brief itself flagged memorisation as a known cost.
Ordering it third meant two arms were paid for before learning that the material
could not support them.

## What would fix the material

Make the lookup impossible to memorise rather than merely large: **give each
problem its own handbook**, with properties drawn per case, so the value cannot be
recalled from training and has to be queried. The expert would then know *which*
property it needs — which is the physics — and not *what it is*, which is the
tool's job. That is a change to `multitool.py`, not to the architecture, and it is
the next run rather than a repair of this one.

**Redesign count: 0.** The material's fault is reported, not patched into a
friendlier number.
