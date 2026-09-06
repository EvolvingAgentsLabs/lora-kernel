# The frontier is scaffolding

*How to distil a frontier model into a pool of small experts without ever running
an evaluation — and then take the frontier out.*

*[Léeme en español](es/the-frontier-is-scaffolding.md)*

---

Ismael Faro suggested I go and study speculative decoding, and see what it could
be used for.

What follows is what that study turned into: an architecture in which **the
entire agentic system is a set of QLoRA adapters over one base model**, the
routing between them costs nothing, and the expensive model you start with is
designed to be removed.

## The setup

Two facts, both ordinary on their own.

**One.** vLLM can hold many LoRA adapters over a single resident base model and
serve them in the same batch. One base in memory, many small deltas, no second
model.

**Two.** Speculative decoding makes generation faster by having a small model
guess ahead. A **drafter** proposes a handful of tokens; a **target** checks them
all in one forward pass; the survivors are kept. And it comes with a guarantee
that is the entire reason anyone uses it: **the tokens that come out are
distributed exactly as the target would have emitted them.** The drafter can make
the answer arrive sooner. It cannot make it a different answer.

Now put those together, and make one choice that decides everything.

## The choice: the target is a frontier model

Let the experts be the drafters, and let the thing that verifies them be a
frontier model.

Three or four domain adapters draft in parallel on the same context. The frontier
model verifies every branch in a single forward pass with tree attention. The
branch it accepts most is the one that gets emitted.

Look at what the acceptance rate now means.

The frontier model is not agreeing with the blandest adapter. It is agreeing with
the adapter that **produced what the frontier itself was about to produce** — in
this domain, on this problem, right now. That is not a speed statistic. That is a
per-region distillation score, and you get it for free, inside inference you were
paying for anyway.

You are not running an evaluation. You are not building a benchmark. You are
serving traffic, and the serving path is quietly filling in a map: *which small
expert can already stand in for the frontier, and where.*

```mermaid
flowchart TD
    P["PROMPT / CURRENT STATE"]
    A["Draft QLoRA<br>clinical-admin"]
    B["Draft QLoRA<br>contract-review"]
    C["Draft QLoRA<br>incident-triage"]
    T["TARGET — FRONTIER MODEL<br>one forward pass, tree attention"]
    W["The branch the frontier accepted most wins<br>the expert that already thinks like the frontier, here"]

    P --> A
    P --> B
    P --> C
    A -- "branch: code this referral" --> T
    B -- "branch: flag this clause" --> T
    C -- "branch: page the on-call" --> T
    T ==> W

    classDef expert fill:#EAF1F9,stroke:#3E52A3,color:#15171B
    classDef target fill:#FDF4E6,stroke:#8A5C10,color:#15171B
    classDef win fill:#E7F1EA,stroke:#2E7D4F,color:#15171B
    class A,B,C expert
    class T target
    class W win
```

Routing, which normally costs a classifier call nobody trusts, costs nothing. The
tokens existed. The pass was happening. The winner is a by-product.

## Then you take the frontier out

This is the part that turns a clever trick into an architecture.

The frontier model is **scaffolding**, and the design says when to remove it.

In **Phase A**, you pay frontier prices and you get frontier answers. The map
fills in. For each region of the problem space, one adapter's acceptance rate
climbs — the frontier keeps agreeing with it.

In **Phase B**, for the regions where an adapter crossed the threshold you chose,
you **promote it from drafter to generator and drop the frontier**. What replaces
the frontier is not another large model. It is **only a router**, fitted to the
acceptance surface Phase A already produced.

```mermaid
flowchart LR
    subgraph PA["PHASE A — the frontier is the target"]
        direction TB
        A1["experts draft"] --> A2["FRONTIER verifies"] --> A3["α accumulates, per region"]
    end
    subgraph PB["PHASE B — the frontier is gone"]
        direction TB
        B1["router selects"] --> B2["EXPERT generates"] --> B3["no frontier call"]
    end
    PA == "withdraw, per region, above your threshold" ==> PB

    classDef a fill:#FDF4E6,stroke:#8A5C10,color:#15171B
    classDef b fill:#E7F1EA,stroke:#2E7D4F,color:#15171B
    class A1,A2,A3 a
    class B1,B2,B3 b
```

|  | Phase A | Phase B |
|---|---|---|
| **cost** | frontier | local |
| **quality** | frontier | at the α threshold you required |
| **what you also get** | a distillation score, free | — |

The threshold is yours to set, per region, on a measured surface: how much
frontier agreement do you demand before a small expert is allowed to answer
alone? And it is reversible — a region whose verified score drops goes back to
Phase A.

There is one number this whole architecture exists to make small: the **withdrawal
gap**, the verified task score after the frontier leaves minus the score it had
while it was there. Everything else is machinery in service of that number.

## The harness is an adapter too, and that is the part I keep coming back to

Everything above is about *which expert answers*. This is about *how any of them
acts at all*, and it is the piece I find hardest to stop thinking about.

A harness today — LangChain, CrewAI, whatever is in your stack — does two things
that are both slightly embarrassing when you say them out loud. It **injects the
tool schemas into the system prompt**, so every single call pays for a JSON
document describing functions the model will mostly not use, and the model's
attention is spread across it. And then it **validates the output afterwards**,
with a parser that is guessing whether the model meant to call a tool, or with a
grammar that constrains the decoder.

The protocol lives in the prompt, which is the most expensive and least reliable
place to put anything.

**So put it in the weights.** Train one adapter — `harness.lora` — on nothing but
the execution protocol:

- tool-call syntax, and **action tokens** emitted natively:
  `<invoke_tool name="sql">`, `<observe>`, `<eval_state>`
- what an API error looks like and what to do about it
- state transitions: when a step is finished, when to hand back, when to stop

It never learns a domain. It learns *how to act*, once, and every expert composes
with it. The domain adapter thinks; the kernel acts.

What that buys, stated as the claim rather than the hope: the schema leaves the
context window entirely, the format stops being something a parser recovers, and
a fleet of twenty experts does not contain twenty copies of the same tool
protocol.

### Why this is more than a token-count optimisation

Here is the part that made me keep turning it over.

**A harness in weights is a harness you can version, score and evolve — like
everything else in the pool.**

Today the harness is code. You cannot cheaply run two of them against the same
traffic and keep the better one; you refactor, you deploy, you hope. As an
adapter it enters the same tournament as the experts, with the same fitness
function and the same held-out verifier. `harness-v3` can lose to `harness-v4` on
malformed-call rate and be retired overnight.

The orchestration layer stops being the one part of the system that cannot
improve by itself.

### And the honest half

The comparison that would flatter this is "look how much smaller the system
prompt is". The comparison that counts is **our own previous result**:
`gemma4nanoloop` bound tools per phase — the model only ever sees the two or
three tools the current phase can use — and took peak schema overhead from 5,548
tokens to 817, a reduction of 85%, **with no training at all.** A harness adapter
has to beat that.

And on syntax the incumbent is not prose, it is grammar-constrained decoding,
which does not make malformed output unlikely — it makes it **impossible**. We
built that too, in `token-trie`, and archived it for a reason that matters here:
masking logits needs the sampler, and an API does not give you the sampler.

Which points at the resolution rather than a contest: they are complementary. The
adapter makes the *right* call likely; the grammar makes the *malformed* call
impossible. Ship both, and measure the adapter on tokens, on malformed-call rate,
and on latency including the cost of swapping it in — winning on the first and
losing on the second is not winning.

## Two kinds of competition, and they are not the same mechanism

The word "compete" hides two different things, and separating them is what makes
the pool tractable.

**Across sub-domains, competition is routing.** `clinical-admin`,
`contract-review` and `incident-triage` draft the same request; one of them is
simply the right expert for it; the acceptance rate says which. This happens
**per request**, in the forward pass, and it is the free part.

**Within one sub-domain, competition is evolution.** Three adapters all trained
for contract review — `contract-v1`, `contract-v2`, `contract-v3` — are not
answering different questions. They are three attempts at the same job, and the
question is which attempt is better. That is not decided per request; it is
decided over hundreds of them, offline, on accumulated fitness:

```
score = w₁ · verified task success
      + w₂ · α (acceptance against the frontier target)
      − w₃ · tokens consumed
```

The worst is retired. The winners' best trajectories become a DPO or GRPO
dataset, and `contract-v4` is trained from them — in the dream pass, over traces
that `agentvcs` versioned alongside the goal and the model that produced them.

Conflating the two is how you get a system that re-decides its architecture on
every request. Routing is a decision about *this* prompt; evolution is a decision
about *the pool*, and it belongs in the night.

## The whole system collapses into adapters

Once the routing is free and the teacher is removable, the rest falls over.

The kernel is an adapter. The experts are adapters. The evolution loop produces
adapters. A clinical coder, a contract reviewer, an incident triager and a
manuscript editor are four files of a few hundred megabytes each, sharing one set
of weights in memory.

Two things stay stubbornly non-neural, and that is deliberate:

**Memory is markdown in git.** A weight delta cannot be read, diffed, cited, or
corrected by a person. Everything this organisation has measured about memory
says the durable asset is the part a human can read.

**Execution is a sandbox.** Tools run as processes.

That is the system. A GPU, a base model, a pool of deltas, a text repository, and
a sandbox. The multi-agent framework — the Python orchestrating API calls, the
router model, the schema injection, the retry logic — is gone, because it turned
into weights.

## What has to be true, and what it costs

I want to be precise about the state of the ground, because the appeal of an idea
is not the same as its availability.

**Multi-LoRA serving over one target ships today.** Tree-structured draft
verification ships today. **LoRA-as-drafter does not yet** — it is an open vLLM
RFC, filed on 12 August 2026. Until it lands, Phase A runs with adapters applied
to drafter models outside vLLM's speculative path, or with small per-domain
drafters: more memory, identical experiment.

The RFC is also the best argument for the economics: an **r=64 adapter is about
28× smaller** than the 0.8B drafter it replaces, at drafting quality within
roughly **2%** of a fully-trained per-domain drafter. That ratio is why a pool of
twenty experts is a reasonable thing to hold in memory.

**The genuinely hard part is the KV cache.** Branches from one drafter share a
representation you can cache — that is what tree attention exploits. Branches
from *different adapters* do not, because a LoRA changes the projections that
produce K and V. Prefix sharing is standard; cross-adapter branch sharing is the
open problem. It is worth solving once the first acceptance surface says the
branches are worth comparing, and not before.

## Two things I am carrying in from measurements that were not kind

**Owning the runtime is what makes any of this available.** Both halves of the
harness argument above — the adapter and the grammar — need the sampler, and an
API does not hand you the sampler. That is the same wall `token-trie` hit.

**The tournament can breed flattery.** The same procedure, the same text, the
same rule, once classified as *interface compensation* on a 4B model and as
*persistent gain* on a 12B. Whether an expert is real is not a property of the
expert — it is a property of the pair. So the fitness function's task-success
term has to come from a verifier the loop cannot see, or the loop will
enthusiastically evolve adapters that agree with their scorer and know nothing.

## What runs first

A headroom check, because a base model already at the ceiling makes every expert
tie and a tie reads as a success.

Then two domain adapters and one frontier target, to produce the first acceptance
surface — Phase A in miniature.

Then the withdrawal, and the number that decides everything: how much verified
quality is lost when the frontier walks away.

---

*The repository is [`lora-kernel`](https://github.com/EvolvingAgentsLabs/lora-kernel).
Nothing is built yet.*

*Thanks to [Ismael Faro](https://github.com/ismaelfaro), who suggested studying
speculative decoding — and whose suggestion turned out to be about distillation.*
