# lora-kernel

![A specialist at a desk in a small reading room. Behind them a wall of card-catalogue drawers in two halves — PROCEDURES, its drawers joined by a route line, and ENCYCLOPEDIA, branching like a tree. A small radar dish on the desk lights exactly three drawers. Through a doorway, far off, a large building marked 'frontier'.](docs/img/hero.png)

*The specialist, the library, the radar — and, through the door, the frontier, for when no drawer fits.*

**The LoRA is not the textbook. It is the specialist who knows how to use the library.**

[![license Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![family Qwen 3.x](https://img.shields.io/badge/family-Qwen%203.x-8A5C10)](docs/ARCHITECTURE.md)
[![core 1.0 specified](https://img.shields.io/badge/core%201.0-specified-555)](docs/MEMORY.md)
[![record v0.1-foundations](https://img.shields.io/badge/record-v0.1--foundations-555)](docs/RECORD.md)

*[Español](README.es.md)*

## The problem

An organisation running on agents keeps sending the same handful of repeating jobs — triage an
inbox, log a maintenance request, answer from a checklist — to a frontier model in the cloud, at
frontier prices, on data that often should not leave the building. The usual answer, fine-tuning a
model on the outcomes, trades that away for a worse problem: the facts end up **baked into the
weights**, so the day a procedure changes there is no file to edit — only a retrain, and until it
happens the model confidently gives the old answer.

lora-kernel keeps the facts in a library of markdown notes a person can read and correct, and trains
a small model only to find its way to the right one. What an expert knows how to *do* — which tools
to reach for, in what order, under this organisation's own rules — lives in a small adapter's
weights, trained by ordinary SFT. What it needs to *know* — the current value, the current
procedure — stays outside the weights, in a file. A very small router decides which expert's
territory a request falls in, and abstains to a frontier model for everything else, so nothing gets
answered outside its trained ground.

It ships as an **OpenAI-compatible API** — one resident model, several adapters, each request served
by its own — with **OpenClaw instances per task** on top.

Every claim below is marked **[ran]** (observed in this repository, run named), **[read]** (from
source or a paper) or **[spec]** (decided, not yet built) — and everything measured so far is on
generated suites, not real traffic yet. The living numbers, including what has not passed, are in
[`docs/PLAN.md`](docs/PLAN.md) and [`docs/RECORD.md`](docs/RECORD.md); what follows is what does not
change every time one of them moves.

---

## The core of version 1.0

![A request meets a signpost, the router. Two lanes lead to two specialists, each at a desk with its own two-shelf bookcase; a dashed third lane leads off to a distant building, the frontier. One band runs under both desks: the runtime, the referee.](docs/img/core-1-0.png)

*The core of 1.0: a router that may abstain, a specialist and a library per subdomain, one referee under all of them.*

Five things, and how each one changes:

| | what it is | changes by |
|---|---|---|
| **An expert is its corpus** | a QLoRA per subdomain, trained by ordinary SFT; served under exactly the prompt, tool block and result format its corpus taught — or it is a different model | a training run |
| **The router** | a very small model of those same corpora: *whose distribution is this request?* — and it **abstains** when the answer is none. Abstention is the frontier | re-indexing the corpora |
| **The memory** | a library of notes the expert navigates — below | **editing markdown** |
| **The runtime** | a small Python referee inside the proxy: executes the expert's commands, applies a site's rules, enforces the order of steps | a code change |
| **The release contract** | one manifest per member — corpus, adapter, library, radar and grammar, each hashed; admitted by a paired test against the bare base | a gate that has to pass |

And one thing that attaches per subdomain where it is measured to pay, **not required by 1.0**: a
second LoRA on a large model of the same family, trained on the same corpus, that verifies what the
small one drafts ([`docs/PLAN.md`](docs/PLAN.md) milestones 3–4).

### The memory, in five pieces

Full specification: [`docs/MEMORY.md`](docs/MEMORY.md) **[spec]**.

1. **The library — two shelves of markdown**, each note under half a page. The **operational
   harness** (*how is it done?*): recipe-like notes whose links are the control flow — `requires`
   (before this, that), `next` (the step that follows), `uses` (for this step, consult…). The
   **encyclopedic wiki** (*what is it, which formula applies?*): a tree, general to specific, that
   classifies which case you are in before you compute. **Shaped like Wikipedia, its unit is the
   atomic statement:** a page is a list of one-sentence, checkable statements under anchors
   (`§supplier`, `§if-damaged`), links live inside the statement that names them, and an answer cites
   the statement it rests on — so the memory is verifiable, not just searchable
   ([`docs/MEMORY.md`](docs/MEMORY.md) §1.6 **[spec]**, measured next as W9).
2. **The radar — embeddings compressed to one subdomain.** Not a general search engine. In a closed
   domain the vocabulary has exact functional meaning, so a small vector is enough to map the only
   two intents that matter: *what situation is this note for* (`when:`) and *what does it define*
   (`what:`). It returns the two or three notes of exactly the subdomain the expert is working in.
3. **The language — three verbs.** `<search>a situation or a doubt</search>` returns titles and ids.
   `<open>id</open>` returns the note and its links. `<calc>expression</calc>` — so the model never
   does arithmetic in its head, where it always fails.
4. **The LoRA — trained on the habit of navigating.** Its training cases draw their constants fresh
   every time — a liquid invented for one exercise, a local dwell time of 15 seconds instead of 5 —
   so the answer cannot be memorised and the model is *forced to open the note to see the number*.
   What ends up in the weights is a choreography: read, search the harness, open the protocol, make
   a stop in the wiki when a step needs a fact, send the numbers to `<calc>`, follow `next`.
5. **The runtime — the software referee.** It turns the pages, writing each result right after the
   tag. It applies local rules automatically: a ward that cleanses for 20 seconds has that value
   substituted *before* the note reaches the expert, which reads the rule already resolved. And it
   watches for cheating: if step 4 `requires` step 1 and the expert never opened step 1, the runtime
   cuts the execution — without needing to know whether the final answer was right.

![Seven numbered panels joined by one line, like a subway map: a request, a search that lights three cards, a procedure opening, the line running along the harness shelf, a detour down to the wiki shelf and back, a calculator, the answer.](docs/img/memory-walkthrough.png)

*One task, end to end. The detour from the harness to the wiki and back is the point.*

**The gain.** If the protocol changes tomorrow you edit one markdown file in git. The LoRA is not
retrained, because what it learned was to obey the links and read the notes.

---

## The request path

![Five stations on one line: client, proxy, router, expert with its library, answer. From the router a dashed branch runs along the bottom to the frontier and rejoins at the answer. Under the expert, three keys: search, open, calc.](docs/img/request-path.png)

*The path of a request. Abstaining to the frontier is a lane, not an error.*

```mermaid
flowchart LR
    C["client<br>OpenAI API · OpenClaw"] --> P["proxy<br>prune · member prompt"]
    P --> R["router<br>a small model of the experts' corpora"]
    R -- "falls in a corpus" --> E["expert LoRA<br>trained to navigate"]
    E <--> M["runtime + library<br>search · open · calc"]
    R -- "falls in none · or region measured to fail" --> F["frontier model"]
    E --> A["answer"]
    F --> A
    classDef local fill:#e8f1e4,stroke:#4a7a3a,color:#1d3314
    classDef art fill:#eef0f6,stroke:#4a5a8a,color:#1d2240
    classDef out fill:#f4e6d4,stroke:#9a6a2a,color:#3d2a0e
    class P,R,E local
    class M art
    class F out
```

## Where it sits in an organisation

An organisation that runs on agents tends to draw the same picture: people in a few roles on top; an
agent runtime with **one agent per role**; the applications those agents operate; the channels people
already use; and, at the bottom, one database with identity, payments and monitoring beside it. In
that picture every agent is a system prompt over the same remote model.

lora-kernel is the layer under the agent column. **Each role becomes an expert** — an adapter trained
on how *this* organisation does that job — **with two drawers of notes**: how we do it here, and what
we know. The role a message arrives from says *which* expert — free, and measured safe **[ran]** F2; *whether* the request is inside that expert's region is still the router's job. What an
expert is measured to handle is answered on the organisation's own machine; the rest goes to the
frontier, or to a person where policy says nothing leaves the building. The systems of record stay
where they are: **records stay in the database, habits go in the adapter, knowledge stays in notes a
person can read and correct.**

![A solution architecture in five layers: people in four roles; an agent runtime with one agent per role; order and back-office applications; app and messaging channels; one database with identity, payments and monitoring. Under the agents, one graphics card drawn as a bookshelf: one thick spine, the resident model, and a thin spine per role, each with two drawers of notes. A signpost routes by role; dashed lines leave for the frontier and for a person.](docs/img/solution-architecture.png)

*Where it sits in an organisation: records stay in the database, habits go in the adapter, knowledge stays in notes a person can read.*

The same shape, in other rooms — none of these is measured, they are where the design points:

| organisation | roles that become experts | what goes in the two drawers |
|---|---|---|
| **a distributor** | customer service, receiving, dispatch, purchasing, claims | the site's handling procedures · catalogue, carriers, service levels |
| **an accounting or law office** | intake, document review, deadlines, billing | the firm's checklists and templates · the rules of its jurisdiction, client by client |
| **a school or training centre** | enrolment, teaching support, communications, purchasing | how this school handles each case · programme, calendar, regulations |
| **a repair or field-service company** | equipment intake, diagnosis, spare parts, warranties | the procedure for each kind of repair · manuals, parts lists, warranty terms |
| **a club or community centre** | memberships, activity sign-ups, facilities, collections | how this club handles each case · activities, fees, house rules |
| **a property manager** | tenant requests, maintenance, collections, suppliers | the escalation procedure per building · contracts, by-laws, supplier terms |

What they share is what makes a region worth an expert: **the same few procedures, repeated daily,
with local rules that differ from the textbook, over data that should not leave.** The first library
in this repository is built from an open textbook's step-by-step procedures
([`knowledge/nursing-iv/`](knowledge/nursing-iv/)). What is *not* established is in the section
below, and it applies here in full: no real data yet, and the claim that a library extends an expert
to a procedure it never trained on is untested.

## Where it stands

**Already running.** One vLLM instance serving several LoRA adapters off one resident base, each
request routed to its own adapter, live through the OpenAI-compatible API and through OpenClaw
**[ran]** — the mechanism above is not a diagram, it answers real turns today. One trained expert,
served exactly the way its corpus taught it, reaches human-level accuracy on the job it was trained
for (inbox triage, 0.989 against a bare base's 0.345) **[ran]**.

**The open question the whole design turns on.** Does a library actually let an expert handle a
procedure it never trained on, the way a person would look one up? Navigation transfers — the
trained habit of searching, opening and following links works on notes the adapter has never seen —
but *reading* a note whose shape the corpus never showed does not yet transfer reliably (35 of 56,
against an untrained base handed the right note scoring 45 of 56). That is the one result in this
README most likely to still be true next week, because the rest of the plan is built to answer it
next **[ran]** `docs/PLAN.md` milestone 7.

**Next: atomic statements.** The library is being rebuilt as pages of verifiable one-sentence
statements — *what are the works of the author of the Mona Lisa?* is a search, a section, a link and a
section — first on an invented distributor wiki the model cannot know by heart, with the untrained
base measured before any LoRA is trained for it **[spec]** `docs/MEMORY.md` §1.6, W9.

**Not solved yet.** The router is still a keyword dictionary — its two learned replacements are both
measured and neither passes, for the same reason: a request from an unfamiliar sender and a familiar
listing followed by an unfamiliar task look alike to both **[ran]** `docs/PLAN.md` milestone 2. No
real traffic has been measured anywhere in this repository yet.

**Everything else — every milestone, every arm, every run — moves as the project does and is not
repeated here, on purpose.** [`docs/PLAN.md`](docs/PLAN.md) is the living state, with a gate and
falsification condition written before each milestone runs. [`docs/RECORD.md`](docs/RECORD.md) is
the full ledger, including what failed and the instruments that lied. [`docs/FRAMEWORK.md`](docs/FRAMEWORK.md)
is the gap analysis against being a generic framework, self-contained and written to be reviewed by
another model.

**Engineering constraints, decided and not up for debate.** The family is Qwen 3.x — small
`Qwen3.5-4B`, large `Qwen3.8-27B` — trained and served on Colab, in sessions under an hour, never on
a user's machine. A 27B is A100 work in 4-bit. Gemma 4 is the named alternative and is blocked at
PEFT for now.

---

## Run it

```bash
# the gates that need no GPU
python -m pytest tests -q
python scripts/check-mirrors.py

# the routing replay — by request against by region, zero GPU
python -m training.harness.route

# anything that runs a model runs on Colab through one chain — streamed, resumable, under an hour
GPU=L4 BRANCH=main MODULE=training.harness.verify_substrate \
  RUN_DIR=results/my-run training/harness/chain_serve.sh
```

Serving the pool to an agent, the proxy's flags and the substrate gate:
[`docs/SERVING.md`](docs/SERVING.md). OpenClaw, step by step, as it ran live:
[`docs/OPENCLAW.md`](docs/OPENCLAW.md). A member is served with three flags, each a default for a
reason: `--prune` (its own tool surface), `--member-prompt` (the prompt its corpus taught), `--auto`
(the client names no model).

## What is in the box

| path | what |
|---|---|
| `training/harness/openai_proxy.py`, `route.py` | the API: pruning, the member prompt, routing per request |
| `training/harness/train_pool.py`, `contract.py` | the pool registry — each member a record read off its corpus |
| `roles/`, `rolepack/` | **one declared directory per role** — member, corpus, prompt and tool block by reference and hash, route, answer policy, egress, loop, library — and the linter that checks every line against its artefact (`python -m rolepack.lint roles/`) |
| `training/harness/release_gate.py`, `pool_second.py`, `pool_base.py`, `verify_substrate.py` | the door a member enters through, on this base or another |
| `training/harness/accept_rank.py` | the corpus-mode loop — stop at the closing tag, write the result inline, continue — that the memory's runtime is built on; and acceptance by teacher forcing |
| `training/harness/corpus_mode_arm.py`, `training/physics/result_use.py` | an expert re-served as its corpus taught; a failure read where it happens — *was the result used?* |
| `training/harness/corpus_router.py`, `embed_router.py`, `router_sets.py` | the router's learned arms, and the eight sets any router is scored on |
| `training/nursing/` | the first text here nobody generated: three IV-therapy checklists, 72 checkable questions |
| `training/harness/lora_matrix.py`, `rekey.py`, `awq_lora_gate.py` | does this base — small or large — serve a LoRA at all |
| `training/harness/chain_serve.sh` | the Colab chain: provision, run detached, stream, fetch weights as they appear, resume |
| `training/harness/bill.py` | prices an existing replay at real frontier rates — zero GPU, nothing re-run (`results/M6-bill-20260921/`) |
| `examples/` | **the reference organisation, code-only, before any adapter** — `school/` and `distributor/`, both two tenants; a toy store, a tool layer that enforces permission outside the model, an MCP server per domain, an adversarial suite at 0 leaks; `examples/README.md` says how to point your own OpenClaw at it |
| `releases/`, `results/` | the manifests, and the runs the documents cite |

## Documents

| | |
|---|---|
| [`docs/MEMORY.md`](docs/MEMORY.md) | **the memory, as it will be built** — library, radar, three verbs, the LoRA's habit, the referee; build order for 1.0 |
| [`docs/KNOWLEDGE-TRAJECTORIES.md`](docs/KNOWLEDGE-TRAJECTORIES.md) | the *why* behind it, self-contained, written to be reviewed by other models: ten findings, five strategies, ten questions |
| [`docs/FRAMEWORK.md`](docs/FRAMEWORK.md) | **state and gaps, self-contained, written to be reviewed by other models** — what works, what does not, and what is missing for this to be a generic framework for an organisation with one agent per role |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | the system: experts, router, memory, runtime, the pair, the frontier — and where it sits in an organisation (§9) |
| [`docs/PLAN.md`](docs/PLAN.md) | the living plan — milestones, gates, kill arms |
| [`docs/RECORD.md`](docs/RECORD.md) | everything measured, including what failed; each line names its run |
| [`docs/FOUNDATIONS.md`](docs/FOUNDATIONS.md) | the mathematics, tied to the runs that instantiate it |
| [`docs/SERVING.md`](docs/SERVING.md) · [`docs/OPENCLAW.md`](docs/OPENCLAW.md) · [`docs/SUBSTRATE-GATE.md`](docs/SUBSTRATE-GATE.md) | running it |
| [`docs/articles/`](docs/articles/2026-09-it-was-the-harness.md) | *An organisation that runs on agents, on a single GPU: the architecture* — the solution architecture first, then what is already measured (the harness finding among it), what is not, the roadmap |
| [`CLAUDE.md`](CLAUDE.md) | instructions for coding agents, and the measurement rules that were paid for |

**The record before the rewrite of 2026-09-19** — seventy-four run directories, the retired experts,
the analyses, a 2,800-line plan — is the tag
[`v0.1-foundations`](https://github.com/EvolvingAgentsLabs/lora-kernel/tree/v0.1-foundations).
A P-number cited here without a directory on `main` lives there.

## Scope

Open source: the runtime, the memory's runtime and formats, the release contract, the gates. **Not
part of this runtime nor of the open-source version:** the customisation service and its tooling — a
customer's corpora and libraries, adapters trained as a service, the automation of traces → corpus →
gate → release. This repository builds the instrument that measures a customisation, not the tooling
that produces it at scale. Material from third parties keeps its licence: *Nursing Skills* is CC BY
4.0 and is attributed where it is used; WHO publications default to CC BY-NC-SA and are not shipped.

Apache 2.0. The idea began in a conversation with Ismael Faro.
