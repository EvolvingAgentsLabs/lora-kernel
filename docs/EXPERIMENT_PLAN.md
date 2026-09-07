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
| **S1** | headroom: can this suite show a withdrawal gap at all | S2 | ~$5 | **suite answered locally ([`S1a`](../results/S1a-delta-20260907/BRIEF.md)); frontier arm blocked on a key** — §4 |
| **S2** | does **agreement** order candidates the way verified quality does | S4 | ~$15 | **local proxy DONE, frontier arm blocked on a key** — §5 |
| **S3** | attribution: does a lexical/embedding router do the same job | the routing claim | ~$0 | `NEXT` after S2 |
| **S4** | two real QLoRA adapters on regions where S2 showed signal | S5 | GPU rental | `NEXT` after S3 |
| **S5** | **the withdrawal gap** | the product | GPU + frontier | `NEXT` after S4 |
| **S6** | `harness.lora` against the −85 % schema baseline | the kernel | GPU rental | **under review — S0 says it is upstream of α, §12** |
| **S7** | the tournament, with a held-out verifier | evolution | GPU rental | after S5 |

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
| **`held_out_delta` (S1a)** | **8/12** | **3/12** | **4/12** |

**There is headroom, on the split whose planted rule inverts.** The 12B pulls
+4 clear of its best drafter where it was tied before, and the drafters separate
from each other. This is what the frontier arm needs to exist: a configuration
where being better is possible. The suite question is answered — **S1 is worth
its $5 on `held_out_delta`, not on `held_out`.**

**And it produced the trap C9 predicted, in the form that would have been
believed.** Ordering by α matched ordering by verified score (9B > 4B) — for the
wrong reason: the 9B pretty-prints like the target and the 4B does not. A
confirmation of the project's central claim, arriving by accident of
indentation. The report now refuses to interpret that line while C9 stands.

**Blocker for a human — one now, not two.** `OPENROUTER_API_KEY` is not set on
this machine and is not on disk **[ran]**. The run is one command once it
exists, and it now has a suite worth pointing at.

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

**S2a — the local proxy, computed at $0 from runs already on disk.** The criterion
was applied to the persisted answers of S0c and S1a; no inference was re-run
**[ran]**:

| run | | agreement | verified | orderings |
|---|---|---|---|---|
| S0c `held_out` | `qwen3.5:4b` | 0.667 | 3/12 | **not comparable** — the candidates |
| | `qwen3.5:9b` | 0.727 | 3/12 | tie on quality, so there is no order to reproduce |
| **S1a `held_out_delta`** | `qwen3.5:4b` | 0.333 | 3/12 | **agreement 9b > 4b** |
| | `qwen3.5:9b` | 0.556 | 4/12 | **verified 9b > 4b — they agree** |

One informative comparison, two candidates, n = 12, against a **local stand-in
target**. That is not a distillation score and is not evidence for the thesis: a
12B that itself scores 8/12 is not a frontier model, and agreement with it means
agreement with a peer. What it does establish is that the criterion is
computable, is not degenerate, and did not contradict quality on the only
configuration where quality separated. The real S2 needs the frontier target.

**Gate.** S4 — no adapter is trained until acceptance is known to carry the
signal that promotion would be based on.

**Falsification.** The orderings disagree, or agreement is flat across candidates
that differ in verified quality. Either kills acceptance as a promotion criterion; the
adapter pool survives, the free router does not, and the plan reopens at the
router.

**Second control, same run, free.** α dispersion. If every candidate accepts
alike, there is nothing to route on regardless of what α means.

## 6. S3–S7 — the steps that cost money, and what each has to clear first

**S3 · the attribution arm.** A lexical rule and an `embeddinggemma` classifier
routing the same cases. If either matches acceptance-routing, the expensive
mechanism bought nothing — the shape of a result this workspace has already had
once, when a memory hierarchy lost to plain lexical search **[read]**. Bought
only after S2 shows an effect, never before.

**S4 · two adapters.** QLoRA trained off this machine and graded here — the
training environment does not decide whether the training worked. Only on regions
where S2 found signal. **Gate:** the adapter's α must beat the best stand-in's α
in its own region, or the training added nothing acceptance can see.

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

## 11. The decision on the table

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

**Decided 2026-09-07: C.** The promotion criterion for S1–S5 is semantic answer
agreement, character α is reported beside it and ranks nothing, and S6 owns the
question of whether pinning the format reconciles the two. Implemented in
`alpha/report.py::semantic`, pinned by six tests, and applied retroactively to
every run already on disk — the criterion is computed from the stored answers, so
nothing had to be re-run.

## 12. History

| date | change to this plan | why |
|---|---|---|
| 2026-09-07 | plan created; S0 built and run; the α-versus-quality test moved ahead of adapter training | the specification's E1 validates α only after adapters exist, which is where the test stops being cheap |
| 2026-09-07 | S0 run three times; §3 filled in; C9 and C10 added; the redesign counter reached its stopping condition and the instrument was **not** changed a fourth time | the metric was measuring layout, and the rule about counting redesigns exists precisely for the moment it is inconvenient |
| 2026-09-07 | S6 moved from "parallel" to "under review, possibly upstream of α" | if the kernel adapter is what pins the format, then it is what makes character acceptance mean anything |
| 2026-09-07 | S1a run on `held_out_delta`: 8/12 against 3/12 and 4/12. S1's suite question closed for $0; only the key still blocks it | the fallback was named in the step before the step ran, which is the only reason changing the split here is a plan and not a search for a friendlier number |
| 2026-09-07 | S6a run for $0 from existing runs: the protocol costs ~96 tokens here and the 12B never malforms, so S6 needs a real tool distribution before either of its numbers means anything | checking the headroom of the treatment before building it is the cheapest run there is, and this one cost no inference at all |
| 2026-09-07 | C11 added and surfaced in the report | the model with the best agreement was also the one that answered nothing 25 % of the time, and the criterion was quietly excluding exactly those cases |
| 2026-09-07 | §11 decided (option C): the promotion criterion is semantic answer agreement; S2 rewritten around it; S6 gained a second win condition; the four runs on disk were re-scored without re-running anything | character agreement failed on a correct answer and succeeded for reasons unrelated to quality, on the same suite, on the same day |
| 2026-09-07 | a tie in verified quality is no longer reported as a failed ordering test | S0c's candidates both scored 3/12, and calling that a disagreement manufactures a failed test out of an untestable one |
| 2026-09-07 | reporting bug fixed — the overall ordering used the payload metric while the per-region ordering used the raw one, so one report claimed agreement and disagreement about the same run. Not a redesign; the counter stays at 3 | a report that contradicts itself in two lines is worse than one that says nothing |
