# Architecture

> **Specification.** Nothing here is built. Written to be argued with before it
> is, which is cheaper.
>
> *[Léeme en español](es/ARCHITECTURE.md)*

---

## 1. The stack

```mermaid
flowchart TB
    L1["<b>1 · HOST</b><br>vLLM — one GPU, one resident base model,<br>multi-LoRA serving, adapters batched per request"]
    L2["<b>2 · TARGET</b><br>PHASE A: a frontier model. Verifies, and its agreement is the measurement<br>PHASE B: withdrawn. Replaced by the router alone"]
    L3["<b>3 · KERNEL</b><br>harness.lora — action tokens, tool syntax,<br>state transitions, error shapes. Always loaded"]
    L4["<b>4 · USER SPACE</b><br>the expert pool. Domain QLoRAs, hot-swapped,<br>versioned, scored, promoted, retired"]
    L5["<b>5 · ROUTER</b><br>PHASE A: acceptance rate α, free<br>PHASE B: a small router fitted to the α surface"]
    L6["<b>6 · MEMORY</b><br>markdown + git. Not neural, on purpose"]
    L7["<b>7 · DREAM</b><br>offline: traces → DPO/GRPO dataset → next delta.<br>Tournament, promotion, retirement"]

    L1 --- L2 --- L3 --- L4 --- L5 --- L6 --- L7

    classDef host fill:#F4F3F0,stroke:#C4C4BF,color:#15171B
    classDef target fill:#FDF4E6,stroke:#8A5C10,color:#15171B
    classDef lora fill:#EAF1F9,stroke:#3E52A3,color:#15171B
    classDef open fill:#FCF3F1,stroke:#B0523C,color:#15171B
    classDef text fill:#E7F1EA,stroke:#2E7D4F,color:#15171B
    class L1 host
    class L2 target
    class L3,L4,L7 lora
    class L5 open
    class L6 text
```

**Layers 3, 4 and 7 produce only adapters. Layer 6 produces only text. Layer 1 is
somebody else's runtime.** That is the whole system — and layer 5 is drawn as the
one open box on purpose, because naming the router "speculative" before the α
surface exists would be assuming the result.

## 2. Why the target must be frontier-grade

Speculative decoding emits the *target's* distribution. So what acceptance rate
measures is **agreement with whatever you chose to verify with**, and the choice
therefore decides what the number means:

| target | what a high α tells you |
|---|---|
| the shared base model | this expert has drifted least from the base — *anti-correlated with specialisation* |
| **a frontier model** | **this expert already produces what the frontier would, here** |

The second is a distillation score. It is the design.

This is the single rule that keeps the architecture coherent, and it is why the
frontier is not an optimisation but a component: **remove it in Phase A and the
router is measuring the wrong thing.**

## 3. Frontier withdrawal

The frontier is scaffolding with a stated removal condition.

**Phase A.** Experts draft, frontier verifies, α accumulates per expert per
region of the problem space. Cost is frontier cost; quality is frontier quality;
the measurement is free.

**Phase B.** For a region where an expert's α crossed threshold, promote it from
drafter to generator, drop the frontier, and let the router choose. Cost collapses
to local inference.

**The threshold is a product decision, made on a measured surface.** How much
frontier agreement do you require before an expert answers alone? Per region.
Recorded, revisable, and reversible — a region can be sent back to Phase A when
its verified score drops.

**The number that decides the whole architecture** is the withdrawal gap: the
verified task score after withdrawal, minus the score the frontier had. Making
that gap small *is* the project.

## 4. Composition — kernel plus expert

The kernel and the expert are different adapters and must stay so.

- `harness.lora` owns **how to act**: action tokens, tool syntax, state.
- a domain adapter owns **what is true** in its region.

Merging them would make every domain adapter re-learn the protocol, which is the
cost this design exists to remove. Serving them together is a multi-adapter
composition question and is treated in
[`TECHNICAL-REFERENCE.md` §5](TECHNICAL-REFERENCE.md).


### What is measured, and what is not [ran]

The first half of this section is now a result rather than a claim. A kernel
adapter trained on 600 examples containing **no physics whatsoever** — shop
receipts, means, compound growth, cone volumes — walked into fluid mechanics and
called the tool on **30 of 30** cases, malforming **not one call**, under a prompt
that never mentions the tool. The protocol is learnable in weights of its own and
it transfers to a domain its corpus never contained.
[`results/P8-harness-lora-20260909/`](../results/P8-harness-lora-20260909/BRIEF.md)

The domain half is a result too: with its arithmetic repaired step by step, a
physics expert's chains reach the oracle's answer on **30 of 30** cases while its
raw score is **1 of 30**, with zero tool calls. Its formulas are exact; only its
arithmetic fails. The expert needs delegation and nothing else.
[`results/P9-shared-contract-20260909/`](../results/P9-shared-contract-20260909/BRIEF.md)

**Serving them together is now measured, and it works only one way.** Applying
both at once makes them compete for the same word: stacked they delegate on 5 of
30 cases, disjoint matrices make it worse, and weighting one up deletes the other
**[ran]** `results/P9-…`, `results/P11-…`. **Taking turns removes the competition
entirely** — delegation goes from 0.6 to 4.7 calls per case
**[ran]** `results/P13-sequential-20260910/`. So §5's option 1 is the composition
mode, and the price is two forward passes per step and a runtime that owns the
turn boundary.

**What remains unproven is the kernel's own value.** In a suite with one tool a
thin harness beat the kernel adapter 23/30 to 9/30, because the call was a copy of
an expression the expert had already written. Whether a learned protocol earns its
weights where the call is *not* a copy is being measured, against a hand-written
competitor that scores 92.9%.

**And the expert's region has a hard edge it cannot feel** [ran]
`results/P14-held-out-20260910/`: formulas exact 30/30 inside, 1/20 one family
outside, with nothing in the output marking the difference. Per-region promotion
needs a guard, and the first candidate reads the *tool layer's* rejection rate
rather than the model's confidence.

## 5. The tournament

Per executed task:

```
score = w₁ · verified task success
      + w₂ · α (against the frontier target)
      − w₃ · tokens consumed
```

- **`w₁` must come from a verifier the loop cannot see.** Otherwise the loop
  breeds adapters that flatter their scorer, and the strongest measurement this
  organisation has is that the same procedure was *interface compensation* on one
  model and *persistent gain* on another. **[read]**
- **`w₂` is only meaningful while the target is frontier-grade.** After
  withdrawal it measures agreement with a peer and must be re-weighted or dropped.
- **Offline, always.** A tournament that runs inline changes the thing it
  measures.

Promotion, retirement and crossing are commits: `agentvcs` versions the adapter
alongside the traces and the goal that produced it, so a regression is diffable
and revertible.

## 6. What is not neural, and why that is not aesthetics

**Memory is markdown under git.** A weight delta cannot be read, diffed, cited or
corrected by a person, and it cannot be pointed at in an audit. Every measurement
this organisation has on memory says the durable asset is the part a human can
read.

**Execution is a sandbox.** Tools run as processes.

**Verification is a verifier**, never the model's opinion of itself, and its
strength — exact, deterministic, statistical, human, judge — is recorded with
every result.

## 7. Order of work

| | | gates |
|---|---|---|
| **E0** | headroom on the base alone | everything |
| **E1** | the α surface: 2 experts, 1 frontier target | E2 |
| **E2** | withdrawal: promote, remove the frontier, measure the gap | the product |
| **E3** | `harness.lora` against the −85% schema baseline | the kernel |
| **E4** | the tournament, with a held-out verifier | evolution |

## 8. Deliberately not built yet

- **Tree attention across adapters.** The KV-cache problem is the expensive part
  and it is only worth solving once E1 says the branches are worth comparing.
- **Ten verticals, adapter marketplace, control plane.** Downstream of E2.
- **A new inference runtime.** vLLM is the substrate. Needing our own would be a
  finding, not a plan.
