# Architecture

> **Specification.** Nothing here is built. It is written to be argued with
> before anything is, which is cheaper.

---

## 1. The shape, if the question in §4 comes back positive

```
┌──────────────────────────────────────────────────────────────────────┐
│  HOST            one GPU, one vLLM runtime, one base model resident  │
├──────────────────────────────────────────────────────────────────────┤
│  TARGET          the base model. Verifies. Owns the output           │
│                  distribution — see TECHNICAL-REFERENCE §1           │
├──────────────────────────────────────────────────────────────────────┤
│  KERNEL          harness.lora — tool syntax, action tokens, state    │
│                  transitions. One adapter, always loaded             │
├──────────────────────────────────────────────────────────────────────┤
│  EXPERTS         a pool of domain adapters. Interchangeable, small,  │
│                  versioned, scored                                   │
├──────────────────────────────────────────────────────────────────────┤
│  ROUTER          ← THE OPEN QUESTION. Not assumed to be acceptance   │
│                  rate; that is the thing being measured              │
├──────────────────────────────────────────────────────────────────────┤
│  MEMORY          markdown + git. Not neural, on purpose              │
├──────────────────────────────────────────────────────────────────────┤
│  EVOLUTION       offline: trajectories → dataset → new adapter,      │
│                  scored by a verifier, promoted only if it wins      │
└──────────────────────────────────────────────────────────────────────┘
```

Two layers are drawn deliberately thin. **ROUTER** is a hole, not a component —
naming it "speculative" in the architecture would be assuming the result. And
**EVOLUTION** is offline because a tournament that runs inline changes the thing
it measures.

## 2. Why the router is a hole

Under a shared base target, ranking experts by acceptance rate ranks them by
*similarity to the base*, and fine-tuning moves an adapter away from the base by
construction. The metric is anti-correlated with the property it was meant to
detect, unless something empirical rescues it.

So the architecture carries three router candidates and commits to none:

| candidate | cost per decision | claim |
|---|---|---|
| **acceptance rate** | zero — falls out of a pass already happening | only if §4 finds signal |
| **adapter-on-target** | one verification pass per candidate | correct by construction, not free |
| **learned or cheap router** | one small forward pass | ordinary; the fallback |

A design that had picked one of these before measuring would be three of four
subsystems built on an assumption.

## 3. What the layers owe each other

**The kernel is not an expert.** `harness.lora` owns *how to act*; domain
adapters own *what is true*. Merging them would make every domain adapter
re-learn the tool protocol, which is the cost this design exists to remove.

**The target owns the distribution.** Nothing downstream may claim an expert's
output unless the expert was on the target when the tokens were emitted. This is
the single invariant that keeps the architecture honest, and it is the one the
original idea crossed without noticing.

**Verification is not the model's opinion of itself.** An adapter is promoted
because a verifier accepted its work, and the verifier's strength is recorded
with the result.

**Memory stays outside the weights.** Not aesthetics: a weight delta cannot be
read, diffed, cited or corrected by a person, and everything this organisation
has measured about memory says the durable asset is the part you can read.

## 4. The first experiment, which gates everything else

**E0 · Headroom.** Score the base model, alone, on the task distribution. If it
is at the ceiling or the floor, stop — every expert will tie, and a tie reads as
a success. This arm has killed candidate domains here before.

**E1 · The correlation.** With `n` domain adapters over one base:

1. Measure `α(adapter_i, base)` at a fixed draft length `k`.
2. Measure the **verified task score** of each adapter *used as the target*, so
   its knowledge actually reaches the output.
3. Rank both ways and compare.

> **Falsified if the rankings are uncorrelated.** Then routing-by-acceptance is
> dead, the README says so, and the router becomes the adapter-on-target design
> at its honest price.

**E2 · The harness adapter** *(only after E1 resolves)*. Against
`gemma4nanoloop`'s measured −85% schema reduction, not against a straw baseline.
Three numbers: protocol tokens per call, malformed-call rate, latency including
adapter swap.

**E3 · The tournament** *(only if E1 is positive)*. And with the warning from
this organisation's own results attached: the same procedure classified as
*interface compensation* on a 4B and *persistent gain* on a 12B. An evolutionary
loop scored against one target breeds adapters that flatter that target, so the
fitness function must include a held-out verifier the loop cannot see.

## 5. Deliberately not built

- **Tree attention across adapters.** The KV-cache problem is real and expensive.
  It is only worth solving if E1 says the branches are worth comparing.
- **Ten verticals, adapter marketplaces, a control plane.** Downstream of a
  result that does not exist.
- **A new inference runtime.** vLLM is the substrate. If this needs its own
  runtime, that is a finding, not a plan.

## 6. What would make this whole design unnecessary

Stated plainly, because a design that cannot say this is a design nobody can
argue with:

If a single mid-sized model with a good harness matches a pool of experts on the
task distribution, the pool is machinery for a problem that does not exist. This
organisation has measured something adjacent and uncomfortable: a **feedback
message** moved one model **+30 points** with the information held constant, and
model size was **non-monotonic** across 4B/9B/12B. Capability has not, so far,
lived where the architecture diagram says it should. **[read]**
