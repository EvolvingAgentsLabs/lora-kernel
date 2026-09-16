# Four layers, and which of them is already a dict

**Analysis, 2026-09-16.** Prompted by the worry: *with many experts, evaluating all
of them to pick a speculative drafter is not efficient — so how do we decide which
experts to evaluate?* Proposed shape: (1) a subspecialty router, (2) optional
structural tokens added to the input, (3) today's domain sub-experts, with the layer-1
router naming the speculative **candidates**, (4) a layer activating only the
tool-generating experts for the chosen subspecialty.

**The worry is correct and it is the published field's own problem.** It is also,
for the layer that matters most today, cheaper to answer than it looks.

---

## 1. Layer 1, priced before it is built

The cheapest possible competitor to a learned router is a keyword rule. Twelve lines
of it, over 140 fluids cases spanning all seven ladder depths plus 60 email listings:

| question | what it decides | lexical baseline |
|---|---|---|
| **coarse** — which suite | **which tool surface to mount** | **1.000** |
| fine — which family | which drafter to prefer | 0.845 |

**[ran]** 2026-09-16, n = 200.

**The coarse job does not need a model.** It is perfect with keywords, and it is
exactly the job layer 4 needs — pick the tool surface. A learned router for it is
unbuyable.

**The fine job has a baseline of 0.845**, and the residual confusions are not noise:

    L2_pressure           -> L3_pressure_converted   7
    L1_property           -> L4_force_on_base        7
    L2_pressure           -> L4_force_on_base        7

`L2` and `L3` are **the same physics**; they differ only in whether a unit needs
converting. That is the *depth* boundary, and P45 showed depth is exactly what an
expert is locked to **[ran]**. So the hard part of fine routing is the part the
contract's `band` field already names, and a rule that reads the units in the
statement would take most of it.

> A caveat that makes the number stronger, not weaker: these keywords were written
> knowing the generators. That makes the baseline **generous**, which is the
> conservative direction for the conclusion *don't build a router model yet*.

---

## 2. Layers 1 and 4 are one artifact

Layer 1 asks *which subspecialty*. Layer 4 asks *which tools to expose for that
subspecialty*. That is one decision taken once, with two consumers — and merging
them is the difference between a stage and a pipeline of stages.

**It is also the live product blocker.** The OpenClaw demo put **54** tools with
prefixed names in front of an expert trained on **3**, and it called none **[ran]**
2026-09-15. A layer that narrows the surface by subspecialty is the fix, it needs no
new serving (the pool already selects by model name, measured three times), and its
routing job is the one scoring **1.000** above.

**And the contract already gives it a second job.** `contract.accepts(record, steps)`
exists since 2026-09-15: a member declares the band it was trained on, so this layer
can **refuse** an expert work outside its band instead of letting it over-solve. P45
is the evidence — below its band `fluids-full` invented an area on 18 of 18 cases.

---

## 3. Layer 2 is a corpus change, and the one precedent we have is negative

Adding structural markers — *problem starts here, context here, these are the
variables* — is not an input-side change in this repository. It is a change to the
prompt every expert was trained against, and that has a measured price:

- **P38.** A corpus that drifted from the served prompt produced **71 refusals of 606
  calls that looked like physics** and voided a whole run **[ran]**. The rule since:
  a corpus must teach the prompt the model will be served.
- **P28.** The one time extra structure was declared to the model — allowed values on
  a tool parameter — it was **harmful**: it fixed what it aimed at and made handbook
  misses rise **3 → 17**, because telling the adapter part of the vocabulary changed
  what it did elsewhere **[ran]**.

So layer 2 means retraining every expert whose corpus lacks the markers, and the
closest thing to prior evidence says the effect can be negative.

**The cheap version, if it is wanted:** plain-text markers, no new token ids, no
embedding resize, on **one** expert, scored against that expert's existing corpus as
an A/B. If it helps without retraining, it is free. If it only helps after
retraining, it is a corpus purchase and should be bought once and measured, not
adopted across the pool.

---

## 4. Layer 3: the selection problem is real, and not yet live

**Speculative decoding only pays against a bigger target.** A 3B drafting for a 3B
buys nothing — the acceptance is 1.0 and so is the cost. It needs a large
same-family target, which is **P4**, still unbought, and whose shared-tokenizer
premise is `[read]` rather than measured
([`composition-and-speculative.md`](composition-and-speculative.md)).

**One piece of good news, and it is structural.** Every adapter here sits on one
resident base, so **they all share its tokenizer** — any member can draft for any
other without the cross-vocabulary machinery OmniDraft exists to provide. The
drafter/target pairing is unconstrained. That is a property of the pool design rather
than something we would have to buy.

**And the field's answer to the worry is: do not evaluate all of them.**

| | what it does | relevance |
|---|---|---|
| [TaskSpec, 2505.08600](https://arxiv.org/html/2505.08600v1) | a prompt classifier picks among four task-specific drafters; acceptance **16% → 58%** | this is layer 1 → layer 3 exactly, published |
| [Not-a-Bandit, 2510.20064](https://arxiv.org/html/2510.20064v1) | provably no-regret **drafter selection** | the principled form of "which candidates" |

TaskSpec's classifier is a *deterministic* selector, not a search, and explicitly
does **not** use acceptance rate as the routing signal. Our 0.845 lexical baseline is
the number a learned version of it would have to beat.

---

## 5. The efficiency answer, concretely

The worry is *k experts means k evaluations*. It does not have to.

> **k typed questions about one context cost one prefill, not k.** Prefill the shared
> context once, repeat the KV cache across k branches, run one batched forward, and
> slice each branch's logits to its own candidate ids.

Recorded in [`constrained-decoding.md`](constrained-decoding.md) from reading a
third-party engine. Asking *which of twenty experts?* is then one forward pass and
twenty logit slices — not twenty runs. It is the same economy the cross-model
KV-cache work reports at 58× on multi-adapter pipelines.

**So the cost of many experts is not the routing. It is the corpora** — N experts is
N corpora and N chances at P38's drift, which is where this project has actually been
hurt.

---

## 6. What to do, in order

1. **Merge layers 1 and 4 and build that.** It is the live blocker, its routing
   question scores 1.000 with keywords, it needs no new serving, and the contract's
   `band` gives it a refusal rule. **Start as a dict, not a model.**
2. **Layer 3 after P4.** The selection problem is real but it has no target to draft
   for yet. When it does, the pairing is unconstrained because the pool shares a
   tokenizer, and the literature says pick with a classifier rather than evaluate all.
3. **Layer 2 only as a measured A/B on one expert.** The only prior evidence here is
   negative, and adopting it across the pool means retraining everything.

## 6b. Do the three payoffs survive the layering?

The question is whether stacking layers still pays off in **speculative decoding**,
in **QLoRA cheapness**, and in **having many experts** — over one base model.
Taking them one at a time, because two survive and one is conditional.

### One base across every layer — this is the load-bearing property, and it gets better

Every member sits on one resident base, selected by the `model` field of an HTTP
request; measured three times, including with a stranger's adapter beside ours
**[ran]** P40/P41/P42. So *k* layers × *m* experts is `k·m` **rank-16 deltas over one
set of base weights** — roughly 100 MB each, not 6 GB each.

**More layers make this argument stronger, not weaker.** A layer whose expert is a
separate model would multiply the resident cost; a layer whose expert is an adapter
adds a rounding error. The whole thesis is that the system is a pool of adapters over
one base, and layering is the first structure that actually needs many of them.

> **The unmeasured thing, and it is the only real risk in this answer: we have never
> served more than TWO adapters at once.** `--max-loras` has only ever been 1 or 2
> here. S-LoRA reports thousands on one machine **[read]**; whether *our* stack holds
> latency at ten or twenty is a guess. It is also a **cheap test** — load ten copies
> of the two adapters we have under ten names and watch tokens/s. No training, no new
> corpus, one short session.

### Many experts — the layering *reduces* how many have to be trained

This is the part that inverts the worry. A layer is cheap when it is a **rule** and
expensive when it is an **expert**, and §1 measured which is which:

| layer | job | what it has to be |
|---|---|---|
| 1 · subspecialty | which suite | **a dict** — 1.000 lexically |
| 2 · structural tokens | prompt shape | a prompt change, if anything |
| 3 · domain sub-experts | the work | **an expert** |
| 4 · tool surface | which tools to expose | **a dict** — same decision as layer 1 |

**Three of the four layers train nothing.** So the pool does not grow with the number
of layers; it stays *domain experts plus a routing table*. And the cost that genuinely
multiplies — **N experts is N corpora and N chances at P38's drift** — is untouched by
adding decision layers.

### Latency — the reason the layering is affordable at all

A naive reading says *k* layers cost *k* forward passes. It does not, because the
layers are of two kinds:

- **Decision layers are nearly free.** *k* typed questions about one context cost
  **one prefill** — prefill the shared context once, repeat the KV cache across
  branches, one batched forward, slice each branch's logits to its own candidates
  ([`constrained-decoding.md`](constrained-decoding.md)). Layers 1 and 4 are one
  decision with two consumers, so they are one slice of one pass.
- **Generation layers cost a full pass each.** Layer 3 is the only one that generates.

**So the four-layer design costs about one extra forward pass in total, not four** —
and only if layer 1 is ever promoted from a dict to a model.

### Speculative decoding — conditional, and the layering is what makes it work

Two facts have to be held together.

**It pays only against a bigger target — and the comparison that matters is
drafter-against-target, not drafter-against-drafter.** An earlier draft of this
section said *"a 3B drafting for a 3B saves nothing"*, which described the degenerate
case of one model drafting for itself and read as if same-size experts were the
problem. They are not. **k experts all of one size, drafting against one larger
target, is the architecture** — that every drafter is 3B is irrelevant; what pays is
that the target is bigger and slower, so the small model emits several tokens in the
time the large one emits one.

And that turns acceptance into something this project has wanted since S7:
**a ranking of experts that needs no judge and no verifier.** Same target, same
prefix, same conditions — each expert's acceptance rate is directly comparable. It is
also the shape of the **withdrawal gap**, restored at the right granularity: if a
subdomain's expert reaches the target closely enough, the target can be withdrawn
**for that subdomain**, which is exactly the per-region granularity that already
delivered 0.546 → 0.775 **[ran]** P41.

**Acceptance alone does not say who was right.** Where the drafter is rejected there
are two cases — the small model was wrong, or the small model was right and the large
one was not — and only the verifier beside it can tell them apart. Both suites have
one, so the arm is *acceptance and verified score on the same cases*, never acceptance
alone.

**But when it is live, the layering is exactly what the literature says it needs.**
TaskSpec reports a prompt classifier over four task-specific drafters lifting
acceptance **16% → 58%** **[read]** — that is layer 1 choosing layer 3's drafter,
published. Without a layer naming candidates you are back to evaluating all of them,
which is the original worry.

**And one thing is free here that usually is not.** Every member shares the resident
base's tokenizer, so **any adapter can draft for any other** with no cross-vocabulary
machinery. The only pair that ever needed checking is base-against-target, and it has
now been checked rather than assumed **[ran]** 2026-09-16,
`results/P48-tokenizer-compat-20260916/`:

| target | target vocab | ids match | usable | extra ids |
|---|---:|---|---|---:|
| **Qwen2.5-7B / 14B / 32B / 72B-Instruct** | 151,643 | **yes** | **yes** | 0 |
| Qwen3-14B / Qwen3-32B | 151,643 | **yes** | **yes** | 4 (`<think>`, …) |
| **Qwen3.5-27B / Qwen3.6-27B / Qwen3.8-27B** | **248,044** | **no** | **NO** | 26-33 |

**The Qwen3.x line changed its vocabulary at 3.5**: 151,643 entries becomes 248,044,
so `Qwen3.6-27B` — the strongest candidate on quality — **cannot verify our drafters'
tokens at all**. Only the original Qwen3 (14B, 32B) still shares the map.

So a **cross-generation target is usable**, which the plan's C3 had written off. The
catch the hashes do not show is the one that would ruin the number: those four ids are
emittable by the target and unreachable by the drafter, so a **thinking** target
rejects at every `<think>` it opens. C7 already says acceptance is read on the answer
channel; against a thinking target that stops being a convention and becomes the
difference between a real acceptance rate and a fictional one.

**The clean choice is therefore a large Qwen2.5** — identical tokenizer, no thinking
channel, same chat template — with Qwen3 available as a second, harder arm rather than
as the first one.

> **An idea this makes available, named as untested rather than planned.** Acceptance
> between *two same-size local experts* is an agreement signal that costs no frontier
> call — and P41 found that agreeing with a stronger model is the one escalation
> signal that works, while costing exactly that call **[ran]**. Whether local-local
> agreement correlates with correctness is **unmeasured**, and it costs two local
> passes rather than one, so it is a candidate and not a plan.

### The summary

| payoff | survives the layering? | why |
|---|---|---|
| **one resident base** | **yes, strengthened** | `k·m` adapters, one set of weights — but never tested above 2 |
| **many experts** | **yes, and fewer are needed** | three of four layers are rules, not models |
| **speculative decoding** | **conditional on P4** | same-size drafting saves nothing; the layering supplies the drafter choice it needs |

## 7. What this does not claim

- **Not that a learned router is useless.** It is unpriced above 0.845 on fine
  routing, and the fine job is not the one blocking anything today.
- **Not that the lexical baseline generalises.** It was written against these
  generators. On a domain nobody wrote keywords for it would start at chance — which
  is an argument for measuring it per domain, not for skipping the measurement.
- **Not that structural tokens are a bad idea.** P28 is one adjacent result, not a
  verdict on markers nobody has tried.
