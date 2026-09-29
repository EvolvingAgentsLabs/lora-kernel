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
- **Two runtimes, the user's decision, 2026-09-28.** `server` is vLLM on Colab — every training and every
  measurement. `edge` is **llama.cpp on the user's own machine** — serving a member to a live runtime (OpenClaw):
  the E4B as **Q8_0** GGUF (Q4_0 flips an order id with the prompt cache **[ran]** LIVE-distributor) plus the member's
  LoRA converted to GGUF, hot-swapped per request or by `POST /lora-adapters` in ~3 ms **[ran]** MAC2. The distributor
  ran 6/6 live that way, Haiku writing the one out-of-scope turn **[ran]** M10. MLX stays a research bench (Python access
  to the graph). ~~MLX stays the `edge` engine~~ (MAC2's verdict was about speculative decoding, not serving). A result
  from the edge is a different arm from the same member on vLLM bf16, and says so.
- **New members are trained on Gemma 4 E4B — the user's decision, 2026-09-25, on B1 [ran].** Measured against
  `Qwen3.5-4B` on W9's wiki with the same corpus and recipe: a tie (38/40 against 35 and 35, 4 : 1 each), and the user
  had decided before any stage ran that parity chooses Gemma because the development stack targets it. The LoRA must
  exclude Gemma's vision/audio towers (`s4_train.towers_to_exclude`) — P29's block was that and nothing else. **The
  released members move one by one through the gate:** **every released member is on Gemma**: `email-full@v3` (M1b **[ran]**), `desk-commitment@v3` trained on both desk bands (M1d **[ran]**: shallow 240/240, deep 239/240 against the bare Gemma's 83), `distributor-wiki@v2` (B5 **[ran]**: W9's corpus plus comparisons, 37/40 on the comparison band, W9's set unchanged);
  the `@v1` releases on `Qwen2.5-3B-Instruct` stay as the control arm. New regions still check the bare base's headroom
  first — Gemma's leaves less than Qwen's (it walks W9 untrained 19/40 where Qwen walks 0/40). The large half of a pair on Gemma is `gemma-4-12B-it` (B2 **[ran]**: one id space, LoRA served); its LoRA raises
  acceptance of E4B drafts α 0.871 → 0.898 (B4 **[ran]**), and buys no accuracy: taught comparisons, the E4B alone does 37/40 (B3, B5 **[ran]**). Speculative decoding with a LoRA on the 12B runs in vLLM with Gemma's own MTP drafter: 1.7–2.1× with the LoRA on, 2.7× without (F0 **[ran]**, FP8, output identity not yet established); 1.92× in bf16 on an A100 (C0 **[ran]**); on the E4B with its own MTP drafter 2.4× with the LoRA on (C0-upper **[ran]**). The LoRA halves the drafter's acceptance on its domain (0.8 → 0.4, both sizes), confining the LoRA to the upper layers gives none of it back (ρ = −0.02, C0-upper **[ran]**), and on the Mac the MTP drafter slows the 12B (MAC2 **[ran]**): an aligned drafter is the open lever. ~~The family is Qwen 3.x and that is decided … Gemma 4 is the named alternative and is
  blocked at PEFT **[ran]** P29.~~ Do not shop for other bases; run `lora_matrix` against a candidate instead.
- **Multi-turn goes through a short-term operational memory, not through the prompt — the user's design, 2026-09-29.**
  `examples/common/opmemory.py`: a session cache (organisation, user, session) and an organisation cache (`global.<key>`),
  served by the tool layer as `<get>key</get>` / `<put>key=value</put>`, bounded by the claim, every write logged;
  workflows declared in TOML (`examples/<org>/workflows/`), advanced by the calls that ran, never by the model. A member
  served with it (`Gateway(memory=, workflows=)`) reads one line — `state: <workflow>/<state> · keys: <names>` — instead of
  the conversation, and learns in its corpus the workflow, its tools and the keys: **the workflow harness, inside each
  member**, not a composed adapter (what parked `harness.lora`). Its bar is MT0 **[ran]**: without the conversation 4/54
  dependent turns, with it 43/54 — but a reference written into free text is lost 8/10. H1 **[ran]**: the harness
  member resolves 53/54 against history's 43/54 (claims 10/10), every right turn fetched by key, a flat prompt — per arm
  PASSED — **the user's decision, 2026-09-29, of the two readings recorded**; as written the verdict was VOID because
  the brief's first-turns rule applied across arms and the no-block arm scored 0/60 (a member never shown its tools
  undescribed does not know them) — an instrument error, kept on record. **A VOID rule is per arm** from now on. Design and decisions in `docs/review/harness-workflow-kv.md`; every mechanism explained
  in `docs/MECHANISMS.md`. The long-session test is the **team tracker** (`examples/tracker/`, Jira + Confluence-like,
  synthetic; H2 **[ran]** 2026-09-29: harness 146/160, 91.3 %, flat prompt, descriptively 142:0 — **as written
  FALSIFIED**, because `base-history`'s own broken first turns, 44/60, tripped the same per-arm VOID rule and voided
  the comparison instead of the treatment; **the lesson: a per-arm first-turns VOID guards a trained member against a
  mid-training failure, and must not be asked of an untrained baseline whose failure is the headroom** — **the user's
  decision, 2026-09-29: reading 1, the harness PASSED on the readable conditions; FALSIFIED-as-written stays on
  record with its two instrument errors (the per-arm VOID and the anchor check below).** Not rerun: no rule change
  could move a baseline at 4/160. `harness-noblock` (80/160) is a corpus bug, not partial learning: the block-less
  third was rendered by `j % 3 == 2`, the same modulus the roles rotate on, so all 400 block-less rows were QA's —
  the member learned block-less exactly the role it was shown (QA 80/80; lead/developer 0/20, lead's one exception
  `sprint_board`, a call with no argument). QA's final-comment miss (6/20) is one eval phrasing ("Note on it: …" 1/15
  vs "Put a comment on it: …" 5/5). **H3 is pre-registered and running**: `tr-s1` on a second corpus against `tr-s0`
  on a fresh held-out suite (`results/H3-tracker-corpus-v2-20260929/BRIEF.md`). The gateway's
  default still reads only the last request; `history=True` is the naive arm, never the product.
- **One L4 serves several members at once without contention** (C1 **[ran]**: four adapters mixed keep 1.03× one adapter's
  throughput at 16 sessions; 32 sessions at p95 TTFT 0.24 s, 0 errors). Do not design around LoRA-mixing cost on vLLM.
- **The frontier is a permanent component**, `google/gemini-3.8-flash` through the same
  client the members use — in the live runs, **Claude Haiku 4.5** through the gateway's `--frontier-*` flags, the key
  in `~/.config/lora-kernel/frontier.env` (never in a flag, a log or a commit), under a spend cap. A member reaches it only
  if its corpus taught it to answer `OUT OF SCOPE` (the school's does; the distributor's since M10 **[ran]**). It answers what falls in no corpus and what a region is measured
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
- **A balanced corpus over eight notes teaches eight notes** — a reading skill needs the shape over many
  notes, or is left to the base. Shown a conditional value in eight trained notes, the adapter reads it
  there (17/18) and on an unseen note writes the first number (4/15) where the untrained base reads 15/15
  **[ran]** W5c.
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
  worktree for documents while a chain is fetching; **never `colab exec` into a session a chain is
  polling** — a hand probe beside the chain's own may have cost W5c a whole session **[ran]**. **A rejected
  accelerator is quota, not an outage** — `colab new` exits 0 on it, the chain now reads what it said and
  stops; a T4 is not a substitute (no bf16: an adapter trained in bf16 and served in fp16 is a second
  unknown) **[ran]** 2026-09-20. **A launch is proven by `run.log` on the VM, not by the exec's exit code** — W5e's first A100
  sat 25 minutes behind a runner that never started; the chain now probes and relaunches. **Killing a chain
  does not stop its card** (SIGTERM skips the EXIT trap): `colab stop -s <name>` after **[ran]** 2026-09-23.
  **An adapter a later arm carries in lives outside the scratchpad** (`~/lora-kernel-adapters/`): W5c's was lost.
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
- ~~**No model runs on the user's machine.**~~ **Measurement and training run on Colab through the chain**; local is for
  tests, generators, replays over records — and, since 2026-09-28, the `edge` runtime above (llama.cpp serving a member
  for a live demo, the user's decision). Nothing local is a measurement of a member unless its brief names the local arm.
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
