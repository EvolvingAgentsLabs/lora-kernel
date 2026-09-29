# Architecture

The system as designed on 2026-09-19, state as of 2026-09-20. What is built and measured is marked
**[ran]**; what is designed and not built says so. Where it sits in a whole organisation, and what is
missing for it to be a generic framework, is §9 and [`FRAMEWORK.md`](FRAMEWORK.md). The measurements behind every choice are in
[`RECORD.md`](RECORD.md); the order of work is [`PLAN.md`](PLAN.md). How every mechanism named below
connects, turn by turn, is [`MECHANISMS.md`](MECHANISMS.md).

## 1. One fact, four components — and what version 1.0 is

**An expert is the distribution of its corpus.** Not the weights alone: the tool block, the
argument keys and their order, the system prompt, the depth of the problems it saw. Served
outside that distribution it is a different, worse model — 2 of 32 live turns call a tool
under a foreign prompt, 19 of 32 under its own **[ran]** P63; an expert that reasons through
6-to-9-step chains scores 11 of 90 when its tools' results reach it as `tool_calls` messages and
**90 of 90** when they are written inline, as its corpus taught **[ran]** M7 arm 0b.

**Version 1.0 is five things [spec]:** experts defined by their corpora, the router with its
abstention, the memory (§4), the runtime that referees it, and the release contract that hashes all
of it. The pair of §3 attaches per subdomain where it is measured to pay and is not required by 1.0.

Everything else is that fact applied four times:

| component | what it is | state |
|---|---|---|
| **the expert** | a QLoRA on the small model, trained by SFT on one corpus, released with a contract that records the distribution | **[ran]** two released; since M1 on `Qwen3.5-4B`, each tying its Qwen 2.5 release |
| **the router** | a very small model *of the same corpora*: which expert's distribution does this request fall in — or none | a keyword dictionary **[ran]**; two learned arms **[ran]** M2, neither passes; in a deployment with one agent per role, *the role is the route* (§9) |
| **the pair** | a second LoRA, on the large model, trained on the *same corpus*; the small one drafts, the large one verifies | designed; milestones 3–4 |
| **the memory** | the subdomain's library — an operational harness and an encyclopedic wiki — a radar over it, three verbs, and a referee; the LoRA learns the **habit of navigating**, not the content | library, referee, corpus built **[ran]** W1, W2, W4; search under its bar **[ran]** W3; **the central claim measured three times and not passed** **[ran]** W5, W5b, W5c — navigation transfers, reading a conditional value in an unseen note does not (§4) |

```mermaid
flowchart TB
    subgraph REL["a release = one corpus, recorded"]
        K["corpus<br>block · keys · order · prompt · band"]
    end
    K --> E["expert LoRA on the small model"]
    K --> T["LoRA on the large model<br>same subdomain"]
    K --> R["router<br>one class per corpus + abstain"]
    K --> B["knowledge base of the subdomain<br>notes · links · embeddings"]
    E -- "navigates · reads · follows" --> B
    R -- "this corpus" --> E
    E -- "drafts" --> T
    R -- "no corpus" --> F["frontier model"]
    classDef art fill:#eef0f6,stroke:#4a5a8a,color:#1a2240
    classDef local fill:#e8f1e4,stroke:#4a7a3a,color:#1d3314
    classDef out fill:#f4e6d4,stroke:#9a6a2a,color:#3d2a0e
    class K,B art
    class E,T,R local
    class F out
```

One artefact — the corpus named in the release manifest — defines the expert, trains its
large half, and trains the router's class for it. Adding a region adds one corpus, and the
base of knowledge that corpus's trajectories walk through.

## 2. The request path

```mermaid
sequenceDiagram
    participant C as client
    participant P as proxy
    participant R as router
    participant S as small + LoRA
    participant L as large + LoRA
    participant F as frontier
    C->>P: chat completion, no model named
    P->>R: the conversation's user text, runtime envelope cut out
    alt falls in a member's corpus, region served locally
        R-->>P: member
        P->>S: member prompt, pruned tools, corpus-mode bounds
        S->>L: draft, where the region is measured to need the pair
        L-->>P: verified answer
    else falls in none, or region measured to fail
        R-->>P: out
        P->>F: forwarded as it came
    end
    P-->>C: answer, with the route logged as shapes only
```

**The proxy** (`openai_proxy.py`) **[ran]**. It speaks the OpenAI API. For a member it
prunes the offered tools to the member's declared surface (`--prune`), replaces the
runtime's system prompt with the one the corpus taught (`--member-prompt`), and runs the
corpus-mode loop — generation stops at a closing tag, the tool's result is injected, it
continues — bounded at six round-trips and 256 tokens a step, the bounds the corpus itself
has. It refuses rather than serving wrong: a request it cannot route is a 503, not a guess.

**The router** reads the subject of the conversation and nothing else: every user turn,
with the runtime's internal-context envelope cut out — a runtime's own system prompt
out-scored the email in the user turn the first time a live agent called **[ran]** P63.
Two decisions are kept apart on purpose:

- *whose distribution is this* — the router's, learned from the corpora. Its first learned arm, an
  n-gram model of each corpus's frame, was safe on foreign text and lost every request from an
  unseen sender **[ran]** M2; the dictionary stays until the embedding arm is measured;
- *is that region served locally* — a measured table, `serve: local | out`. The table is only as
  good as the measurement behind it: fluids was marked *out* on 11 of 90, which turned out to be
  the serving path — locally, as taught, it is 90 of 90 against the frontier's 66 **[ran]** M7 arm
  0b — and it goes back through the release gate before the mark changes.

**The default is the frontier.** A model asked to choose always chooses, so abstention is
designed in and measured first (milestone 2).

**In front of an organisation's tools, the gateway [ran] 2026-09-25** (`examples/school/gateway.py`, the reference
organisation's path). What the proxy does for a member, plus the four things a role-based agent system needs and a
model must not decide:

| step | what it does | where it lives, and why not in the model |
|---|---|---|
| **who** | the bearer token is verified → user, role, tenant; a role asked for in `model: auto:<role>` must match it | `examples/common/tokens.py` (HS256 with a demo secret, standing in for the identity provider's RS256/JWKS — that verification is not built) |
| **permission** | every tool runs with that claim; another tenant's row is refused before it is read | the tool layer (`examples/school/tools.py`) — 77 adversarial cases, 0 leaks **[ran]** |
| **a person for what matters** | a payment or an all-families message is HELD; a director of the same tenant approves it, never the account that asked; it then runs with the requester's scope | `examples/common/approvals.py` |
| **what a reply may state** | every item of a reply must occur in a real tool result, or the reply is replaced by the tools' own text; instruction-shaped text found in a record is removed from what is shown | `examples/common/grounding.py` — the school-staff LoRA invented a line of a tool's list on the demo day; the filter replaced 2 of 5 local replies and the user saw neither **[ran]** `results/DEMO-school-gemma-20260925` |
| **scope** | a request the role's tools do not cover follows the role's egress: the frontier, or a person's queue | the model says `OUT OF SCOPE`; the policy decides where it goes — the model's judgment is recorded, not trusted |
| **log** | one JSON line per request — who, role, route, calls, denials, holds, grounding, tokens — and a dashboard that prices the local tokens at the frontier's rates | the monitoring feed; the GPU's own cost is not priced |

**One process per organisation, not one gateway for all of them [ran] 2026-09-28** (`--org school|distributor`).
Each organisation's tools, corpus and approval state live in its own process, so a school's HELD approvals and a
distributor's egress policy never share memory by accident. The two organisations differ on purpose, not by omission:
the distributor's member is served its **own corpus prompt**, with no SCOPE line — its scope decision is trained into
the corpus itself (below), not stated in the system prompt — and its writes run without a director's approval, a
policy choice for that organisation's roles, not a gap in the approvals mechanism above.

**The gateway carries a session's state, not its transcript — H1 has a result, read two ways [ran].** The naive fix
for multi-turn is `Gateway(history=True)`: replay the conversation so a reference to an earlier turn ("move it to
dock 5") has a referent. **[ran] MT0** (`results/MT0-multiturn-baseline-20260929`, 60 held-out distributor sessions,
124 turns, 54 dependent on an earlier turn) measures it: without the conversation, 4 of 54 dependent turns resolve —
first turns, independent of history, score 60 of 60 in both arms, so the gap is specific to what depends on an
earlier turn, not a general regression. With the conversation, 43 of 54 (79.6%), at the edge of the headroom this fix
has to give: it resolves a reference copied straight into an argument (receiving 10/10, returns 10/10, purchasing
9/10, dispatch 12/14) but not one written into free text — a claim about "that order" is filed without the order
number 8 of 10 (customer service 2/10) — and tokens keep growing with the session (+24% by turn 2). The alternative,
`Gateway(memory=, workflows=, tool_block=)`, replaces the transcript with one line — `state: <workflow>/<state> ·
keys: <names>` — backed by the operational memory (§4), and is now measured rather than only designed.

**[ran] H1** (`results/H1-workflow-harness-20260929`, pre-registered, 60 of MT0's sessions): the harness arm
(`wf-s0` + the operational memory) holds 53 of 54 dependent turns — 1 lost against `history`, 11 gained — naming the
order fetched by key in every customer-service claim (10/10 against `history`'s 2/10), dispatch 14/14, and tracing
every one of the 53 right turns to a `<get>` by key (53/53); the prompt itself stays flat per turn (745, 726, 710
tokens) where `history`'s keeps growing (345, 428, 394). The same corpus served without the tool block
(`harness-noblock`) scores 0 of 60: the member calls no tool and states data it never read, because its corpus was
never trained without the block. The pre-registered gate required every arm — including that no-block control — to
clear 90% on first turns; the control's own failure trips the gate and voids the run as written, an instrument
design error recorded here rather than patched after seeing the result. Read per arm instead, the harness **PASSED**
and harness-noblock **FALSIFIED**; **the user's decision (2026-09-29): the per-arm reading stands, the as-written
VOID kept as the record of that instrument error.** The saving the harness is
built for — a flat prompt instead of a growing transcript — barely shows over 2–3 turns (the harness pays roughly 2×
the tokens per turn there, one extra get → call → put round-trip); over five turns on a Jira-and-Confluence-like
tracker domain (`examples/tracker/`, **[ran] H2**, `results/H2-tracker-harness-20260929`), it holds — 146 of 160
dependent turns (91.3%), flat prompt across all five ($\bar p_5 \le 1.1\ \bar p_1$) — but the run reads FALSIFIED
as written rather than VOID: the untrained `base-history` baseline's own low first-turn score, 44 of 60, trips the
same per-arm rule that fixed H1, which makes the pre-registered "beats `base-history`" claim unreadable rather than
false. Descriptively, paired on the same 160 turns, 142 : 0 favour the harness. Reading pending the user, as it was
for H1: `docs/review/harness-workflow-kv.md` §9.

**How the mechanisms connect on one turn, now that the harness has a result.** The gateway reads the request's
context line — `state: <workflow>/<state> · keys: <names>` — instead of the transcript; the role names the member
(§1) to serve it; the member's trained choreography reaches for `<get>key</get>` or `<put>key=value</put>` against
the operational memory exactly where a step needs a value, through the same tool layer that runs a domain tool under
the caller's signed claim (§2's table); every call the tool layer actually *ran* — not one the model merely
proposed — advances the workflow's declared state machine, which the model only ever reads back next turn; and the
reply is checked against real tool results by the grounding layer before it reaches the client, the same gate that
replaced 2 of 5 invented lines in the school demo, now also guarding a line whose only source may be a value just
fetched by key.

**Abstention lives in the corpus, per member, not in a second model in front of it. [ran] M10:** the distributor's
member is trained on `train_out` — its usual 700 turns byte for byte, plus 70 `OUT OF SCOPE` turns drawn from the
role's own egress policy. Against the member without them, nothing already learned regresses (0 of 70 held-out) and
every held-out out-of-scope request abstains (20/20, against 0/20 for the plain member); the scripted demo goes 6/6
against 5/6. This is the same `scope` row above, trained rather than prompted: the model still only *proposes*
`OUT OF SCOPE`, and the policy — not the model — decides where the request goes.

**The edge deployment, run against a real client, not a replay. [ran] LIVE-distributor, M10:** the distributor's
member served through llama.cpp on the user's own machine (`google/gemma-4-E4B-it` Q8_0 + the member's LoRA converted
to GGUF, `python -m examples.school.gateway --org distributor --upstream <llama-server>`) went 5 of 5 turns through
the real OpenClaw 2026.9.4; the abstaining member then went 6 of 6, the one out-of-scope turn (a thank-you note to
suppliers) forwarded to **Claude Haiku 4.5** through the gateway's frontier exit (10,198 + 195 tokens, $0.0112). What a
real client caught that a replay would not: llama.cpp drops the stop string the corpus-mode loop relies on to end a
turn, and the distributor's own store was not thread-safe under OpenClaw's concurrent calls (first attempt void; both
fixed). Neither member is a formal release from this run (no release file) — it demonstrates the path, not a gate pass.

## 3. The pair

**Why the large half is trained, not borrowed.** An untrained large model is not a better
expert in a narrow region: 0.967 against the small expert's 1.000 on the desk, 0.746
against 0.989 on triage **[ran]** P55, P55b. Verification by a model that disagrees with a
*correct* draft rejects good tokens. Training the large model on the same corpus is what
makes it a verifier of this subdomain rather than a generalist second opinion.

**What is already known about the halves.** vLLM applies a LoRA over a 4-bit large model
**[ran]** P60 §3b. Qwen 3.5 adapters are servable once their tensors are named for the class
vLLM serves **[ran]** D2. The small and large models of the family share one id space, so a
drafted token *can* be verified **[ran]** D0 — between families, or against a frontier API,
it cannot **[ran]** P48.

**What is not available.** vLLM's speculative decoding does not take a LoRA-adapted drafter;
that is an RFC **[read]**. Until it ships, acceptance is measured by teacher forcing — the
large model scores the small one's finished draft in one prefill (`accept_rank.py`,
[`FOUNDATIONS.md`](FOUNDATIONS.md) §5.3, §6) — which gives α exactly and the speed-up not at
all. The pair is first a **quality** device (does large + LoRA beat small + LoRA where the
small one has headroom) and then a **speculative** one (does the matched LoRA raise α).

**Where it runs.** The small pool is served from one L4. The large half, `gemma-4-12B-it`, is served in bf16 from one A100 (B3, B4) and is sized for a Mac mini; ~~a 27B is A100 work in 4-bit~~.

**One L4 serves several members at once without contention. [ran] C1** (`results/C1-concurrency-20260929`, vLLM
0.30, four members mixed — `school-s0`, `upper-s0`, `staff-s0`, `out-s0`): 16 sessions split across the four adapters
reach 278.6 tok/s against 269.7 tok/s for the same 16 sessions on one adapter alone (1.03×); 32 sessions across the
four reach 504 tok/s, p95 time-to-first-token 0.24 s, 0 errors of 128 requests; throughput scales near-linearly from
one session to 32 (22.7 → 135 → 270 → 500 tok/s), with the ceiling still above 32. This supersedes E5's single-burst
reading of 0.88 — that number held at the edge of one burst of 16, not at the scale several concurrent sessions
actually produce.

**Two runtime profiles name this split explicitly, the user's decision 2026-09-28.** **`server`** is vLLM on Colab —
every training run and every measurement, the pair included. **`edge`** is **llama.cpp on the user's own machine**,
serving *one member* (not the pair) to a live agent runtime: the E4B as **Q8_0** GGUF — Q4_0 flips an order id with
llama.cpp's own prompt cache **[ran]** LIVE-distributor — plus the member's LoRA converted to GGUF, hot-swapped in
**~3 ms** by `POST /lora-adapters` **[ran] MAC2**. MLX, the Mac's earlier engine, is now a research bench: its
hot-swap (2.9 µs, **[ran] MAC**) needed Python access to the graph that `edge` does not. ~~MLX stays the `edge`
engine~~ — that was MAC2's verdict about speculative decoding specifically, and it does not extend to serving.

**A LoRA confined to the upper layers: a lever for shared KV across experts, not a fix for the drafter.** Two
measurements read the same lever two different ways. **[ran] E6:** training a LoRA on only the upper half of the
decoder (layers 21–41 of 42) costs nothing measured against the full-depth member — 70/70 held-out, 15/15 demo — and
the KV of the layers below comes back **bit-identical to the base model's own** (a base-vs-base control matched it).
That is the precondition a server would need to compute the shared lower KV once, from the base, and let every
expert's requests read it — still not built (§8); the caveat is that the E4B already caches 24 of its 42 layers on its
own, a boundary this LoRA's layer choice does not line up with, so a switch still recomputes layers 21–23. **[ran]
C0-upper:** the same restriction does **not** help the drafter — on the E4B with its own MTP, α on the domain moved
base 0.82 → full-depth LoRA 0.44 → upper-half LoRA 0.43 (ρ = −0.02, read as none). The reason the two diverge
**[read]**: MTP already reads from near the top of the stack, which an "upper-half" adapter still touches — confining
the LoRA there removes almost nothing of what the drafter sees. In vLLM the upper-half adapter also serves at exactly
the full adapter's speed: it saves memory, not time.

## 4. The memory — the core of 1.0

> **The LoRA is not the textbook. It is the specialist who knows how to use the library.**

**State, 2026-09-25 [ran].** **The memory works on its first test bed.** On a wiki of atomic statements (below),
whose facts no model can know, the untrained base does not walk two- and three-hop questions (0/40 on Qwen3.5-4B; it
never writes a verb after a result) and a trajectory LoRA trained on 32 other worlds does — 35/40 on both seeds, every
citation verified, 3-hop 16/16; on Gemma 4 E4B 38/40 (W9, B1). Before it, on the nursing library (W1–W5e), the result
had two halves that still stand: **navigation transfers** to a procedure the adapter never saw (42 : 0 against the
untrained base made to navigate), **reading a value under a condition in an unseen note does not** (the untrained base
reads it, 15/15; a split by kind of task tied, W5d; and two training draws of one recipe disagreed on 25 of 67 rows,
W5e — so members are trained on two seeds). Search with an off-the-shelf encoder reached recall@3 0.638 against a bar
of 0.80 (W3); the searcher is lexical. ~~State, 2026-09-20 … evidence of nothing until it is run on a set written after
the policy is frozen.~~

**Editing the page after training holds up, for the reason the design intends. [ran] W7:** one statement patched in
`distributor-wiki@v2`'s own library, no retraining: 37 of 38 control answers on that member's own worlds and questions
followed the new value, cited to the patched line; 0 stale. Closed-book, without the page in front of it, the weights
still answer with the old value on 1 of 40 — not zero. The member learned the *route* well enough to occasionally
reproduce what it usually only reads; that is reading, not the library overruling memory, and it bounds rather than
removes the risk the split is meant to close.

**The unit of the library, from 2026-09-24: the atomic statement — [ran] W9, PASSED.** The user's design: the
library is shaped like Wikipedia. A page is about one thing and is a list of **atomic statements** —
one checkable sentence each, under an anchor — and **the statement, not the page, is the unit of
memory**. Links live inside the statement that names them (a product's `§supplier` is also the way to
the supplier's page); operative pages are recipes whose statements are steps and branches, and a plan
is the trajectory the task's context chooses through them. `<open>id</open>` shows a page's sections,
`<open>id§anchor</open>` one statement, and every answer cites the statement it rests on — a citation
the runtime checks mechanically, so the memory is its own verifier. First test bed: an invented
distributor wiki whose operative pages follow the roles of the reference organisation (purchasing,
receiving, dispatch, claims and returns, customer communications, finance, HR, marketing, IT), generated
per world so no value can be known by heart; the untrained base is measured before a trajectory LoRA is
bought ([`MEMORY.md`](MEMORY.md) §1.6).

Specified piece by piece in [`MEMORY.md`](MEMORY.md) **[spec]**; argued for, with its open
questions, in [`KNOWLEDGE-TRAJECTORIES.md`](KNOWLEDGE-TRAJECTORIES.md). Five pieces, four of them
not neural:

| piece | what it is | where it lives |
|---|---|---|
| **the library** | markdown notes under half a page, on two shelves — and, since W9 **[ran]**, pages of atomic statements with their links inside, cited by every answer. **Operational harness** — *how is it done*: recipe-like notes whose links are control flow (`requires`, `next`, `uses`). **Encyclopedic wiki** — *what is it, which formula applies*: a tree, general to specific (`parent` → `children`) | `knowledge/<subdomain>/`, in git |
| **the radar** | embeddings compressed to one subdomain; per note two vectors, *when is it for* and *what does it define*; returns the two or three notes of exactly the subdomain in play | one small index per subdomain |
| **the language** | three verbs the expert may write — `<search>`, `<open>`, `<calc>` — each answered inline after its closing tag | a grammar, versioned with the release |
| **the LoRA** | trained on the *habit of navigating*: cases whose constants change every time, so the number has to be read from the note | the adapter — the only trained piece |
| **the runtime** | a small Python referee in the proxy: turns the pages, substitutes a site's rules before the expert sees the note, cuts a walk that skips a `requires` | `memory/` **[spec]**, on the corpus-mode loop that already serves every member |

```mermaid
flowchart LR
    Q["request in the subdomain"] --> E["expert LoRA<br>the habit of navigating"]
    E -- "search: a situation or a doubt" --> I["radar<br>this subdomain only"]
    I -- "titles and ids" --> E
    E -- "open: id" --> RT["runtime — referee<br>fills slots · site rules · requires guard"]
    RT --> H["harness shelf<br>requires · next · uses"]
    RT --> K["wiki shelf<br>parent · children"]
    RT -- "the note, already resolved" --> E
    E -- "calc" --> C["calculator"]
    E --> A["answer"]
    classDef local fill:#e8f1e4,stroke:#4a7a3a,color:#1d3314
    classDef art fill:#eef0f6,stroke:#4a5a8a,color:#1d2240
    class E,RT,C local
    class I,H,K art
```

![A bookcase with two shelves — a route of cards above, a tree of cards below — a small radar lighting three cards, a specialist holding three tools, and beneath them a band, the referee: a page being turned, a stamp for a site's rule, a barrier gate.](img/memory-five-pieces.png)

*The five pieces of the memory. Four of them are not neural.*

**Why it is a harness.** A classical agent harness keeps three things fused: the procedure in the
system prompt, the loop in hand-written code, and the hope that the model obeys. Here they are
apart. The procedure is the harness shelf — *editable text*. The loop is the links — *editable
frontmatter*, enforced by the referee where it matters. And obedience is no longer hoped for: it is
the one thing the adapter is trained on. This is what `harness.lora` was reaching for — a shared
protocol adapter composed with domain adapters, parked when composition could not be measured
cleanly — now per subdomain, and with its content outside the weights.

**Three measurements force the split rather than suggest it.** A small model does not follow a
procedure it merely reads — base + document, 0 tool calls on 351/351 **[ran]** P61 — so following is
what is trained. Fixed knowledge in a corpus is memorised and then prices nothing — a control with no
lookup tool scored 27/30 over fourteen values **[ran]** P15, P21 — so what a case needs is drawn per
case and delivered only through a note's slots. And a specialist is confidently wrong one step
outside its region — 30/30 inside, 1/20 on sibling families **[ran]** P14 — which is the headroom and
the claim: *the sibling's notes extend the region with no retraining.* That claim is untested.

**What is already known to work** is the channel: an expert does use a result written inline after
its tag — 90 of 90 on chains of six to nine tool calls **[ran]** M7 arm 0b — and the memory delivers
every note through exactly that.

**What is not assumed.** That a hierarchy beats a flat search — in this workspace's earlier memory
benchmark it lost to lexical search, and `evolving-memory`'s dual index changed nothing **[read]** —
or that compressing the radar to a small dimension costs nothing. Both are arms with a flat baseline.

![Two panels. Left, the conversation in the prompt: a scroll growing turn after turn and a claim form whose order field is empty, 43 of 54. Right, the keys in a memory: one index card with the state and the key names, a drawer opened on order 58, and the claim form filled with it, 53 of 54. Title: carry the keys, not the conversation.](img/operational-memory.png)

*H1: fetching a value by key fixes what reading the history lost — the claim now names the order.*

**Beside the library, not instead of it.** The library above holds knowledge — encyclopedic and operational — that a
member navigates by key: content that changes rarely, edited by a person rather than by the conversation. The
**operational memory** holds the opposite kind of thing: the live state of a workflow or a conversation, changing
every turn and gone when the gateway exits. Both are read by key; the weights hold the route to each, never the
content of either.

**The operational memory — built [ran] in tests, and trained on by two members since** (`examples/common/opmemory.py`): a SESSION
cache keyed by (organisation, user, session) and a GLOBAL cache per organisation (`global.<key>`), served by the tool
layer exactly like any domain tool and bounded by the same signed claim that already keeps one tenant's rows out of
another's reach (§2) — no key crosses an organisation or a user. Keys are validated, values capped at 500 characters,
every write logged. Workflows are declared, not neural — one TOML file per role
(`examples/distributor/workflows/*.toml`, six roles, two to three states each) — and the state advances only from the
calls the tool layer actually ran; the model never sets it, and reads it only in the one-line context of §2.

**The workflow harness is the member's learned part of this — [ran] H1, read two ways (§2).** What is trained is not
the cache, which stays outside the weights exactly as the library does, but the *habit* of operating it: for its
domain, the workflows as state machines, its tools and how to call them, and the keys under which a session's context
lives — one corpus, inside the member, the way a member already learns its tool block and its library's routes. It
is a harness *inside* each member, not a second adapter composed with a domain one — which is what parked
`harness.lora`, where composition could not be measured cleanly (P9, P13 **[ran]**). It extends W9's key-addressed
reading (`<open>id§anchor</open>`) from encyclopedic knowledge to operational memory, and from reading alone to
reading *and* writing. Whether it beats carrying the conversation is H1 (§2 has the numbers): **PASSED** per arm,
**VOID** as pre-registered — the user's decision (2026-09-29): per arm stands, the as-written VOID kept as the
record of that instrument error. Design and open decisions:
[`review/harness-workflow-kv.md`](review/harness-workflow-kv.md); how every piece here connects end to end:
[`MECHANISMS.md`](MECHANISMS.md).

## 5. The release contract

A region enters through one door **[ran]**: a suite with a verifier the training loop never
sees; the bare base as the headroom arm; the exact sign test on discordant pairs. The
manifest that comes out (`releases/*.json`) holds base, recipe, corpus hash, adapter hash,
prompt hash, the score and the paired comparisons. Re-serving it and re-training from it
both tie the recorded run **[ran]** P57. `training/harness/train_pool.py` holds each member
as a record read off its corpus — band, surface, keys, order, system prompt — and tests
re-read every corpus and fail if a declaration drifts. With milestone 7 the manifest gains the
knowledge base's hash and its index's hash: a member is its corpus *and* its base.

## 6. The family

**Gemma 4, from 2026-09-25 — the user's decision on B1 [ran].** `google/gemma-4-E4B-it` small; `gemma-4-12B-it`
large (~~`gemma-4-31B-it`~~, changed for a Mac mini): one id space with the E4B and a LoRA served applied (B2 **[ran]**);
its LoRA raises acceptance of the small member's drafts, α 0.871 → 0.898 (B4 **[ran]**); it buys no accuracy on the
comparison band once the small member is taught it (B3, B5 **[ran]**). **Served with its own MTP drafter** (`gemma-4-12B-it-assistant`) and an expert LoRA in one vLLM server: 2.7× on the base, 1.7–2.1× with the LoRA on (F0 **[ran]**). **What is hot-swapped and what is not:** the expert LoRA per request (0.25 s to load one at runtime, F0; 2.9 µs on the Mac's MLX research bench, MAC; **~3 ms on the Mac's `edge` profile, llama.cpp, via `POST /lora-adapters`, MAC2** — §3); the drafter is one per server and takes no LoRA in vLLM — a drafter tuned per expert is strategy A (one shared, trained), C (a full aligned draft: **[ran] C0** — Gemma's own MTP with the expert LoRA on recovers to 1.92× domain / 2.40× general against 2.80×/2.60× on the base; a merged, purpose-built E4B draft has not run, blocked this round by memory and quantization on every GPU tried), or B (a drafter LoRA, parked — MTP already pays for itself on an L4 and does not on the Mac); [`GUIDE.md`](GUIDE.md) §6.5, §6.6. On the Mac's `edge` profile Gemma's MTP does not help the 12B the way it does on an L4: it slows it (0.52× with the LoRA on its own domain, 0.66–0.87× otherwise, **[ran] MAC2**), and the E4B+12B pair does not fit together in 16 GB. On W9's wiki, with the same corpus and recipe, Gemma's member
tied Qwen3.5-4B's (38/40 against 35 and 35, 4 : 1 against each); untrained, Gemma already walks it 19/40 where Qwen
walks 0/40, and it trains in a third of the time. The user decided before the comparison ran that parity chooses
Gemma, because the development stack targets it. Two engineering constraints come with it: the LoRA excludes the
vision and audio towers, whose projections are `Gemma4ClippableLinear` (P29's block, and nothing else —
`training/s4_train.py::towers_to_exclude`); and its thinking channel stays off for members, as Qwen's did.

**Every released member has moved through the release gate:** `email-full@v3` is on Gemma (M1b **[ran]**: a tie
with `@v2`, 119 : 0 over the bare Gemma); `desk-commitment@v3` too, trained on both desk bands (M1d **[ran]**: deep band 239/240 against the bare
Gemma's 83); `distributor-wiki@v2` on Gemma (B5: plus comparisons, 37/40 on that band); the `@v1` releases on `Qwen2.5-3B-Instruct` stay as the control arm. The family is named in one place,
`training/harness/family.py`. ~~Qwen 3.x: `Qwen3.5-4B` small, `Qwen3.8-27B` large … Gemma 4 meets the id-space
requirement and not yet the PEFT one **[ran]** P29.~~

Nothing in §1–§5 names a family. A pair needs one id space and a base PEFT can attach to; Gemma 4 E4B meets the
second **[ran]** B1, and shares its id space with the 12B — byte-identical vocabularies, 0 target-only ids **[ran]** B2.

## 7. What is not neural, on purpose

- **Memory and knowledge** are markdown and git; an index of embeddings is derived from them, never the source.
- **Execution** is a sandbox; tools are an MCP server (`training/mcp/inbox_server.py`).
- **Arithmetic** is a calculator: distillation transferred a procedure and not the
  arithmetic **[ran]** P5–P7.
- **Whether a region is served locally** is a table of measurements, not a model's opinion.

## 8. Deliberately not built

A bespoke inference runtime, KV-cache sharing across adapters (a layer-restricted LoRA's precondition for it — a
bit-identical lower KV against the base — is measured, §3; the sharing itself is not built), tree attention across
adapters, composition of adapters, a tournament that breeds them, the control plane, vertical packs. And, by scope
rather than by order: the customisation service and its tooling are not part of this runtime nor of the open-source
version.

## 9. Where it sits in an organisation — and the framework boundary

The deployment this is aimed at is an organisation that runs on **one agent per role**: people in a
few roles; an agent runtime with an agent per role; the applications those agents operate
(scheduling, administration); the channels people already use (an app, messaging split into an
outside and an internal audience); and one relational database with identity, payments and monitoring
beside it. lora-kernel is **one layer under the agent column** and replaces nothing above or below it:

```mermaid
flowchart TB
    P["people, in roles"] --> RT["agent runtime — one agent per role"]
    RT <--> APPS["applications and channels"]
    APPS <--> DB["systems of record<br>database · identity · payments · monitoring"]
    RT -- "OpenAI-compatible API + a signed token" --> PX["gateway — token → user · role · tenant<br>prune · member prompt"]
    PX --> RO{"router<br>the role is the route"}
    RO -- "a measured region" --> EX["the role's adapter<br>on one small resident model"]
    EX <--> REF["referee — search · open · calc · site rules · guard"]
    REF <--> LIB["the role's library<br>how we do it here · what we know"]
    EX <--> TL["the org's tools, run with the token's permission<br>payments held for a director"]
    TL <--> DB
    EX --> GRD["grounding — no line shown that a tool did not return"]
    RO -- "unmeasured" --> FR["frontier model"]
    RO -. "policy: nothing leaves" .-> HU["a person"]
    classDef ours fill:#e8f1e4,stroke:#4a7a3a,color:#1d3314
    classDef theirs fill:#eef0f6,stroke:#4a5a8a,color:#1a2240
    classDef out fill:#f4e6d4,stroke:#9a6a2a,color:#3d2a0e
    class PX,RO,EX,REF,LIB,TL,GRD ours
    class P,RT,APPS,DB theirs
    class FR,HU out
```

**Records stay in the database, habits go in the adapter, knowledge stays in notes a person can read
and correct.** Three consequences for the design:

- **The role says which member — not whether.** The runtime already knows which agent a message came
  from, and the role rides in the model id (`auto:<role>`). **[ran]** F2: with the role *confirmed by
  the member's own keys* there are never more misroutes than with the keys alone, nothing is served
  under a wrong role, and the 240-case replay ties at 0.775; it is the proxy's default. The policy
  that let the role decide alone served 120 of 120 foreign tasks and failed. So half of the router's
  open problem is gone — *which* — and half remains: *is this request in the region at all*.
- **The unit is a role pack, not an adapter.** Tool surface, prompt, corpus, library, suites, and two
  policies: *who writes which kind of answer* (§4's split) and *what may leave* (frontier, a person,
  or nothing). **[ran]** F3: `roles/<role>/role.toml`, every line checked against its artefact by
  `rolepack.lint`; the two released members re-expressed with the served prompt and tool block
  byte-identical, the registries derivable and equal. The code does not read the packs yet, and the
  memory's member declares a loop — the referee's — that the API cannot serve.
- **The model never holds a credential.** Tools reach the systems of record *as the person asking*;
  permission is checked by the tool, outside the model, and every action is logged. **[spec]** —
  nothing of this layer exists, and no expert here has been measured performing a write.

What exists, what is missing and the order to build it — thirteen gaps, eight interfaces, seven steps,
each with the result that would stop it — is [`FRAMEWORK.md`](FRAMEWORK.md). The scope line of §8 does
not move: the framework is the runtime, the formats, the gates and *reference* role packs on generated
data; a customer's corpora and the pipeline from traces to a release are not in this repository.

**Read against a pasted architecture, 2026-09-20.** A five-phase plan — an educational centre and a
distributor under one kernel, speculative decoding, Postgres row-level security behind Auth0, Docker
Compose — arrived pasted into a session and was checked against the gap table above: most of it was
already built (role packs, F3), already sequenced later (concurrency, the bill, installation), or
blocked (a LoRA-adapted drafter is a vLLM RFC, not a feature). One gap it named correctly and this
repository had not closed — permission enforced outside the model, not asked of it — becomes the
next step, scoped to **one** neutral domain, not two, with a toy store standing in for Auth0/Postgres
RLS until shown insufficient, gated at **0 leaks** on an adversarial suite. `W5d` — the read/write
split a role's answer policy needs — runs first: it is cheaper and the next step's role packs already
declare a policy they have no measured value for. Full reading, phase by phase: [`FRAMEWORK.md`](FRAMEWORK.md)
§9; the plan entry: [`PLAN.md`](PLAN.md) §0.

**The code-only half is built [ran] 2026-09-21** (`examples/`): `school/`, the user's own named main
case, all seven roles the reference diagram draws — `dev`, `trainee`, `marketing`, `educador`,
`compras`, `cfo`, `it` — thirteen tools, two tenants, an adversarial suite at **0 leaks**, both
domains' MCP servers registered and `mcp probe`-verified against a real OpenClaw instance. What is
still missing is the falsifier's model-side half (does a *model* ever try the cross-tenant call —
needs an account behind an OpenClaw turn, not yet run) and any corpus or adapter — nothing here
trains. Milestone 6's own first number also landed the same day: pricing the existing P41/P62 replay
at real `google/gemini-3.8-flash` rates puts today's frontier bill for the 37.5 % sent out at **$0.18**
— a fraction of a dollar at this scale, and the GPU's own cost is the one input still unpriced, named
rather than guessed (`docs/PLAN.md` milestone 6, `results/M6-bill-20260921/`).
