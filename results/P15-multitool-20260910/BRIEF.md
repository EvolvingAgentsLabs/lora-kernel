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
