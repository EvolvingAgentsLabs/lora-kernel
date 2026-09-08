# lora-kernel — instructions for coding agents

This repository has one job: find out whether **acceptance against a frontier
target is a valid promotion criterion for small experts**, and then whether the
frontier can be withdrawn without losing verified quality.

Everything else — the adapter pool, the tournament, the kernel adapter, the
verticals — is downstream of that and must not be built before it.

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
- **The models this project uses are the ones the user named**:
  `google/gemma-4-26B-A4B-it` and `google/gemma-4-E4B-it` for the adapters
  (`gemma-4-12B-it` is the local baseline already measured), and small qwen3.5
  models as candidates. Not a menu to re-litigate each session.
- **Do not spend a session shopping for a target.** The frontier is scaffolding
  and it is designed to be removed; if it fails its gate, record it and go back
  to the adapters.
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
runtime, vertical packs, the control plane. All of it is downstream of the
withdrawal gap in [`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md) §S5.
