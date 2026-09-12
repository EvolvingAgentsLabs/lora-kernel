# The plan

> **Living document.** This is the project's position, not a proposal. Every step
> carries its objective, its gate and its falsification condition, written before
> it runs; every finished step carries the number that came out, whichever way it
> came out.
>
> *[Léeme en español](es/EXPERIMENT_PLAN.md)*

---

## 0. How to read this

| mark | meaning |
|---|---|
| **[read]** | inferred from source, docs or an issue, and cited |
| **[ran]** | observed by executing something here, with the run directory named |
| `NEXT` / `RUNNING` / `DONE` / `BLOCKED` / `DROPPED` | the step's state |

Rules that bind whoever edits this file: update a step's row **in the same
session** the step finishes; keep superseded text visible with a reason rather
than deleting it; update the Spanish mirror in the same commit.

## 1. The one question

> **Is acceptance against a frontier target a valid promotion criterion for a
> small expert — and how much verified quality is lost when the frontier is
> withdrawn?**

Everything in `README.md` and [`ARCHITECTURE.md`](ARCHITECTURE.md) rests on two
claims, and only these two are worth spending money on first:

1. **α means distillation.** A high acceptance rate against a frontier target
   identifies an expert that already produces what the frontier would, *here*.
2. **The frontier is removable.** Once α crosses a threshold in a region, the
   expert generates alone and the verified score barely moves. That difference —
   the **withdrawal gap** — is the product.

**What falsifies the project:** if α does not order candidates the way verified
task quality orders them, claim 1 is false and acceptance cannot be the promotion
criterion. The architecture would survive; the free router would not.

## 2. The order, and why this order and not the specification's

[`ARCHITECTURE.md` §7](ARCHITECTURE.md) lists E0–E4 and it is right about the
destination. This plan differs on **where the cheap falsification sits**: the
specification validates α *after* adapters exist, which is where the test stops
being cheap. Here the α-versus-quality question is answered with models that
already exist, before a single adapter is trained.

| step | objective | first gate it opens | cost | state |
|---|---|---|---|---|
| **S0** | the instrument measures what it claims | everything | $0, local | **DONE, and it moved the plan** — §3 |
| **S1** | headroom: can this suite show a withdrawal gap at all | S2 | $0.47 + a local re-run | **DONE — failed on the clinical suite, settled on fluid mechanics at +0.533** — §4, P10 |
| **S2** | does **agreement** order candidates the way verified quality does | S4 | included above | **DONE — 14/15 pairs, but against peers** — §5 |
| **S3** | attribution: does a lexical/embedding router do the same job | the routing claim | $0, offline | **DONE — mechanism 9/10, but ties the keyword rule** — §6 |
| **S4** | **the adapters** — does specialisation happen, and is it per region | S5 | free Colab T4 | **DONE. Q1 +63.3 points, probe negative. Q2 yes, +20 points, asymmetric** — §6 |
| **S5** | **the withdrawal gap** | the product | GPU + frontier | **DONE in region — 0.000.** The region's edge is hard and the expert cannot feel it — P7, P14 |
| **S6** | `harness.lora` — a kernel apart from the expert | the kernel | GPU rental | **half done. Composition solved by taking turns (P13); whether the kernel is worth its weights is being measured (P15)** |
| **S7** | the tournament, with a held-out verifier | evolution | GPU rental | **blocked: there is no judge without an oracle** — `OPEN-PROBLEMS.md` problem 4 |

Two rules govern the sequence. **Arms are bought one at a time** — the arm that
can kill the hypothesis runs before the arm that explains it. **Nothing that
needs a GPU is bought before something that does not has failed to kill the
idea**: `vllm` cannot serve on this machine at all **[ran]**, so every
vLLM-dependent step is rented time.

## 3. S0 — the instrument · DONE

**Objective.** Produce an acceptance surface and a verified score from one run,
against a local stand-in target, and show the two numbers move independently.

**Gate.** Nothing downstream is believable until the instrument has been made to
fail on purpose.

**What was built.** `alpha/` — case loader over the borrowed `clinical_learning`
suite with a frozen, hashed prompt; two greedy backends; the measurement; the
report. `tests/test_alpha.py` holds 13 checks that each pin one way the number
could come out clean and wrong; all pass **[ran]**.

**What the build found before any result was trusted** (each is now a constraint
in §7):

- ollama's chat renderer **does not honour an assistant prefill** — a qwen
  drafter re-opened its turn and restarted the answer **[ran]**. Mid-answer α is
  therefore optional and gated on a per-call `restarted` flag; the primary number
  is α at position 0, which needs no prefill and is the one Phase B actually runs
  on.
- **every local model here is a thinking model** **[ran]**. The reasoning stream
  is emitted before the answer and silently eats a budget sized for the answer,
  returning an empty answer channel. `think=false` works on qwen and returns
  HTTP 500 on gemma. The instrument records the two channels separately and
  aborts rather than scoring an empty answer as α = 0.

**Result — three runs, $0, and the instrument found four ways to lie.**

| run | prompt | n | target `gemma4:12b` | `qwen3.5:4b` | `qwen3.5:9b` | what it established |
|---|---|---|---|---|---|---|
| [`S0`](../results/S0-instrument-20260907/BRIEF.md) | frozen | 4 | 1/4 | 1/4 | 0/4 | the pipeline runs end to end |
| [`S0b`](../results/S0b-payload-20260907/BRIEF.md) | frozen | 12 | 3/12 | 3/12 | 2/12 | α over the payload; dispersion 0.076 |
| [`S0c`](../results/S0c-canonical-20260907/BRIEF.md) | canonical | 12 | 4/12 | 3/12 | 3/12 | our prompt removed as a variable |

**[ran]** All three under `results/`, one JSON per case, reports regenerable with
`python3 -m alpha.report <run-dir>`.

**Two findings that change the plan, not just the code.**

**1 · This suite does not separate these models single-shot, and the target has
no headroom over its own drafters.** 4/12, 3/12 and 3/12 are the same number. A
12B target that cannot beat a 4B drafter cannot stand in for a frontier model,
and a frontier arm bought on this configuration would be measuring nothing. Note
what this also says about the published ladder: 38–41/50 came from the *runtime*
— contract, feedback, action validation — and single-shot raw generation is
33 %. **The harness is most of that score**, which is the thesis
`../verified-runtime` exists to test, arriving here as a constraint.

**2 · Character-level agreement measures layout, not agreement.** The skeptic
pass ran it in both directions **[ran]**:

| input | what the metric said | what is true |
|---|---|---|
| same answer, one pretty-printed and fenced, one compact | agreement **0.00** | the verifier passes both |
| different answers, both pretty-printed | agreement **0.44** | they agree on `\n      "` and nothing else |

In run S0c the 4B produced the exactly correct answer and scored **0.00**, while
a model that gave the same answer with indentation scored **1.00**. Layout
dominates content, so α measured this way is not merely noisy — it is
anti-informative across model families.

**What that implies, and it is the most useful thing S0 produced:** in the
architecture the answer format is not a variable, because **`harness.lora` pins
it**. Character acceptance only becomes meaningful once the kernel adapter makes
the format a constant. So `harness.lora` is not a parallel track — **it is
upstream of α**, and §2's order is wrong about S6. The proposal on the table,
which needs a decision rather than a commit, is in §12.

## 4. S1 — headroom · BLOCKED

**Objective.** Establish that a frontier target scores materially above the
strongest local model on this suite. Without that distance there is nothing for a
withdrawal gap to be a gap *in*.

**Why this is the likeliest way the project stalls.** `gemma4:12b` already scored
**38–41/50** on this held-out set and `qwen3.5:4b` reached 38/50 under a repaired
interface **[read]**. If a frontier model scores 43/50, the whole architecture is
being asked to preserve a 2-point difference, every arm ties, and a tie reads as
success.

**Gate.** S2 does not run until this passes.

**Falsification.** Frontier minus best local is inside the paired interval on
n = 50 → **this suite cannot measure this project**, and the fix is a harder task
distribution, not a better treatment. Candidate replacements, in order: the
`clinical_learning` `held_out_delta` split (its rule inverts, so memorised
protocol fails), then the `causal_workflow` and `quantum` domains already in
`../verified-runtime`.

**S1a — the fallback this step named in advance, run before spending anything.**
[`results/S1a-delta-20260907/`](../results/S1a-delta-20260907/BRIEF.md), $0,
12 cases of `held_out_delta`, everything else identical to S0c **[ran]**:

| | `gemma4:12b` (target) | `qwen3.5:4b` | `qwen3.5:9b` |
|---|---|---|---|
| `held_out` (S0c) | 4/12 | 3/12 | 3/12 |
| **`held_out_delta` (S1a, n=20)** | **12/20** | **6/20** | **6/20** |

**There is headroom, on the split whose planted rule inverts.** The 12B pulls
**+6 of 20** clear of its best drafter where it was tied before. This is what the frontier arm needs to exist: a configuration
where being better is possible. The suite question is answered — **S1 is worth
its $5 on `held_out_delta`, not on `held_out`.**

**And it produced the trap C9 predicted, in the form that would have been
believed.** At n=12, ordering by α matched ordering by verified score (9B > 4B)
— for the wrong reason: the 9B pretty-prints like the target and the 4B does not.
A confirmation of the project's central claim, arriving by accident of
indentation, on a difference of one case that vanished at n=20. The report now
refuses to interpret that line while C9 stands.

**S1 ran, three times, and failed its own gate every time.** All 20 delta cases,
canonical prompt, exact verifier, four local candidates held constant **[ran]**:

| target | verified | cost | headroom over `gemma4:12b` (12/20) |
|---|---|---|---|
| `gemini-3.5-flash-lite` | 13/20 | $0.0028 | **+1** |
| `gemini-3.8-flash` | 13/20 | $0.1338 | **+1** |
| `gemini-3.1-pro-preview` | **8/20** | $0.2885 | **−4** |
| `gemma4:12b-mlx`, local | 12/20 | $0 | — |

Total spend $0.47, inside the $1 ceiling the brief pre-registered. **The gate said
the target must clear the best local model by a margin a withdrawal gap could
live in. None of them does, and the most expensive one is the worst.**

**What that costs the architecture, stated plainly.** Phase A's premise is *pay
frontier prices, get frontier answers, and collect the measurement for free*. On
this task, paying **48× more** bought the same 13/20 and paying **100× more**
bought 8/20. There is no withdrawal gap to measure here because there is almost
nothing to withdraw from — and that is this workspace's recurring result arriving
again: on a bounded administrative task, capability sits in the interface and the
verifier, not in model size or price.

**It is a finding about the suite, not about the thesis.** The frontier's
advantage, if it exists, is not visible in single-shot generation on a
20-case referral check. The three configurations that could still show it are in
§12's decision.

**No longer blocked.** The key exists and was used; the target choice is what
failed.

## 5. S2 — does α order candidates the way quality does · BLOCKED

**Objective.** The project's own falsification condition, bought as cheaply as it
can be bought: with **no adapters trained at all**.

**The criterion, decided 2026-09-07 (§11, option C).** Not character acceptance —
**semantic answer agreement**: the candidate's parsed answer against the target's
parsed answer, so item order, indentation and a markdown fence cannot move it.
Character α is still recorded beside it, and comparing the two is S6's job.

**Design.** Three models whose verified scores on this suite are already known —
`qwen3.5:4b`, `qwen3.5:9b`, `gemma4:12b` — stand in as candidate experts. Measure
their agreement with the target per region, and ask whether ordering by agreement
reproduces ordering by verified score.

**S2a — the local proxy, and the correction it produced.** The criterion was
applied to the answers persisted by S0c and S1a, then the delta split was
completed to its full 20 cases **[ran]**:

| run | | agreement | verified | ordering test |
|---|---|---|---|---|
| S0c `held_out`, n=12 | `qwen3.5:4b` | 0.667 | 3/12 | **not comparable** — the candidates |
| | `qwen3.5:9b` | 0.727 | 3/12 | tie on quality |
| ~~S1a `held_out_delta`, n=12~~ | ~~`qwen3.5:4b`~~ | ~~0.333~~ | ~~3/12~~ | ~~agreement and quality agree~~ |
| ~~superseded — see below~~ | ~~`qwen3.5:9b`~~ | ~~0.556~~ | ~~4/12~~ | ~~9b > 4b on both~~ |
| **S1a `held_out_delta`, n=20** | `qwen3.5:4b` | 0.350 | **6/20** | **not comparable** — the |
| | `qwen3.5:9b` | 0.533 | **6/20** | candidates tie on quality |

**The n=12 result did not survive its own split.** At 12 cases the candidates
differed by one verified case and the orderings "agreed"; at 20 they tie exactly,
and there is no ordering for the criterion to reproduce. One case of difference
was never an ordering, and the earlier row is kept struck rather than deleted
because that is the failure this plan exists to make visible.

**S2 ran against all three targets, and the criterion holds** — with a caveat
that has to travel with it. The ordering test is scored pairwise over the
candidate pairs whose verified scores differ, with a fourth candidate
(`qwen3.5:2b`) added so the ladder spans 2B to 12B and no longer ties **[ran]**:

| target | **semantic agreement** | character α | what character α said |
|---|---|---|---|
| `gemini-3.5-flash-lite` | **5/5** | 2/5 | ranked the **best** candidate **last** |
| `gemini-3.8-flash` | **5/5** | 1/5 | ranked the **best** candidate **last** |
| `gemini-3.1-pro-preview` | **4/5** | 4/5 | ranked it first — this target pretty-prints |

**14 of 15 discriminable pairs ordered correctly, across three independent
targets.** The criterion the plan adopted in §11 does what a promotion criterion
has to do.

**And the same table settles §11 empirically.** Character α scored 1/5 with one
target and 4/5 with another **on the same candidates and the same cases** — the
only thing that changed is whether the target happens to indent like the
candidate. A metric whose concordance quadruples because the target's formatting
habits changed is measuring formatting. Option C was the right call and the
evidence is now direct rather than argued.

**The caveat that must travel with it.** S1 failed, so all three targets are
**peers of the strongest candidate, not frontier models**. Agreement with a peer
is not a distillation score, and this therefore validates **the mechanics of the
criterion**, not the architecture's claim. The distillation claim needs a target
that is actually better, and no available Gemini was.

**And C11 is visible in the numbers:** `qwen3.5:9b` produced no parseable answer
in 5 of 20 cases, which the criterion excludes, so its agreement is measured on
the 15 cases where it answered at all.

**And it made C11 concrete.** `qwen3.5:9b` scores the *best* agreement (0.533)
while producing no parseable answer in **5 of 20** cases — which the criterion
excludes. A model that often answers nothing looks like a good agreer.

**Gate.** S4 — no adapter is trained until acceptance is known to carry the
signal that promotion would be based on.

**Falsification.** The orderings disagree, or agreement is flat across candidates
that differ in verified quality. Either kills acceptance as a promotion criterion; the
adapter pool survives, the free router does not, and the plan reopens at the
router.

**Second control, same run, free.** α dispersion. If every candidate accepts
alike, there is nothing to route on regardless of what α means.

## 6. S3–S7 — the steps that cost money, and what each has to clear first

**S3 · the attribution arm — answered for $0, and it says both things at once.**
S4's region arms recorded three answers per case (each expert, and the
all-clinics adapter as reference), so routing is a computation over runs already
on disk rather than an experiment to buy. `python3 -m training.route_offline`,
40 cases **[ran]**:

| policy | accuracy |
|---|---|
| oracle — the better expert, per case | 0.750 |
| **routed by agreement** | **0.725** |
| **always the case's own-region expert** | **0.725** |
| always the other expert | 0.525 |

**The mechanism works.** On the 10 cases where the two experts actually disagree,
agreement picked the correct one **9 times**, and routing recovered 0.725 of the
0.750 available.

**And it bought nothing here.** A rule that reads `clinic:` out of the prompt and
picks that clinic's expert scores exactly the same 0.725, for free. That is the
result this workspace has had before, when a memory hierarchy lost to plain
lexical search **[read]** — and it arrives because **this suite labels the
region in the prompt**. Routing exists for the case where the region is *not*
stated, and this benchmark cannot pose that case.

So the attribution arm does not kill acceptance-routing; it says the suite cannot
price it. A suite that withholds the region label can, and that is the cheapest
version of the next question.

**S4 · the adapters — brought to the front, and the kit is built.** S1's failure
stalls the frontier path, and this project is adapters: a session that produces no
adapter has not advanced it ([`../CLAUDE.md`](../CLAUDE.md) §0). So S4 no longer
waits behind S3.

**What ships in this repository** (`training/`), ready to run on Colab because a
26B does not fit on this machine:

| | |
|---|---|
| `build_dataset.py` | generates **600 train / 120 val / 60 delta** cases with the sealed benchmark's own generator at a **different seed**, and refuses to write if any training prompt matches a sealed one **[ran]** |
| `evaluate.py` | the exact verifier, one copy, grading every arm — a base model and an adapter graded by different code are not comparable |
| `lora_kernel_colab.ipynb` | baseline → QLoRA → adapter, then two region experts cross-evaluated |

**Models**: `google/gemma-4-E4B-it` (free T4) and `google/gemma-4-26B-A4B-it`
(A100), with `gemma-4-12B-it` as the local baseline already measured at 12/20.

**The two questions, and what falsifies each.**
1. **Does specialisation happen at all?** The adapter must beat the base on `val`,
   which neither was trained on. If it does not, no routing scheme rescues it.
2. **Do experts differ by region?** An adapter trained on clinic α and one trained
   on clinic β must each be better on their own region. If they are not, the pool
   is one expert wearing three names and there is nothing for acceptance to route
   between — which would end the architecture's central claim, cheaply.

**QUESTION 1 IS ANSWERED: SPECIALISATION HAPPENS.** `Qwen/Qwen3.5-2B`, 2026-09-08,
[`results/S4-qwen35-2b-20260908/`](../results/S4-qwen35-2b-20260908/BRIEF.md),
all four numbers **[ran]** on cases neither arm was trained on:

| | base | **adapter** | |
|---|---|---|---|
| `val` (60) | 6/60 · **0.100** | **44/60 · 0.733** | **+63.3 points** |
| `val_delta` (30) | 6/30 · 0.200 | **12/30 · 0.400** | **+20.0 points** |

Zero unparseable answers in either adapter arm. Per clinic the gain is even —
alpha 15/20, beta 15/20, gamma 14/20 — so it is not one protocol carrying the
result. The adapter is **10.9 M trainable parameters, 0.58 % of the model**,
trained for two epochs on 600 generated cases on a free T4, adapting **all
seven** attention and MLP projections — including `q_proj` and `k_proj`, which
an earlier note claimed were excluded for qwen3's QK-norm. They were not: the
flag that excluded them was read only by the preflight, and the concern did not
bite in training. **[ran]**

**And the false-promotion probe came back negative, which is the stronger half.**
`delta` is the clinic that appears in no training split and whose unpublished rule
**inverts**. An adapter that had memorised the rule would gain on `val` and
collapse there. This one **improved by 20 points** on it. What was learned reads
the case rather than reciting the protocol.

**How much of this project's history was infrastructure, and how it was
separated from the result.** The adapter arm returned 0 three times before this,
and every one was the machine: a card with no real bf16 (C15), a resume that
would have banked that zero (C15), and gradient checkpointing left on during
generation, which does not merely slow the KV cache but corrupts the output.
Each zero read exactly like *"specialisation did not happen"* — one of this
step's two falsification conditions. The true number is +63.

**QUESTION 2 IS ANSWERED TOO, AND THE ANSWER IS ASYMMETRIC.** Two experts, one
trained on clinic `alpha` only and one on `beta` only, each with the **training
budget matched to the all-clinics adapter** rather than the epoch count, then
cross-evaluated **[ran]**:

| | on `alpha` | on `beta` |
|---|---|---|
| **expert α** | **0.700** (14/20) | 0.400 (8/20) |
| **expert β** | 0.650 (13/20) | **0.750** (15/20) |

**The diagonal wins in both directions** — own region 0.725 against other region
0.525, **+20 points** — so there is something for a router to choose between and
the pool is not one expert wearing three names.

**But only one column can carry that claim.** On `beta`'s cases the two experts
differ by seven cases (15 against 8); on `alpha`'s they differ by **one** (14
against 13), which at n = 20 is not a difference at all. Expert β generalises to
α's clinic almost as well as α does; expert α does not return the favour.

So the honest statement is: **specialisation by region is real, and it is not
symmetric.** A router built on this surface would have a strong signal in one
region and none in the other — which is a finding about what routing has to
handle, not a flaw in the adapters.

**The first attempt at this arm was voided and re-run**, because 200 cases at the
same epoch count is a third of the updates: the first α expert reached
`train_loss` 1.079 against the all-clinics adapter's 0.103 and scored 3/20 on its
own region. Comparing an undertrained expert with a trained one measures the
budget and calls it specialisation.

**The probe that has to be reported beside any gain.** `delta` inverts one of the
unpublished rules and appears in no training split. An adapter that memorised the
rule scores well on `val` and collapses on `val_delta`. That gap is the **false
promotion** number, and a gain published without it is not a result.

**S5 · the withdrawal gap.** Promote where α crossed the threshold, remove the
frontier, re-measure on the sealed split. The threshold and the non-inferiority
margin are pre-registered before the run; `evaluation/frontier_gap.py` in
`../verified-runtime` already carries the warning that a closed-gap fraction is
not an equivalence claim **[read]**.

**S6 · `harness.lora`, and it now has a second win condition.** S0 found that
character acceptance is dominated by layout, and pinning the layout is exactly
what the kernel adapter does. So beyond the token and malformed-call numbers, S6
answers: **does pinning the format make character-α agree with semantic
agreement?** If it does, the architecture's free per-region acceptance score is
recovered and the kernel adapter is what recovered it — the strongest argument
for `harness.lora` this project could produce. If it does not, character α stays
a within-family statistic and the promotion criterion stays semantic.

**S6a — its headroom, computed at $0 from the runs already on disk** (`python3
-m alpha.kernel_headroom`) **[ran]**:

| number | value | what it means |
|---|---|---|
| protocol overhead in the canonical prompt | **~96 tokens, 43 % of a 223-token prompt** | the bar is `gemma4nanoloop`'s 817 peak on a real tool set. Two actions is not a tool distribution, and an adapter that removes 96 tokens cannot be shown to beat −85 % here |
| malformed-call rate, `gemma4:12b` | **0/40 across four runs** | nothing to repair |
| malformed-call rate, `qwen3.5:4b` | 1/40 | nothing to repair |
| malformed-call rate, `qwen3.5:9b` on `held_out_delta` | **3/12 — 25 %** | the only headroom the kernel adapter has on this suite, and it is on one model on the hardest split |

**So S6 cannot be run on this suite as a token argument, and can only barely be
run as a syntax argument.** It needs a real tool distribution — many actions,
several phases — before either of its numbers means anything. That is a finding
about the suite, and it was bought for nothing.

Its own headroom check, when a real tool distribution exists: protocol-token count and
malformed-call rate of the base model with action tokens in the prompt. If that
is already at 817 tokens and zero malformed calls, the adapter has nothing to
repair on this suite and needs a harder tool distribution. Reported as three
numbers together — tokens, malformed-call rate, latency including adapter swap —
against `gemma4nanoloop`'s −85 % and against constrained decoding, never against
prose **[read]**.

**S7 · the tournament.** Offline only, `w₁` from a verifier the loop cannot see.

## 7. Constraints the instrument has to live inside

Facts, not objections. Each one shapes how a step is run, not whether the
architecture is right.

| # | constraint | consequence |
|---|---|---|
| C1 | At T = 0 the accepted prefix **is** the longest common prefix with the target's greedy continuation, and greedy is prefix-consistent **[read]** | the α surface is measurable today — no GPU, no vLLM, no `LoRA-as-drafter` |
| C2 | Frontier chat APIs do not expose logprobs of a **forced** continuation **[read]** | true rejection sampling against a frontier API is not implementable; C1 is the instrument |
| C3 | A frontier target does not share the base model's tokenizer **[read]** | α is measured in characters. Sound as a distillation score, **unsound as a speedup claim** |
| C4 | `vllm` does not serve on this machine (arm64, 16 GB) **[ran]** | every vLLM step is rented GPU and late in the order |
| C5 | LoRA-as-drafter is an open RFC, [vllm#52038](https://github.com/vllm-project/vllm/issues/52038) **[read]** | Phase A runs with adapters outside the speculative path, or with small per-domain drafters |
| C6 | ollama ignores an assistant prefill **[ran]** | position 0 is primary; mid-answer α is gated on the `restarted` flag |
| C7 | Every local model here is a thinking model **[ran]** | α is measured on the **answer channel**; the reasoning channel is recorded and never concatenated |
| C8 | No `OPENROUTER_API_KEY` on this machine **[ran]** | S1 and S2 are blocked on a human |
| C9 | Character-prefix agreement is dominated by layout: identical answers score 0.00 across formats, different answers score 0.44 within one format **[ran]** | **decided (§11, option C):** the promotion criterion is semantic answer agreement; character α is reported beside it and never ranks anything; whether pinning the format reconciles them is S6's win condition |
| C10 | Agents under `.claude/agents/` load for a session rooted at this repository, not at the workspace above it **[ran]** | they are symlinked into `../.claude/agents/` so a workspace-rooted session can address them too |
| C18 | **vLLM 0.28.0 accepts a `LoRARequest` and silently serves the base model.** No error, no warning, byte-identical output, on a valid peft adapter whose config matches the served model **[ran]** | the architecture's substrate is unproven, and any future serving number has to be checked against a known-different adapter output before it is believed |
| C17 | **Gradient checkpointing left on during generation corrupts the output**, it does not merely disable the KV cache: the same adapter scored 0/60 with it on and 44/60 with it off **[ran]** | training flags are turned off before evaluating, and a zero from a model whose training loss was 0.10 is treated as an instrument fault until proven otherwise |
| C15 | A **T4 has no bf16**. The base generated fine in bf16 and every LoRA generation then died with "GET was unable to find an engine to execute this computation" — reported as 0/60 **[ran]** | precision is chosen by `is_bf16_supported()`, not by habit. Read as a result it would have said "specialisation did not happen", which is one of S4's two falsification conditions |
| C16 | Free Colab **reclaimed three sessions** inside roughly 40 minutes of GPU work each **[ran]** | per-arm persistence has to survive the *session*, not just the process: results are pulled to this machine after every arm, and a resume must upload them back. Otherwise the tier has to change |
| C14 | Training data is **generated** with the benchmark's own generator at a different seed, and a leak check refuses to write if a training prompt equals a sealed one **[ran]** | an adapter can be trained on hundreds of cases while the sealed 50 + 20 stay unseen; without the check the evaluation would be a memory test and every number after it void |
| C12 | On this suite, three Gemini targets scored 13/20, 13/20 and 8/20 against a local 12B's 12/20, at $0.003, $0.13 and $0.29 **[ran]** | there is no frontier advantage to distil here; Phase A's premise needs a task where paying more buys more, and finding that task is now the gating question |
| C13 | Character α's pairwise concordance moved **1/5 → 4/5** across targets, on identical candidates and cases, purely because the pro target pretty-prints **[ran]** | direct evidence for C9, and the reason §11's decision is now settled rather than provisional |
| C11 | Semantic agreement **excludes** cases where either side produced no parseable answer, and `qwen3.5:9b` produced none in 3 of 12 delta cases while scoring the *best* agreement **[ran]** | the criterion must always be read beside the unparseable count, or a model that often answers nothing looks like the best agreer — and that failure is precisely what `harness.lora` exists to repair, which couples S6 to the criterion rather than leaving it downstream |

## 8. Deliberately not built

Cross-adapter KV cache, tree attention across adapters, a bespoke runtime,
vertical packs, the control plane, the marketplace. All downstream of §S5. The
KV-cache problem is the expensive part of the architecture and it is only worth
solving once a surface says the branches are worth comparing.

## 9. Agents and skills — the ledger

Created, edited and retired as the work learns. The lifecycle rule is
[`../CLAUDE.md`](../CLAUDE.md) §5.

| date | change | because |
|---|---|---|
| 2026-09-07 | created [`headroom-auditor`](../.claude/agents/headroom-auditor.md) | S1 is the step most likely to end the project, and it is the one a session is most tempted to skip |
| 2026-09-07 | created [`instrument-skeptic`](../.claude/agents/instrument-skeptic.md) | S0 found two instrument failures before any number existed; that check should not depend on remembering to do it |
| 2026-09-07 | created [`alpha-runner`](../.claude/agents/alpha-runner.md) | runs must stream, persist per case and be abortable |
| 2026-09-07 | created [`mirror-keeper`](../.claude/agents/mirror-keeper.md) | the repository's only CI gate is the bilingual documents |
| 2026-09-07 | created skill [`experiment-brief`](../.claude/skills/experiment-brief/SKILL.md) | the briefing goes before the run, not beside the report |
| 2026-09-07 | created skill [`alpha-surface`](../.claude/skills/alpha-surface/SKILL.md) | what α licenses and what it does not has to travel with the command |
| 2026-09-07 | searched both skill marketplaces, installed nothing | every evaluation skill found is built on LLM-as-judge; this project's verifier is exact **[ran]** |
| 2026-09-07 | added [`../CLAUDE.md`](../CLAUDE.md) §0 — the anti-drift rule — at the user's instruction | two sessions of measurement produced four instrument findings and **no adapter**; the rule names the drift so the next session does not repeat it |
| 2026-09-07 | built `training/` — dataset builder, shared verifier, Colab notebook | the project is adapters and the machine cannot train one; the deliverable for anything needing a GPU is a notebook committed here |
| 2026-09-07 | created [`colab-runner`](../.claude/agents/colab-runner.md); `adapter-trainer` never written | the Colab CLI turns the adapter step into something this session executes rather than hands over, so the agent that was declared for S4 became the one that drives the runtime |
| 2026-09-07 | removed the mid-answer prefill path, the second prompt template, the duplicated verifier and the superseded 6-case run | ollama ignores a prefill so those positions never produced a number; two prompts is one variable too many; a copied verifier is a second thing to keep in step |
| 2026-09-07 | edited skill [`alpha-surface`](../.claude/skills/alpha-surface/SKILL.md) | the promotion criterion changed under §11, and a skill that still described the old one would travel with every future command |

**Declared, not built:** `adapter-trainer` (S4), `kernel-bench` (S6),
`tournament-referee` (S7), skills `withdrawal-gap` (S5) and `adapter-training`
(S4). Each waits for the step that justifies it.

## 10. Stopping conditions, decided now

- **Instrument redesigns.** **3, then a fourth made under review.** The three
  were: the thinking channel and the missing prefill; measuring the payload
  instead of the format; and reverting to the canonical prompt. The condition
  fired, the session stopped, and the fourth change — the promotion criterion
  becoming semantic — was **decided by the human the rule required**, not by the
  person building the instrument (§11, 2026-09-07). The counter resets to 0 and
  the rule stands for the next three.
- **Flat arms are abandoned, not completed.** A run visibly flat a third of the
  way through is killed, and what it cost to abort versus to finish is recorded.
- **A number is published whichever way it comes out.** The withdrawal gap is the
  project; a large gap is a result, not a failure to be re-run until small.

## 11. The decision on the table — one taken, one open

### Taken 2026-09-07: what α is

Not a commit — a choice, because it changes what α *is* and that is the
architecture's central term.

**The problem.** The promotion criterion has to compare a small local expert with
a foreign frontier model that shares neither tokenizer (C3) nor formatting
conventions (C9). Character acceptance across that boundary measures layout.

**Option A — semantic answer agreement.** Promotion is decided on whether the
expert's *parsed answer* matches the target's. Honest, cheap, available today,
and it is what Phase B actually needs. What it gives up: the word "acceptance".
This is no longer speculative decoding's α; it is answer agreement, and the
"free inside the serving path" story becomes "free inside a pass we were paying
for anyway", which is still true but is a smaller claim.

**Option B — pin the format first.** Character acceptance becomes meaningful the
moment the format stops being a variable, and pinning the format is exactly what
`harness.lora` is for. This makes **S6 upstream of S2** and reorders the plan: no
α surface until the kernel adapter exists. Faithful to the architecture as
specified, and considerably more expensive — it puts a training run before the
project's cheap falsification, which is the thing this plan was reordered to
avoid.

**Option C — both, in order.** Option A now, as the promotion criterion for S1–S5,
with character-α reported beside it *within a single model family* where it is
defined. Then Option B measured as S6's own win condition: does pinning the
format make character-α agree with semantic agreement? That question is worth a
number on its own, and it is the strongest argument for the kernel adapter this
project could produce.

**Decided 2026-09-07: C**, and since confirmed directly by C13. The promotion
criterion for S1–S5 is semantic answer
agreement, character α is reported beside it and ranks nothing, and S6 owns the
question of whether pinning the format reconciles the two. Implemented in
`alpha/report.py::semantic`, pinned by six tests, and applied retroactively to
every run already on disk — the criterion is computed from the stored answers, so
nothing had to be re-run.

### The road back to the original plan, in dependency order (2026-09-08)

Colab Pro is confirmed on this account **[ran]**: **L4** (23 GB, capability 8.9)
and **A100-SXM4** (40 GB, capability 8.0), both with real bf16. Three blockers
dissolve at once — session tenure, the fp16 workaround that produced every false
zero, and the impossibility of running vLLM.

**And one that was never obvious: the target does not have to be an API.** A 40 GB
card can host a large Qwen3.5 as the strong reference, and a target from the
**same family as the adapters shares their tokenizer** — which is exactly what C2
and C3 said made true token-level acceptance unmeasurable. The architecture's
central metric becomes available for the first time.

| # | step | card | gate it must clear | cost |
|---|---|---|---|---|
| **P1** | **Price the router.** Re-run the 40 routing cases with the `clinic:` line **masked**, so the lexical rule has nothing to read | L4 | agreement still picks the right expert while the keyword baseline collapses to chance | ~15 min |
| **P2** | **Replicate S4 in bf16.** Same arms, real bf16, no fp16 path | L4 | the +63.3 survives; if it does not, every S4 number was a precision artefact | ~30 min |
| **P3** | **vLLM multi-LoRA, the substrate** | A100 | **RESOLVED on a dense base** — silent failure on Qwen3.5 | spent |
| **P4** | **A same-family strong target.** Serve a large Qwen3.5 beside the 2B adapters | A100 | **token-level** acceptance measurable at last, shared tokenizer, no text-agreement surrogate | ~1 h |
| **P5** | **S1 again, locally.** Does the strong same-family target clear the adapters by a margin a withdrawal gap can live in | A100 | if it does not, the suite is still wrong and §11's other options apply | ~30 min |
| **P6** | **S5 — the withdrawal gap.** Promote where acceptance crosses threshold, remove the target, re-measure | A100 | **the product** | ~1 h |
| **P7** | **S6 — `harness.lora`** against a real tool distribution, which this suite does not have | L4 | tokens, malformed-call rate and swap latency together | new fixtures first |
| **P8** | **S7 — the tournament**, `w₁` from a verifier the loop cannot see | L4 | evolution | after P6 |

**Why this order.** P1 and P2 are cheap and they settle whether what we already
have is real; running them on a Pro card costs minutes and removes two standing
doubts. P3 and P4 buy the substrate and the metric — nothing above them can be
claimed about *serving* until they exist. P5 is the gate that decides whether P6,
the product, is buyable at all; it is bought before P6 and not alongside it.

**The A100 is the expensive resource, so P1, P2, P7 and P8 stay on the L4.**

**The run directories drifted from this table after P4, and the names on disk
win.** `P5` is the headroom check on the new suite, `P6` the withdrawal gap,
`P7` the calculator step that closed it — inserted because the gap did not
close without a tool — and `P8` is `harness.lora`, which this table calls P7.
The tournament, this table's P8, has not been bought.


#### P20 — a fitness that does not select for failing quietly

[`results/P20-fitness-20260911/`](../results/P20-fitness-20260911/BRIEF.md). P19
found that a transcript-reading judge accepts **41% of wrong work that looks
clean**, so a variant whose failures are invisible outranks one that is more often
right. Four combinations of two judges were listed before any was scored, and all
four reported **[ran]**:

| fitness | pairs with a real gap ordered right |
|---|---|
| model judge alone | 1/2 |
| procedural alone | 1/2 |
| **both must accept** | **2/2** |
| either may accept | 1/2 |

| | wrong work that looks clean | correct work |
|---|---|---|
| model judge alone | accepts **41%** | accepts 96% |
| **both must accept** | accepts **2%** | accepts 90% |

**False acceptance falls from 41% to 2% for six points of correct work.** The model
judge reads a transcript and cannot tell *clean because correct* from *clean
because it never tried*; the procedural check re-executes the chain and is
indifferent to how it looks. Neither is sufficient and the conjunction is — and it
comes out nearly calibrated, scoring P13's control at 0.767 against a true 0.767
and P15's rule at 0.231 against a true 0.231.

**The obvious fix was backwards and is worth recording as such.** Subtracting the
tool layer's rejections penalises the arm that shows its failures, which is the
better one. A visible error is a signal: it costs correct work almost nothing and
lets a judge reject wrong work.

**Two pairs is not a tournament.** The candidates were not bred by a loop, so
nothing here shows that repeated selection converges, or that a loop optimising
this fitness would not learn to satisfy both judges while being wrong.

#### P17 — a judge exists, and judging is easier than solving

[`results/P17-judges-20260910/`](../results/P17-judges-20260910/BRIEF.md). 100
chains from P13 and P14 whose correctness is known — 33 right, 67 wrong — scored by
candidates that never see the answer. The bar is **0.67**, the majority class
**[ran]**:

| judge | accuracy | finds the right work | finds the wrong |
|---|---|---|---|
| always "incorrect" — the bar | 0.67 | 0.00 | 1.00 |
| procedural (no model) | 0.66 | 0.94 | 0.52 |
| `qwen3.5:4b` — a peer | **0.82** | 0.97 | 0.75 |
| `gemini-3.8-flash` — the frontier | **0.89** | 0.89 | 0.89 |

**The peer's numbers are the ones that matter.** `qwen3.5:4b` *solves* this
material at **0.467** and *judges* it at **0.82**. **Judging is easier than
solving**, widely, for the same model on the same problems — which is what makes a
tournament buildable after the frontier is withdrawn. The grade does not have to
come from something that could have done the work.

**The procedural judge fails in a shape worth keeping.** It ties the trivial bar on
accuracy with the opposite error profile: 94% of the correct work found, 52% of the
wrong. It sees arithmetic and is blind to a wrong relation — and a wrong relation
is exactly what an expert outside its region produces.

**What this cannot escape.** The frontier judges well here partly because it can
solve the problem: it scores 1.000 on this material. Where nothing available can
solve the work, judging is untested. And 7 of its 100 replies were not verdicts,
recorded as abstentions rather than folded into "incorrect", which would have handed
it the majority class.

**The fault caught on the way**: the first run gave a one-word verdict 8 tokens. A
reasoning model spends that thinking and returns an empty answer, so the frontier
abstained on 100 of 100 and read as "cannot judge". Both judges were re-run at 400;
the arm it invalidated was thrown away rather than reported.

#### P18 — the guard is falsified: P16 measured two families, not a boundary

[`results/P18-confirm-20260910/`](../results/P18-confirm-20260910/BRIEF.md). P16's
cut applied unchanged at `rejection_rate > 0.50`, on `weir_flow` and `jet_reaction`
— families no run that fitted anything had seen **[ran]**:

| arm | in region | new families | guard accuracy |
|---|---|---|---|
| sequential | 0.15 | **0.18** | **0.62** |
| control | 0.15 | **0.14** | **0.58** |

**Outside its region the tool layer refuses calls at nearly the rate it refuses
them inside.** 0.62 is chance: with 30 cases in and 20 out, answering "in region"
every time scores 0.60.

**P16's 0.86 came from six signals chosen with the answers visible and a cut fitted
on the same fifty problems that scored it** — exactly what its brief warned about.
The warning was right and the number was not. This is what a pre-registered
confirmation is for, and it is the cheapest experiment in the project to have run.

**A nuance, because two real figures disagree.** Pooled over the arm, 23 of 66 calls
were refused — 0.348. Averaged per case it is 0.18. A detector thresholds a *case*,
so the per-case mean is the one that counts; the pooled figure is higher because a
few cases fail badly and most do not. Quoting 0.348 would have been true and
misleading.

**What it costs.** The expert's formulas still fall from 30/30 inside its region to
1/20 outside, nothing in its prose marks the difference, and now nothing in the tool
layer's behaviour does either. **Per-region promotion still has no guard**, and the
cheap direction — read the process rather than the model — is exhausted. What
remains is a second expert whose disagreement flags the edge, or sampling the
frontier after withdrawal, which is the cost withdrawal exists to avoid.

#### P16 — a guard on the region's edge, read from the tool layer rather than the model

[`results/P16-tripwire-20260910/`](../results/P16-tripwire-20260910/BRIEF.md).
P14 ruled out the obvious guard: nothing in the expert's prose marks the boundary.
Six signals were pre-registered and all six reported, over transcripts P13 and P14
had already banked — arithmetic over files, no GPU **[ran]**:

| signal | sequential arm | control arm | verdict |
|---|---|---|---|
| calls per case | 0.66 | 0.60 | neither |
| **rejected calls per case** | **0.86** | **0.76** | **both** |
| **rejection rate** | **0.86** | **0.76** | **both** |
| numbered steps | 0.68 | 0.68 | neither |
| chains with no evaluable step | 0.60 | 0.60 | neither |
| transcript length | 0.72 | 0.62 | neither |

**The rejection rate runs 0.15 in region and 0.63 outside** where the kernel writes
the calls. Outside its region the expert names quantities it does not understand,
and the tool layer cannot turn those names into valid calls — **the tool layer
fails where the prose does not**, so the guard reads a process instead of the
model's opinion of itself.

It is weaker where the harness writes the calls (0.76), which fits the mechanism:
a harness that only evaluates the expression it is handed has less to refuse than a
kernel that must build a call from a label. **The guard is a property of having a
tool layer that can fail** — which makes `harness.lora` load-bearing for a reason
nothing before this suggested.

**It is not a detector and the brief says so.** The signals were chosen with the
answers visible, the threshold is fitted on the same 50 points that score it, and
the two families used are the only held-out families the suite has. Making it one
needs two families neither run used, a threshold fixed from this run rather than
refitted, and the separation surviving.

#### P15 — the kernel beats the rule, and the suite fails its own question

[`results/P15-multitool-20260910/`](../results/P15-multitool-20260910/BRIEF.md),
four families, three tools, three phrasings each, statements that name their fluid
instead of handing over a density **[ran]**:

| arm | accuracy | oracle's queries reproduced | queries | rejected |
|---|---|---|---|---|
| **kernel adapter** | **10/30** | **91/96 — 94.8%** | 118 | 19 |
| hand-written rule | 7/30 | 88/96 — 91.7% | 96 | 0 |
| **no tool layer at all** | **27/30** | — | **0** | 0 |

**A learned protocol beats a hand-written rule where the call is not a copy**, on
both metrics and narrowly: 94.8% against 91.7%, 10/30 against 7/30. That reverses
P13's verdict and locates it — a learned protocol loses to a regular expression
when asking for a tool means copying an expression already written, and wins when
it means choosing between three tools and building keyed arguments out of prose.
**P13 measured the suite, not the adapter.**

**And the control voids the question the suite was built for.** With no tool layer
at all the expert scores **27/30 while asking nothing**, three times either tool
arm. The domain corpus shows the table's values, and seven fluids times two
properties is fourteen numbers plus five conversions — memorisable many times over
from 600 examples. The tools were never necessary here, and adding them *hurts*.

**The arm that could kill the experiment was bought last**, against this project's
own rule, and the brief had already flagged memorisation as a known cost. Two arms
were paid for before learning the material could not support them.

**The fix is to the material, not the architecture**: give each problem its own
handbook, with properties drawn per case, so a value cannot be recalled and has to
be queried. The expert would know *which* property it needs — the physics — and not
*what it is*, which is the tool's job.

#### P14 — the expert's region has a hard edge, and the expert cannot feel it

[`results/P14-held-out-20260910/`](../results/P14-held-out-20260910/BRIEF.md),
`drag_force` and `orifice_discharge` — two families the expert never saw, same
domain, same question style **[ran]**:

| arm | in region | held out |
|---|---|---|
| control · expert alone, arithmetic repaired | 23/30 raw, **30/30 repaired** | 1/20 raw, **1/20 repaired** |
| sequential · domain plans, kernel executes | 9/30, 13/30 | 0/20, 0/20 |

**Repaired accuracy falls from 1.000 to 0.050.** That measure is the formulas
rather than the arithmetic, so this is not the expert failing to compute — it is
the expert not knowing the relation and writing one anyway.

**And nothing in the output marks the difference.** Same numbered structure, same
confident phrasing, invented physics: a "volume fraction" of `4/3 * pi/6`, a Stokes
criterion that is not the Stokes criterion, a drag force that is not the drag
force. The specialist that scores 30/30 on its own material produced that, in the
same voice.

**What it costs the design.** Per-region promotion is what lets the frontier be
withdrawn, and this says **"proven on this region" carries no information about the
request just outside it**. The evidence available when the promotion decision is
made is the agreement map, which records where the expert *has been tested* — not
where it stops working. The difference between those two sets is precisely where a
confident wrong answer appears with nothing watching. The rule needs a guard, and
this run says the guard is necessary without supplying one.

#### P13 — taking turns restores delegation, and the kernel loses to a thin harness

[`results/P13-sequential-20260910/`](../results/P13-sequential-20260910/BRIEF.md),
same 30 cases, same shared contract, **[ran]**:

| arm | raw | repaired | calls/case |
|---|---|---|---|
| **sequential · domain plans, kernel executes** | **9/30** | 13/30 | **4.7** |
| **control · domain alone, harness repairs** | **23/30** | **30/30** | 4.9 |
| *(P9 stacked)* | *4/30* | *22/30* | *0.6* |
| *(P9 domain alone, no tool)* | *1/30* | *30/30* | *0.0* |

**Sequential activation works, and it answers the question three steps could not
reach.** Delegation goes from 0.6 calls per case to **4.7 — eight times** — and
accuracy more than doubles. The competition that suppressed the kernel on 25 of 30
steps is gone the moment the two patches are never asked for the same word. §5's
option 1, this reference's own declared default, is measured at last and it holds.

**And the kernel loses its job to twenty lines of `re`.** The control — the expert
writing its chain with a thin harness executing the arithmetic exactly and **no
kernel weights loaded** — scores 23/30 raw and **30/30 repaired**. Asking the
kernel to write the expression for a physics label it does not understand is
asking the expert's job of the wrong patch.

**The bias in the sequential arm was measured, not assumed.** The kernel writes
`<calc>A = 1.96 * 1.27 = 2.4932</calc>` — an assignment and its own answer inside
the tag — and the evaluator rejects **16% of its 130 calls, touching 11 of 30
cases, none of which passed**. Accepting every recoverable form puts the ceiling
near 20/30, still below the control. Real, and it does not change the verdict, so
the arm is not re-run.

**What this costs the architecture, stated plainly.** The modularity §4 wanted is
reached — an expert with no protocol in its weights, no merged adapter — but it is
reached **without §4's mechanism**. On this suite a learned protocol has nothing
to contribute that a regular expression cannot, because there is one tool and the
call is a copy of an expression already written. `harness.lora` has to earn its
place where the call is *not* a copy: several tools, arguments to format, a choice
of which to use. That experiment does not exist yet.

#### The geometry of the two patches [ran]

252 shared modules, rank 16, each compared against chance for its own dimensions:

| | measured |
|---|---|
| what they READ (row spaces of `A`) | **0.99x chance** |
| where they WRITE (column spaces of `B`) | **3.87x chance** (median 3.42, max 10.05) |
| delta alignment (Frobenius cosine) | **+0.035** |

They read independently, write into overlapping directions, and their deltas are
not aligned. That is **contention over a shared output channel**, not a collision
of subspaces — which is why P11's disjoint modules did not help (write directions
belong to the residual stream, not to the matrix they are written from), and it
predicts that orthogonality regularisation or null-space projection would
reproduce P11's weighted trade rather than escape it: take the expert out of the
shared channel and the expert goes with it.

#### P11 — both weight-space fixes for delegation fail, and one closes a family

[`results/P11-disjoint-20260909/`](../results/P11-disjoint-20260909/BRIEF.md) **[ran]**:

| arm | raw | repaired | calls/case |
|---|---|---|---|
| domain (MLP only) | 1/30 | **30/30** | 0.0 |
| kernel (attention only) | 0/30 | 0/30 | **6.0** |
| **F3 · kernel + domain, disjoint matrices** | 0/30 | 5/30 | **0.2** |
| **F2 · kernel 1.0 + domain 0.5** | 0/30 | 0/30 | **3.5** |
| *(P9 · shared matrices)* | *4/30* | *22/30* | *0.6* |

**F3 closes the linear-algebra family.** Giving each adapter its own projections —
no matrix in common, nothing to sum — made delegation **worse** (0.2 against 0.6)
and cost most of the physics. Two adapters with no shared parameter still fight, so
the competition was never a collision in weight space: both deltas shape the same
output distribution, and where they live is irrelevant to that.

**F2 proves delegation is controllable and shows the price.** Weighting the kernel
up moved calls per case 0.2 → 3.5, seventeen-fold — and the expert disappeared with
it, repaired 0/30 against its own 30/30. Under a weighting the two halves do not
combine; one wins outright.

**Each half remains healthy alone**: the kernel calls 6.0 times per case trained on
attention only, the domain's physics is exact on the MLP only. The failure is
behavioural competition at the token, which is exactly why a magnitude knob trades
one half for the other. What remains is of a different kind: change what the expert
is taught to produce (P12), or make the losing behaviour **impossible** at decode
time — a logit mask on digits outside `<calc>` is the only intervention a competing
delta cannot out-vote, and it is not bought yet.

#### P10 — the honest frontier gap is +0.533, and half of +0.975 was the prompt

[`results/P10-baseline-recheck-20260909/`](../results/P10-baseline-recheck-20260909/BRIEF.md),
same 30 cases, P9's eval seed, 6000-token budget, **[ran]**:

| arm | accuracy |
|---|---|
| `qwen3.5:4b` under the **legacy** prompt ("show no working") | **0/30 — 0.000** |
| `qwen3.5:4b` under the **shared** contract | **14/30 — 0.467** |
| `gemini-3.8-flash` under the shared contract | **30/30 — 1.000** |
| **the honest gap** | **+0.533** |

**The prompt was worth 0.467 of the 0.975 P5 reported.** Every baseline in P5–P8
was told not to show its working while every treatment was trained to show it, so
the published gap was in part the difference between a model allowed to think and
a model forbidden to. The corrected figure replaces +0.975 wherever it is cited.

**And a token budget was worth the rest of the doubt.** At 2000 tokens the same
frontier scored 17/30 and the same local model 12/30: both were truncated
mid-chain, and `parse_answer` falls back to the last bare number, so a cut-off
derivation scores an intermediate value and reads as bad physics. The record now
carries the length, the tail and whether the agreed JSON appears at all; at 6000
tokens **neither arm has a single response without it**.

**The headroom survives, halved.** +0.533 is still a gap a withdrawal can fall
from — the clinical suite, where this project stalled, offered +0.05. And it
sharpens P7 rather than weakening it: the adapter with a calculator scores 1.000
where a fair baseline scores 0.467, so the treatment closes a real +0.533 and not
a manufactured +0.975.

#### P9 — composition under a contract the two halves share · DONE

[`results/P9-shared-contract-20260909/`](../results/P9-shared-contract-20260909/BRIEF.md).
Written before the run, so it is a plan and not a description.

P8's arms cannot be re-read, only re-run: the two corpora taught different
notations and every arm used the domain's system prompt. `training/protocol.py`
now holds **one** system prompt and **one** user instruction, imported by both
corpora and by the evaluation, and the instruction **says nothing about `<calc>`**
— if the prompt asked for tags, the prompt would be the protocol and the kernel
adapter would be decoration. The domain corpus is the oracle's own chains with the
tags removed and the arithmetic left in place. The two adapters now differ in
exactly one thing: whether the arithmetic is delegated. P6 and P7 stay
reproducible — 600/600 legacy messages unchanged **[ran]**.

**The measurement P8 was missing.** `training/physics/repair.py` re-evaluates each
step of a chain exactly and carries the corrected value forward, so *wrong formula*
and *right formula, wrong arithmetic* stop sharing a score. It recovers the
oracle's answer on **200/200** chains known to be correct **[ran]**. Without it,
the domain half's contribution is unmeasurable — and in P8 it was never measured.

| # | arm | what it answers |
|---|---|---|
| 1 | **domain** | Does the expert know the physics at all? Scored raw **and** repaired |
| 2 | kernel | The protocol, under a prompt that does not ask for it |
| 3 | **kernel + domain** | The claim |
| 4 | base | Attribution, bought last because it cannot kill anything |

**Arm 1 reported [ran].** The domain adapter's **repaired** accuracy is **30/30** against a raw **1/30**, with **0** tool calls. Its formulas are exact on every case; only its arithmetic fails. The gate (0.25) opens by a distance, the domain half is verified to contribute, and the composition arm is bought.

**The stopping condition, enforced in the runner and not in judgement.** If the
domain arm's repaired accuracy is below **0.25**, arms 2–4 are not bought: a
composition cannot be shown to gain from a half that contributes nothing.

**Falsification.** With the contract shared and the domain half verified, if
`kernel + domain` still fails to beat both halves alone, **weight-space
composition is dead** and §4 must be served another way — sequential activation
(§5 option 1) or disjoint target modules, neither of which is bought here.

**All four arms reported [ran].**

| arm | raw | repaired | calls/case |
|---|---|---|---|
| domain | 1/30 | **30/30** | 0.0 |
| kernel | 0/30 | n/a | **7.7** |
| **kernel + domain** | **4/30** | 22/30 | 0.6 |
| base (control) | **4/30** | undefined | 0.0 |

**1. P8's conclusion was the confound, and composition does compose.** With the
contract shared, `kernel + domain` beats both halves — 4/30 against the domain's
1/30 and the kernel's 0/30 — and inherits most of the physics, 22/30 repaired
against the domain's 30/30. Nothing here looks like the 0/30 P8 reported.

**2. The mechanism works whenever it fires, and it rarely fires.** Split the
composition's 30 cases by whether it delegated at all:

| | cases | passed |
|---|---|---|
| the composition delegated | 5 | **3 — 0.60** |
| the composition did not | 25 | 1 — 0.04 |

A fifteen-fold difference. The composition is not broken; **it delegates on 5 of
30 cases where the kernel alone delegates on all 30 at 7.7 calls each.** The
domain delta wins the competition for the format at almost every step, and the
kernel's protocol only survives where it does not.

**3. The finding that costs the most: the base is not at zero.** Under a prompt
that asks for a numbered chain, `Qwen2.5-3B-Instruct` with **no adapter** scores
**4/30** — a tie with the best composition, and above every adapter alone. Every
baseline in P5–P8 was measured under a system prompt that told the model to
**show no working**, while every treatment was trained to show working. The
headroom those steps reported is smaller than reported, by an amount this run
does not measure. **The +0.975 frontier gap and the 0/40 attribution arms inherit
this doubt and must be re-measured under the shared contract before being cited
again.**

**4. `repaired` is undefined for the base, not zero.** It writes a numbered
heading and puts the arithmetic on continuation lines: 83 numbered lines across
30 cases, of which the extractor can read **0**. The metric is valid where the
chain layout matches the corpus and nowhere else, and comparing repaired scores
across layouts would be measuring the layout — the same mistake character-α made.

**Deliberately not bought:** constrained decoding and tag repair (19 of P8's 30
stacked failures had every call clean, so syntax was never the dominant failure),
and further weighting knobs (one blend was pre-registered and run; a second would
be a search).

#### P8 — the protocol is separable, and it does not stack

[`results/P8-harness-lora-20260909/`](../results/P8-harness-lora-20260909/BRIEF.md),
`Qwen/Qwen2.5-3B-Instruct`, two adapters over one resident base, 30 held-in cases
each, the harness answering every `<calc>` call **[ran]**:

| arm | accuracy | tool calls | calls/case |
|---|---|---|---|
| base + tool | 0/30 | 44 | 1.5 |
| **kernel + tool** (never saw physics) | 1/30 | **169** | **5.6** |
| **domain + tool** (never saw a tag) | 0/30 | **0** | 0.0 |
| **kernel + domain + tool** (stacked) | **0/30** | 154 | 5.1 |

**The first half of §4 holds, and it is the surprising half.** A kernel trained
only on shop receipts, means, compound growth and cone volumes — *no pipe, no
fluid, no Reynolds* — walks into fluid mechanics and calls the tool 5.6 times per
case, on every one of 30 cases. The domain expert, which knows the physics, calls
it **zero** times in 30. The protocol is a thing that can be learned on its own,
in weights of its own, and it transfers to a domain its corpus never contained.

**The second half does not.** Stacked, the two adapters score 0/30 — below the
kernel alone. And the failure is not that one adapter wins: **both are visibly
present in the output**. The composition names the right physics *and* calls the
tool, and the calls come out corrupted:

    1. cross-sectional area: <calc>1.96 * 1.27</calc>= 2.4892
    2. wetted perimeter: <calc>1.96 + 2 * 1.27</calc>= 4.5
    3. hydraulic radius: <calc><b>2.4892</b> / 4.5</b>= 0.553133</calc>= ERROR: unparseable
    4. flow velocity: <calc>0.015 * 0.553133 * \sqrt{1 + 4*0.01518^2}</calc>= ERROR

LaTeX leaking through, stray markup inside the tags, terms dropped from formulas.
This is what two deltas at α=32 do to a base tuned for one: `LoraModel` **sums**
the active deltas, so the composition perturbs the weights twice as hard as
either adapter was trained under, and fidelity is the first thing to go.

**The falsification fired as written**: the composition did not beat both halves,
so the protocol does not compose *by stacking*. One alternative was bought, and
it was named in the brief before this number existed — `add_weighted_adapter` at
0.5/0.5, the mechanical correction for a doubled perturbation.

**The blend fails too, and it refutes the reason I gave for the first failure.**

| arm | accuracy | tool calls | cases with a call the evaluator rejected |
|---|---|---|---|
| kernel + tool | 1/30 | 169 | **0 / 30** |
| kernel + domain, stacked | 0/30 | 154 | 11 / 30 |
| **kernel + domain, blended 0.5/0.5** | **0/30** | 129 | **12 / 30** |

Halving each delta did not restore call fidelity — it got marginally worse. So
the corruption is **not** a magnitude effect, and "two adapters at α=32 perturb
twice as hard" was the wrong explanation, offered before the data that tests it.
What the blend does show is the corruption's shape: the chains keep the right
step names and the right order and lose the *content* — a Swamee-Jain line that
is not Swamee-Jain, a pipe's length substituted for its diameter, a tag opened
inside a tag. The kernel alone never malforms a call, on any of 30 cases.

~~**The reading that survives.** Two LoRAs trained independently on the same
projections do not sum into the union of their behaviours; they interfere, and
the interference lands on exactly the thing each adapter was most specific
about.~~ **Withdrawn the same day, 2026-09-09** — see the confound below. The
numbers above stand; this explanation of them does not.

#### The confound that voids P8's causal claim (2026-09-09) [ran]

Reading the two corpora side by side, after the arms had run:

| | kernel corpus | domain corpus |
|---|---|---|
| examples with `<calc>` | **600 / 600** | **0 / 598** |
| examples with LaTeX (`\text`, `\frac`, `$`) | **0 / 600** | **433 / 598** |
| its system prompt | "you may not perform arithmetic yourself: every computed number must come from a `<calc>` call" | "show no working in the final message: reply with one JSON object only" |

Three things are wrong with that, and each one is enough on its own.

1. **The two corpora taught different notations, not just different content.** The
   corruption I attributed to subspace interference — `\sqrt{...}` inside a
   `<calc>` tag, `\times`, stray markup — is the *superposition of two surface
   forms the adapters were literally trained on*. The calculator cannot parse
   LaTeX, so a chain that mixes them fails at the tag rather than at the physics.
2. **The domain corpus's system prompt contradicts its own targets.** It says
   "show no working" over 598 assistant messages that all show working. It is a
   leftover from P6's headroom prompt.
3. **Every arm was evaluated under the *domain's* system prompt**, including the
   kernel arm and both composition arms — a prompt that instructs the opposite of
   what the kernel was trained to do.

So P8 cannot distinguish *"weight-space composition fails"* from *"the two
adapters were taught to write in different languages and judged under a prompt
that matched neither"*. The second is simpler and fits every observation.

**What still stands, because it does not depend on the confound.** The kernel
called the tool on **30 of 30** cases and malformed **not one** — under a system
prompt that told it not to show working, in a domain its corpus never contained.
That is a stronger result for protocol transfer than the original write-up
claimed, not a weaker one.

**What is now known to be unmeasured.** The domain adapter emitted only
`{"answer": ...}` on all 30 cases — no chain at all under the eval prompt — so
whether it knows the physics was never measured. Its direct answers sit around
2x off. A composition cannot be shown to gain anything from a half whose
contribution has never been established.

**And syntax is not the dominant failure**, which the free diagnostic settled
before any of this was written: of the stacked arm's 30 failures, **19 had every
call clean** and still got the physics wrong. Repairing tags, or constraining
them with a grammar, addresses at most a third of the gap.

**What this costs the architecture.** §4's separation stands as a fact about
*learning* — the kernel exists, and it transfers to a domain its corpus never
contained — and falls as a fact about *serving*: the configuration that works is
P7's merged adapter, 40/40, and a change to the tool surface therefore costs a
retrain of every expert in the pool. That is the price §4 exists to avoid, and it
is not avoided.

**Not bought, deliberately.** Option 1 of `TECHNICAL-REFERENCE.md` §5 —
sequential activation, the two adapters never live at once — is untested and
cheap, since both adapters exist. It is not run here: the brief pre-registered
**one** alternative, and buying a third composition mode after two failures is
how a measurement turns into a search. It gets a step of its own, with its gate
written first, or it does not get bought.

#### P7 — the withdrawal gap closes, and it takes both halves

[`results/P7-calculator-20260908/`](../results/P7-calculator-20260908/BRIEF.md),
`Qwen/Qwen2.5-3B-Instruct`, 600 oracle-written chains, the harness answering
every `<calc>` call **[ran]**:

| arm | | accuracy | tool calls |
|---|---|---|---|
| teacher `gemini-3.8-flash` | 40/40 | **1.000** | — |
| base | 0/40 | 0.000 | 0 |
| base + calculator | 0/40 | **0.000** | **53** |
| adapter alone | 4/40 | 0.100 | 0 |
| **adapter + calculator** | **40/40** | **1.000** | 156 |

**The withdrawal gap is 0.000** on the region the expert was distilled for. And
neither half does it alone: the base made 53 tool calls and got nothing right;
the procedure without the tool got 4 of 40. `ARCHITECTURE.md` separates the
kernel that acts from the expert that thinks — here that separation is the
difference between 4/40 and 40/40, with each half held out in turn.

**The bound is the architecture's own.** The held-out families were at 0 of 10
when the session ended: the expert does not generalise outside its region, which
is exactly why the plan promotes and withdraws **per region**. That arm did not
finish, and 0/10 is reported as observed rather than as a persisted result.


#### P3 resolved — the substrate exists, on a base vLLM can serve

`Qwen/Qwen2.5-3B-Instruct` — `Qwen2ForCausalLM`, dense, no vision tower — on an
A100 with vLLM 0.28.0 **[ran]**:

    [gate] adapter changes output: True
    [pure batch]  20/60 = 0.333   77.66 prompts/s

The gate passed, and the served accuracy matches what `transformers` measured for
the same recipe (18/60). **Two implementations agreeing is what P3 was built to
check**, and it is the first time this architecture's layer 1 has existed.

By elimination the earlier silence is explained: `Qwen3.5-2B` is hybrid and
multimodal, and the vLLM class declaring `SupportsLoRA` is neither.

**The mixed-batch arm is voided, and the fault is this repository's.** It called
`generate()` once per prompt while cycling adapters — sixty sequential
round-trips — and reported 3.85 prompts/s against 77.66, which reads as a 20×
penalty for holding a pool. It measured the loop. Pricing the pool honestly needs
per-request adapters *inside one scheduling pass*: the async engine, or the
OpenAI-compatible server with one model name per adapter. Until then that arm
reports nothing.


#### P3 — the pool is not servable, and it fails without saying so

[`results/P3-vllm-20260908/`](../results/P3-vllm-20260908/BRIEF.md), A100,
vLLM 0.28.0, `Qwen/Qwen3.5-2B` **[ran]**:

| arm | accuracy | throughput |
|---|---|---|
| base, no adapter | 0.100 | — |
| `all-clinics` | **0.100** | 90.2/s |
| `alpha` | **0.100** | 93.3/s |
| `beta` | **0.100** | 92.7/s |

Every adapter scores **exactly the base's 6/60**, and a direct two-prompt check
returned `RESULT IDENTICAL` both times: the served text is byte-for-byte the base
model's. vLLM accepted every `LoRARequest` **with no error and no warning** and
applied nothing.

Ruled out: the adapter files are valid (`adapter_config.json` + 43 MB
`adapter_model.safetensors`), `base_model_name_or_path` matches, `max_lora_rank`
matches `r`, and there is no V0 to fall back to — `VLLM_USE_V1` is an unknown
variable in 0.28.0. Open: V1 LoRA support is documented as experimental
**[read]**; `q_proj`/`k_proj` under Qwen3's QK-norm is exactly the mapping a
serving stack must rebuild; or a regression in this version.

**The arm that caught it was the one that looked redundant** — "the same numbers
must come out". Measuring only throughput would have reported three adapters
served at 90 prompts/s and called the substrate proven.

**P4, P5 and P6 all serve adapters, so none of them can be bought until an
adapter demonstrably changes vLLM's output.** The next move is a decision, not a
run: pin a different vLLM version, or retrain the pool without `q_proj`/`k_proj`
and re-test. Both are cheap; choosing between them is not this session's call.

### Open: how to get an adapter graded at all

Six infrastructure failures and three reclaimed sessions, and the adapter has
never been scored. The choice is between:

1. **Chain short sessions.** One arm per session, uploading the partial results
   at start and pulling them at the end. The persistence already exists in one
   direction; this adds the other. No money, more orchestration, and each arm has
   to fit in ~15 minutes.
2. **Colab Pro.** Longer tenure and an L4 or A100 — which also has bf16, so the
   fp16 path stops being needed. Costs money and is the user's call.
3. **Another provider.** New surface area, and the workspace rule is that new
   surface area is the expensive kind of progress.

Recommended: **1, then 2 if a chained run also fails.** The base arms are already
banked, so the next session only owes the adapter.

### Open: where a frontier advantage is visible at all

S1 says this suite cannot show one. Three configurations could, in ascending
cost, and the choice is the user's because it decides what the project measures:

1. **Put the runtime loop back in.** The published 38–41/50 came from contract,
   feedback and action validation; single-shot raw is 33–60 %. If the frontier's
   advantage is in *using* an interaction contract rather than in one-shot
   accuracy, this is where it appears — and it reuses `../verified-runtime`
   wholesale.
2. **A harder domain.** `causal_workflow` and `quantum` already exist next door
   with their own verifiers. A task with a real solution space is where a 12B
   should fall away from a frontier model.
3. **A different task shape entirely** — long-context legal or clinical
   documents, which is the vertical the architecture was written for and the one
   place where a local 12B is least likely to hold.

Until one is chosen, S4 and S5 cannot be bought: promoting an expert and
withdrawing a frontier that was never ahead measures nothing.

## 12. History

| date | change to this plan | why |
|---|---|---|
| 2026-09-09 | **P8 run: the protocol is separable but does not stack.** A kernel that never saw physics calls the tool 5.6x/case in fluid mechanics; the physics expert calls it 0 times; stacked they score 0/30 with both behaviours visibly present and the calls corrupted. The blend at 0.5/0.5 was pre-registered before the number existed | §4 separates what the kernel owns from what the expert owns, and only the merged case had ever been measured — the half that holds and the half that does not are different halves than the architecture assumed |
| 2026-09-07 | plan created; S0 built and run; the α-versus-quality test moved ahead of adapter training | the specification's E1 validates α only after adapters exist, which is where the test stops being cheap |
| 2026-09-07 | S0 run three times; §3 filled in; C9 and C10 added; the redesign counter reached its stopping condition and the instrument was **not** changed a fourth time | the metric was measuring layout, and the rule about counting redesigns exists precisely for the moment it is inconvenient |
| 2026-09-07 | S6 moved from "parallel" to "under review, possibly upstream of α" | if the kernel adapter is what pins the format, then it is what makes character acceptance mean anything |
| 2026-09-07 | S1a run on `held_out_delta`: 8/12 against 3/12 and 4/12. S1's suite question closed for $0; only the key still blocks it | the fallback was named in the step before the step ran, which is the only reason changing the split here is a plan and not a search for a friendlier number |
| 2026-09-08 | S3 answered offline from S4's records: agreement picks the correct expert on 9 of 10 decisive cases and recovers 0.725 of a 0.750 oracle — and ties exactly with reading `clinic:` out of the prompt | the mechanism is real and this suite cannot price it, because it labels the region the router is supposed to infer |
| 2026-09-08 | **S4 complete. Question 2 answered: own region 0.725 against other 0.525, diagonal winning both ways — but on `alpha`'s cases the two experts differ by one case of twenty, so the signal is asymmetric.** The first region arm was voided for an unmatched training budget | there is a pool to route between, and the routing problem is now known to be uneven across regions rather than assumed uniform |
| 2026-09-08 | **S4 question 1 answered: the adapter scores 44/60 against the base's 6/60, +63.3 points, and gains 20 points on the inverted-rule split it never saw.** C17 added | the first real result this project has produced, and the third zero before it was gradient checkpointing rather than the model |
| 2026-09-08 | S4 run on `Qwen/Qwen3.5-2B`: base arms banked at 6/60 and 6/30; adapter arms blocked. C15 and C16 added; the abort rule fired at the third reclaimed session | the 0/60 the T4 produced would have read as "specialisation did not happen" — a falsification condition met by the GPU rather than by the model |
| 2026-09-07 | S1 bought and failed three times ($0.47 total); S2 bought in the same purchases and passed 14 of 15 pairs; C12 and C13 added | the gate was written before the run and it fired — the cheapest possible outcome, since it stopped S4 and S5 from being bought on a configuration where the frontier was never ahead |
| 2026-09-07 | a fourth candidate (`qwen3.5:2b`) added at the user's suggestion | the local ladder tied at 6/20 and a tie makes the ordering test unbuyable; spanning 2B to 12B gave the criterion something to be right or wrong about |
| 2026-09-07 | targets given their own token budget, and local answers cached | a thinking target returned 9 of 20 answers truncated at 700 tokens, and re-generating four local candidates for every new target was eight minutes buying nothing |
| 2026-09-07 | S1a extended to the full 20-case split; the n=12 ordering agreement **did not survive** and the superseded row is struck, not deleted | the candidates differed by one verified case at n=12 and tie exactly at n=20 — one case was never an ordering, and a plan that quietly dropped the earlier row would be a record of nothing |
| 2026-09-07 | S6a run for $0 from existing runs: the protocol costs ~96 tokens here and the 12B never malforms, so S6 needs a real tool distribution before either of its numbers means anything | checking the headroom of the treatment before building it is the cheapest run there is, and this one cost no inference at all |
| 2026-09-07 | C11 added and surfaced in the report | the model with the best agreement was also the one that answered nothing 25 % of the time, and the criterion was quietly excluding exactly those cases |
| 2026-09-07 | §11 decided (option C): the promotion criterion is semantic answer agreement; S2 rewritten around it; S6 gained a second win condition; the four runs on disk were re-scored without re-running anything | character agreement failed on a correct answer and succeeded for reasons unrelated to quality, on the same suite, on the same day |
| 2026-09-07 | a tie in verified quality is no longer reported as a failed ordering test | S0c's candidates both scored 3/12, and calling that a disagreement manufactures a failed test out of an untestable one |
| 2026-09-07 | reporting bug fixed — the overall ordering used the payload metric while the per-region ordering used the raw one, so one report claimed agreement and disagreement about the same run. Not a redesign; the counter stays at 3 | a report that contradicts itself in two lines is worse than one that says nothing |
