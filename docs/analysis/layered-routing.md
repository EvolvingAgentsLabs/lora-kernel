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

## 7. What this does not claim

- **Not that a learned router is useless.** It is unpriced above 0.845 on fine
  routing, and the fine job is not the one blocking anything today.
- **Not that the lexical baseline generalises.** It was written against these
  generators. On a domain nobody wrote keywords for it would start at chance — which
  is an argument for measuring it per domain, not for skipping the measurement.
- **Not that structural tokens are a bad idea.** P28 is one adjacent result, not a
  verdict on markers nobody has tried.
