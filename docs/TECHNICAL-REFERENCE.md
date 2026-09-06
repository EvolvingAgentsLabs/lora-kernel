# Technical reference

> **Reference for mechanisms that exist; specification for the parts that do
> not.** Every claim about a system outside this repository is marked **[read]**
> and cited. Nothing here has been run.

---

## 1. Speculative decoding, precisely

A small **drafter** proposes `k` tokens. The **target** scores all `k+1`
positions in one forward pass. A rejection-sampling step accepts a prefix of the
draft and resamples at the first rejection.

The construction is chosen so that **the accepted tokens are distributed exactly
as the target would have emitted them**. It is lossless by design, not by
approximation. **[read]**

Two things follow that decide this project's shape:

- **The drafter cannot change the answer.** It changes *when* the answer arrives.
  Two different drafters over the same target produce the same output
  distribution; they differ only in how many forward passes it took.
- **Acceptance rate `α` is a similarity statistic.** It is the expected fraction
  of drafted tokens the target keeps — a measure of *agreement between drafter
  and target*, and therefore of speed. It is not a measure of correctness, and
  no published treatment claims it is. **[read]**

### 1.1 The consequence for expert routing

If experts are drafters and the target is a shared base model, then:

```
argmax_e  α(expert_e, base)   =   the expert that has drifted least from base
```

Fine-tuning a domain adapter moves its distribution *away* from the base — that
is what fine-tuning is. So under a shared base target, **the tournament is
biased against specialisation**, monotonically. The more expert an expert
becomes, the worse it scores on the metric meant to select it.

This is the repository's central finding and it was available before any code.

---

## 2. What would have to change for routing-by-acceptance to work

Exactly one of these:

**(a) The target carries the adapter.** Verify branch `e` under
`base + adapter_e`. Then the emitted tokens really are the expert's, and `α`
measures self-agreement. Cost: **one verification pass per candidate expert**,
so the "free routing in a single forward pass" property is gone. This is a real
architecture; it is just not free.

**(b) `α` turns out to predict quality anyway.** Not by the mechanism above, but
empirically: an expert whose drafts the base accepts may be one whose framing of
the problem the base shares. This is a hypothesis with a plausible null and it is
what [`ARCHITECTURE.md` §4](ARCHITECTURE.md) proposes measuring first.

**(c) A different signal entirely.** Rank by the drafter's own confidence, by a
learned router, or by a cheap verifier. All of these cost something; none is
free in the sense the original idea meant.

---

## 3. Multi-adapter serving — what exists today

| capability | state | source |
|---|---|---|
| Many LoRA adapters over one **target** model, batched | **ships** in vLLM | **[read]** |
| LoRA adapter as the **draft** model | **open RFC**, filed 2026-08-12 | [vllm#52038](https://github.com/vllm-project/vllm/issues/52038) **[read]** |
| Earlier attempt at LoRA + spec-decode | adapter applied to target, **disabled on the draft** | [vllm#11966](https://github.com/vllm-project/vllm/pull/11966) **[read]** |
| Tree-structured draft verification | shipped via EAGLE/Medusa-family drafters | **[read]** |

The RFC's own figures are the reason this is worth tracking: an **r=64** adapter
is roughly **28× smaller** than the 0.8B drafter it replaces, at drafting quality
within about **2%** of a fully-trained per-domain drafter. **[read]**

> **The brainstorm that started this repository asserted the mechanism was
> "totally viable today with vLLM".** It is not; it is three weeks old as a
> proposal. That correction costs nothing now and would have cost a milestone
> later.

---

## 4. Acceptance rate — definition used here

For drafter `d`, target `t`, prompt distribution `P`, draft length `k`:

```
α(d, t) = E_{x~P} [ accepted_tokens(x) / k ]
```

Reported with the draft length it was measured at, because `α` falls as `k`
grows and a number without its `k` is not comparable. Speedup is a function of
`α`, `k` and the drafter/target cost ratio — never of `α` alone.

**What must be reported beside it, always:** the verified task score of the same
configuration. The whole question is whether these two move together.

---

## 5. The harness adapter

A `harness.lora` trained to own the execution protocol rather than the domain:
tool-call syntax, action tokens, state transitions, error shapes.

**The claim to test is narrower than it sounds.** The comparison is not against
"large JSON schemas in the system prompt". It is against **this organisation's
own previous version**: `gemma4nanoloop` binds tools per phase and took peak
schema from **5,548 to 817 tokens, −85%**, with no training at all. **[read]**

So the harness adapter must beat a measured, training-free baseline on:

- **tokens of protocol overhead per call** — the −85% is the number to beat
- **malformed-call rate** — where constrained decoding is the incumbent, not prose
- **latency**, including adapter switch cost

A harness adapter that wins on tokens and loses on malformed calls has not won.

### 5.1 Action tokens

Emitting `<invoke_tool …>` as learned tokens rather than as prose the parser
must recover is the mechanically strongest part of the proposal, because it moves
a *format* guarantee from a prompt into weights. The honest comparison is against
**grammar-constrained decoding**, which already makes malformed output
*impossible* rather than unlikely — and which this organisation has built before:
`token-trie` masks logits so a small model cannot emit invalid syntax. That work
was archived for a reason worth repeating here: **masking logits needs the
sampler, which an API-backed SDK does not expose.** Owning the runtime is what
makes either approach available at all. **[read]**

---

## 6. The KV cache, which is where this gets expensive

Parallel branches from different adapters diverge. Each branch needs its own
key/value state for its own tokens while sharing the prompt prefix.

- Prefix sharing is standard (paged attention).
- Tree attention over one drafter's branches is solved. **[read]**
- **Branches from *different adapters* are the open engineering question** — the
  adapter changes the projections that produce K and V, so the branches do not
  share a cacheable representation the way one drafter's tree does.

This is named as the main cost, not waved at. If §4's experiment says `α` carries
no quality signal, none of this needs solving.

---

## 7. What is deliberately not neural

- **Memory**: markdown files under version control. Readable without the model
  that wrote them, diffable, and citable.
- **Execution**: the sandbox where tools actually run.
- **Verification of task success**: a verifier, never the model judging itself.
  The strength of the verifier (exact / deterministic / statistical / judge) is
  stated, never assumed.
