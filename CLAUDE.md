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
is downstream of a pool with **two useful members**, which it does not yet have.

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

**This project builds LoRA adapters.** The thesis is that the entire agentic
system is a pool of QLoRAs over one base model. Everything else — the acceptance
surface, the target, the tournament — exists to decide *which adapter* and *when*.
A session that produces no adapter, and no measurement of an adapter, has not
advanced the project however good its numbers are.

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
  248,044 entries and cannot verify our drafters at all **[ran]** P48. Run
  `training/harness/tokenizer_compat.py` before proposing any other.
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
members** — which needs a second expert that clears its own bar, and a routing
signal that can see a chain which is coherent and wrong.

**Composition and `harness.lora` are parked, not out of scope**: they return if
producing self-contained experts turns out expensive at scale, with P34's result
already paid for.
