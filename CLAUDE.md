# lora-kernel — instructions for coding agents

This repository has one job: **build the agentic system as a pool of
self-contained QLoRAs over one resident base, discover which of them are good
enough to trust, and route what they cannot do to a frontier model.**

~~find out whether acceptance against a frontier target is a valid promotion
criterion for small experts, and then whether the frontier can be withdrawn
without losing verified quality~~ — **restated 2026-09-15**, and the history is
kept because the change was earned rather than chosen:

- **The frontier is no longer scaffolding to withdraw. It is a permanent
  component**, used where the local expert is measured to fail. P41 delivered
  **0.546 → 0.775** by sending one failing subdomain away, with 38% of cases
  leaving the machine **[ran]**.
- **Acceptance is not retired; it moved.** It was a promotion criterion for
  training. Its open job now is as a **routing signal** — deciding, per case,
  whether the local answer can be trusted. That is the same question asked where
  it pays.
- **Experts are trained by ordinary supervised fine-tuning first**, and the
  acceptance machinery is bought only to improve one that already exists (decided
  2026-09-15, `docs/EXPERIMENT_PLAN.md` §11).
- **Composition is out.** `harness.lora` is parked, not falsified: its measured
  result — a physics kernel taking a base from 0 to 123 of 150 cases reaching for
  email tools — stands and waits.

Everything else — the tournament, the verticals, a router that picks the member —
is downstream of a pool with **two useful members**, ~~which it does not yet have~~
**which it has on a synthetic region since 2026-09-18 [ran] P64**: `desk-commitment@v1`
released beside `email-full@v1` on one vLLM — 240/240 tying its recorded run, 202 : 0
against the base, each routed by its question. Both read the same inbox, so they *do*
meet in one problem; what selects between them is still a dictionary. What is not yet
had is a second member on a **real** region (milestone 4), and the band saturates at
`g75`, so nothing in P64 ranks experts.

**The buildable form of the original question, restated 2026-09-16** (plan §1):

> **Does acceptance against a larger model of the same family order small experts the
> way verified quality orders them — and can that model then be withdrawn, per region,
> without the verified score falling?**

Four things about it are settled and should not be re-derived:

- **The target is `Qwen2.5-32B-Instruct-AWQ`**, not a frontier. A frontier API cannot
  verify a drafted token **at all** — no logprobs for a forced continuation, a
  different tokenizer **[ran]** P48. The frontier keeps a different, permanent job:
  answering what the pool is measured to fail, worth 0.546 → 0.775.
- **Acceptance is for ranking, never for speed.** A drafting head trained on the
  target's hidden states beats our experts at latency and one exists for this target
  **[read]**; what it cannot do is choose between k experts. That is the only claim
  this architecture uniquely has.
- **A drafter's corpus is written by the target, not by an oracle** — and each expert
  sees only its own region, or acceptance comes out flat and the ranking collapses.
- **The suite passes `training/suite_gates.py` first.** All four suites this project
  previously measured on fail at least one **[ran]** P50.

**Restated 2026-09-16, and the correction was the user's.** Two useful members is
necessary and not sufficient: **they have to be close enough to meet in one
problem.** The two we have are fluid mechanics and inbox triage, which never co-occur
— and the proof is a number I first reported as good news: a twelve-line keyword rule
picks the right one **1.000** of the time **[ran]**. A discrimination problem solved
by twelve keywords is not a test of expert selection. The same run shows where it
gets hard: the fine route falls to **0.845**, confusing families that differ only in
whether a unit needs converting.

So the objective is **several close experts on one problem**, selected by
**acceptance** rather than by a router — because when candidates resemble each other
the prompt stops carrying the answer, and *which expert looks relevant* and *which
expert wrote what the larger model would have written* come apart. Design:
[`docs/analysis/close-experts.md`](docs/analysis/close-experts.md).

The workspace rules in `../AGENTS.md` apply here in full. What follows is what
this repository adds.

## 0. Do not drift off the project — read this before choosing what to run

**This project builds the runtime of a service: an OpenAI-compatible API that
resolves locally what falls in a measured region and sends the rest to a frontier
model, and OpenClaw instances per task on top of it** (README, *What this provides*).
Local resolution is a QLoRA, a written procedure the harness puts in the context, or
both; which one buys a region is measured, never assumed. A session that produces
neither an adapter, nor a knowledge document measured against one, nor a measurement
of the routing, has not advanced the project however good its numbers are. **The
customisation service and its tooling are not part of this runtime nor of the
open-source version** — build the instrument that measures a customisation, not the
tooling that produces it at scale.

The drift is real and it already happened once, on 2026-09-07: two sessions of
measurement produced four instrument findings, a failed frontier gate and a
validated promotion criterion — **and not one adapter**. The user's words:
*"¿por qué estás utilizando verified runtime, estamos construyendo el kernel
lora, con LoRAs? ¿o me estás saboteando el proyecto?"* The criticism landed.

So, the rules that keep a session on the project:

- **`../verified-runtime` is a yardstick, not the subject.** Borrowing its cases
  and its exact verifier is correct and cheap. Letting *its* question — how much
  capability lives in the harness — replace *this* project's question is the
  drift. When a result is about the suite rather than about adapters, say so and
  move on rather than buying another arm of it.
- **Anything needing a GPU is a Colab notebook or script, committed here.** This
  machine is a 16 GB arm64 Mac: it cannot serve vLLM and cannot hold a 26B. Do
  not propose local training of a large model, and do not let the machine's
  limits shrink the experiment — move the experiment to Colab instead.
- **The base is `Qwen/Qwen2.5-3B-Instruct`, and that is settled by measurement,
  not preference.** P33 read it against a control: vLLM 0.29.0 loads a LoRA on
  `Qwen3.5-4B`, logs that it did, and **serves the base anyway** **[ran]**. Gemma 4
  is not a peft base (`Gemma4ClippableLinear` is not `nn.Linear`). Do not
  re-litigate this; run `serve_openai --gate-only` against any new base instead.
- **Do not spend a session shopping for a target — the two that matter are
  already decided by measurement.** The **fallback** is `google/gemini-3.8-flash`,
  **66/90** on the fluids suite through the same client the local expert uses
  **[ran]** P41. The **speculative target** is `Qwen2.5-32B-Instruct`, because every
  `Qwen2.5-Instruct` size shares a byte-identical `tokenizer.json` with the base
  while the `Qwen3.x` line changed its vocabulary at 3.5 — its 27B models have
  248,044 entries and cannot verify a **Qwen 2.5** drafter **[ran]** P48. Usability
  is a property of the *pair*: a `Qwen3.5-2B/4B` drafter shares `Qwen3.8-27B`'s id
  space **[ran]** D0, which is why the 27B is the **goal** and the drafter is what
  moves (README, *The goal*). Run `training/harness/tokenizer_compat.py` before
  proposing any other pair.
- **When in doubt, the next step is the one that puts a weight delta on disk.**

## 1. The plan is the state

[`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md) is a **living document**, not
a proposal. It is the single place where the project's position is recorded.

- Every step carries its **objective**, its **gate**, and its **falsification
  condition**, written *before* the step runs.
- When a step finishes, its row is updated **the same session**, with the number
  that came out — whichever way it came out.
- When a result changes the plan, the change is written into the plan with the
  reason, and the superseded text stays visible as struck history rather than
  being deleted. A plan that only ever agreed with itself is not a record.
- Update the Spanish mirror in the same commit (§4).

## 2. [read] and [ran]

Every claim carries a marker.

- **[read]** — inferred from source, docs or an issue. Cite it.
- **[ran]** — observed by executing something in this repository, with the run
  directory named.

A previous flagship in this organisation reached 18,680 lines with three test
functions by not doing this. An unmarked claim is treated as [read].

## 3. Measurement rules that already cost us something

These are not style. Each one was paid for.

- **Headroom before treatment.** If the baseline sits at the ceiling, every arm
  ties and a tie reads as success. Check first; it is the cheapest run there is.
- **The verifier the loop cannot see.** Any fitness signal used to select or
  train an adapter comes from a held-out verifier. Otherwise the loop breeds
  adapters that flatter their scorer.
- **Report α with its `k`, and beside the verified score of the same run.** α
  alone is not a decision.
- **Buy arms in sequence, never as a grid.** The arm that can kill the hypothesis
  runs first. Attribution arms are bought only once there is an effect to
  attribute.
- **Persist every result as it lands, and stream position.** A run you cannot see
  the position of cannot be stopped early; a report written only at the end makes
  aborting cost everything.
- **A corpus must teach the prompt the model will be served.** The proxy appends
  the tool surface with arguments in **alphabetical** order; a corpus trained on the
  bare statement produced **71 refusals of 606 calls that looked like physics** and
  voided a whole run **[ran]** P38. Build the corpus by *calling* `render_tools`, not
  by copying what it prints — the copy is what drifted.
- **Keep the chain, not the last line.** A routing decision is made per case and
  reads the chain; P40 stored `{"answer": 35584.2}` and the question the pool exists
  to answer was not computable from a finished run **[ran]**.
- **A threshold inside the run-to-run spread reports the scheduler.** The same
  adapter, the same cases, temperature 0, scored **84, 81, 82** against a gate
  demanding 83 — every pair a tie **[ran]** P36/P38/P40. vLLM is not deterministic
  run to run. Read a clears/does-not verdict *beside* the paired comparison, never
  instead of it, and say which one is marginal.
- **A guard that reads source must read the code.** Three guards in one day fired on
  prose describing the absence they check for — `automated` inside an automated
  email's body, `fluid` inside a comment saying *no fluid names*, the broken idiom
  inside the comment documenting it **[ran]** 2026-09-15.
- **`grep -c` prints its zero and exits 1**, so `$(… | grep -c X || echo 0)` is
  `"0\n0"`. That made a weights rescue skip itself and cost a trained adapter
  **[ran]**. Use `weights_in()` in `chain_separate.sh`.
- **Check the floor as well as the ceiling.** The ceiling rule is written above;
  the mirror had no rule and cost a conclusion. **If every task sits above the
  treatment's floor, every arm fails and the failure reads as "the approach does not
  work."** The fluids suite's oracle solutions are 6, 7 or 9 steps with **no case
  below six**, and each family is pinned at one depth — so *this expert is too weak*
  and *this suite is too hard* were the same number, 0.122 **[ran]** 2026-09-15. A
  suite needs a difficulty axis before a capability claim is made on it;
  `training/physics/ladder.py` is the fluids one.
- **A gate copied from the frontier answers a different question.** *Can the
  frontier be withdrawn here* is gated on the frontier's score, and P41 used it
  correctly. *Is this expert sufficient* is gated on an **absolute** standard set by
  the work, with the frontier reported beside it as a ceiling check and ranking
  nothing. Asking only the first one makes every small expert look useless at
  whatever difficulty the suite happens to have.
- **A corpus with one difficulty teaches a floor, not just a skill.** P45: every
  example the fluids expert saw was a 6-to-9-step chain, and below that depth it
  over-solves on **18 of 18** cases — median five calls where the oracle needs two,
  inventing an area to answer a question about force that nobody asked. At or above
  its training depth, **0 of 17**. On three-step problems the **bare base beats it,
  0.167 to 0.000** **[ran]** 2026-09-15. Train on the band you intend to serve, and
  never read a specialised expert's score on an easier band as a capability.
- **Check the ceiling on *ranking*, not only on accuracy.** A calibration number
  has its own headroom and it is set by the information in the input. Group the
  cases by what the model can actually see; inside a group every case is identical,
  so the best any model can output is that group's base rate, and the AURC of *that*
  is what is achievable. P44 read a **0.400** AURC gap as room for a typed head;
  **69-82% of it was the suite**, and on the full inbox both arms were already at the
  ceiling — 0.030 and 0.007 left **[ran]** P46. `training/harness/ceiling.py`, and it
  costs no GPU.
- **A generated suite's shape space is bounded by its generator, and an adapter
  memorises shapes.** Three attempts, each defeated one level up: P53 memorised **one
  tail per family** (180/180 held-out completions verbatim in training); P54 memorised
  **one skeleton per (family, cut)** — 197 distinct completions, **6** skeletons; and
  adding names and loop forms raised the space to about **60**, which 720 training
  examples cover **twelve times over** **[ran]** 2026-09-16. For a held-out shape to
  be novel the space must exceed the training set — roughly ten structural dimensions
  of four choices each, which is a program generator and a different project.
  **Stop at three.** [`docs/analysis/generated-code-ceiling.md`](docs/analysis/generated-code-ceiling.md).
- **A distinct prompt is not a distinct question.** P53's step zero scored the
  adapter **180/180** against the base's 56/180, paired, p < 1e-5 — and **every one of
  those 180 held-out completions was already in the training set, word for word**
  **[ran]** 2026-09-16. The prompts all differed, because the constants differed; the
  *completion* was identical, because the constants were referenced by name and lived
  in the prefix. The adapter memorised one tail per family.
  **Deduplicate on what gets written, not only on what gets asked** — and check that
  what the answer contains comes from a space large enough not to recur: five
  polynomials across two hundred programs is thirty combinations and the tail repeats
  with them.
- **Training releases its GPU memory by exiting, not by asking.** P53 trained an
  adapter in-process and vLLM refused to start beside it: *"Free memory on device
  cuda:0 (32.79/39.49 GiB) on startup is less than desired GPU memory utilization
  (0.9, 35.54 GiB)"* — **6.7 GiB still held** **[ran]** 2026-09-16. `free()` runs
  `gc.collect()` and `empty_cache()`, which return cached blocks to the allocator;
  neither releases the CUDA context, and nothing running *inside* a process can.
  Train in a subprocess. P26's brief already said not to train inside a serving run,
  and overriding it with a reason that was sound about the *question* did not change
  the *mechanism*.
- **What a chain installs is derived from what the trainer imports, never kept by
  hand.** `chain_serve.sh` learned to train and its dependency line was never brought
  in line with the two chains that always did, so P53 reached `SFTTrainer` and died on
  `No module named 'trl'` **after twenty minutes of boot** **[ran]** 2026-09-16. The
  failure was documented in a comment two lines above the short list — recorded as
  *do not train in a serving session* rather than as *the list is short*. Fourth
  hand-kept list to lag the thing it tracked.
  **And the check must read the install command, not the file:** its own first version
  searched the whole script and found `trl` in the comments explaining that `trl` was
  missing. Fourth guard to fire on prose describing the absence it checks for.
- **An arm proves it can reach its tools before it scores anything.** P51's first
  attempt served vLLM without `--enable-auto-tool-choice --tool-call-parser`, so
  **every one of 240 requests returned HTTP 400** — and the progress line read
  `correct 0 calls 0 refused 0`, which is exactly what a model that cannot do the
  task looks like **[ran]** 2026-09-16. One probe call, checked for an error *and*
  for a tool call, costs ten seconds and would have saved the arm. Errors belong in
  the progress line for the same reason: a broken run must not be able to look like
  a floor.
- **A long run checkpoints and resumes, or a dead session costs all of it.** P47
  was lost **twice on the same measurement**: to a `KeyError` after all 475 cases had
  been scored, and then to a Colab session that stopped answering at **260 of 475**
  **[ran]** 2026-09-16. The first fix moved the summary after the write and did not
  help the second, because the loop still wrote **once, at the end**. A runner over a
  rented card writes every N cases and skips what is already on disk — and the chain
  downloads the partial file, because a checkpoint nobody fetches is a checkpoint
  nobody has.
- **Write the records before the summary, not after.** The rule above says persist
  every result as it lands; the failure it does not name is a runner that scores
  everything, then crashes computing its own summary with the file still unopened. A
  `KeyError` on a field name written from memory — `aurc_floor` for
  `aurc_oracle_floor` — threw away **475 cases of rented L4** that had already
  finished **[ran]** 2026-09-16. Dump the records first, compute the summary in a
  `try`, dump again.
- **A suite passes `training/suite_gates.py` or its numbers are not evidence.** The
  report of 2026-09-16 lined up every negative result of ten days and found the same
  thing underneath almost all of them: the suite was wrong, not the architecture.
  Seven ways, each paid for. They are now gates, and **all four suites this project
  has ever measured on fail at least one** **[ran]**
  `results/P50-suite-audit-20260916/`:
  - **every region of every suite sits at exactly one depth** — 4 of 4, 8 of 8, 2 of
    2, 3 of 3 — so region and difficulty are one variable everywhere, which is P45
    generalised and it was never noticed outside fluids;
  - the region is readable off the prompt at **0.856** (fluids) and **0.940** (email
    triage) against chance;
  - email drafting has **one** difficulty for all 180 cases.
  Four of the seven gates need a model and say so rather than guessing. And the
  deepest finding has no gate at all, because a check over a generator has the same
  author as the generator: **a generated suite cannot contain a difficulty nobody
  thought of.** The answer to that one is to let the base model choose where the
  difficulty is.
- **Count instrument redesigns.** Once is fine, twice is suspicious, three times
  is looking for the result. The stopping condition goes into the plan before the
  run.

## 4. Documents ship in two languages

`docs/*.md` has a mirror at `docs/es/*.md`. CI checks that the mirrors exist and
have the same section count, and that every internal link resolves:

    python3 scripts/check-mirrors.py

A stale mirror is worse than an absent one. Same commit, both sides.

## 5. Agents and skills are part of the deliverable

`.claude/agents/` and `.claude/skills/` are versioned with the code, and they are
expected to **change as the project learns**:

- After each step, ask whether the step needed a capability no agent had, or
  whether an agent stopped having a job. Create, edit or **deprecate** it, and
  record the change in the plan's §9 ledger.
- A deprecated agent is moved to `.claude/agents/deprecated/` with one line at
  the top saying what killed it. Deleting it loses the reason.
- New surface area is the expensive kind of progress: a new agent has to be
  justified by a step that already exists in the plan.

## 6. Git — land every significant step, do not accumulate

The user's instruction, 2026-09-08: **on each significant advance, commit, push,
open a PR and merge it to `main`.**

- **Never push to `main` directly.** The PR is the record; merging it is how the
  step lands. A branch that carries three steps is three steps nobody can revert
  independently.
- A step is significant when it changes what the project knows or can do: a
  result, a fix that changed a conclusion, a new capability, a decision recorded
  in the plan. Not every commit — every advance.
- The plan and its Spanish mirror are updated in the same PR as the work they
  describe, or the record and the code disagree the moment it merges.
- Commits say what changed and why, in the voice of the repository: declarative,
  specific, no ceremony.

## 7. What is out of scope until the plan says otherwise

Cross-adapter KV cache work, tree attention across adapters, a bespoke inference
runtime, vertical packs, the control plane. ~~All of it is downstream of the
withdrawal gap in §S5.~~ **Restated 2026-09-15**: the withdrawal gap is closed and
the frontier is staying, so all of it is now downstream of **a pool with two useful
members** — which needs a second expert that clears its own bar (**cleared on a
synthetic region [ran] P64 2026-09-18**; a real one is milestone 4), and a routing
signal that can see a chain which is coherent and wrong (**still open**).

**Composition and `harness.lora` are parked, not out of scope**: they return if
producing self-contained experts turns out expensive at scale, with P34's result
already paid for.

**Restated 2026-09-18, service order.** The customisation service and its tooling — a
customer's procedure documents, adapters trained as a service, the automation of
traces → corpus → gate → release — are out of scope for this runtime and for the
open-source version. What is in scope is every instrument that measures whether a
customisation works (P61 is the first), and the runtime that serves it.

## 8. The order of dependencies — phases, bottom-up (adopted 2026-09-17)

The plan is a stack. **Each layer is validated alone, frozen with a test that
protects it, and only then is the layer above built on it.** This formalises what
§3 already says as explicit dependencies, because every time a layer above was
touched while one below was in doubt it cost a whole run (P53, P55 A twice).

**The global rule.** No piece counts as working until it has **(a) a preflight,
(b) a persisted artefact, (c) a test that re-verifies it every session, and (d) a
failure condition written before it runs.**

| # | piece | depends on | the arm that kills first | cost |
|---|---|---|---|---|
| **0** | the serving substrate — C18 on every pool member, tools reachable, stop honoured | nothing | the identity gate | minutes |
| **1** | a reproducible release of `email-full` (adapter + corpus + prompt hash), re-served and paired against its recorded run | 0 | the re-serve | low |
| **2** | a suite with a verifier and a gradient: `suite_gates` pass; base gradient ≥ 0.30 across depth; **target beats the best expert, paired, $p \le 0.05$** (M-target) | 1 | headroom, **zero GPU** where P51 already measured it | zero → low |
| **3** | experts the verifier orders (M1): nested grades, adjacent pairs paired | 2 | **the smallest grade alone** — if `g25` already saturates, stop before `g75` | medium |
| **4** | the ordering verdict by acceptance (M-α, M2) — *the thesis* | 3 | the thesis itself | medium–high |
| **5** | the product end to end with real groups (CASE-TEAM), `--prune` off as the attribution arm | 1 | attribution of `--prune` | medium |
| **6** | the route to `Qwen3.8-27B` (D2 → D3 → D4) | **4 = SUPPORTED** — and Phase 4 **reopened as one arm on 2026-09-17 after review**: what is measured is $Q(T) < \max Q(E)$ for an *untrained* target in two easy regions, not that no generated suite has the window — the next arm is a trained 32B on a deeper `commitment` band (P60). The route stays blocked until M2 has a verdict | D2 with the log in hand | high |

**Phase 0** is `training/harness/verify_substrate.py` (spec:
[`docs/SUBSTRATE-GATE.md`](docs/SUBSTRATE-GATE.md)); it is the entry to everything
and is re-run whenever vLLM or the base changes — the only permitted way to
re-validate. **Phase 6 is blocked on M2 SUPPORTED as a dependency, not a
preference**: if acceptance does not rank, D4 buys a faster version of a mechanism
that does not work.

Three transversal rules, added to §3's:

- **Freeze per piece.** When a phase passes, its prompt, corpus, flags and vLLM
  version are frozen; changing any of them is a **counted redesign** — for what works
  as well as for the instrument.
- **One unknown per run.** Phase 4 measures acceptance *over grades Phase 3 already
  validated*. Training grades and measuring α in one session and getting a strange
  number is not attributable; the phase split is the free attribution.
- **The negative outcome is a deliverable.** If M1 or M2 fails, the plan ends there
  and the README is rewritten around the measured product. That commitment is signed
  *before* Phase 4 runs: FALSIFIED closes acceptance-as-ranking for good; UNRESOLVED
  allows one more redesign (the third is the stopping condition, already written).

## 8b. The service order — milestones over the phases (adopted 2026-09-18)

§8's phases remain the dependency order of the *instrument*. What is built next is
decided by the **service**: first an OpenAI-compatible API that resolves locally and
forwards the rest, then OpenClaw instances per task over it; some of it artisanal at
first, automated over two to three months. The milestones, in order, each with the
arm that kills it first:

| # | milestone | depends on | the arm that kills first |
|---|---|---|---|
| **1** | weights or harness on one region (P61): base, base + procedure document, trained expert, one session, sign test on discordant pairs | Phase 1 | base + document ≤ base — a 3B does not follow a written procedure |
| **2** | routing per request: the proxy decides local or frontier | 1 | the region classifier below P41's by-region 0.775 |
| **3** | OpenClaw live with `--prune`; a profile template per task | Phase 5 | the live turn calls tools it was not offered |
| **4** | the first real region, customised by hand, released through Phase 1's door | 1–3, a sandbox, keys rotated | the release gate |
| **5** | second and third regions; the region table per client | 4 | a second member that fails its own bar (fluids did) |
| **6** | traces → corpus → gate → release without hands | 4, 5 | the automated release regresses the hand-made one |
| **7** | the large local model, `Qwen3.8-27B` (Phase 6) | 5, and the frontier bill | D2 |

Three rules that follow:

- **M2 does not block the service.** P60 §3b **[ran]** 2026-09-18: vLLM applies a
  LoRA over the AWQ 32B (logprob gate 3/3 against a base-vs-base control; text gate
  2/3), so the trained-target arm (3c/3d) is buildable. It runs after milestone 5, as
  a quality gate on local answers, and the redesign counter (2 of 3) still applies.
- **A customisation is measured before it is sold.** Every region enters through the
  same door: a suite with a verifier, the base as the headroom arm, the sign test.
- **Milestone 1 is measured [ran] P61 2026-09-18: on a 3B the procedure has to be in the
  weights.** Base + a 914-token procedure document made 0 tool calls on 351/351 human
  messages and stayed under the majority bar; the expert beats it 137 : 1. Do not write
  another procedure document for this base; a document carries knowledge on top of an
  adapter, or the base is larger and that is measured first.
- **A member is what its corpus taught — the block and the prompt [ran] P63 2026-09-18.**
  Live, under the runtime's prompt the expert called a tool on 2/32 human turns (0.281);
  under its released prompt with the corpus loop's bounds, 19/32 and 0.688. Serve members
  with `--prune --member-prompt`; measure a member under any other prompt as a different
  arm, never as the member.
- **Artisanal is allowed; unmeasured is not.** A hand-written document or a
  hand-trained adapter is fine in the first months if its number is on disk.

## 9. The mathematics is required, everywhere (adopted 2026-09-17)

Every document, the tests' documentation and every next-step entry carry the
formula they rest on, tied to the run that instantiates it —
[`docs/FOUNDATIONS.md`](docs/FOUNDATIONS.md) derives them and §11 there maps section
→ run. **Every Colab run updates the formula it instantiates.** A formula with no run
under it is a claim; a run with no formula over it is a number.

