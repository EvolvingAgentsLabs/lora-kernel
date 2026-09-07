# lora-kernel — instructions for coding agents

This repository has one job: find out whether **acceptance against a frontier
target is a valid promotion criterion for small experts**, and then whether the
frontier can be withdrawn without losing verified quality.

Everything else — the adapter pool, the tournament, the kernel adapter, the
verticals — is downstream of that and must not be built before it.

The workspace rules in `../AGENTS.md` apply here in full. What follows is what
this repository adds.

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

## 6. Git

- **Never push to `main`.** Branch, commit, open a PR — including for documents.
- Commits say what changed and why, in the voice of the repository: declarative,
  specific, no ceremony.

## 7. What is out of scope until the plan says otherwise

Cross-adapter KV cache work, tree attention across adapters, a bespoke inference
runtime, vertical packs, the control plane. All of it is downstream of the
withdrawal gap in [`docs/EXPERIMENT_PLAN.md`](docs/EXPERIMENT_PLAN.md) §S5.
