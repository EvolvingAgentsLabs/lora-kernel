# lora-kernel

![A specialist at a desk in a small reading room. Behind them a wall of card-catalogue drawers in two halves — PROCEDURES, its drawers joined by a route line, and ENCYCLOPEDIA, branching like a tree. A small radar dish on the desk lights exactly three drawers. Through a doorway, far off, a large building marked 'frontier'.](docs/img/hero.png)

*The specialist, the library, the radar — and, through the door, the frontier, for when no drawer fits.*

**The LoRA is not the textbook. It is the specialist who knows how to use the library.**

[![license Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![family Qwen 3.x](https://img.shields.io/badge/family-Qwen%203.x-8A5C10)](docs/ARCHITECTURE.md)
[![core 1.0 specified](https://img.shields.io/badge/core%201.0-specified-555)](docs/MEMORY.md)
[![record v0.1-foundations](https://img.shields.io/badge/record-v0.1--foundations-555)](docs/RECORD.md)

*[Español](README.es.md)*

lora-kernel is the runtime of a service: an **OpenAI-compatible API** that answers locally what
falls inside a measured region and forwards the rest to a frontier model, with **OpenClaw instances
per task** on top. A region is a small QLoRA expert over one resident small model. What an expert
knows how to *do* is in its weights; what it needs to *know* is in a library of markdown notes it
has been trained to navigate — so when a protocol changes you edit a file in git, and nothing is
retrained.

Every claim below is marked **[ran]** (observed in this repository, run named), **[read]** (from
source or a paper) or **[spec]** (decided, not yet built). **Everything measured so far is on
generated suites; no real traffic has passed through it.** That is the first thing to know about
the numbers, and the core of 1.0 is *specified*, not shipped.

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
   classifies which case you are in before you compute.
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

## What is measured

On `Qwen2.5-3B-Instruct`, the base the pool was built on — and, since milestone 1, on `Qwen3.5-4B`, where both released members hold their numbers.

| what | the number | run |
|---|---|---|
| **One vLLM, one base, several adapters**, each request served by its own | identity `applied` on every member, tools reachable, stop honoured | **[ran]** P56 |
| **`email-full@v1`** — inbox triage, tools and judgement in one adapter | **0.989** on human messages against the base's **0.345**; re-served and re-trained, both tie the recorded run | **[ran]** P36, P57 |
| **`desk-commitment@v1`** — a second member on the *same inbox*, a different question | **240/240** against the base's **38/240**, discordant **202 : 0** | **[ran]** P64 |
| **The pool on the Qwen 3.x family** — both members retrained on `Qwen3.5-4B`, same corpora, same recipe (`@v2`) | `email-full` **471/475**, exactly its Qwen 2.5 release (tie, 1 : 1); `desk-commitment` **240/240** (tie); identity `applied` on both full-recipe adapters | **[ran]** M1 |
| **An expert that reasons, served the way its corpus taught** — fluid mechanics, 6-to-9-step chains with a calculator and a per-case handbook | **90/90**, where the same adapter on the same cases scored **11/90** through `tool_calls` messages (79 : 0, paired) — and **24 : 0** against the frontier's 66/90. No evaluated case is in its corpus | **[ran]** M7 arm 0b |
| **On a 3B, a procedure merely pasted into the prompt is not followed** | base + a 914-token procedure: **0 tool calls on 351/351**, under the majority bar; the trained expert beats it **137 : 1** | **[ran]** P61 |
| **The API routes per request**; the client names no model | replay on 240 cases: 0.546 → 0.775, 0 misrouted | **[ran]** P41, P62 |
| **OpenClaw, live, from a laptop** | 40/40 turns local, 0 invented calls, 19/32 human turns call a tool | **[ran]** P63 |
| **A member must be served its own tool surface** | offered OpenClaw's 54 tools it copies tags off the block: 225 of 227 calls refused; pruned, 8 of 1160 | **[ran]** P59 |
| **vLLM applies a LoRA over a quantised large model** | logprob gate 3/3, mean \|Δℓ\| 0.22–0.49 nats against a base-vs-base 0.000 | **[ran]** P60 §3b |
| **Qwen 3.5 adapters are servable** — "vLLM ignores them" was a naming mismatch | same weights, 496 tensors renamed, not retrained: `not applied` → **`applied`** | **[ran]** D2 |

**The one lesson under half of that table: serve an expert the way its corpus taught it.** Under a
foreign system prompt 2 of 32 live turns call a tool, under its own 19 of 32 (P63). Through
`tool_calls` messages an inbox expert scores 0.808, with results written inline 0.992 (P55). And the
line this repository quoted most — *"the expert that decides works, the expert that reasons fails"* —
was read off a harness that never showed the expert its results the way it had been taught to read
them: 11 of 90 became 90 of 90 (M7 arm 0b). The memory is built on exactly that channel.

## What is not measured, or does not work

- **No real data.** Every suite so far is generated here, and a generated suite cannot contain a
  difficulty its author did not think of **[ran]** P50. The first real region is named — **nursing
  procedures** (Open RN *Nursing Skills*, CC BY 4.0) — and only its headroom is measured: an untrained
  4B goes from 29/48 closed-book to 45/48 with the right note open, and from 0/12 to 12/12 on a value
  a unit's protocol changed **[ran]** M5. Nothing is trained on it yet, and retrieval is untested.
- **The memory's central claim was measured once and did not pass.** That a library extends an expert
  to a *procedure it never trained on*: on 56 held-out walks the library arm scores 35, the same expert
  without the library 2, the untrained base navigating by itself 0 — and the untrained base *handed the
  right notes* 45 (6 : 16 paired, $p=0.052$) **[ran]** M7-W5. Navigation transferred; reading a note
  that states two values, a shape the corpus never showed, did not (0 of 11) — and a second corpus that
  *did* show that shape, over eight notes, did not teach it either: 4 of 15 on an unseen note, 17 of 18
  on the trained ones, the pair still a tie at 12 : 16 **[ran]** M7-W5c. The library, the referee
  and the corpus are built (W1–W4); the radar reaches recall@3 0.64 against a bar of 0.80 (W3). Without one, a specialist just outside its region is
  confidently wrong — 30/30 inside, 1/20 on sibling families **[ran]** P14.
- **The router is still a keyword dictionary.** Its first learned replacement, an n-gram model of
  each corpus, is safer on foreign text (0 of 128 served locally against the dictionary's 59) and
  loses **every** legitimate request from a sender the generator never drew, 120 of 120 **[ran]** M2.
  An embedding model does the same, and not for want of a better threshold: a request from an unseen
  sender and *a member's own listing followed by another task* sit at the same distance from the
  corpus **[ran]** M2 arm 2. What is left is a representation that separates the task from its content
  — the radar's learned projection, reached from the router's side.
- **On the new base an adapter has less to add.** The bare `Qwen3.5-4B` scores 0.632 on human email
  where the 3B scored 0.345 **[ran]** M1. The members still tie their old releases; how much headroom
  a 4B leaves is a question every new region now has to ask first.
- **Outside its training depth the reasoning expert is unmeasured again.** The result that it
  over-solves shorter problems (P45) came through the `tool_calls` path, and is open.
- **The saving in money has never been measured**, and no signal yet sees an answer that is coherent
  and wrong.

The full ledger, including everything that failed and the instruments that lied, is
[`docs/RECORD.md`](docs/RECORD.md).

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
above, and it applies here in full: no real data yet, and the claim that a library extends an expert
to a procedure it never trained on is untested.

## From a runtime to a framework

What this repository is today is a **measured runtime**: a pool of experts behind one API, a library
with its referee, and the gates that decide what is released. What the drawing above needs is a
**framework** — something a third party fills in without reading our code. The distance between the
two is written down in [`docs/FRAMEWORK.md`](docs/FRAMEWORK.md); in short:

| | |
|---|---|
| **works [ran]** | several adapters on one resident model · two released experts through a paired gate · the API that prunes, prompts and routes · OpenClaw live · the library format, the lint, the referee · **navigation that transfers to a procedure never trained on** |
| **does not yet** | the memory's central claim (three runs, not passed: the adapter navigates, the *untrained* base reads better) · note search (0.64 against 0.80) · a learned router · moving a reasoning expert across bases |
| **exists since, zero GPU [ran]** | **the role as the route** (`auto:<role>`; says *which* member, never *whether*) · the **role pack** — `roles/<role>/role.toml`, every line checked against its artefact; three members expressed; not yet the source the code reads · **the tool layer's code-only half** — `examples/school/`, seven roles (the reference diagram's full roster), thirteen tools, an adversarial suite at **0 leaks** across two tenants, both MCP servers `mcp probe`-verified against a real OpenClaw instance; `examples/distributor/` the same shape, unexpanded · **a first price on the P41/P62 replay** (`training/harness/bill.py`) — today's real `gemini-3.8-flash` bill for the 37.5 % sent out, $0.18; the GPU's own dollar cost still unpriced, named rather than guessed |
| **does not exist** | the tool layer's model-side half — whether a *model* ever tries the cross-tenant call — an OpenClaw turn needs an account behind it, prepared not run · per-user isolation · concurrency, latency measurements · an installer · any language but English · any measured *write to a real system of record* (the toy store's writes are real; a customer's are not) |
| **next, cheapest first** | **W5d** — who reads (one session, no training; pre-registered) — first, because the memory needs its answer · then a live OpenClaw turn against `examples/` (bring-your-own account, `examples/README.md`) — the model-side half of the 0-leaks falsifier · then a second role pack skeleton, or the corpus generator that turns `examples/school/`'s tools into training data for a first LoRA on this domain |

A five-phase architecture (two domains, Auth0, Postgres row-level security, Docker Compose, speculative
decoding) arrived pasted into a session on 2026-09-20 and was read in full against this table — most of
it was already built, already sequenced later, or blocked by a vLLM RFC; the one gap it named correctly
and this repository had not closed (permission outside the model) is the step above. The reading, phase
by phase, is [`docs/FRAMEWORK.md`](docs/FRAMEWORK.md) §9; the re-ordering is
[`docs/PLAN.md`](docs/PLAN.md) §0.

## Where it goes

Each milestone has a gate and the arm that can kill it, written before it runs
([`docs/PLAN.md`](docs/PLAN.md)). Arms are bought in sequence, never as a grid.

| # | milestone | state · the arm that kills it first |
|---|---|---|
| **1** | the pool on Qwen 3.x small (`Qwen3.5-4B`) | ✅ **[ran] — moved.** Both members tie their Qwen 2.5 releases; `@v2` manifests |
| **2** | the router as a small model of the corpora | arms 1 and 2 **[ran]**, neither passes: both lose every request from an unseen sender · next, a projection that factors task from content, on new sets |
| **7** | **the memory** — the core of 1.0 | arm 0 and 0b **[ran]**: the channel works · under an **oracle** walk — exactly the right notes open — the expert still scores ~1/20 on a sibling procedure it never trained on · **W1–W4 built; W5 [ran], not passed:** 35/56 against the untrained base that reads at 45/56 — navigation transferred, a two-valued note was not read (attributed **[ran]** W5b: with the base writing the line, 0 of those 12 remain — a shape the corpus never showed) · **W5c [ran], falsified:** shown the shape over eight notes, the adapter learns the notes, not the reading — 4/15 |
| **5** | the first real region: nursing procedures | headroom **[ran]**: 29/48 closed-book → 45/48 with the note open, 0/12 → 12/12 on a site's value · next: the same content as *walks*, against the untrained base reading the same notes |
| **3–4** | the large half of a pair, and acceptance between the halves | not started · large + LoRA does not beat small + LoRA; then: acceptance no higher than under the bare large model |
| **6** | the service policy, with the bill | first pass **[ran]** on the P41/P62 replay: today's frontier bill $0.18, avoided by the local share $0.11 · fraction-of-a-dollar at this scale — the GPU's own cost, still unpriced, is what decides it |

**Engineering constraints these carry — facts, not objections.** Everything that runs a model runs
on Colab, in sessions of under an hour; nothing runs on the user's machine. A LoRA-adapted drafter is
a vLLM RFC, not a feature **[read]**, so acceptance is measured by teacher forcing and claims no
speed-up. A 27B is A100 work in 4-bit. The `<think>` channel of the 3.x line is off for members.
Gemma 4 (2B / 12B) is the named alternative family and is blocked at PEFT **[ran]** P29.

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
| `training/harness/corpus_router.py`, `embed_router.py`, `router_sets.py` | the router's two learned arms, and the eight sets any router is scored on |
| `training/nursing/` | the first text here nobody generated: three IV-therapy checklists, 72 checkable questions |
| `training/harness/lora_matrix.py`, `rekey.py`, `awq_lora_gate.py` | does this base — small or large — serve a LoRA at all |
| `training/harness/chain_serve.sh` | the Colab chain: provision, run detached, stream, fetch weights as they appear, resume |
| `training/harness/bill.py` | prices an existing replay at real frontier rates — zero GPU, nothing re-run (`results/M6-bill-20260921/`) |
| `examples/` | **the reference organisation, code-only, before any adapter** — `school/` (7 roles, 13 tools, two tenants) and `distributor/` (2 roles); a toy store, a tool layer that enforces permission outside the model, an MCP server per domain, an adversarial suite at 0 leaks; `examples/README.md` says how to point your own OpenClaw at it |
| `releases/`, `results/` | the manifests, and the runs the documents cite |

## Documents

| | |
|---|---|
| [`docs/MEMORY.md`](docs/MEMORY.md) | **the memory, as it will be built** — library, radar, three verbs, the LoRA's habit, the referee; build order for 1.0 |
| [`docs/KNOWLEDGE-TRAJECTORIES.md`](docs/KNOWLEDGE-TRAJECTORIES.md) | the *why* behind it, self-contained, written to be reviewed by other models: ten findings, five strategies, ten questions |
| [`docs/FRAMEWORK.md`](docs/FRAMEWORK.md) | **state and gaps, self-contained, written to be reviewed by other models** — what works, what does not, and what is missing for this to be a generic framework for an organisation with one agent per role: thirteen gaps, eight interfaces, seven steps |
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
