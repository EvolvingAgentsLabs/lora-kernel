# Sequential composition by pipeline, and whether speculative decoding replaces the router

**Analysis, 2026-09-15. Nothing implemented.** Prompted by two questions: can
composition come back if the adapters are *piped* rather than *stacked*, and is
there a case where speculative decoding does the router's job? Both turn out to
have published answers, and one of them is half-built here already.

---

## 0. The concrete problem this has to solve

Today's demo produced the case. `email-full` is served inside OpenClaw with its
tools mounted over MCP; the tools **reach the model** and the model **does not call
them** **[ran]** 2026-09-15:

    54 tools sent, including lora-inbox__thread_history, lora-inbox__sender_stats,
                            lora-inbox__message

The adapter was trained on a surface of **three**, with **unprefixed** names.
`minimal` excludes MCP entirely, `full` sends 54, and an explicit allowlist does not
resolve against MCP tools. **An expert trained on a narrow tool surface is brittle
against a real runtime's broad one** — and that is a routing problem, which is why
these two questions stopped being theoretical this afternoon.

---

## 1. Composition by pipeline: `base→lora1`, then `base→lora2`

### It is not the thing this project dropped

What was dropped on 2026-09-15 was **weight-space composition**: two deltas applied
to the same forward pass, stacked or blended. The reasons were that P8's apparent
interference was void on a notation confound and that P35 measured a real cost to
splitting a capability in two — the vocabulary was learned and asking fell from 123
of 150 cases to 22 **[ran]**.

**Piping is a different object.** `base→lora1` runs to completion, its output
becomes input, `base→lora2` runs to completion. **No two deltas are ever active at
once**, so the interference question does not arise. The thing that made composition
unmeasurable is absent by construction.

### And it costs nothing to serve, because it already works

This is the part worth underlining: **the pool already serves exactly this.** Two
adapters, one resident base, selected by the `model` field of an HTTP request,
measured three times **[ran]** P40/P41/P42 — including with a **stranger's** adapter
alongside ours. A pipeline is two requests with two model names. **There is no
serving work to do.**

The open question is not *can we* but *what orchestrates it*, which is question 2.

### What the literature has

| | what it does | relevance here |
|---|---|---|
| [LoRAuter, arXiv 2601.21795](https://arxiv.org/abs/2601.21795) | training-free adapter routing from task representations, no access to adapter training data, overhead scaling in the number of tasks | **the closest thing to what we need** — routing without training a router |
| [MoLoRA, arXiv 2603.15965](https://arxiv.org/html/2603.15965) | a learned router selects an adapter **per token** | the opposite end from piping; per-token is weight-space, and inherits the question we dropped |
| [Task-Aware LoRA Composition, arXiv 2602.21222](https://arxiv.org/html/2602.21222v1) | fuses adapters at inference via similarity retrieval, no retraining | fusion, i.e. weight-space again |
| [S-LoRA, arXiv 2311.03285](https://arxiv.org/pdf/2311.03285) | thousands of concurrent adapters on one machine | the substrate we already have via vLLM |
| [Cross-model KV-cache reuse, arXiv 2512.17910](https://arxiv.org/html/2512.17910v1) | **58× latency reduction in multi-turn, multi-adapter pipelines** | **directly about the pipeline shape**, and the number is about the cost piping would otherwise pay |

**The honest reading**: piping is not novel and does not need to be. It is the
cheapest arrangement available to us, it is already served, and the published work
that matters is about making it *fast* (KV-cache reuse) rather than making it
*possible*.

---

## 2. Can speculative decoding replace the router?

### The case where it can, and it is a strong one

Speculative decoding runs a **draft** and a **target**; the target verifies tokens
the draft proposed. The acceptance rate is, by construction, *how often the small
model already agreed with the big one* — which is the project's own original
question, asked per token instead of per case.

**Where this replaces routing entirely**: if the target is a larger local model,
every answer has target quality at draft cost, and there is nothing left to route.
No confidence threshold, no escalation rule, no per-case decision — the verification
is the decision, taken token by token.

**And P41 is why that matters.** Per-case escalation delivered **less** than routing
by region (0.378 and 0.689 against 0.775), because the available rules cannot see a
chain that is coherent and wrong, and the one signal that works — agreeing with the
frontier — **requires calling the frontier** **[ran]**. Speculative decoding calls
the bigger model too, but it calls it *cheaply and on every token*, which is the
thing the escalation rules were trying to avoid paying for.

### What the literature has

| | finding | what it means here |
|---|---|---|
| [TaskSpec, arXiv 2505.08600](https://arxiv.org/html/2505.08600v1) | four task-specific drafters, a **learned prompt classifier** picks one; acceptance **16% → 58%** on reasoning, **1.10–2.64×** speedup | **this is our pool, built by someone else.** Task-specific drafters + a router = exactly the architecture, and the acceptance gain is the measured benefit of specialising the drafter |
| [Not-a-Bandit, arXiv 2510.20064](https://arxiv.org/html/2510.20064v1) | provably no-regret **drafter selection** | drafter selection *is* the router; there is a principled formulation to borrow |
| [OmniDraft, arXiv 2507.02659](https://arxiv.org/html/2507.02659v1) | draft and target with **different tokenizers**, via an online n-gram cache plus hybrid distillation; **1.5–2×**, on-device | **attacks constraint C3 head-on** |
| [WhiFlash, arXiv 2606.07710](https://arxiv.org/html/2606.07710v1) | token-level routing across draft paradigms | per-token routing, again the weight-space end |
| [Efficiently aligning draft models, arXiv 2603.09527](https://arxiv.org/html/2603.09527) | **LoRA is used to adapt drafters**; dynamic adapter switching pairs one drafter with any target | the pool as a drafter pool — the same objects, a different job |

**TaskSpec is the most important row.** It reports that a *deterministic classifier*
choosing among task-specific drafters raises acceptance from ~16% to ~58%. That is
the pool thesis with a measured number attached, published by somebody else, and it
is **not** what we measured — we measured delivered accuracy, they measured
acceptance. The two are different claims and the literature has the one we have not
made.

### The constraint that decides whether we can do it at all

**C3: speculative decoding needs a shared tokenizer**, and the plan already records
what that costs us:

- A hosted frontier does **not** share the base's tokenizer and does not return the
  logprobs of a *forced* continuation (C2, C3). So α against it is measured in
  characters — *"sound as a distillation score, unsound as a speedup claim"*.
- **C9 is the reason that surrogate was retired**: identical answers scored 0.00
  across formats and different answers scored 0.44 within one **[ran]**. Character
  agreement is dominated by layout.
- **P4 is the step that dissolves this**, and it predates this analysis: *"the target
  does not have to be an API"* — a same-family target on the same card shares the
  tokenizer, and token-level acceptance becomes measurable for the first time.

**Two corrections to P4 as written, both from things measured since.** It says
*"serve a large Qwen3.5 beside the 2B adapters"*, and (a) the adapters are on
**Qwen2.5-3B** now, so the target has to be a large **Qwen2.5** for the tokenizer to
match, and (b) that a 3B and a 32B of the same family share a tokenizer is
**[read]**, not measured here — it is a one-line comparison of two
`tokenizer.json` hashes and it should be the first thing P4 does, not an assumption
it runs on.

**So the answer is conditional, and the condition is cheap to check rather than
already checked.** OmniDraft says the cross-vocabulary case is attackable if the
check fails; a same-family local target means we probably do not have to.

---

## 3. What this changes, and what it does not

**It does not resurrect weight-space composition.** Nothing here argues the dropped
decision was wrong. Piping avoids the question; per-token routing (MoLoRA, WhiFlash)
walks straight back into it.

**It does give the router a shape and a published baseline.** TaskSpec's classifier
is a deterministic task detector, not a bandit and not a confidence threshold — and
it is exactly the shape the typed-adapter analysis argued for
(`docs/analysis/typed-adapters.md`, H3). **Two independent lines now point at the
same artifact**, which is the strongest argument in this document.

**And it names a measurement we have never made.** Every number in this repository
is *delivered accuracy*. The literature's number for this architecture is
**acceptance rate**, which is cheaper to measure, does not need a verifier, and is
the quantity P32 was designed around and never ran.

---

## 4. What would be worth buying, in order

1. **P4, re-aimed at a large Qwen2.5 and gated on the tokenizer hash.** It is
   already specified and already sequenced; what it needs is the corrected family
   and the one-line check in front of it. It measures **acceptance**, which is the
   literature's own number, needs no verifier, and tells us whether a local target
   makes routing unnecessary rather than merely cheaper.
2. **A tool-surface router, as a pipeline stage.** `base→router` picks three tools
   out of fifty-four; `base→email-full` sees the surface it was trained on. This is
   the concrete blocker from today's demo, it needs no new serving, and LoRAuter is
   the published precedent for doing it without training data.
3. **Nothing per-token, for now.** MoLoRA and WhiFlash are the interesting frontier
   and they are weight-space composition under another name. This project closed
   that question today for reasons that have not changed.

## 5. What this analysis does not claim

- **Not that TaskSpec's 16%→58% transfers.** Different suites, different drafters,
  different base. It is evidence the architecture has been made to work, not a number
  we can quote.
- **Not that piping beats a single expert.** Nothing here measures it. The argument
  is only that it is free to try, which is a statement about cost.
- **Not that speculative decoding is cheaper than the current arrangement.** It is
  cheaper *per token of target quality*; whether that beats "route 38% of cases to a
  frontier" depends on numbers nobody here has.
