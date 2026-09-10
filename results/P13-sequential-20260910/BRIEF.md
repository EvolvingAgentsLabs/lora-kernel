# P13 — sequential activation: the two patches take turns instead of competing

**Why this is the experiment that defines the project.** Every measurement so far
says the two halves exist, are healthy alone, and cannot both speak at once:

| | measured |
|---|---|
| kernel alone | calls the tool on **30/30** problems, 7.7 times each, 0 malformed, knows no physics |
| expert alone | formulas exact on **30/30** repaired, **1/30** raw, **0** calls |
| stacked | **4/30**, 0.6 calls per case — the expert wins the format at 25 of 30 steps |
| disjoint matrices | **0/30**, 0.2 calls — worse |
| weighted 1.0/0.5 | **0/30**, 3.5 calls — delegation returns, the expert vanishes |
| merged into one patch | **40/40** — works, at the price the design exists to avoid |

`TECHNICAL-REFERENCE.md` §5 names sequential activation as **option 1 and its own
default**, and it has never been measured. It is the only composition mode left in
which the two patches are never asked to produce the same word.

## The division of labour, and why it is the architecture's own

`ARCHITECTURE.md` §4 gives the expert *what is true* and the kernel *how to act*:

    domain turn   `3. Reynolds number:`                      the PLAN
    kernel turn   ` <calc>998 * 1.17 * 0.22 / 0.0008</calc>` the EXECUTION
    harness       `= 3.21e6`                                 the value

Each turn ends in the format the other patch was trained to continue from, and at
no point are both active. Switching is a pointer, not a load.

## The control that keeps this honest

A harness that could reconstruct the kernel's contribution would make the kernel a
channel nobody needs, and the measurement void however clean the numbers looked.
Here it cannot: **the domain turn stops at the colon, so the expression exists
nowhere until the kernel writes it.** A test asserts exactly that — that nothing
evaluable is in the transcript at the moment the kernel is handed the prefix.

The control arm is therefore a different thing: the expert generating alone with
the harness repairing its arithmetic exactly, which delegates on 100% of steps by
construction and never loads the kernel's weights at all.

## The arms

| # | arm | what it answers |
|---|---|---|
| 1 | **domain plans, kernel executes** | the claim — does taking turns give modular 40/40? |
| 2 | control · domain alone, harness repairs | what the kernel adapter is worth at the delegation point |

## Falsification, written before the run

**If the sequential arm does not raise calls per case far above the stacked 0.6
while keeping accuracy well above the stacked 4/30, taking turns is not the answer
either**, and the only configuration that works stays the merged adapter — which
means every expert must carry the protocol and the tool surface cannot change
without retraining the pool.

**And if arm 1 ties arm 2**, the kernel adapter earns nothing *at the delegation
point in this suite*: the expert plus an exact calculator would be the whole
result, and the modularity the kernel buys would have to be argued somewhere a
single tool and a plain-ASCII expression cannot show it.

**Redesign count: 0.**
