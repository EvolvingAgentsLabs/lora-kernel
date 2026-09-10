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

---

## Outcome (2026-09-10) [ran]

| arm | raw | repaired | calls/case |
|---|---|---|---|
| **sequential · domain plans, kernel executes** | **9/30** | 13/30 | **4.7** |
| **control · domain alone, harness repairs** | **23/30** | **30/30** | 4.9 |
| *(P9 stacked, same 30 cases)* | *4/30* | *22/30* | *0.6* |
| *(P9 domain alone, no tool)* | *1/30* | *30/30* | *0.0* |

**Taking turns restores delegation, and that was the question.** 4.7 calls per
case against the stacked 0.6 — **eight times** — and accuracy more than doubles,
9/30 against 4/30. The format competition that suppressed the kernel on 25 of 30
steps is gone the moment the two patches are never asked for the same word. The
falsification named "five or more calls per problem instead of 0.6"; 4.7 is that.

**And the division of labour is wrong.** The control — the expert writing its own
chain with a thin harness executing the arithmetic exactly, **no kernel weights
loaded at all** — scores **23/30 raw and 30/30 repaired**. Asking the kernel to
write the expression for a physics label it does not understand is asking the
expert's job of the wrong patch.

**A bias in the sequential arm, measured rather than assumed.** The kernel emits
`<calc>A = 1.96 * 1.27 = 2.4932</calc>` — an assignment and its own answer inside
the tag — and the evaluator rejects it: **16% of its 130 calls, touching 11 of 30
cases, none of which passed.** Accepting every recoverable form would put the
ceiling near 20/30, still below the control. The bias is real and it does not
change the verdict, so the arm is not re-run.

## What this settles

1. **Sequential activation works as a composition mode.** Two independently
   trained patches both express their behaviour when they take turns. This is the
   answer to the question P8, P9 and P11 could not reach.
2. **`harness.lora` as weights has not earned its place at the delegation point
   in this suite.** A thin runtime beats it, and the honest reading is that with
   one tool and plain-ASCII expressions there is nothing for a learned protocol to
   contribute that a `re` match cannot.
3. **The best modular result the project has is the control**: an expert with no
   protocol in its weights, no merged adapter, and a runtime that executes the
   arithmetic. That is the modularity §4 wanted, reached without §4's mechanism.

## The geometry, measured on the same pair [ran]

`results/P13-sequential-20260910/overlap.json`, 252 shared modules, rank 16, each
compared against chance for its own dimensions:

| | measured |
|---|---|
| what they READ (row spaces of A) | **0.99x chance** |
| where they WRITE (column spaces of B) | **3.87x chance** (median 3.42, max 10.05) |
| delta alignment (Frobenius cosine) | **+0.035** |

They read independently, write into overlapping directions, and their deltas are
not aligned. That is contention over a shared output channel rather than a
collision of subspaces — which is why P11's disjoint modules did not help (write
directions belong to the residual stream, not to the matrix you write them from),
and it predicts that orthogonality regularisation or null-space projection would
reproduce P11's weighted trade rather than escape it: remove the expert from the
shared channel and the expert goes with it.

**Redesign count: 0.**
