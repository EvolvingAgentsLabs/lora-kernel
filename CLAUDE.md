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
- **Do not spend a session shopping for a target.** `google/gemini-3.8-flash`
  scores **66/90** on the fluids suite through the same client the local expert
  uses **[ran]** P41. That is the fallback's number; a better one is a purchase,
  not a prerequisite.
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
