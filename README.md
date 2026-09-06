# speculative-experts

**Can a tournament between small experts choose which one is right — for free, in
the forward pass that was going to happen anyway?**

*[Léeme en español](README.es.md)*

> **Status: nothing built, nothing run.** This repository exists to answer one
> question, and it opens with the reason that question is not yet answered:
> the mechanism the idea rests on measures something else.

---

## The idea, as it arrived

Serve one base model. Load many QLoRA adapters — one per expert. When a prompt
arrives, let several adapters draft in parallel, verify all branches in a single
forward pass with tree attention, and **emit the branch with the highest
acceptance rate.** Routing becomes free: the expert is chosen by the same pass
that produced the tokens. Every agent collapses to a weight delta.

It is a beautiful architecture. Two of its three legs hold.

## The leg that does not hold, stated first

**Speculative decoding preserves the target model's output distribution.** That
is not a side effect; it is the entire guarantee — rejection sampling is
constructed so that accepted tokens are distributed exactly as the target would
have emitted them. **[read]**

Three consequences follow, and they are fatal to routing-by-acceptance as
described:

1. **The expert's knowledge never reaches the output.** Whatever the drafting
   adapter knows, the tokens that get emitted are the *target's* tokens. A
   domain adapter used as a drafter makes the answer arrive sooner. It does not
   make it a different answer.
2. **Acceptance rate is a latency metric.** It measures how often the drafter
   guessed what the target was going to say. The literature that formalises
   drafter selection ([Not-a-Bandit, arXiv:2510.20064](https://arxiv.org/abs/2510.20064))
   frames it as a no-regret problem over **speed**, never over quality. **[read]**
3. **So the tournament selects for agreement with the base**, which is the
   opposite of the thing it was meant to find. The adapter that wins is the one
   that has drifted *least* from the base model — the least specialised expert
   in the pool.

There is a second, more ordinary correction. The mechanism is also **not
available today**: vLLM serves many LoRA adapters over one target, but
speculative decoding still requires a separate fully-trained draft model per
domain. LoRA-as-drafter is an open RFC, filed 2026-08-12
([vllm#52038](https://github.com/vllm-project/vllm/issues/52038)); an earlier
attempt applied the adapter to the target and **disabled it on the draft**
([vllm#11966](https://github.com/vllm-project/vllm/pull/11966)). **[read]**

## What survives, and it is the interesting part

The objection kills one mechanism, not the thesis. Three routes remain, and they
are not equally cheap:

| route | what it costs | what it buys |
|---|---|---|
| **Accept losslessness.** Many experts on one base, spec-decoded for speed. | nothing — this ships today, minus the RFC | cost and latency, no capability claim |
| **Break losslessness deliberately.** Put the domain adapter on the *target*, so the emitted tokens are the expert's. | a verification pass per expert — the free routing is gone | real expert output |
| **Keep acceptance rate, but as a *signal* rather than a verdict.** | one experiment | if it works, free routing |

The third is the one worth running, and it reduces to a single empirical
question this repository is built to answer:

> **Does a drafter's acceptance rate carry any signal about whether its expert
> would have produced a better answer — or only about how much it agrees with
> the base?**

If it carries signal, the architecture stands and routing really is free. If it
does not, the router has to be something else, and knowing that costs one
experiment instead of a runtime.

**It is not obvious which way this goes.** A drafter and a target that agree are
representing the problem the same way, and "this expert already thinks like the
model that will judge it" is not nothing. But it is a hypothesis with a plausible
null, which is the only kind worth building an instrument for.

## The falsification condition, written before anything is built

> On a task distribution with **demonstrated headroom**, rank the experts by
> acceptance rate and rank them by verified task score. **If the two rankings
> are uncorrelated, routing-by-acceptance is dead** and this repository says so
> in its README.

The headroom check runs first and is the cheapest arm. A base model already at
the ceiling makes every expert tie, and a tie reads as a success.

## The other two legs

**The harness as an adapter.** Train one `harness.lora` that owns the execution
protocol — tool-call syntax, action tokens, state transitions — so the schema
stops living in the system prompt. This is testable and the baseline is not
"giant JSON schemas": it is **our own previous version**. `gemma4nanoloop`
already took peak schema from **5,548 to 817 tokens (−85%)** by binding tools per
phase, with no training at all. A harness adapter has to beat *that*. **[read]**

**Experts as weight deltas, evolving.** A tournament over adapters, with the
losers dropped and the winners crossed, is a real design — and it inherits a
warning from this organisation's own measurements: the same procedure classified
as *interface compensation* on a 4B model and *persistent gain* on a 12B. Whether
an expert is real is not a property of the expert. An evolutionary loop scored
against one target will breed adapters that flatter that target.

## Lineage

This is the substrate layer under work that already exists, not a restart.

| | |
|---|---|
| [`evolving-agents`](https://github.com/EvolvingAgentsLabs/evolving-agents) | The organisation's active repository, where `ai-os` now lives. Flows, memory at four levels, agents as markdown |
| [`gemma4nanoloop`](https://github.com/EvolvingAgentsLabs/gemma4nanoloop) | The measured case that a small local model runs a closed loop — by subtraction, not by speculation |
| `agentvcs` | Versions code, skills, goals, models and traces together — the substrate for scoring adapters over time |

> *Evolving Agents was the conceptual laboratory for adaptive agents. This is the
> question of whether their selection can happen in the forward pass.*

## Documents

- [`docs/TECHNICAL-REFERENCE.md`](docs/TECHNICAL-REFERENCE.md) — the mechanisms,
  what ships in vLLM today versus what is an RFC, and where the KV cache gets
  expensive.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — the layers, and why the
  **router is drawn as a hole** rather than as a component.
- [`docs/agents-as-weight-deltas.md`](docs/agents-as-weight-deltas.md) — the
  article: the idea, the objection, and what is left standing.

## Acknowledgement

The line of enquiry began with a conversation with **[Ismael Faro](https://github.com/ismaelfaro)**,
who suggested studying speculative decoding and what it could be used for. The
suggestion was right and the first thing the study found was that the obvious use
is not the one that works — which is what makes it worth writing down.

## Convention

**[ran]** — observed here. **[read]** — taken from a source, cited.

There is no **[ran]** in this file. That is what the status line means.

---

<sub>Apache 2.0 · [Evolving Agents Labs](https://github.com/EvolvingAgentsLabs)</sub>
