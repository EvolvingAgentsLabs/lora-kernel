# lora-kernel — instructions for coding agents

This repository has one job, restated by the user on 2026-09-19:

> **Build the service as experts defined by their corpora: a very small router that decides
> which expert's corpus a request falls in and abstains to a frontier model when it falls in
> none; and, per subdomain, a speculative pair — a LoRA on a small model and a LoRA on a
> large one, trained on the same corpus. Family: Qwen 3.x, small and large.**
>
> **And each expert gets a knowledge base of its own subdomain — encyclopedic and operational
> notes, embedded — where what the LoRA learns is the *trajectory* through it. The weights hold
> the navigation, the base holds the content; a trajectory through operational notes is the
> harness. Measured on fluid mechanics, split into subdomains.**

**The LoRA is not the textbook; it is the specialist who knows how to use the library.** The memory —
library, radar, three verbs, a LoRA trained on the habit of navigating, a software referee — is the
core of version 1.0 and is specified in [`docs/MEMORY.md`](docs/MEMORY.md). Build it in that
document's order (W1–W7); do not start a piece whose gate the piece before it has not passed.

The service is an OpenAI-compatible API that resolves locally what falls in a measured
region and forwards the rest, with OpenClaw instances per task on top. Read
[`README.md`](README.md) for the shape, [`docs/PLAN.md`](docs/PLAN.md) for the position,
[`docs/RECORD.md`](docs/RECORD.md) before proposing anything — most obvious ideas are
already in it, measured, several of them negative.

The workspace rules in `../AGENTS.md` apply here in full. What follows is what this
repository adds.

## 0. Do not drift off the project

A session that produces neither an adapter, nor a router measured against the dictionary,
nor a measurement of a pair, nor a knowledge base measured against the same expert without it,
nor a region released through the gate, has not advanced the
project however good its numbers are. The drift already happened once: two sessions of
instrument findings and not one adapter, and the user's words were *"¿me estás saboteando
el proyecto?"* **When in doubt, the next step is the one that puts a weight delta on disk.**

- **`../verified-runtime` is a yardstick, not the subject.** Borrow its cases and verifier;
  do not let its question replace this one.
- **Anything needing a GPU runs on Colab through `training/harness/chain_serve.sh`.** This
  machine is a 16 GB arm64 Mac. Do not shrink an experiment to fit it. A 27B is A100 work.
- **The family is Qwen 3.x and that is decided.** Small `Qwen3.5-4B` (or `2B`), large
  `Qwen3.8-27B`; one id space **[ran]** D0. **The released members are on
  `Qwen3.5-4B` since milestone 1 [ran]** (`releases/*@v2.json`, each tying its Qwen 2.5 release);
  the `@v1` releases on `Qwen2.5-3B-Instruct` stay as the control arm. New regions are trained on the
  4B — after checking how much headroom its bare base leaves, which is a lot less than the 3B's. Gemma 4 is the
  named alternative and is blocked at PEFT **[ran]** P29. Do not shop for other bases; run
  `lora_matrix` against a candidate instead.
- **The frontier is a permanent component**, `google/gemini-3.8-flash` through the same
  client the members use. It answers what falls in no corpus and what a region is measured
  to fail. It is never a speculative target: no logprobs, another tokenizer **[ran]** P48.
- **Scope.** The customisation service and its tooling — a customer's corpora, adapters as
  a service, traces → corpus → gate → release without hands — are not part of this runtime
  nor of the open-source version. Build the instrument that measures a customisation.
- **Respect the design; bring facts as constraints.** The architecture is the user's.
  Technical findings enter as engineering constraints inside it, with their run named.

## 1. The plan is the state

[`docs/PLAN.md`](docs/PLAN.md) is a living document. Every milestone carries objective, gate
and falsification condition **before** it runs; its row is updated the same session a result
lands, whichever way; superseded text is struck, not deleted; the Spanish mirror changes in
the same commit. A finished measurement also gets its line in
[`docs/RECORD.md`](docs/RECORD.md).

**Brief before run.** `results/<run>/BRIEF.md` — what, why, which model, which provider,
what falsifies it, the verdict table — exists before the chain starts, not beside the report.

## 2. [read] and [ran]

Every claim carries a marker. **[read]** — inferred from source, docs or a paper; cite it.
**[ran]** — observed by executing something here, run directory named. Unmarked is treated
as [read]. A previous flagship in this organisation reached 18,680 lines with three test
functions by not doing this. A P-number with no directory on `main` is at the tag
`v0.1-foundations`.

## 3. Measurement rules that already cost something

These are not style. Each was paid for; [`docs/RECORD.md`](docs/RECORD.md) §4 has the bill.

**Before the treatment**
- **Headroom first — the ceiling and the floor.** A baseline at the ceiling makes every arm
  tie and the tie reads as success; every task above the treatment's floor makes every arm
  fail and that reads as "the approach does not work". A suite needs a difficulty axis.
- **A ranking or calibration number has its own ceiling**, set by the information in the
  input. `training/harness/ceiling.py`, zero GPU.
- **A suite passes `training/suite_gates.py` or its numbers are not evidence.** A generated
  suite cannot contain a difficulty nobody thought of, and an adapter memorises shapes:
  deduplicate on what gets *written*, not on what gets asked.
- **A corpus with one difficulty teaches a floor.** Train on the band you intend to serve.
- **Knowledge that sits fixed in a corpus is memorised, and then it prices nothing.** A control
  with no lookup tool scored 27/30 over a fourteen-value table (P15, P21). Whatever a knowledge
  base is meant to supply is drawn **per case** — values *and* the coefficients of a procedure —
  and the run asserts that no looked-up value occurs in the statement.
- **A small model does not follow what it merely reads** (P61). If notes are to be followed,
  following is what the adapter is trained on; never measure a base of knowledge by pasting it
  into the prompt of a model that was not.
- **A corpus must teach the prompt the model will be served.** Generators *call*
  `render_tools`; the copy is what drifted. **A member is its corpus — block and prompt:**
  serve with `--prune --member-prompt`, and measure a member under any other prompt as a
  different arm, never as the member.

**During the run**
- **Buy arms in sequence, never as a grid.** The arm that can kill the hypothesis first;
  attribution only once there is an effect.
- **One unknown per run.** Training and measuring in one session yields a number nobody
  can attribute.
- **An arm proves it can reach its tools before it scores.** A broken run must not be able
  to look like a floor; errors belong in the progress line.
- **Persist every result as it lands, stream position, checkpoint and resume.** Records
  before the summary; the chain fetches partials. No `| tail`.
- **Training releases GPU memory by exiting.** Train in a subprocess.

**Reading the result**
- **The verdict is in the file, never in the exit code.**
- **The verifier the loop cannot see.** Any signal used to select or train comes from a
  held-out verifier.
- **Two arms on the same fixtures are paired** — exact sign test on discordant pairs,
  `bar.compare`. "Beats the bar" fires ~45 % by chance on a model sitting at the bar:
  `bar.py`, exact binomial.
- **A threshold inside the run-to-run spread reports the scheduler.** vLLM is not
  deterministic at temperature 0: 84, 81, 82 on one adapter. Read a verdict beside the
  paired test.
- **Report α with its `k`, beside the verified score of the same run.**
- **A gate copied from the frontier answers another question.** *Is this expert
  sufficient* is gated on an absolute standard; the frontier is a ceiling check beside it.
- **Keep the chain, not the last line.** A routing decision reads the chain.
- **On a large quantised model use the logprob gate with a base-vs-base control.** The text
  gate read a toy adapter on a 32B as *not applied*.
- **Split a log into its events before counting lines in it.** vLLM activates dummy LoRAs
  while profiling; a line counter read 0 of 178 modules as 531.

**The harness itself**
- **A guard that reads source must read the code**, not prose describing the absence it
  checks for. Four guards fired that way.
- **What a chain installs is derived from what the trainer imports.** Every new `[prefix]`
  a runner prints goes in the chain's peek regex (`tests/test_chain_scripts.py`).
- **Bash:** `grep -c` prints its zero *and* exits 1; backticks in an unquoted heredoc
  execute; a chain runs from a copy of itself, so do not edit it while it runs;
  `pytest | tail -1 && git commit` does not stop on failure; `MARGS=""` falls to the chain's
  default.
- **Colab:** T4 has no bf16 whatever the flag says; an expired `colab exec` is not a failed
  command; install vLLM first; one chain at a time — they share `/tmp/_v*.py`; use a
  worktree for documents while a chain is fetching.
- **Freeze the design, *then* write the set that counts.** Three looks at the same sets said
  milestone 2's router was perfect; one set written after the freeze found it loses every
  real-looking request. A set the designer has iterated against is a training set.
- **A model of a generated corpus learns the generator.** Every generated address ended `.com`,
  so `. com >` became part of what a request *is* (M2).
- **Clean the tree by what is *named*, not only by what is imported.** An import closure removed
  a trainer three runners start by name in a subprocess; `tests/test_pool_base.py` resolves every
  `training.*` module named in a string, a chain or a document.
- **Serve an expert the way its corpus taught it, and suspect the path before the model.** A
  fluids expert scored 11/90 through `tool_calls` messages and **90/90** with results written inline
  as trained; for four days that was *small models cannot reason*. Before a capability is declared
  absent, read the failure where it happens (*was the result used?*) and re-serve once in corpus mode.
- **A Colab session lives sixty minutes** (`colab log -s <name> | grep EVENT`). The unit of work is a
  session: one training per session, adapters fetched while it lives, runs resumable across sessions.
- **No model runs on the user's machine.** Anything that calls a model goes through the chain; local
  is for tests, generators and replays over records.
- **On the 3.x line, thinking is off for members, in every render.** A trained turn sits behind an
  empty `<think>` block and the default generation prompt leaves it open: a bare base thinks its
  tokens away and scores as a floor.
- **Count the redesigns.** Once is fine, twice is suspicious, the third is looking for the
  result. The stopping condition goes in the brief.

## 4. Documents ship in two languages

`docs/*.md` has a mirror at `docs/es/*.md`, same section count, every internal link
resolving — `python3 scripts/check-mirrors.py`. `README.md` has `README.es.md`. A stale
mirror is worse than an absent one: same commit, both sides. Formulas are required
(§7): a formula with no run under it is a claim; a run with no formula over it is a number.

## 5. Agents and skills are part of the deliverable

`.claude/agents/` and `.claude/skills/` are versioned and change as the project learns.
After each step ask whether it needed a capability no agent had, or whether an agent lost
its job. A deprecated agent moves to `.claude/agents/deprecated/` with one line saying what
killed it. Record the change in the plan's §4 ledger. A new agent is justified by a step
that already exists in the plan.

## 6. Git

On each significant advance: commit, push, open a PR. **Never push to `main`.** The PR is
the record; the merge is the user's call unless they have said so in the session. A step is
significant when it changes what the project knows or can do. Commits say what changed and
why, declarative and specific.

## 7. The mathematics is required

Every document, every test's docstring and every plan entry carries the formula it rests
on, tied to the run that instantiates it. [`docs/FOUNDATIONS.md`](docs/FOUNDATIONS.md)
derives them and its §11 maps section → run. Section numbers there are stable: living code
cites them.
