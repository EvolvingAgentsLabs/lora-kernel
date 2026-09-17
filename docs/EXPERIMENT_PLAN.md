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

## 0b. The order of dependencies — phases, bottom-up (adopted 2026-09-17)

The plan is a stack: **each layer is validated alone, frozen with a test that
protects it, and only then is the layer above built on it.** `CLAUDE.md` §8 carries
the rule; this is the state. No piece counts as working until it has (a) a
preflight, (b) a persisted artefact, (c) a test that re-verifies it every session,
and (d) a failure condition written before it runs.

| # | piece | depends on | gate | state |
|---|---|---|---|---|
| **0** | the serving substrate — C18 on every member (≥ 2 of 3 probes differ), tools reachable through the proxy, stop honoured. Spec: [`SUBSTRATE-GATE.md`](SUBSTRATE-GATE.md) | — | `verdict.json` `pass: true` | ✅ **[ran]** P56, 2026-09-17: both members `applied` **3/3**, tools reachable through the proxy (`email-full` 1 tool call; `fluids-full` none — pruned to its own surface), stop honoured. `results/P56-substrate-20260917/verdict.json` |
| **1** | a reproducible release of `email-full`: adapter + corpus + prompt hash, re-served in corpus mode and paired against its recorded 471/475 | 0 | the re-serve is a tie by the paired test | ✅ **[ran]** P57, 2026-09-17: re-served vs recorded **0 : 0** discordant (identical case by case); re-trained from the same corpus and recipe **472/475**, vs re-served **1 : 0**, $p = 1.0$ — **training variance: one case in 475**. Manifest `releases/email-full@v1.json` |
| **2** | a suite with a verifier and a gradient: `suite_gates`; base gradient ≥ 0.30 across depth; the target beats the best expert, paired, $p \le 0.05$ (M-target, FOUNDATIONS §7.2) | 1 | all three on one region | desk `commitment`: gradient **1.000 → 0.000** and target **1.000** at every depth **[ran]** P51; M-target formally re-tested in Phase 3's session against the best grade |
| **3** | experts the verifier orders (M1): `g25 ⊂ g75 ⊂ 600`; **the smallest grade is trained and scored first** — if `g25` already saturates, stop | 2 | ≥ 1 adjacent pair resolved, $p \le 0.05$ | **P58 attempt 1** **[ran]** 2026-09-17: two instrument faults, mine — the corpus-mode loop crashed on a closing tag with no canonical opening (`g25` writes `<message id="msg-006" from=…>`, *fabricating* the email in XML instead of asking for it — 209 of 240 chains lost) and the C18 gate read an errored record as a difference (`applied` 8/8 over nothing). Both fixed with tests; `--max-model-len` 8192 for the desk (7 base requests hit 400 at 4096). Base in corpus mode **41/240 = 0.171** (it wanders into self-closing XML). **Attempt 3 clean [ran]: `g25` = 0/240** — 1152 of 1194 calls malformed, it *fabricates* the email in XML in 240 of 240 cases; C18 `applied`, 0 errors. **The kill condition did not fire** ($Q(g25) = 0.000 \ll 0.95$): the bottom grade exists. **P55b [ran]** 2026-09-17: `g75` **240/240**, `g600` **240/240**, `g25` 0 — M1 passes on **one bit**: the two resolved pairs are *broken vs perfect*, and `g75` ≡ `g600` (0 : 0). **The saturation risk was real: 75 examples suffice for a one-call protocol; no intermediate grade exists on this suite** |
| **4** | the ordering verdict by acceptance (M-α, M2): three α per case, SUPPORTED / FALSIFIED / UNRESOLVED-as-failure written first (§7.4) | 3 | the thesis itself | **P55b stopped at M-target [ran]**: the 32B in corpus mode **227/240**, **232/240** once the verifier stopped rejecting `2023-01-05` for `January 5` (5 of its 13 losses were format; the check was deleted); the remaining 8 are real — it wanders `thread_history → inbox` and says *no date*. Against `g600` at 240/240: **0 : 8, $p = 0.008$** — the untrained target is resolvably below the trained expert, **the second time** (triage: 0.746 vs 0.989). **Not measured.** Redesign counter: 2 of 3. ~~Closed 2026-09-17 (decision D): M2 is not buyable on any suite this project can generate~~ — **corrected the same day by review: what is measured is that the window does not exist in two easy regions with an *untrained* target.** The ordering between grades is decided by the material's difficulty, and a trained target enables $Q(T) \ge \max Q(E)$. **Reopened as one arm (P60, next): a 32B trained on the desk + a deeper `commitment` band where trained grades do not saturate + M-target under §7.2's `≥`.** A brazo, not the last redesign; if the window still does not appear, the closure is signed with the right arm run |
| **5** | the product with real groups (CASE-TEAM), `--prune` off as the attribution arm; every new member enters through Phase 1's door | 1 | 0.546 → 0.775 reproduced on new traffic, the leaving share measured | **P59 [ran]** 2026-09-17, the surface OpenClaw actually sends (54 tools, recorded): `--prune off` human **0.664**, 227 calls of which **225 refused** — it copies `agents_list`, `apply_patch`, `browser`… off the block; `--prune on` **0.729**, 1160 calls, 8 refused. Paired 87 : 64, $p = 0.073$ — **a tie on accuracy at $n = 475$, not a tie in behaviour**: unpruned, the expert reaches for the runtime's own tools. Block **~7,956 → ~77 tokens** per turn. `--prune` is the recommended default. Attempt 1 void (context 4096) |
| **6** | the route to `Qwen3.8-27B`: D2 (C18's mechanism, with the log) → D3 → D4 | **4 = SUPPORTED** | D2: `applied` on the identity gate | **blocked by design** — 4 closed without a verdict; not by the tokenizer, not by C18 |

**The three outcomes of Phase 4 are committed now.** SUPPORTED opens Phase 6 and the
tournament. FALSIFIED closes acceptance-as-ranking for good and the README is
rewritten around the measured product. UNRESOLVED permits one more redesign — the
third is the stopping condition (counter: 2 of 3 after P55b).

**Map from the mechanisms above to the phases:** C18 → 0 · S9, S10 → 1 · P50
suite gates, headroom, M-target → 2 · M1 → 3 · M-α, M2 → 4 · S8, S3, pool > 2 → 5 ·
D2–D4 → 6.

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

---

### Restated 2026-09-16, and this is the version that is buildable

The question above was never answered — it **dissolved**, because the configuration
it assumed was not constructible. A frontier API cannot be a speculative target at
all: it returns no logprobs for a *forced* continuation (C2) and does not share the
base's tokenizer (C3) **[ran]** P48. So claim 1 was never priced (S3 tied with a
regex reading `clinic:` out of the prompt) and claim 2 closed with a calculator
rather than with acceptance (P7, 40/40).

**The same question, in the configuration that exists:**

> **Does acceptance against a larger model of the same family order small experts the
> way verified quality orders them — and can that model then be withdrawn, per
> region, without the verified score falling?**

Every word of that is now measurable, and none of it was on 2026-09-07:

| what it needs | state |
|---|---|
| a target whose tokens ours can be verified against | **`Qwen2.5-32B-Instruct-AWQ`** — byte-identical `tokenizer.json`, 19.3 GB, fits beside the 3B on an A100 **[ran]** P48 |
| a pool that serves several adapters over one base | **built, measured three times**, including with a stranger's adapter **[ran]** P40/P41/P42 |
| a suite where acceptance and verified quality are both readable | **built** — `training/email/desk.py`, four regions × four depths, mechanically checkable answers |
| a suite whose numbers are evidence | **seven gates in code**; all four previous suites failed, the new one passes three and waives one by name **[ran]** P50 |
| a corpus that can produce a drafter worth accepting | **known and not yet built** — it must be generated by the **target**, not by an oracle |
| experts close enough that choosing between them is a real question | **not yet** — the two we have are told apart by twelve keywords at 1.000 |

**What changed about claim 2.** The frontier is not what gets withdrawn — it is the
permanent fallback for what the pool is *measured* to fail, worth **0.546 → 0.775**
**[ran]** P41. What a high acceptance rate would let us withdraw is the **local
32B**, per region, which is a cheaper and more honest version of the same product.

**What falsifies the restated question, unchanged in spirit:** if acceptance does not
order the experts the way the verifier does, on the same cases, the free router does
not exist. The pool, the serving substrate and region routing all survive that; only
the router is lost, and it is a dict today anyway.

**What is out for good.** Acceptance against a *frontier API* — not hard, impossible.
Weight-space composition and `harness.lora` — dropped on measurement, and piping
costs nothing if they are ever wanted. An EAGLE head as a ranking mechanism — one
head per target, nothing to choose between.



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
| **S9** | a **region** that is somebody's morning, and the multi-turn loop | delivery | free | **the loop closes** — 24 calls, 0 refused, 0 undecided; the suite's ceiling from the listing is exactly its majority class, and its truth is mechanically checkable (P30) |
| **S8** | the pool behind an **OpenAI-compatible endpoint** | delivery | GPU rental | **DONE for serving, priced for tool-calling** — each adapter is its own model name and applies (P26); the tag→`tool_calls` converter is domain-free, 604/604 round trips (P27); the schema→tag direction costs **0.188** (P27 arm 3) |

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


#### P24 — a grammar mask buys cleanliness, not accuracy

[`results/P24-constrained-20260912/`](../results/P24-constrained-20260912/BRIEF.md).
Masking the sampler so a malformed call is impossible rather than unlikely. Refusals
fall **23 → 10** while the oracle's tool values stay at **94/96, identical** — the
trade it was built for, and a coverage *rise* would have meant the grammar was doing
the adapter's job. The final answer moves 5/30 to 4/30, which is one case: **P21
already showed 22 of 25 failures were physics with every value in hand.** The
prediction, replayed offline over P21's transcripts, said 74% of refusals would
become impossible and it was 57% — a good predictor of direction, an optimistic one
of size, because the repair is a property of the failure distribution it meets rather
than a constant of the mask. And the treatment crashed once on a shape
`grammar_check.py` could not see: Qwen pads its embedding matrix past the vocabulary,
and **a checker that verifies the grammar is not a checker for the sampler**.

#### P28 — one schema convention works, the other backfires

[`results/P28-schema-conventions-20260914/`](../results/P28-schema-conventions-20260914/BRIEF.md).

| arm | oracle's tool values | refused |
|---|--:|--:|
| trained instruction | 59/96 = 0.615 | 17 |
| OpenAI schema, plain | 41/96 = 0.427 | **88** |
| **schema + arity** | 51/96 = **0.531** | **17** |
| schema + arity + enums | 48/96 = 0.500 | 37 |

**Arity — one required parameter renders positionally — drops refusals to the trained
arm's exact number and recovers 55% of the schema's cost**, with 0 of 48 lines naming
a tool or a domain.

**Enums were predicted to do nothing here and made it worse.** They fixed what they
aimed at — `property=D` appears seven times without them and never with them — and
handbook misses rose **3 → 17**: telling the adapter part of the vocabulary made it
query more confidently and miss on a different argument. **"56% of out-of-domain
refusals are names" survives; "so tell it the names" does not follow.**

#### P30 — a region that is somebody's morning, and the first multi-turn run

[`results/P30-email-triage-20260914/`](../results/P30-email-triage-20260914/BRIEF.md).
Triaging one person's mail is a narrow task repeated daily, and unlike fluid
mechanics **the right answer is mechanically checkable** — a verifier without a
judge, which is what S7 still lacks.

**The suite had to fail its own test twice before it was worth running.** A
listing-only rule reached **0.795** against a 0.520 bar in the first draft, because
`Re:` was written exactly when the user had replied and the preview carried the ask;
**0.770** in the second, because `noreply@` is visible and automated is never
important. The second failure corrected the instrument rather than the material:
spotting an automated sender is free and a human does it at a glance, so the ceiling
is checked on the **human** messages, where it lands at **0.680 against a bar of
0.680** — exactly the majority class, with all 0.320 of the remaining margin owned by
the tools.

**And the multi-turn loop ran for the first time.** `docs/SERVING.md` called it
assembled and not measured; an OpenAI client sending `tools=[…]`, reading
`tool_calls`, executing them and returning `role: "tool"` results closed the path at
**24 calls, 0 refused, 0 undecided**. That is now a test rather than a hope. **No
trained model has been run on this suite** — the stub proves the plumbing, not the
pool.

#### P44 — the confidence this pool already has does not order its errors

[`results/P44-calibration-20260915/`](../results/P44-calibration-20260915/BRIEF.md).
A headroom check bought **before** any typed adapter was trained, because the
proposal in [`docs/analysis/typed-adapters.md`](analysis/typed-adapters.md) rests on
a claim — *a first-token logprob is a poor proxy* — that arrived **[read]** from a
brief citing a lab with no public benchmark, and that is testable on our own model
for free.

| | `email-full` | base |
|---|--:|--:|
| accuracy, **no tools** | 0.425 | 0.345 |
| **mean confidence** | **0.902** | **0.999** |
| ECE | 0.478 | 0.654 |
| **AURC** | **0.612** | 0.627 |
| oracle floor | 0.213 | 0.289 |
| **gap** | **0.400** | **0.338** |

**The base says it is 99.9% sure and is right 34% of the time** **[ran]**.

**The pre-registered middle row is what makes this readable.** A confidence that is
miscalibrated but *rankable* is fixed by temperature scaling, which costs no
training — and that would have been the honest answer to a large ECE alone. **These
are not rankable**: 0.40 and 0.34 above the floor. The typed arm is **bought**, not
tied and not cancelled.

**The caveat travels with the numbers**: these accuracies are tool-free, one forward
pass from the listing, which is why 0.425 and not P43's 0.741. That is the
like-for-like baseline a typed head would face, and it is not the expert doing its
job.

**The floor to beat is now explicit**: AURC gap **0.400** on 351 cases, with
`bar.calibration()` as the instrument.

#### P43 — the end-to-end runs, and the gate can finally decide

[`results/P43-openclaw-e2e-20260915/`](../results/P43-openclaw-e2e-20260915/BRIEF.md).

**The gate decides now.** 260/351 human messages = **0.741** against a bar of 0.655,
passing at 246, **exact one-sided p = 0.00036** — clear by fourteen cases, not by
one **[ran]**.

**And the accuracy barely moved**: 0.726 → 0.741, inside the spread three earlier
runs already showed. What changed is the gate. The **84, 81, 82** that straddled a
threshold of 83 were never the model wavering — **the suite was too small for the
effect and the threshold sat inside its own dispersion**. Power at n = 351 is
**87%**; at n = 113 it was **47%**.

`bar.n_for(0.655, 0.071)` fixed the size *before* the run, and the brief
pre-registered that landing near the threshold again would be read as **a smaller
effect, not a bigger suite**.

**The end-to-end runs**: OpenClaw on the user's Mac → local proxy → cloudflared →
vLLM on an L4 → the `email-full` QLoRA → back, `status=200`, `NOT IMPORTANT`,
`stopReason=stop`, and **zero requests left the machine**.

**What it does not show.** The OpenClaw turn made **no tool calls** — OpenClaw sends
its own tools, not the inbox's, so the expert answered from the listing alone, which
is what the base does. **The 0.741 comes from `agent_sim`, which supplies the inbox
tools and executes them.** The agent turn demonstrates the transport; the suite
demonstrates the expert. Wiring the inbox tools into OpenClaw is real work and is
not done.

**Three things running it found that no test could**: a doubled `/v1` in the
fallback URL (every test stubbed the fetch), `config patch` taking `--file` rather
than a positional argument (the manual was wrong two hours after being written), and
**OpenClaw streaming by default** with its per-model `streaming: false` not taking.
The proxy's refusal — *refuse rather than fake* — was right while the alternative was
a misleading measurement and **wrong when the alternative was being unusable**.

#### P41 — routing the failures to the frontier, with the frontier measured

[`results/P41-routing-20260915/`](../results/P41-routing-20260915/) ·
`training/harness/routing.py`. The pool's experts are not equally good, so the
frontier stops being scaffolding to withdraw and becomes a **fallback for what the
local expert is measured to fail at**. This is that, in numbers.

**`google/gemini-3.8-flash` on the fluids suite, through the same client the local
expert uses: 66/90 = 0.733** **[ran]** — not 1.000, so the earlier `≤ 0.871` was a
bound and is now replaced by a result.

| policy | delivered | leaves the machine |
|---|--:|--:|
| everything local | 0.546 | 0% |
| **fluids → frontier, by region** | **0.775** | **38%** |
| by case · tripwire `has_left_its_region` | 0.378 | 37% |
| by case · quality gate `is_probably_wrong` | 0.689 | 91% |

**Routing by region works and pays: +0.23 delivered, and 62% of the work stays on
one resident base.** That is the pool's economic argument stated as a measurement
rather than a hope — we pay the frontier only for the part we measured we cannot do.

**And routing by case is worse than by region, which is the finding.** Both
escalation rules — built and measured in P19/P21 — detect a chain that is
**dimensionally or mechanically inconsistent**. This expert's chains are perfectly
consistent and the physics is wrong: it follows the procedure, the units close, the
arithmetic closes, the answer is not right. **The rules are looking for a failure
this expert does not have.**

So the open problem is sharp and it is new: **a routing signal that can see a chain
which is coherent and wrong.** That is exactly where the parked acceptance
machinery has a job — not as a promotion criterion for training, but as the
per-case trust decision — and it is the reason §11's restatement keeps it rather
than retiring it.

**Two instrument findings paid for here.** The frontier first scored **0/4**, and
reporting that would have said *"the frontier cannot do this suite either"* — the
most interesting and most false conclusion available. It was a tool refusing
`T=20 C` for its phrasing and a token cap cut to the length of an expert whose final
messages are 19 characters. Fixed, it scored **5/6** on the same probe **[ran]**.

#### P37–P40 — the pool serves two experts, and only one of them is good

[`results/P40-pool-retried-20260915/`](../results/P40-pool-retried-20260915/BRIEF.md).
A second expert on a genuinely different subdomain — fluid mechanics, chosen over a
calendar suite precisely because the distance between the domains is what the thesis
claims does not matter — trained the same way and served **beside** the email expert
in one vLLM.

**The substrate works, measured three times.** Both adapters applied, **distinct from
each other**, one resident base, each routed by the `model` field of an HTTP request
to its own client and its own oracle **[ran]**. The distinctness check is new: two
names over one adapter would produce two respectable numbers and be one expert, which
is the failure that looks most like success.

**Co-residency costs the working member nothing**: 84/113 alone against 81 and 82 in
two pool runs, every pair a tie, with 393/393/390 tool calls **[ran]**.

| member | score | calls | refused | out of turns |
|---|--:|--:|--:|--:|
| `email-full` | 82/113 = 0.726 | 390 | 0 | — |
| `fluids-full` | **12/90 = 0.133** | 603 | **0** | **0** |

**The fluids arm was void once and is clean now.** P38's corpus never showed the
model the surface it was served with — the proxy appends 388 characters listing
arguments alphabetically where the corpus writes them in tool order — and **71 of 606
calls were refused for reasons that had nothing to do with physics**. The generator
now *uses* `render_tools` rather than a copy of it, and the test that checks this
existed for email and had never been written for fluids.

**Fixing it made the number worse, and that is the finding.** 0 refused, 0 out of
turns, 90 of 90 answered, 6–8 calls against the 7 the corpus teaches: **the protocol
is exactly right and the physics is wrong 78 times out of 90.** Paired against P24 on
cases that are literally the same by id, it **loses to the hand-written rule** —
3/30 against 12/30, 2:11 discordant, **p = 0.022** — and ties with everything else.

**Two corrections this project owes itself.**

1. P38 named *"beat the hand-written rule, paired"* as the fluids bar. **The rule is
   not a solver** — it writes calls and a model does the physics — so that bar was
   never directly measurable as stated. The paired comparison against P24's arms is.
2. **P36's headline is qualified.** The same adapter, the same cases, temperature 0,
   gives **84, 81, 82** across three runs with every pair a tie. The gate demands 83.
   vLLM is not run-to-run deterministic, so *"the first pool member clears its gate"*
   cleared **once in three**, decided by the scheduler. **The effect is not marginal,
   only the verdict is**: against the base it is **8 : 51 discordant, p ≈ 0**.

**What the split between the members says.** The member that has to **decide** works;
the member that has to **reason** does not. Email is a two-of-four rule over facts the
tools hand over; fluids composes Manning, Swamee-Jain, centroid depths and areas over
numbers that change per case. **600 supervised examples taught the protocol perfectly
and the physics not at all.**

That anchors against P6/P7, where a fluids expert reached **40/40 — with a
calculator, on a suite whose values were given in the statement** **[ran]**. Here it
has a calculator and must also *find* the values. The difficulty between those two
suites now has a number on it.

**"Pool" is still not earned**, and what is missing is exactly one thing: a second
*useful* member. Whether that needs more corpus, another subdomain, or an admission
that 600 examples do not buy composed reasoning is open — and it is the first
question the parked acceptance mechanism might be in a position to answer.

#### P36 — the first pool member clears its gate

[`results/P36-ceiling-20260915/`](../results/P36-ceiling-20260915/BRIEF.md). One
adapter, tools and judgement together, served over Qwen2.5-3B with the identity gate
`applied` before a case was scored.

| arm | asked in | refused | human messages | exact p |
|---|--:|--:|--:|--:|
| base (P31) | 0/150 | 0 | 39/113 = 0.345 | 1.000 |
| kernel-mt, physics (P34) | 123/150 | 127 | 39/113 = 0.345 | 1.000 |
| kernel-email, names (P35) | 22/150 | 0 | 42/113 = 0.372 | 1.000 |
| **email-full (P36)** | **113/150** | **0** | **84/113 = 0.743** | **0.028** |

**It clears** — 84 against the 83 the exact one-sided binomial demands at α = 0.05,
and the 0.320 of margin the tools held is **28% claimed**, 0.655 → 0.743 **[ran]**.

**393 calls, 0 refused.** It asked in 113 of 150 cases and in 37 it did not, and the
37 are almost exactly the automated messages the corpus teaches to settle at a
glance. **It learned *when* to ask, not "always ask"** — the failure a corpus that
queried three tools for everything would have produced. 97 cases at 3 calls, 14 at
6, 2 at 9; none ran out of turns and none was undecided. **0 of 150** answered from
a fabricated tool result, so the confound pre-registered in P35's brief stays dead.

**Under the decision taken while this ran**, the reading is not permission to keep
measuring — it is the result: **a self-contained QLoRA, trained by ordinary
supervised fine-tuning on one subdomain, served over a resident base and swappable
per request, does a job the base cannot do at all.** The base's 0.345 is the exact
complement of its own bar, from answering `NOT IMPORTANT` to everything without
consulting anything. The whole difference is the adapter, with no composition, no
shared kernel and no tournament.

**Three things this does not claim.** Not that a composed pool could not do better —
composition is parked and nothing here compares against it. Not a ceiling — 0.743
against a 1.000 nothing has reached, and what the remaining 0.257 costs is
unmeasured. **Not generalisation**: one subdomain, one generator, one base. *A pool*
needs a second expert before the word is earned.

#### P35 — the vocabulary is learnable, and learning it costs the disposition

[`results/P35-email-kernel-20260914/`](../results/P35-email-kernel-20260914/BRIEF.md).
A kernel trained on 600 examples of the **email tool names and nothing about
triage**, served over Qwen2.5-3B with the identity gate `applied` before a case was
scored.

| arm | asked in | calls | refused | human messages |
|---|--:|--:|--:|--:|
| base (P31) | 0/150 | 0 | 0 | 39/113 = 0.345 |
| kernel-mt, physics tools (P34) | **123/150** | 127 | **127** | 39/113 = 0.345 |
| **kernel-email (P35)** | **22/150** | 44 | **0** | 42/113 = 0.372 |

**The vocabulary was learned**: every one of the 44 asks was answered — right names,
right argument keys, **0 refused** against P34's 127. That is the gap P34 left open,
closed **[ran]**.

**And teaching it cost the disposition**: asking fell from **123 of 150 cases to
22**. That is the fourth outcome the brief named in advance, and the reason is
visible in the corpus — it teaches four *question shapes*, and a triage prompt is not
one of them. The adapter learned *ask when the question looks like this*; the physics
kernel, trained on another domain entirely, had generalised *ask whenever you lack a
fact*.

**No arm clears the gate**, and all three **tie** on accuracy: base against
kernel-email is **0:3 discordant, p = 0.250**, the same shape of claim withdrawn
from P15 this morning. **The pre-registered confound is dead** — `strip_calls`
leaves a fabricated `= {…}` in the content and **0 of 150** carry one, so the model
did not answer from its own invention.

**The sharper statement of the pool thesis.** Tool use is not one capability a LoRA
either carries or does not. It is at least two, and they generalise differently:

| | how it transfers |
|---|---|
| **disposition to ask** | broadly but vaguely — reaches for email tools in 123 of 150 cases, in the wrong vocabulary |
| **vocabulary** | precisely but narrowly — asks correctly every time, only for shapes it was trained on |

Neither alone reaches the margin, so the pool's next question is whether the two
**compose** — the shape P8 already measured for physics, sequentially and by taking
turns.

#### P34 — the protocol transfers as behaviour, not as vocabulary

[`results/P34-protocol-transfer-20260914/`](../results/P34-protocol-transfer-20260914/BRIEF.md).
`kernel-mt` — trained on `<calc>`, `<lookup>` and `<convert>` over fluid mechanics —
served over Qwen2.5-3B against the **email** suite, whose tools it has never seen.

| | base alone (P31) | **kernel-mt** |
|---|--:|--:|
| tool calls | 0 | **127** |
| refused | 0 | **127** |
| cases that asked | 0 of 150 | **123 of 150** |
| human messages | 39/113 = 0.345 | 39/113 = 0.345 |

**Zero became 127, and every one was refused.** The base alone asked for nothing 150
times; with the protocol adapter the same base reaches for a tool in 123 of 150 cases
on a domain with no overlap — in the vocabulary it learned, not the one this suite
has **[ran]**.

This is the middle of three readings written down before the run, and neither
neighbour fits: the protocol **does** cross vocabularies (0 → 127), and it does
**not** serve tools it was never trained on (0 of 127 answered).

**Accuracy did not move — 39/113 both times, identical.** A protocol adapter that
asks and is refused scores what a base that never asks scores. **The ask is the
finding and the score is not**, which the brief said in advance it would report
either way.

**What was not bought**: which name it reached for. The record counted refusals
without recording the ask, and that was fixed the same session so the next run
answers it for free. It was not bought as its own arm because **it cannot change the
next purchase** — a wrong name and a malformed argument both lead to a protocol
adapter trained on this tool vocabulary, and a corpus built from the tools' own
schema covers both.

**For the pool thesis this is the non-obvious half.** The reusable capability is the
**disposition to ask**, and it demonstrably survives a complete change of domain,
task and tool names. What does not travel is the vocabulary — cheap to teach, and
domain-specific by nature. So the pool does not need a protocol adapter per domain
for the *behaviour*; it needs one that knows the *names*. Whether one adapter can
carry several tool sets is now a question about training data rather than about
whether the idea works.

#### P31 — the base cannot do triage, and that does not mean what the brief said

[`results/P31-triage-headroom-20260914/`](../results/P31-triage-headroom-20260914/BRIEF.md).
Qwen2.5-3B-Instruct, no adapter, 150 messages through vLLM, the proxy and the real
agent loop. It answered **`NOT IMPORTANT` to all 150, in identical words, on the
first model call** — **39/113 = 0.345** on the human messages against a bar of
0.655, exact one-sided p = **1.000**, and **0 tool calls** **[ran]**.

The tool surface was not the problem: the proxy's rendering was reproduced offline
and the model was shown all three tags plus *"Use the tools to find out — the
listing does not say"*. **It was offered the tools, told to use them, and asked for
none.**

**The pre-registered rule said the next purchase is a different base, and that rule
is withdrawn rather than applied.** It reasoned that "an adapter teaches a policy;
it does not teach a model to hold a tool conversation it cannot hold". P8 measured
the opposite on this exact base **[ran]**:

| arm | tool calls on 30 cases |
|---|--:|
| base + tool | 44 |
| **kernel + tool** | **169** |
| domain + tool | 0 |

A protocol adapter nearly quadruples how often this base asks for a tool; a domain
adapter with no protocol in its corpus suppresses asking to zero. **The failure P31
observed is exactly the one a protocol adapter exists to repair**, so base-at-floor
does not imply adapter-at-floor, and buying a different base would spend money on an
inference this repository has already contradicted.

**The comparison is suggestive, not exact**, and the limit is recorded with it: P8
runs physics through a stop-string harness, P31 runs email through the OpenAI
`tools=[…]` convention. What transfers is the within-P8 contrast — same base, same
task, same channel — not the raw count.

**What the arm does establish**: the base cannot do this unaided; the suite is not
answerable from the listing; and all 0.320 of the margin still sits with the tools,
unclaimed.

#### P33 — Qwen3.5 trains a LoRA; vLLM serves the base anyway

[`results/P33-lora-matrix-20260914/`](../results/P33-lora-matrix-20260914/BRIEF.md).
**Pre-registered before the run, and it exists because four runs produced an
unreadable result.** Each asked whether vLLM applies a LoRA to `Qwen3.5-4B`; each
answered `IDENTICAL TO BASE`; and none could separate *the model class does not
apply LoRA* from *the adapter was never trained* from *the check itself was wrong*.
It was the check, twice — so **both Qwen3.5 diagnoses on this page were withdrawn
on 2026-09-14**: that its adapter touched only MLPs (the loaded module tree does
carry `q_proj`), and that the class does not serve LoRA (measured through a
self-check that generated twice through the adapter and called the results
identical).

**The missing piece was never a better subject. It was a control.** A negative
result is only readable beside a positive one taken the same way, so the identical
procedure runs on `Qwen2.5-3B-Instruct` — where P26 measured base 0/60 against
adapter 20/60 **[ran]** — in the same session as the subject.

| gate | question | conclusive on its own |
|---|---|---|
| **G1** in-process | did `lora_B` move **and** did the output change | yes — a no-op adapter is never handed to G2 |
| **G2** served | does vLLM's text differ from the base | yes |
| **G3** merged | bought only if G2 fails | yes, and it is **not a pool** |

**Falsification, written before the run**: if the control fails either gate the run
is **void** and no claim about Qwen3.5 survives it. That row did not exist in any of
the four earlier runs, and it is the only thing that separates "the subject is bad"
from "the harness is bad".

**G3 is priced rather than discovered.** Merging writes the delta into the weights
and serves an ordinary model — unsloth's own Qwen3.5 guide routes through
`save_pretrained_merged` for exactly this **[read]**. It works, and it costs one
full copy of the weights per expert with no shared base and no per-request
swapping: the thing this architecture exists to avoid.

## The result — 2026-09-14 **[ran]**

| base | role | G1 in-process | G2 served | s |
|---|---|---|---|--:|
| `Qwen2.5-3B-Instruct` | control | **passed** · `lora_B=18660.98` | **applied** | 323 |
| `Qwen3.5-4B` | subject | **passed** · `lora_B=18739.84` | **IDENTICAL TO BASE** | 495 |

**`control_valid: true`**, so the subject's negative is a fact about Qwen3.5 and not
about this code. The reading, from the table written before the run:

> the adapter trains and changes the output in process, and vLLM serves the base
> anyway — **a serving-stack limit, not a model one**

**This is different in every respect from the two claims withdrawn the same day.**
Qwen3.5 is not incapable of LoRA: `lora_B_abs_sum = 18739.84` across all twelve
projections, `in_proj_qkv` and `out_proj` on the linear-attention layers included,
and the output changes. What fails is the serving stack — **and it fails silently**,
which is the whole of C18. `vllm.log` carries `Loaded new LoRA adapter: name 'tiny'`
and then serves the base. A deployment reading that line would believe it was
serving an expert.

The subject's G2 also carries **`"exit": 0`**: `serve_openai` exits cleanly on a run
whose gate said *not applied*, so reading the return code instead of the verdict file
would have reported the subject as a pass — the same shape of error behind both
withdrawn diagnoses.

**Decision: Qwen 2.5 for the end-to-end.** Not because Qwen3.5 is weaker, but because
a pool of QLoRAs needs adapters swappable per request over one resident base, and
vLLM does not apply them on this class. **G3 was not bought**: merging would work and
is not a pool — one full copy of the weights per expert, no shared base, no swapping
— so it is recorded as a priced fallback rather than an option, and no GPU time went
to confirming a cost we can state.

**Instrument note that outlived the run.** The chain died before the A100 did any
work, on a Python comment inside an unquoted heredoc:

    # raised on `import`, so vllm never starts

There, `#` comments nothing and backticks execute. `chain_serve.sh` already carried
a note reading *"No backticks in this heredoc — third time today"*; the fourth
arrived in a line added beneath it. A rule a person has to remember is not a rule,
so `tests/test_chain_scripts.py` now fails the build on it — and found two live
instances the moment it existed, including the warning comment itself **[ran]**.

#### P26 — the pool answers on `/v1/chat/completions`, and each adapter applies

[`results/P26-openai-server-20260913/`](../results/P26-openai-server-20260913/BRIEF.md).
`/v1/models` lists the base and both adapters as separate model names, and the same
prompt to each produces **different text** — the kernel writing tags and delegating
the arithmetic, the domain writing numbered physics and never emitting a tag. **Two
personalities over one resident base, selected by the `model` field of an HTTP
request.** This is the substrate question P3 left open **[ran]**.

**The caveat travels with it**: P3's silent failure was vLLM 0.28.0 on a hybrid
multimodal base and this is 0.29.0 on a dense one — **two things changed**.

**Arm 2 does not test what it was built to test**, and that is recorded rather than
dressed up: both adapters score 0/30, and neither zero is about vLLM. The kernel
emits `<calc>` and waits for an answer a single-turn endpoint never gives; the domain
cannot do arithmetic (1/30 raw, 30/30 repaired, measured long ago). Serving fidelity
needs the same *harness*, not merely the same cases, and remains unanswered.

**Arm 3 rules out the catastrophic version and little else.** Mixed came out *faster*
than pure — 3.01 against 2.69 prompts/s — and the two bursts run in a fixed order with
the first paying warm-up, so **−11.9% is the size of the confound, not a finding**.
What survives is that two adapters interleaved are within noise of one inside a single
scheduling pass, against P3's voided 20×.

#### P27 — the `tool_calls` bridge is a serializer, and the schema direction is priced

[`results/P27-tool-calls-20260913/`](../results/P27-tool-calls-20260913/BRIEF.md).
P26 closed by warning that bridging tags to `tool_calls` "reintroduces the
hand-written harness". **That conflated deciding with serialising**, and the two
measure differently:

| | lines of code naming this suite's vocabulary |
|---|--:|
| the hand-written rule | **19 of 76** |
| the tag→`tool_calls` converter | **0 of 38** |

**604 of 604** calls across both suites round-trip byte-identical, and `search_flights`,
`sql_query` and `send_email` — tools this project has no concept of — convert cleanly,
so the losslessness is not an artefact of a shared vocabulary **[ran]**.

**The other direction is not free, and now has a number.** Rendering a client's
`tools=[…]` into the tag surface, against the trained instruction on the same thirty
cases and the same adapter:

| arm | calls | refused | oracle's tool values |
|---|--:|--:|--:|
| trained instruction | 178 | 16 | **59/96 = 0.615** |
| **OpenAI schema** | 176 | **93** | **41/96 = 0.427** |

**The protocol is not switched off — the form is.** Both arms produce a call in all
thirty cases and make the same number of calls. And **33 of the schema arm's 93
refusals are one mismatch**: a one-property JSON schema renders `<calc>expression=…
</calc>` where the adapter was trained on `<calc>1.2 * 3</calc>`. Every other refusal
category is identical across the arms — 4 and 4, 3 and 3.

**Absolute numbers do not travel**: the trained arm is 0.615 here against P21's 0.979
because this is a *single turn* with no harness answering, so the model writes a whole
chain without ever seeing an intermediate value. **Only the A/B inside this run is
comparable.**

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

#### P22 — dimensional consistency is the first confirmed edge signal

[`results/P22-dimensions-20260912/`](../results/P22-dimensions-20260912/BRIEF.md).
Two cheap signals had failed: the model's own confidence, and the tool layer's
rejection rate, falsified on families it was not fitted to. The hypothesis here is
that outside its region a specialist does not fail quietly — it **invents
relations**, and an invented relation is unlikely to be dimensionally consistent:

    6. Drag force F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)
       kg/m^3 · (m/s)^2 / [1]  =  kg/(m·s^2)  — a pressure, where a force was asked

It consults no model, needs no answer, and has no threshold to fit. **[ran]**:

| | development (P13/P14) | **confirmation (P18)** |
|---|---|---|
| out-of-region work flagged | 0.78 | **0.80** |
| coverage | 0.80 | 0.82 |
| separation | **0.72** against a 0.60 chance line | — |
| false alarm on correct in-region work | **0.22** | — |

**It does not drop on material it was never shown.** The behavioural guard fell from
0.63 to 0.18 at exactly this question; this holds at 0.80. Four out of five
out-of-region chains are caught on `weir_flow` and `jet_reaction`, produced by P18
before the guard existed.

**It is not deployable.** One correct in-region chain in five is flagged, and a
system that escalates one good answer in five has spent much of what withdrawal was
meant to save. The pre-registration said that number counts equally.

**And it is not domain-free.** Manning's `n` is s·m^(-1/3), so that family only
types if the statement names the constant — a new domain costs a table of its own
empirical constants. And numbers are matched by value, so an intermediate that
happens to equal a printed quantity inherits its dimension.

**The instrument changed seven times and the rule never moved.** Every change was
the checker failing to read its input — a verdict read off the last step that
*typed* rather than the last step, `Pa.s` matching the `Pa` prefix, integer
exponents unable to express `R**(2/3)`, and four more, all listed in the brief.
Seven is past where this project's own rule says a measurement is looking for its
result. **The defence is not that each fix was justified: it is that the
confirmation set was scored once, after all seven, on material never opened during
development, and it held.**

#### P21 — the learned protocol ties the hand-written rule, as pre-registered

[`results/P21-handbook-20260911/`](../results/P21-handbook-20260911/BRIEF.md).
P15's material could be answered from memory, so the suite gained a **handbook drawn
per case**: the properties a problem needs did not exist when the expert was trained
and cannot be recalled. The killing arm was bought first and it worked — a control
with no tool layer at all fell from **27/30 to 6/30** **[ran]**.

| arm | final answer | oracle's tool values | calls | refused |
|---|--:|--:|--:|--:|
| no tool layer at all | **6/30** | 0/96 | 0 | 0 |
| hand-written rule | 5/30 | 93/96 = **0.969** | 96 | **0** |
| kernel adapter | 4/30 | 94/96 = **0.979** | 116 | **20** |

**One value apart on the axis declared in advance, and the brief fixed before the
run that a kernel within three is a tie.** It is reported as a tie. All three arms
tie on the final answer too, with the *no-tool* control highest — which the headroom
check predicted: 22 of the rule's 25 failures held every oracle value and the expert
still answered wrong, so a perfect tool layer could only ever have moved three cases.

**What separates them is character.** The rule makes 96 calls with none refused; the
kernel makes 116 with 20 refused — **a 17.2% rejection rate** — and still ends ahead
on coverage. Of its 14 failed cases carrying a rejection, **13 obtained every oracle
value anyway**. The failure taxonomy therefore over-attributes to protocol here, and
`classify` is left alone rather than reordered after seeing which arm it penalises.

**Settled**: a learned protocol is neither worth its weights over a hand-written rule
on this suite nor worse than one — the opposite of P13's 9/30 against 23/30.
**Not settled**: whether 17.2% wasted calls matter against a paid or slow tool, and
whether any of it ports. The rule is **144 lines** that know this suite's label
vocabulary, unit table, fluid names and phrasings; the adapter learned from a corpus
containing none of the evaluation families. A tie between those is not a tie in kind,
but P21 did not measure portability and P9's transfer result remains the only
evidence for it.

#### P23 — S2 re-bought against a target that is actually ahead · RUNNING

[`results/P23-ranking-20260912/`](../results/P23-ranking-20260912/BRIEF.md). S2
passed 14 of 15 pairs against targets that were **peers** of the strongest candidate,
which tests the criterion's mechanics and not the architecture's claim. P10 found a
suite where a target is genuinely ahead, and its answers are already on disk.

**The first replacement target was void, and the data that voided it was already
there.** Against a 30/30 target, agreeing with the target is being correct, so the
ordering test would pass tautologically. The same model at a smaller budget scores
17/30 — and **all 13 of those failures are truncations**, derivations cut off
mid-page whose "answer" is a pipe area. At the full budget it answers 13 of 13
correctly. The target was not wrong, it was silent.

**`gemini-3.5-flash-lite` at the full budget qualifies**: 43/60, nothing unparsed,
and **17 of 17 failures are complete responses** against a pre-registered bar of
0.80 **[ran]**. The ladder so far, all with nothing unparsed:

| candidate | verified |
|---|--:|
| `qwen3.5:2b` | 13/60 |
| `qwen3.5:4b` | 29/60 |
| `qwen3.5:9b` | 39/60 |
| `gemma4:12b` | running |
| *target* | *43/60* |

Differences of 16 and 10 cases — the ±1 tie that voided S2a is not in play.
**Redesign count: 3**, accounted for in the brief rather than reinterpreted, and the
budget is declared spent: if the test voids at n=60, S2 is reported unanswerable on
this suite.

#### P24 — the one number where code beats weights · BUILT, NOT RUN

[`results/P24-constrained-20260912/`](../results/P24-constrained-20260912/BRIEF.md).
P21 left exactly one: 0 refused calls against 20. The adapter is not worse at knowing
what to ask, it is worse at *saying* it — and a sampler can close that. A grammar
mask over the kernel's turn, ~120 lines, no weights and no extra forward pass.

**The result is predicted from P21's own transcripts, before any GPU [ran]**: replayed
over every call the tools refused, the mask makes **14 of 19 impossible**. The five it
misses are syntactically perfect calls refused for a reason no grammar can see — the
adapter asking for water when the problem's handbook holds invented codes. **A mask
that caught those would be deciding content**, so the pre-registration is corrected
downward before the run: rejections fall to about five, not to zero, and **a run
reaching zero voids the arm**.

`grammar_check.py` replays all 2226 calls in both corpora and the evaluation and
fails if one legal character is refused. It caught three bugs in the grammar before
any of it ran; each would have appeared on a GPU as the adapter getting worse.

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

~~**A learned protocol beats a hand-written rule where the call is not a copy**, on
both metrics and narrowly: 94.8% against 91.7%, 10/30 against 7/30. That reverses
P13's verdict and locates it.~~ **Withdrawn 2026-09-14: both metrics are ties.**

Every arm runs the same 30 fixtures, so the comparison is **paired**, and the only
information about a difference lives in the cases where the two arms disagree. Those
totals hide **three** disagreements on the final answer and **four against one** on
the tool values:

| metric | totals | disagreements | exact two-sided p |
|---|---|--:|--:|
| final answer | 10/30 vs 7/30 | 3 : 0 | **0.250** |
| oracle's tool values | 91/96 vs 88/96 | 4 : 1 | **0.375** |

**[ran]** 2026-09-14, `tests/test_paired.py`. Three coin flips landing the same way
is a p of 0.25. The direction was consistent both times and **the claim was never
measured** — and P21, which removed the memorisation by drawing a handbook per case,
put the same three arms at 4, 5 and 6 of 30, every pair a tie as well.

So what P15 establishes is the control, not the contest: **with no tool layer at all
the expert scores 27/30, three times either tool arm** (p < 0.001 against both), and
that is a statement about the suite. Whether a learned protocol beats a regular
expression at choosing among three tools **remains open**, and the honest reading of
P13 is that it was never reversed.

**The one place code genuinely beats weights survives**: in P24 the hand-written rule
beats the kernel adapter 12/30 to 5/30 on **7 : 0** disagreements, p = 0.016 — a real
difference, and it is unflattering to the treatment, which is why it is worth the
same care. **This is not a blanket doubt about the suite; it is the same test applied
in both directions.**

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

### Taken 2026-09-15: composition is dropped, and `harness.lora` parks with it

**The user's call, and the reasoning is right.** `harness.lora` is precisely what
requires composition — it exists so the protocol is taught once and every expert
does not re-learn it. An expert that carries its own protocol has no use for it.

**The thesis is untouched.** A pool of **self-contained** QLoRAs over one resident
base, swapped per request, is still *the whole agentic system is a pool of QLoRAs*.
Composition was an **optimisation** — share the protocol — not the claim. Dropping
it removes machinery, not the question.

**What it buys.** The one thing this repository has never measured cleanly is
composition: P8's apparent "two adapters interfere" is void on a notation confound,
and P35 measured that splitting has a real cost — the vocabulary was learned and
asking fell from 123 of 150 cases to 22. Removing the split removes both the
unmeasured mechanism and the measured cost.

**What it costs, stated rather than discovered.** Every new subdomain expert pays to
learn the protocol again. That is a **training-data** cost and not a runtime one, and
it is small: 600 examples and nine minutes on an L4 taught the email vocabulary with
**0 refusals** **[ran]** P35.

**P34 is parked, not falsified.** That a kernel trained on fluid-mechanics tools
takes this base from **0 to 123 of 150** cases reaching for email tools it has never
seen is measured and stands. It is the only evidence the kernel idea has legs, and if
self-contained experts turn out expensive to produce at scale, it returns with that
result already paid for. The adapters stay on disk; nothing is deleted.

**P36 is reframed by this, before its number existed.** It was bought as a ceiling —
*is the margin reachable at all* — with the brief insisting a monolith that clears is
only permission to keep measuring. Under this decision **a monolith that clears is
the result**: the first pool member scoring on its own subdomain. And a monolith that
fails no longer means *no pool arrangement will work*; it means **this base cannot do
this subdomain**, which is narrower and more honest.

### Taken 2026-09-15: supervised experts first, the mechanism only if it beats them

**The user's proposal, and it is adopted.** Train each subdomain expert by ordinary
supervised fine-tuning, compose it with the kernel adapter, and spend the acceptance
machinery only on **improving** an expert that already exists — if it can.

**Why it is better, and it is not a matter of taste.** It creates the baseline the
mechanism has to beat. Built the other way round, an expert produced by the
tournament has nothing beside it, and whatever number it scores reads as a success.
This repository's own rule is that **the baseline is our own previous version**, and
under this ordering the supervised expert *is* that version.

**And it puts the cheap, proven half first.** Supervised training is measured here
several times over — distillation transfers the procedure (P6/P7, adapter plus
calculator 40/40), the protocol is separable (P8), the tool vocabulary was learned
exactly as intended with 0 refusals (P35). The tournament has **fitness by
conjunction ordering 2 of 2 pairs** and a router that ties. Buying the expensive,
least-validated half first is the wrong way round.

**What it changes.** The frontier had two jobs — teacher for distillation, and
oracle for promotion. The first stays. **The second becomes conditional**: bought
only once there is a supervised expert for it to improve on. That moves this
repository's stated central question one step later, which is why it is recorded
here as a decision rather than left to drift.

**What it does not make easier.** P35 measured that training one capability
supervised **cost another** — the vocabulary was learned and asking fell from 123 of
150 cases to 22. Training experts per subdomain and then adding the kernel meets
exactly that interference, and **composition of two LoRAs has never been cleanly
measured in this repository**: P8's apparent "two adapters interfere" is void on a
notation confound and must not be cited as fact. Under this ordering that question
stops being downstream and becomes the central one.

**P36 already is the first step of both plans.** It was bought as a ceiling — is the
margin reachable at all — and under this decision it is also the first supervised
subdomain expert. The same spend answers both.

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

### Analysed 2026-09-15: composition can return as a pipeline, and P4 is re-aimed

Full analysis: [`analysis/composition-and-speculative.md`](analysis/composition-and-speculative.md).
Nothing implemented; three things change in this plan.

- **Piping is not the composition that was dropped.** `base→lora1` then
  `base→lora2` never has two deltas live in one forward pass, so the interference
  question does not arise — and the pool already serves it, measured three times
  **[ran]** P40/P41/P42. It is two requests with two model names, and costs no
  serving work.
- **P4's family is wrong and its premise is unchecked.** It says *a large Qwen3.5*;
  the adapters are on Qwen2.5-3B, so the target must be a large **Qwen2.5**. And
  that a 3B and a large sibling share a tokenizer is **[read]** — comparing two
  `tokenizer.json` hashes is the first thing P4 runs, not an assumption underneath
  it.
- **The literature's number for this architecture is acceptance, and we have never
  measured it.** Every number here is delivered accuracy.
  [TaskSpec](https://arxiv.org/html/2505.08600v1) reports a prompt classifier over
  four task-specific drafters lifting acceptance **16% → 58%** — our pool, built by
  somebody else, scored on a quantity that needs no verifier.

Not adopted: per-token adapter routing (MoLoRA, WhiFlash). It is weight-space
composition under another name, and that question was closed today.

### Analysed 2026-09-15: the failing expert has no already-good sub-region

Full analysis: [`analysis/narrow-experts.md`](analysis/narrow-experts.md). No GPU;
`results/P41-routing-20260915/` re-read, sliced by family and paired against the
frontier on the same 90 cases.

| family | n | local | frontier | only local | only frontier |
|---|---:|---:|---:|---:|---:|
| manning_channel | 23 | **0.304** | 0.826 | 1 | 13 |
| venturi_flow | 22 | 0.136 | 0.682 | 2 | 14 |
| hydrostatic_force | 23 | 0.043 | 0.609 | 0 | 13 |
| pipe_head_loss | 22 | 0.000 | 0.818 | 0 | 18 |
| **all** | **90** | **0.122** | **0.733** | **3** | **58** |

**[ran]** 2026-09-15.

- **Every sub-region is dominated**, so a finer router would have found nothing.
  Narrowing a subdomain has to **create** its gain by training; it cannot reveal one
  already sitting there.
- **The harness half of this expert already works**: 604 calls, **0 refusals**, 6.7
  calls per case against the frontier's 7.6, a number returned every time. What
  fails is the physics — of 79 failures, **44 wrong**, **12 within 10% but outside
  the 2% tolerance**, 2 off by a factor of ten.
- **More experts is safe only while the finer boundary stays declarable.** By-region
  routing delivers 0.775 because the region is knowable before the model runs; a
  boundary that needs the answer read inherits by-case's 0.378.

**Next arm (pre-registered).** One narrow expert on `manning_channel` alone, scored
on fresh held-out cases of that family. **Gate: 0.826**, the frontier's number
there. Below it, narrowing does not repair a reasoning expert and the idea is closed.
`bar.n_for(0.304, effect=0.522)` returns **10**, so the arm resolves at any n we
would run **[ran]**.

### Analysed 2026-09-15: the suite has no difficulty axis, and the gate was the wrong one

Full analysis: [`analysis/sufficiency.md`](analysis/sufficiency.md). No GPU; P41's
90 cases regenerated from their seed and the **oracle's own solution length** read.

| family | oracle steps | tools | local | frontier |
|---|---:|---:|---:|---:|
| manning_channel | 6 | 2 | 0.304 | 0.826 |
| hydrostatic_force | 6 | 3 | 0.043 | 0.609 |
| venturi_flow | 7 | 3 | 0.136 | 0.682 |
| pipe_head_loss | 9 | 3 | 0.000 | 0.818 |

**[ran]** 2026-09-15.

- **The suite's floor is six steps and each family is pinned at one depth**, so
  depth and family are the same variable. The experiment could only ask *can a 3B
  solve a 6-to-9-step chain*; it could never ask whether a small expert is
  sufficient at the easy end, because the easy end was never generated.
- **Headroom, upside down.** We check ceilings; there was no rule for floors. A
  suite with one difficulty cannot tell *too weak* apart from *too hard* — both give
  0.122. Added to `CLAUDE.md` §3.
- **Qwen 2.5 is a floor we did not choose** (C18, P33), so every number here is a
  **lower bound** on what a small expert can do, not an estimate.

**Built:** `training/physics/ladder.py`, four rungs at 1–4 steps below the suite's
floor — same domain, same three tools, same unmemorisable per-case handbook — and
`fluids_sim --families {suite,ladder,full}` reporting `by_steps`, accuracy against
depth rather than family name. The oracle is checked by running its own chains with
the real tools, which caught a 1.3e-6 answer/chain disagreement in `L4`.

**Supersedes the arm proposed earlier the same day** (*narrow expert on
`manning_channel`, gate 0.826*): it took the frontier's score as the gate on a
family with no easy end. Not bought.

**Next arm (pre-registered), no training:** the bare base, then the existing
`fluids-full` expert unchanged, then the frontier as a **ceiling check only**, over
the full ladder 1 → 9. Arm 1 says which rungs can show an adapter anything; arm 2 is
the actual curve of where a small expert stops being sufficient, and costs inference
only. **Gate for a sufficiency claim: 0.90, absolute** — at 0.80 one answer in five
is wrong and every answer needs checking by hand, which removes the reason to have
the expert. **Falsification:** if the curve is flat — the expert fails a one-step
lookup at roughly the rate it fails a nine-step chain — difficulty is not what blocks
it and this analysis is wrong.

### P45 — 2026-09-15 **[ran]** · FALSIFIED, and not by difficulty

Report: [`../results/P45-ladder-sweep-20260915/RESULT.md`](../results/P45-ladder-sweep-20260915/RESULT.md).
One L4, two arms, 140 cases each, seed 454545. Session stopped cleanly.

| oracle depth | base | expert | n |
|---:|---:|---:|---:|
| 1 | 0.111 | 0.278 | 18 |
| 2 | 0.000 | 0.000 | 18 |
| 3 | **0.167** | **0.000** | 18 |
| 4 | 0.000 | 0.000 | 18 |
| 6 | 0.000 | 0.382 | 34 |
| 7 | 0.000 | 0.000 | 17 |
| 9 | 0.000 | 0.000 | 17 |
| **total** | **5/140** | **18/140** | |

**The pre-registered falsification fired**: easy end 0.069, hard end 0.191 — the
easy end is *below* the hard one, not merely within 0.15 of it. The claim that
bought the run — depth is the axis that reveals a sufficiency band in this expert —
is wrong, and wrong in a direction nobody proposed.

**The mechanism, measured.** Below its training depth the expert over-solves on
**18 of 18** cases; at or above it, **0 of 17**. Its median chain floors near five
calls and will not go under. Asked for `ρ g h` in two steps it converted metres to
metres, invented an area of 100 mm², and answered about force. **A corpus with one
difficulty teaches a floor, not just a skill** — added to `CLAUDE.md` §3.

**What survives.** Not that this expert has a sufficiency band: it does not, because
that band was never in its training data. But the general claim — a small expert can
be sufficient at a known acceptable level — is **untested**, since no expert here has
ever been trained on an easy problem. The suite's missing easy end became the
expert's, because the corpus is generated from the suite.

**Deliberately not launched:** an expert trained on the full ladder. The brief said a
flat curve stops the GPU, and inventing a hypothesis and buying it the same night is
how an instrument starts looking for a result. Specified and waiting.

**Caveat on the base arm:** 140 calls for 140 cases, 85 refused, against the expert's
810 and 75. It measures **disposition**, not difficulty — do not quote *"the base
gets 0.111 at one step"* as *"one-step problems are hard"*.

### P46 — 2026-09-16 **[ran]** · most of P44's room was the suite

Report: [`../results/P46-ranking-ceiling-20260916/RESULT.md`](../results/P46-ranking-ceiling-20260916/RESULT.md).
**No GPU.** P44's own 475 cases, inbox regenerated from its seed with ids and truth
verified to match before any join.

| subset · arm | measured gap | 95% CI | ceiling | room | is the suite |
|---|---:|---|---:|---:|---:|
| all · email-full | 0.128 | [0.105, 0.155] | 0.098 | **+0.030** | 77% |
| all · base | 0.105 | [0.084, 0.127] | 0.098 | **+0.007** | 94% |
| human · email-full | 0.400 | [0.346, 0.449] | 0.277 | +0.123 | 69% |
| human · base | 0.338 | [0.288, 0.388] | 0.277 | +0.062 | 82% |

**P44 asked whether the gap was large. It never asked how much was claimable.** On
the full inbox both arms are already at the ceiling. On the human subset the ceiling
predictor is a **constant** — one group, `rankable: false` — so the remaining 0.123
is room to stop being *worse* than a constant, not room to rank.

**The listing-only typed arm is cancelled**: a constant confidence routes nothing,
which is exactly the blindness P41 found in per-case escalation.

**Re-aimed:** a typed final answer **on top of** the tool chain. With the tools every
fact is recoverable, the truth is decidable, the ceiling collapses to the oracle
floor. `email-full` reaches 0.741 with tools **[ran]** P43 and nobody has measured the
confidence on *that* answer. **Serving, no training** — the next headroom check, not
the next treatment.

New rule in `CLAUDE.md` §3: check the ceiling on ranking, not only on accuracy.
Instrument: `training/harness/ceiling.py`.

### Analysed 2026-09-16: four layers, and P1 is finally priced

Full analysis: [`analysis/layered-routing.md`](analysis/layered-routing.md). No GPU.

**P1 — *price the router* — has been open since 2026-09-08 and is now answered**, by
a twelve-line keyword rule over 140 fluids cases spanning all seven ladder depths plus
60 email listings **[ran]** 2026-09-16, n = 200:

| question | decides | lexical baseline |
|---|---|---|
| **coarse** — which suite | **which tool surface to mount** | **1.000** |
| fine — which family | which drafter to prefer | 0.845 |

- **The coarse route needs no model.** It is the job the tool-surface layer needs and
  it is perfect with keywords. Layer 1 starts as a **dict**.
- **Layers 1 and 4 are one artifact** — one decision, two consumers — and it is the
  live product blocker: 54 tools in front of an expert trained on 3, none called
  **[ran]**. `contract.accepts()` gives it a refusal rule for free.
- **The residual fine confusion is the depth boundary** (`L2` vs `L3` are the same
  physics, one needs a conversion), which is what `band` declares and P45 measured.
- **Layer 2 (structural tokens) is a corpus change, not an input change**, and the one
  adjacent result is negative: P28's declared values were *harmful*, handbook misses
  3 → 17. Buy it as an A/B on one expert or not at all.
- **Layer 3 is downstream of P4** — a 3B drafting for a 3B buys nothing. When it is
  live the pairing is unconstrained, because every member shares the resident base's
  tokenizer. TaskSpec and Not-a-Bandit both say *pick with a classifier*, never
  evaluate all.

`tests/test_router_baseline.py` keeps the number re-runnable rather than quoted.

### Open 2026-09-16: we have never served more than two adapters at once

`--max-loras` has only ever been 1 or 2 in this repository — the largest pool ever
served is `['email-full', 'fluids-full']` **[ran]** P41. The layered design in
[`analysis/layered-routing.md`](analysis/layered-routing.md) §6b is the first thing
that needs many, and S-LoRA's *thousands on one machine* is **[read]**, not ours.

**The cheap test, unbought:** load ten names over the two adapters we already have and
watch tokens/s against a single-adapter baseline. No training, no corpus, one short
session. It is the only real risk in the claim that the layering is affordable.

### P48 — 2026-09-16 **[ran]** · the tokenizer premise, checked instead of assumed

`results/P48-tokenizer-compat-20260916/`. **No GPU.** Published tokenizers hashed and
compared id-by-id. C3 said *a frontier target does not share the base's tokenizer*
and P4 assumed a same-family one did; neither had been measured.

| target | target vocab | ids match | usable | extra ids |
|---|---:|---|---|---:|
| **Qwen2.5-7B / 14B / 32B / 72B-Instruct** | 151,643 | **yes** | **yes** | 0 |
| Qwen3-14B / Qwen3-32B | 151,643 | **yes** | **yes** | 4 (`<think>`, …) |
| **Qwen3.5-27B / Qwen3.6-27B / Qwen3.8-27B** | **248,044** | **no** | **NO** | 26-33 |

**Drafter is `Qwen2.5-3B-Instruct`**, the base every adapter here sits on.
**The Qwen3.x vocabulary changed at 3.5** — 151,643 → 248,044 — so the 27B models are
unusable as speculative targets however good they are. `Qwen2.5-32B-Instruct` is the
choice: byte-identical tokenizer, no thinking channel, same chat template.

- **A same-family target needs no argument.** Every Qwen2.5-Instruct size hashes the
  same file.
- **A cross-generation target is usable**, which C3 had written off. `merges` govern
  text→ids, which happens once for the prompt; speculation lives in id space after
  that.
- **The catch the hashes do not show:** the four target-only ids are unreachable by
  the drafter, so a **thinking** target rejects at every `<think>`. C7's rule — read
  acceptance on the answer channel — stops being a convention there and becomes the
  difference between a real acceptance rate and a fictional one.

Instrument: `training/harness/tokenizer_compat.py`, 5 tests. **It is P4's first step**,
run before anything is served.

### P4 restated 2026-09-16: acceptance as the tournament, withdrawal per subdomain

Analysis: [`analysis/layered-routing.md`](analysis/layered-routing.md) §6b.

The old wording — *serve a large Qwen3.5 beside the 2B adapters, token-level
acceptance measurable at last* — was a speed claim. The shape now is:

**k expert drafters of one size against one larger target.** That every drafter is 3B
is irrelevant; what pays is that the target is bigger and slower, so a small model
emits several tokens while the large one emits one.

- **Acceptance becomes a ranking of experts that needs no judge** — same target, same
  prefix, same conditions. That is what S7's tournament never had, and the quantity
  the literature uses for this architecture while every number here is delivered
  accuracy.
- **It restores the withdrawal gap at the right granularity.** If a subdomain's expert
  reaches the target closely enough, the target is withdrawn **for that subdomain** —
  the same per-region granularity that delivered 0.546 → 0.775 **[ran]** P41.
- **Acceptance alone does not say who was right.** A rejection is either the small
  model being wrong or the large one being wrong, and only the verifier beside it
  separates them. The arm is *acceptance and verified score on the same cases*.
- **Gate, to be pre-registered before the run:** an acceptance threshold alone must
  not authorise a withdrawal — the verified score must not drop where the target is
  removed. That is S5's lesson and it applies unchanged.

### Planned 2026-09-16: close experts on one problem, selected by acceptance

Design: [`analysis/close-experts.md`](analysis/close-experts.md). **Nothing built.**

**The correction, and it inverts a result of mine.** P1's coarse route scored
**1.000** and I reported it as *the layer is a dict, how cheap*. The right reading is
that **a discrimination problem solved by twelve keywords is not a test of expert
selection** — fluid mechanics and inbox triage never meet in one problem. The same
run shows the hard regime: the fine route falls to **0.845**, confusing families that
differ only in whether a unit needs converting.

**Three drafting experts on one inbox**, one set of tools, one base, **only the policy
differing**: `draft-client`, `draft-team`, `draft-vendor`.

**Why acceptance and not a router.** A router asks which expert *looks* relevant;
acceptance asks which expert *wrote what the larger model would have written*. Only
the second survives when candidates resemble each other. And drafting has **no
mechanical verifier**, which is where S7's tournament has always stalled — while
acceptance needs none.

**Target: `Qwen2.5-32B-Instruct`**, byte-identical tokenizer **[ran]** P48.
`Qwen3.6-27B` cannot verify our *Qwen 2.5* drafters at all — 248,044 entries against 151,643; a `Qwen3.5` drafter can be verified by `Qwen3.8-27B` **[ran]** D0 —
and stays available as a quality reference, a different job.

| step | what it buys | trains? | gate |
|---|---|---|---|
| **P49** | **headroom** — does the target draft better than the bare base? | no | a mechanical content check (are the required facts in the draft?) must separate them by a margin `bar.resolvable()` calls detectable. **If not, the design is unbought** |
| **P50** | are three experts three experts, and does acceptance vary by temática? | yes, 3 | pool `members_are_distinct`, then per temática the matching expert beats the best other on a **paired sign test** |
| **P51** | the selection running inside OpenClaw, over the MCP tools and inbox that already work **[ran]** P43 | no | only if P50 clears |

**Falsification, before the run:** flat acceptance across the expert × temática grid
means one expert with three names, and the pool gate is what says so.

**The risk that is not an excuse:** close enough to be interesting is close enough to
be within noise. A power check runs before the arm, not after it.

### P49 — 2026-09-16 **[ran]** · bought, and one temática of three has no headroom

Report: [`../results/P49-draft-headroom-20260916/RESULT.md`](../results/P49-draft-headroom-20260916/RESULT.md).
One A100, two arms, 90 cases, **no training**. Session stopped cleanly.

| arm | complete drafts | fact rate |
|---|---:|---:|
| `Qwen2.5-32B-Instruct-AWQ` | **76/90 = 0.844** | 0.948 |
| `Qwen2.5-3B-Instruct` | **49/90 = 0.544** | 0.756 |

**Margin 0.300 against a pre-registered 0.10 — the design is bought.**

**But the headline hides the thing that matters:**

| temática | target | base | gap |
|---|---:|---:|---:|
| **client** | 0.667 | **0.033** | **0.633** |
| vendor | 0.867 | 0.633 | 0.233 |
| **team** | **1.000** | **0.967** | **0.033** |

**`team` has no headroom** — both arms at the ceiling, which is P42's ARC failure
isolated to one temática. The 0.300 margin is almost entirely `client`, where the
base completes **1 of 30**.

**What the base does, read rather than inferred:** it writes a reasonable reply and
omits the concrete details — the reference missing 28 times, the amount 25. And the
check is not measuring punctuation: of **80** missing facts across both arms, **0**
appear written another way.

**Three consequences for P50.**
1. **`team` is fixed or dropped.** Averaging in a saturated temática dilutes whatever
   the other two show. Note the two with headroom both require an **amount** and the
   one without requires a **first name**.
2. **The gap is a capability gap, not a style gap** — *always name the reference and
   the figure* is a policy, trainable and mechanically checkable, and a better-defined
   target than "write in the client register".
3. **Even the target misses 10 of 30 on `client`**, so acceptance against it is not
   correctness. `carries()` stays **beside** acceptance, never behind it.

### Corrected 2026-09-16: the corpus for a drafter should be written by the target

Reading Model-Optimizer's full README rather than a summary of it changed two things
in [`REPORT.md`](REPORT.md) §6, and one of them changes **session 2**.

> *"To achieve higher acceptance rates during speculative decoding, it is beneficial
> to use conversations generated by the base model as training data. This ensures that
> the draft model's output distribution closely aligns with that of the base model."*
> **[read]**

**Every corpus in this repository is generated from an oracle** — the chain a correct
solver would write. If acceptance against a target is the promotion criterion, the
corpus that produces the drafter should be generated **by that target**. Nobody had
connected the two.

**And the subtlety is what keeps it a ranking signal.** Each expert trains on
target-generated conversations **for its own region only**. Expert A then agrees with
the target on A, expert B on B, and acceptance varies by region — which is the signal
session 3 needs. **If every expert trained on every region's target output, acceptance
would be uniform and the ranking would collapse.** Pre-register against that.

Also corrected: **Qwen 2.5 is in the EAGLE3 support matrix**, and the online training
path is for models that fit in GPU memory — a 3B does, on the A100 this project
already rents. The terabytes belong to the *offline* path and I generalised one path's
cost to both. What has not changed: **an EAGLE head cannot rank experts.**

### P51 — 2026-09-16 **[ran]** · session 1 of 4: the band fired, `usable: false`

Report: [`../results/P51-desk-profile-20260916/RESULT.md`](../results/P51-desk-profile-20260916/RESULT.md).
One A100, two arms, 240 cases, **no training**. Session stopped cleanly.

**base 69/240 = 0.288 · target 101/240 = 0.421**, and three cells of sixteen survive
the band — all of them `importance`. The grid collapsed into a row, which the brief
said would stop the next three sessions. **The band is not being moved.**

**Two regions of four are unanswerable for both models.** `owed` scores **0.000 for
the target too**, across all four depths; `counterpart` reaches 0.133 at best. Both
ask about the whole inbox — enumerate 24 threads, then query per candidate, then
compare — and neither a 3B nor a 32B finishes that in 8 turns. By this project's own
rule those are **broken cells, not hard ones**.

**And the rule found its own flaw.** `commitment@4` is **base 0.000, target 1.000** —
dropped because the base is on the floor, by a clause written for *"every arm fails
and it reads as the approach not working"*. But the target proves the task is doable,
so that cell is the **exact shape a small expert exists to close**, with the whole
distance visible. `commitment` runs 1.000 → 0.800 → 0.133 → 0.000 while the target
holds 1.000 throughout: the cleanest gradient this project has produced, and the band
threw away its bottom half.

**Noticing that after the numbers is precisely when it cannot be fixed unilaterally.**
The floor clause needs a companion — *unless the target clears the cell* — and making
that change now is indistinguishable from moving the band to fit the result. Written
down, left for a decision.

**Next move, if taken:** make `owed` and `counterpart` answerable and land
`commitment`'s gradient inside the band — **suite changes with the band held fixed**,
which is a different act from moving the band. It would be the **first post-result
redesign** of this suite; the counter starts at one.

### P53 — 2026-09-16 **[ran]** · step zero passes at +0.689, and the number is void

Report: [`../results/P53-step-zero-20260916/RESULT.md`](../results/P53-step-zero-20260916/RESULT.md).

**base 56/180 = 0.311 · adapter 180/180 = 1.000**, paired, the adapter winning 124
cases the base loses and losing 0, exact p < 1e-5. The pre-registered gate passes.

**And every held-out completion appears verbatim in the training set — 180 of 180.**
The prompts differ, because the constants differ; the *completion* is identical,
because the constants are referenced by name and live in the prefix. The adapter
learned one tail per family, not how to compute anything.

**The previous fix caused it.** The corpus split found the deepest cut removing the
line holding a program's input, so two programs gave an identical prompt with
different answers; the repair made everything above the implementation uncuttable —
which put every varying value in the prefix and left the tail constant. Parameterising
the constants did nothing, because the constants are the part that never has to be
written.

**What survives:** the machinery, entirely — subprocess training, C18, execution-based
verification over 360 completions with zero transport errors — and the base's 0.311
with **38 of 180** completions failing to run.

**The fix:** inline the constants at their use site so the tail carries them and two
programs of one family never share an answer. **Second post-result suite redesign
today; the counter is at two.**

### P54 — 2026-09-16 **[ran]** · step zero passes at +0.863, and the suite is exhausted

Report: [`../results/P54-step-zero-rebuilt-20260916/RESULT.md`](../results/P54-step-zero-rebuilt-20260916/RESULT.md).

**base 27/197 = 0.137 · adapter 197/197 = 1.000**, paired, 170 to 0, p < 1e-5.

**The leak check ran first, and this is not P53.** Held-out completions verbatim in
training: **0 of 197** against P53's 180 of 180. Every completion the adapter produced
was different. It generalised across constants drawn from the full 32-bit space, so
**the +0.863 is real**.

**And what it learned is narrower than the number sounds.** With constants blanked the
197 completions collapse to **6 distinct skeletons** — two families by three cut
depths is about six (family, cut-point) combinations, each with one correct shape. The
task is *recognise which of six applies and fill in constants readable in the spec
comment*. The base still reaches only 0.137, so it is not trivial; but it is **this
template family**, not code completion.

**So: step zero is answered YES** — a base with the right LoRA learns this predicate
and beats the base widely. **And nothing downstream is measurable here**: an expert at
1.000 cannot be ranked, and acceptance has nothing to discriminate. P42's ceiling from
the treatment side.

**The next suite needs structural variety, not more constants** — the fix that failed
twice was varying the *values*; what must vary is the *shape* of the tail. Target: as
many distinct skeletons as cases, not six.

**Process:** `compare` takes two maps and the same `TypeError` ended P53 *and* P54,
because the first time it was worked around rather than repaired. Fixed, with a test.

### Analysed 2026-09-16: whether to move to the Qwen 3 family, and the answer is not yet

Full analysis: [`analysis/qwen3-migration.md`](analysis/qwen3-migration.md). No GPU.

**The fact that reframes it: the target never needed LoRA.** C18 — vLLM logs
`Loaded new LoRA adapter` and serves the base anyway **[ran]** P33 — constrains the
**drafter**, which is where the pool lives. It says nothing about a dense model that
is only ever asked to verify.

So the question splits, and the halves have different answers:

| | answer | why |
|---|---|---|
| a Qwen 3 **target** | **available today, free** | `Qwen3-32B` is 151,643 ids, matching, 4 target-only **[ran]** P48. Serve it with thinking off, since those 4 ids are `<think>`/`<tool_response>` and the drafter has no column for them |
| `Qwen3.8-27B` as target | **blocked** | 248,044 ids. It forces the drafter onto 3.x, and 3.x is where C18 lives |

**The proposed mechanism for C18 is not what our own log says.** It is right that the
class is `Qwen3_5ForConditionalGeneration` and that GDN linear attention is running
**[ran]**; it is wrong that the language-side kernels fail to dispatch — every
`no matching PunicaWrapper` line names a `visual.` module, `_lora_expand_kernel` JIT
compiled *during inference*, and "the adapter touched only MLPs" is a diagnosis P33
already **withdrew**. The failure is measured; the mechanism is **not known**, and is
recorded as not known.

**Why it is third in line anyway.** This project buys **ranking** from speculative
decoding, not latency — and α has never been measured, on any target.
`Qwen2.5-32B-Instruct` is enough to measure it. A newer, slower target does not bring
that measurement closer; it makes an untaken one more expensive. And
[`analysis/generated-code-ceiling.md`](analysis/generated-code-ceiling.md) records the
harder blocker underneath: **ranking needs experts that differ in quality**, and this
project has one useful expert.

Order: experts that differ in quality → α ranks them or does not → *then* a target
worth migrating to.

### Built 2026-09-16: the tool surface each member declares, and pruning to it

**Not an experiment — the repair P43 named and left undone.** `--prune` on
`openai_proxy`, `surface` on the pool contract, `tests/test_prune.py`.

P43's agent turn made **no tool calls at all** **[ran]**, and two separable things
were wrong with what the expert read: the **volume** of unknown tags (P25 prices an
unknown surface at 27 of 63 **[ran]**) and the **renaming** of the three it knew into
`mcp__lora-inbox__…`. Each member now declares the tags its corpus taught it, beside
the band, and the proxy keeps only offered tools matching one — exact name, or the
last segment of a namespaced one. Calls leave under the caller's name.

**What building it found, which no amount of reading would have.** Rendering the
pruned surface back and requiring it to equal the trained block **character for
character** caught the first version alphabetising the three lines — a block
`email-full` had never read, in a change whose entire purpose was to show it the block
it had read **[ran]** 2026-09-16. Order is now part of the declaration where a corpus
teaches one, and sorted where none does.

**It is off by default**, because every measurement before today ran without it.
`--prune` on and off is the arm pair, and it has not been run.

### Pre-registered 2026-09-16: P55 — acceptance as ranking, on experts graded by construction

Brief: [`../results/P55-graded-ranking-20260916/BRIEF.md`](../results/P55-graded-ranking-20260916/BRIEF.md).
Runner `training/harness/accept_rank.py`, gates as code in `tests/test_accept_rank.py`.
**Session A — `DONE`, 2026-09-17, three attempts, stopped `UNBOUGHT` at M-target.**
Result: [`../results/P55-graded-ranking-20260916/session_a.json`](../results/P55-graded-ranking-20260916/session_a.json);
attempts 1 and 2 kept under their own names — both were instrument faults of mine (a
preflight that measured the base's phrasing; a loop that refused the positional calls
the block itself asks for), each fixed with a test before the relaunch.

| arm | all 475 | human 351 | calls · refused | what it says |
|---|---:|---:|---|---|
| `Qwen2.5-3B` base | 0.516 | **0.345** | 0 · 0 | reproduces P31 exactly |
| **`email-full`, corpus mode** | **0.992** | **0.989** | 1053 · **0** | **M0 unlocked**: through `tool_calls` the same adapter scored 0.808 (P43). Served as its corpus teaches — stop at `</tag>`, inject the real result — it solves the task. Reproduced in two sessions, 31 s each |
| `Qwen2.5-32B-AWQ`, corpus mode | 0.813 | **0.746** | 1248 · 195 | gets every fact in 3–4 calls and **misapplies the rule** on 83 human cases; paired against the expert **2 : 87**, p = 0.0 — **resolvably worse** |

**M-α's preflights all passed** — C18 `applied`, templates identical, `prompt_logprobs`
one entry per token with `rank` — so the instrument is ready and was never run:
**the gate refused the target for the reason it was written for.** On this suite an
untrained 32B is not stronger than the trained 3B, and acceptance against it would
reward agreeing with wrong verdicts. Two things fail at once, both about the suite:
the best expert sits at the ceiling (0.99) and the target sits below it (0.75).

**The mathematics of this step** ([`FOUNDATIONS.md`](FOUNDATIONS.md) §7, §9). The
claim is $Q(E_a) > Q(E_b) \Rightarrow \alpha_T(E_a) > \alpha_T(E_b)$ with
$\alpha_T(E,c) = \tfrac{1}{n_c}\sum_i \mathbf 1[\tilde x_i = \arg\max p_T(\cdot\mid\cdot)]$;
it is only about quality under $Q(T) \ge \max_a Q(E_a)$, which is what M-target tests
as a paired sign test and what failed here ($0.746 < 0.989$, 2 : 87). The grades are
resolvable at $n=351$ only for $\delta \ge 0.07$ (power 0.93), which fixed them at
75 / 200 / 598. **Next step, in the same terms:** a suite where $Q(T) \ge \max Q(E)$
holds and $\max Q(E) < 1$ — the desk's `commitment` region satisfies the first by
measurement (target 1.000 at every depth) and the second by its gradient.

**Redesign candidate, counted as the first:** move the ordering test to the desk's
`commitment` region, where P51 already measured the 32B at **1.000 across all four
depths** and the base falling **1.000 → 0.800 → 0.133 → 0.000** **[ran]** — a target
stronger than the base by construction and a gradient no expert will sit on top of.
Needs a desk corpus (none exists) and three graded desk experts. Left for a decision.

Also from the boot: the chain installs `vllm>=0.28` and resolves to **0.29.0 — the same
version P33 ran** **[ran]**, so track D1 has nothing newer to re-check; D2 is the live
step for a 3.x drafter.

**The first test of the central claim.** Acceptance against a larger target has never
been measured on any target, and the reason was never hardware: ranking needs experts
that differ in quality, and this project has had one. So the experts are graded **by
construction** — `g75 ⊂ g200 ⊂ email-full`, one corpus, one base, only the amount of
data changing — and the verifier must order them *before* the target is served.

**A corpus/serving drift found on the way, and fixed first.** The corpus renders a
chain as `<tag>…</tag>= {result}`; served through `tool_calls` the expert cannot
receive a result mid-generation and **invents one** — P43's record has
`= {"turns": 1, "i_wrote_in_thread": false}` where the tool said `2, true` **[ran]**.
The runner serves the drafter the way the corpus teaches: stop at `</tag>`, inject
the real result, continue. Invented results are counted (`stray_results`), never
scored.

**Acceptance in tokens, for the first time.** Same tokenizer **[ran]** P48, so the
target is handed the draft verbatim and asked for `prompt_logprobs`: a token is
accepted iff its rank under the target is 1. Reported over all decision tokens
(primary), the tag spans, the verdict span, and as the accepted prefix — because a
chain is ~40 tokens and the verdict is one, and *"α does not rank"* has to be able to
say where the agreement lived.

**One mechanism per gate, one gate per session:** corpus-mode serving and C18 →
a target that beats the expert *on triage* (P49 bought it on drafting) → the
instrument's preflights → the grades resolved by the verifier → the ordering test.
Verdicts pre-registered: SUPPORTED / FALSIFIED / UNRESOLVED (a failure, not a tie) /
M1 not unlocked / UNBOUGHT.

**Track D — `Qwen3.8-27B` as the large model** is on the route, as mechanisms in
order. **D0 [ran] today:** `Qwen3.5-2B` and `Qwen3.5-4B` share an id space with
`Qwen3.8-27B` — 248,044 ids, 7 target-only, all audio/TTS specials; `<think>` is
shared. D1 re-checks C18 under the vLLM the chain installs today; D2 reads the
mechanism with the log in hand; D4 is this instrument pointed at 3.8-27B. Nothing in
P55 depends on D; D4 depends on all of P55.

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
