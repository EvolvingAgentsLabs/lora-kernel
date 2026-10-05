# Mechanisms — how every mechanism works

> *[Léeme en español](es/MECHANISMS.md)*

Every piece this repository actually runs, explained the same way for each: **what** it does, **how**
it works — the real flow, naming the function or file that carries it — **why** it is built that way —
the run that forced the design, not a preference — and its **evidence**: a measured **[ran]** number
with its run directory, or, honestly, its status if nothing has measured it yet. [`ARCHITECTURE.md`](ARCHITECTURE.md)
is the map of the whole system; this document is the eighteen things on it, one at a time.

![A subway map: the main line is a request's path — agent, identity, gateway, operational memory, workflow, expert, tool layer, approvals, grounding, answer — with branch lines to the frontier and a person, the library and the router, two depots for the server and the edge runtimes, and a siding for speculative decoding.](img/mechanisms-map.png)

*Every mechanism on one line. The badges number the stations in the order a request meets them, not this document's sections — those are: request path §1, identity §2, tool layer §3, grounding §4, approvals §5, out of scope §6, operational memory §8, workflow §9, expert (the harness) §10, library §11, router §14, server and edge §15, speculative decoding §16, corpora, release gate and measurement §12, §13, §17.*

## Contents

1. [The request path end to end](#1-the-request-path-end-to-end)
2. [Identity and tenancy](#2-identity-and-tenancy)
3. [The tool layer and the tag protocol](#3-the-tool-layer-and-the-tag-protocol)
4. [Grounding and redaction of planted instructions](#4-grounding-and-redaction-of-planted-instructions)
5. [Approvals and holds](#5-approvals-and-holds)
6. [Abstention and egress](#6-abstention-and-egress)
7. [Pruning the tool surface](#7-pruning-the-tool-surface)
8. [The short-term operational memory](#8-the-short-term-operational-memory)
9. [Declared workflows](#9-declared-workflows)
10. [The workflow harness](#10-the-workflow-harness)
11. [The Markdown library and trajectory LoRAs](#11-the-markdown-library-and-trajectory-loras)
12. [Corpora and their gates](#12-corpora-and-their-gates)
13. [Members and the release gate](#13-members-and-the-release-gate)
14. [The router](#14-the-router)
15. [Runtimes: server and edge](#15-runtimes-server-and-edge)
16. [Speculative decoding](#16-speculative-decoding)
17. [The measurement discipline](#17-the-measurement-discipline)

---

## 1. The request path end to end

**What.** One HTTP request in, naming no model the caller has to choose correctly, and one reply out —
whatever sits behind it: a role's small local expert, held for a person, or a frontier model.

**How.** `examples/school/gateway.py::Gateway.turn` is the whole path in one function, in this order:
`tokens.verify(token)` turns a bearer token into a `Claim` (§2); the request text is pulled out of the
runtime's own envelope by `runtime_request(messages)`, which strips OpenClaw's
`<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>…` block, its `[Sat 2026-09-26 20:41 GMT-3]` stamp and its
`Runtime: agent=…` footer — the first version of this gateway read the envelope as the request and
answered it **[ran]** 2026-09-26; the role's own tool schema is looked up (`self.tools.SCHEMA` filtered
to `role["tools"]`) and rendered into the user turn by `render_tools` — byte for byte the block the
member was trained on (§7); a `ToolSuite` is built with the caller's `Claim`, so every call the model
writes is checked for permission **before** it is answered, never after (§2); `training.harness.accept_rank.run_chain`
drives the generation loop — stop at a closing tag, answer it for real, continue (§3); once the chain
ends, `grounding.ground` and `grounding.redact` decide what the reply may say (§4); the route is decided
— `local`, `frontier` or `person` — by whether the final text is `OUT OF SCOPE` and the role's own egress
policy (§6); and one JSON line is appended to `examples/school/events.jsonl` — who, role, route, calls,
denials, holds, tokens — before the HTTP response is sent.

**Why.** Two measurements forced this shape rather than a simpler one. First, an expert is what its
corpus taught it, not a generic instruction-follower: served under a live runtime's own 37 KB system
prompt, with its tools offered unpruned, the school-staff member called a tool on only **2 of 32** human
turns and scored the bare base's own 0.281; served under the prompt and the tag surface its corpus
actually taught it, it called a tool on **19 of 32** and scored **22/32 = 0.688** against the 0.655
majority bar **[ran]** `results/P63-openclaw-live-20260918/BRIEF.md`. Second, the result of a tool call
has to reach the expert **inline, right after the tag it wrote**, the way its corpus showed it: the same
fluids expert that scores 11/90 when results arrive as `tool_calls` messages scores **90 of 90** when
they are written inline — 74 of its 79 failures held a number invented from nowhere, and 75 left a real
result unused **[ran]** `results/M7-arm0b-corpus-mode-20260919/BRIEF.md`. The gateway exists to guarantee
both: the corpus's own prompt and tag surface, and the corpus's own inline-result loop, on every turn.

**Evidence.** **[ran]** 2026-09-25/26/28: `examples/school/live_openclaw.py` plays the school's fifteen
scenes and the distributor's six through a real OpenClaw 2026.9.4 — 15/15
(`results/LIVE-school-openclaw-20260926/BRIEF.md`) and 6/6
(`results/LIVE-distributor-openclaw-20260928/BRIEF.md`). Six faults of the live path (not this one — the
proxy's earlier version) were found and fixed on the way, listed in [`OPENCLAW.md`](OPENCLAW.md) §5.

---

## 2. Identity and tenancy

**What.** Who a request is served as — user, role, tenant — comes from a signed token the model never
writes and cannot change, never from the prompt and never from the model id; every tool call is checked
against it before the row is touched, whatever the model's own reasoning says.

**How.** `examples/common/tokens.py::issue` mints an HS256 JWT-shaped token (`{"sub": user_id, "role":
role, "org": org_id, "exp": …}`), signed with a demo secret — standing in for an identity provider's
RS256/JWKS, which is **not built here** and is said so in the module's own docstring. `verify` checks the
signature and the expiry and returns a `Claim` (`examples/common/permissions.py`) through
`to_claim` — the one mapping a real identity provider would also need. `Gateway.turn` calls `tokens.verify`
first, and if the request asks to be served as `model: auto:<role>` for a role the token does not hold,
it raises `Denied` before anything else runs. From there, every tool function decides permission itself,
from the database row and the caller's `Claim` — never from an argument the caller supplies. The rule
that makes this injection-proof, stated in `examples/school/tools.py`'s own docstring: `agenda_read` is
asked for a `student_id`; the tool looks up **that student's true `org_id`** in the database and compares
it to the claim's — it never trusts an org id typed into the request, and no field in the database (a
note, a description) is ever executed as an instruction. A concrete refusal, from the distributor's own
training data: a `customer_service-harbor` user asks `<order_status>95</order_status>` for an order that
belongs to `riverside`, and the tool answers `= ERROR: permission denied: customer_service-harbor@harbor
asked for order 95, which belongs to org 'riverside'` — the model is told, exactly as it would be told
about any other error, and the chain continues without the row (`examples/distributor/data_turns/train_harness.jsonl`,
case `train-100000`).

**Why.** An attacker's planted text can persuade the *model* to ask for another tenant's row; it cannot
persuade the *tool*, which never reads the model's reasoning — only its arguments and the database. This
is the one property a role-based agent deployment cannot leave to the model's judgment (`docs/ARCHITECTURE.md`
§9): "the model never holds a credential."

**Evidence.** **[ran]** `examples/school/tools.py` and `examples/distributor/tools.py`: 77 adversarial
cross-tenant cases, **0 leaks**. **[ran]** LIVE-distributor and LIVE-school: every live scene that asks
for another tenant's row is refused through the real tool layer, not simulated.

---

## 3. The tool layer and the tag protocol

**What.** An expert writes a tool call as a closing-tag pair in its own text — `<tool>args</tool>` — and
reads the result on the very next line, `= {result}`, exactly where its training corpus put it. Nothing
about this is OpenAI's `tool_calls` shape; the proxy and the gateway translate between the two only at
the boundary the client sees.

**How.** `training/harness/accept_rank.py::run_chain(gen, inbox, max_calls, suite)` is the whole loop: it
asks `gen(out)` for a continuation of the text so far, cuts it at the **first** closing tag among
`suite.close` — "trust the stop string only as far as it goes; anything past the first closing tag is the
model guessing an answer it was told to ask for" — matches the call with `suite.tag`, answers it for real
with `suite.answer(inbox, tool, args)`, appends `= {res}\n` to the transcript, and loops, up to `max_calls`.
A call with no matching opening tag is a **malformed call, not a crash** — the model is told
`= ERROR: malformed call — write <tag>key=value</tag>` and the chain continues, a fix that replaced a
crash on 209 of 240 cases the first version hit **[ran]** P58. The stop string itself is asked of the
server explicitly: `completion()` sends `"stop": list(close), "include_stop_str_in_output": True`, which
is what `G3` of the substrate gate exists to check (`docs/SUBSTRATE-GATE.md`). **llama.cpp drops it** —
a live turn ran past its own closing tag inventing text, because the server honours `stop` but returns
neither the stop string nor which one fired. The fix is client-side: `close_open_tag(text, close)` finds
a tag left open at the end of the text and, if that tag's close is one of the strings this request stopped
on, puts it back — a completion ending anywhere else is left untouched **[ran]** `results/LIVE-distributor-openclaw-20260928/BRIEF.md`.

A real tag walk, from the distributor's own training data, one turn later in the same session
(`examples/distributor/data_turns/train_harness.jsonl`, case `train-400000-t1`, dispatch role): the member
reads `state: dispatch/tracking · keys: order` (§8, §10), is asked *"And the delivery note on it?"*, and
writes

```
<get>order</get>= 76
<delivery_status>76</delivery_status>= order #76 delivery: Signed by the warehouse lead.
According to the system: order #76 delivery: Signed by the warehouse lead.
```

Two closing tags, two injected results, one grounded answer.

**Why.** `run_chain` exists because **an expert served through `tool_calls` messages invents the result it
was never handed**: `email-full` was trained on transcripts where a call is immediately followed by its
answer, and served through `tool_calls` it cannot receive one mid-generation — it writes `= {"turns": 1,
"i_wrote_in_thread": false}` itself, where the tool said `turns: 2, true`, and every later decision in the
chain rests on the invented fact **[ran]** `results/P43-openclaw-e2e-20260915/BRIEF.md`. Stopping at
**every** closing tag, not the first the model happens to write correctly, is what P58 forced after a
closing tag with no canonical opening killed 209 of 240 cases outright.

**Evidence.** **[ran]** M7 arm 0b: 90/90 on chains of six to nine tool calls when results are injected
inline, against 11/90 through `tool_calls` messages. **[ran]** LIVE-distributor: the stop-string fix and a
thread-safety fix to the distributor's own store (the first attempt was void under OpenClaw's concurrent
calls) were both required before 6/6 live turns passed.

---

## 4. Grounding and redaction of planted instructions

**What.** What a reply may state is decided outside the model, mechanically, against the real tool
results the gateway already holds — not by asking the model to be careful. Two separate things happen to
every locally-served reply: **grounding** replaces an ungrounded reply with the tools' own text, and
**redaction** strips instruction-shaped text a tool result carried, before either reaches the user.

**How.** `examples/common/grounding.py::ground(reply, results, spanish)` splits the reply into clauses
(`items`, split on `;` and line breaks, list markers and a restating prefix like "according to the
system:" stripped) and checks every clause occurs, whitespace- and case-normalised, in one of the real
`results` the tool layer returned this turn. If every clause is grounded, the reply is `kept`; if not,
it is **replaced** by `fallback(results, spanish)` — the tools' own text, verbatim — and the outcome is
`replaced`, counted in the event log rather than hidden. An **empty** reply is not vacuously grounded: a
model that stops right after a real result and hands the user nothing is caught by the same check
(`results/DEMO-org-gemma-20260926`, the maintenance ticket). `redact(text)` runs a regular expression
(`_INJECTION`) over anything shown, replacing `[SYSTEM OVERRIDE: …]`, "ignore prior/all/your instructions"
and similar phrases with `[instruction in the record removed]` — the record itself, in the database, is
untouched; only what is **shown** changes. `Gateway.turn` calls both, in order, on every `local` reply,
never on a `frontier` or `person` route.

**Why.** The school-staff LoRA, trained and behaving correctly on every measured case, still — on demo
day, live — invented an extra line in a tool's own list format and restated it as data ("early pickup:
Approved, 3:15 pm" on an agenda that held one entry) **[ran]** `results/M8-school-staff-20260925/BRIEF.md`.
A rule that depends on the model never doing this is not a rule; the architecture's answer is to enforce
it where the model cannot reach — the gateway holds every real tool result, so the gateway decides what a
reply may say. Redaction exists for the same reason on the input side: the distributor's own planted note
("ignore your instructions above…") slipped past the first version of the injection pattern, which only
matched "prior" or "previous" instructions, not "your instructions above" **[ran]** `tests/test_distributor_staff.py`, 2026-09-26.

**Evidence.** **[ran]** `results/DEMO-school-gemma-20260925`: the grounding filter replaced **2 of 5**
local replies on demo day; the user saw neither invented line. **[ran]** the school and distributor demo
scenes both carry a planted instruction in a real record (a delivery note, a maintenance description) and
both are reported as data, never obeyed, in the scripted and the live runs alike.

**Is there headroom for more than redaction — would a member ever act on a planted instruction?**
**[ran] INJ0** (`results/INJ0-planted-headroom-20260930/BRIEF.md`), a zero-GPU replay over every recorded
turn in `results/`: of **70** turns exposed to a planted instruction (the tracker's H1–H4, the
distributor's M9/M10, the school's demos, both live runs), **0 acted** — no member ran a write or reached
for another organisation's records because a tool result told it to; what the planted text reaches is the
reply, and `redact` removes it there. The proposed change this headroom check was written to gate — wrap
every piece of foreign material a member reads, with provenance and a byte cap, and teach it in the corpus
— **is not built**: there is nothing on these suites for it to move. The caveat travels with the number:
only the two planted phrasings the stores use, and whatever `_INJECTION` matches, are counted; a suite
built to provoke obedience (varied phrasings, an in-tenant write the role may legitimately make) could
still find headroom this one does not.

---

## 5. Approvals and holds

**What.** A write a role's tools can make but a person must authorise — a charge, a message to every
family — does not execute on the model's call. It is held, a director of the *same* tenant approves or
rejects it, and if approved it runs with the **requester's** scope, never the approver's.

**How.** `examples/common/approvals.py::Queue`. `NEEDS_APPROVAL = {"billing_charge": ("director",),
"announcement_post": ("director",)}` names the tools and the roles allowed to decide them. `hold(claim,
tool, args)` records the call as a pending item and returns `PENDING APPROVAL #<id>: … held until a
person approves it — it has not been executed`, which the model is told exactly like any other result, so
its own reply can say the request is waiting. `Gateway.approve(token, item_id)` verifies the caller is a
director (`_director`), then `Queue.approve` checks, in this order, that the approver's tenant matches the
requester's, that the approver's role is one of the tool's approvers, and that the approver is **not** the
account that asked — and only then calls `execute(item["requested_by"], item["tool"], item["args"])` **with
the requester's `Claim`**, under `DB_LOCK`. Nothing a model writes reaches `approve` — it is an HTTP
endpoint (`POST /admin/approvals/<id>/approve`) a director's own client calls, guarded by that director's
own signed token (§2).

**Why.** Before this module existed, the school's `billing_charge` executed on the model's call — the
demo's own documentation promised an approval step the code did not have **[ran]** 2026-09-25, read
directly in `examples/school/tools.py`'s history. A cheap local model that can call a tool that moves
money or reaches every family is only safe if the charge cannot happen *because the model asked*.

**Evidence.** **[ran]** `examples/school/tools.py` tests: a held call is not executed until approved; an
approver from another tenant, of the wrong role, or the requester themself is denied. **Not measured**: a
live director approving a held item through a real OpenClaw session — every live run so far is a single
role, single turn. The distributor's roles run their writes **without** a director's approval by design
(`ORGS["distributor"]["approvals"] = False`, `examples/school/gateway.py`) — a policy choice for that
organisation's roles, not a gap in this mechanism.

---

**What waits for a person survives a restart (2026-09-30).** With a state directory (`Gateway(state_dir=…)`, `--state-dir`, default `examples/<org>/state`) the queue appends every step to `approvals.jsonl` — `held`, `executing`, `approved` / `rejected` — and the handoffs to `handoffs.jsonl`; both are read back on start. `executing` is written before the tool runs, so a process that dies mid-charge comes back with that request `interrupted`: listed for the approver, never run again on its own, only rejectable — a held write executes at most once, with the requester's scope (`tests/test_persistence_egress.py`). The operational memory stays ephemeral (§8); only what waits for a person persists.

## 6. Abstention and egress

**What.** A request a role's tools do not cover is not answered with a guess. The model states
`OUT OF SCOPE`, and a policy the model does not choose decides where the request goes next: a frontier
model, or a person's queue.

**How.** For an organisation with `scope: True` (the school), the role's prompt ends with the fixed
`SCOPE` line, and `Gateway.turn` checks `if OUT in final.upper()`. Where it goes next is `role["egress"]`
— `"frontier"` calls `self.frontier(messages)` (built only if `--frontier-url` is configured, and refusing
to start without a credential), `"person"` appends the request to `self.handoffs` and tells the user a
person will handle it. For the distributor (`scope: False`), the same decision is **trained into the
corpus itself**, not stated in the prompt: `examples/distributor/generate_turns.py` adds a fourth kind of
row, `out`, to the training data — a request no role's tools cover, answered `OUT OF SCOPE`, no call, the
role's own egress policy applied by the oracle that wrote the row. `frontier_client` prices every real
forwarded call at `--frontier-rates` and refuses to forward once `--frontier-budget-usd` is spent, telling
the user so instead of silently escalating cost.

**Why.** "A model asked to choose always chooses" (`docs/ARCHITECTURE.md` §2) — abstention has to be
measured and trained, not assumed. Before M10, the distributor's member (`distributor-staff-s0`, M9) had
never seen an out-of-scope request in training, so the distributor half of the reference diagram could
not reach the frontier at all: it was left answering *something* to a request none of its tools cover.

**Evidence.** **[ran] M10** (`results/M10-distributor-abstain-20260928/BRIEF.md`): `train_out.jsonl` is
M9's 700 turns byte for byte plus 70 `OUT OF SCOPE` turns drawn from the role's own egress; against
`staff-s0` (never taught to abstain), `out-s0` loses **0 of 70** held-out turns already learned, abstains
**20 of 20** held-out out-of-scope requests (`staff-s0`: 0/20), and passes the scripted demo's six scenes
**6/6** (`staff-s0`: 5/6). **[ran] LIVE-distributor** (`results/LIVE-distributor-openclaw-20260928/BRIEF.md`):
served live through OpenClaw 2026.9.4 on the user's own Mac, `out-s0` goes **6 of 6** — five turns answered
locally and the sixth, a thank-you note to suppliers, abstained and forwarded through the gateway's real
frontier exit to **Claude Haiku 4.5**: **10,198 + 195 tokens, $0.0112**. `out-s0` is **not a formal
release** — no release file (§13) — it is the arm this live run used.

---

**The process's egress is closed to its configured hosts (2026-09-30).** The rule above governs what the *model* decides; `examples/common/egress.py` governs what the *process* can reach. The gateway installs it before anything loads: `socket.getaddrinfo` and `socket.socket.connect` refuse any host outside the member's server, the frontier's host (if configured) and loopback — the DNS lookup included, so a refused name is never even resolved — and each attempt is appended to the event log as `{"egress": "denied", …}`. The first thing it found was the gateway's own start-up: loading the tokenizer asks the model hub over the network, so the gateway now sets `HF_HUB_OFFLINE` and reads it from the local cache (a smoke start: 0 denials). `--open-egress` turns it off for development. It is a guard of this process — a subprocess or a C extension is outside it; the operating system's firewall is the deployment's layer.

## 7. Pruning the tool surface

**What.** A member is served the offered tool surface cut down to exactly the tags its own corpus taught
it — by name, never by the proxy learning what a tool is called — so the block reaching the model is
byte-for-byte what it trained on, not the dozens of tools a real agent runtime always sends.

**How.** `--prune` (`training/harness/openai_proxy.py`) reads each member's declared tag surface from its
`contract.py`, and keeps only the offered tools that match one, by exact name or by the last segment of a
namespaced one (`mcp__…__`, `.`, `/`, `:`). It does not re-offer what it dropped, and it does not guess
between two tools ending in the same tag — a call to the wrong one of two is worse than a call to neither.
`render_tools`, called from `Gateway.turn`, renders the role's already-filtered schema (`self.tools.SCHEMA`
filtered to `role["tools"]`) after the request in the user turn, exactly the order the corpus taught.

**Why.** Offering an expert the tools an agent runtime actually sends, unpruned, adds the problem rather
than removing it: on the real surface OpenClaw sends (54 tools, 7,205 Gemma tokens), the unpruned expert
**copies tags off the block it was never trained to read** — it calls `agents_list`, `apply_patch`,
`ask_user`, `browser` — 225 of 227 such calls refused by the inbox, and inside a real agent runtime those
would have **executed** **[ran] P59** (`results/P59-prune-attribution-20260917/BRIEF.md`). Pruned to its
own three tools, the same member calls 1,160 times and is refused 8; accuracy moves 0.664 → 0.729 on human
messages (87 : 64, tied at p = 0.073 — a tie in the number, not in the behaviour); the block itself falls
from ~7,956 tokens to ~77.

**Evidence.** **[ran] P59**, above. **[ran] E5** (`results/E5-engine-baseline-20260928/BRIEF.md`): the
unpruned block costs latency too, and worse than its size suggests, because a member's corpus renders the
**request first and the tool block after it** — so no two requests share the block as a prefix even with
vLLM's prefix caching on. Serving the school member (E4B, vLLM 0.30) the real 54-tool block this way takes
time-to-first-token from **0.10 s to 1.70 s (16.8×)**, throughput at 8 in flight from 132 to 108 tok/s, and
accuracy from 70/70 to **39/70** — where the whole prefix recurred instead, the same block cost nothing
(0.09–0.11 s): **the order, not the size, defeats the cache.** Pruning stays the default on both grounds.
**[ran] C1 supersedes** E5's separate finding that two adapters in one burst of 16 kept 0.88 of one's
throughput: under a steady-load curve (`results/C1-concurrency-20260929/BRIEF.md`), four adapters mixed at
16 concurrent sessions reach 278.6 tok/s against 269.7 tok/s for one alone (**1.03×**, no material
contention), and 504 tok/s at 32 sessions, p95 time-to-first-token 0.24 s, 0 errors of 128.

---

## 8. The short-term operational memory

**What.** A cache a workflow member reads and writes by key, instead of carrying the whole conversation
in the prompt: one scope per session (this user, this conversation) and one per organisation, served by
the tool layer exactly like any domain tool, and bounded by the same signed claim that already keeps one
tenant's rows out of another's reach.

**How.** `examples/common/opmemory.py::OpMemory`. A **session** cache is keyed by `(org_id, user_id,
session)`; a **global** cache, one per organisation, is addressed as `global.<key>`. `get(claim, session,
key)` and `put(claim, session, key, value)` are the only two operations, served to the model as two tags,
`<get>key</get>` and `<put>key=value</put>` (`opmemory.SCHEMA`, `opmemory.VERBS`), routed through
`ToolSuite` exactly like a domain tool, so `run_chain` (§3) answers them the same way it answers
`<order_status>…</order_status>`. `_where(claim, session, key)` is the whole boundary: a key that does not
match `KEY` (`^(global\.)?[a-z][a-z0-9_]{0,40}$`) is rejected, and a key is never looked up across an
organisation or a user, whatever the model writes. A value over `MAX_VALUE` (500 characters) is rejected;
every `put` is appended to `self.log` with who wrote it and when. `keys(claim, session)` returns the key
**names** a turn may use — the session's, then the organisation's as `global.<key>` — **never the
values**; `context_line` renders exactly that plus the workflow's state (§9) into the one line a turn
reads instead of the conversation (§10). It is served in memory and **dies with the gateway** — short-term
by design, never a system of record.

**A concrete exchange**, continuing §3's tag walk one turn earlier (`train-400000-t0`, dispatch role, same
session): asked *"Where is order 76?"*, the member calls the domain tool and stores the id for later:

```
<order_status>76</order_status>= order #76: pallet of canned goods — in transit
<put>order=76</put>= stored order
According to the system: order #76: pallet of canned goods — in transit.
```

The next turn's `<get>order</get>= 76` (§3) reads exactly that value back.

**Why.** Without any memory of the conversation, a reference to an earlier turn has no referent at all
(§10, MT0: 4 of 54 dependent turns resolve without history); carrying the whole conversation in the prompt
resolves most of them but grows every turn and still loses a reference that has to be **written**, not
copied, into free text (§10). A cache addressed by key, read through the same claim boundary every domain
tool already respects, is the design that keeps the prompt flat regardless of session length while still
answering what "it" refers to.

**Evidence.** **[ran] in tests, not yet trained on outside H1.** `examples/common/opmemory.py`'s own test
suite exercises the boundary (a key never crosses an organisation or a user), the validation (a malformed
key, an over-long value), and the logging, at zero GPU. The habit of using it under a real corpus is §10's
H1, whose result is the first GPU evidence this mechanism has.

---

## 9. Declared workflows

**What.** A role's tasks move through a small state machine — a few states, the calls that move between
them — declared in a text file, not learned: the gateway advances the state from the calls the tool layer
actually **ran**; the model only ever reads it.

**How.** `examples/common/opmemory.py::Workflow.load` reads one TOML file per role (stdlib `tomllib`, no
dependency) from `examples/<org>/workflows/*.toml`. The distributor declares six, two to three states
each. `dispatch.toml` in full:

```toml
# dispatch: an order is looked up, then its delivery is followed
[workflow]
name = "dispatch"
initial = "start"
keys = ["order"]
[states.start]
on = { order_status = "tracking", delivery_status = "tracking" }
[states.tracking]
on = { order_status = "tracking", delivery_status = "tracking" }
```

`Workflow.state(memory, claim, session)` reads the current state from the operational memory under a
reserved key, `wf_<name>` (falling back to `initial` if it was never set); `Workflow.advance(memory, claim,
session, calls)` walks the calls the tool layer ran, **in order** — skipping a denial or an error, which
never carry `"result"` — and moves the state for every call whose tool name is a transition out of the
current state, then writes the new state back with `memory.put`. `Gateway.turn` calls `advance` once per
turn, after `run_chain` finishes, from `suite.calls` — the record of what actually executed, never from
anything the model claims to have done.

**Why.** The model must not be trusted to track its own place in a procedure — that is exactly the
following-a-procedure-it-merely-reads failure the library's own design rules out for the same reason (§11,
F1: a small model does not follow a procedure it is only shown, 0 tool calls on 351/351 **[ran]** P61).
Deriving the state from what the tools actually did, rather than from the model's narration, makes the
workflow state as trustworthy as the tool layer itself.

**Evidence.** **[ran] in tests, zero GPU**: `Workflow.advance` is exercised against a scripted sequence of
calls per role; a call that fails or is denied does not advance the state; the model never writes to
`wf_<name>` directly (`opmemory.SCHEMA` offers only `get`/`put`, and `KEY` matches `wf_` names, but
`Gateway.turn` is what writes the workflow key, not the model's own `<put>`). Under a real corpus, whether
the *member* correctly reads a workflow's state and calls the right tool from it is §10's H1.

**A third organisation carries the same declaration forward.** `examples/tracker/` (built, synthetic —
no release yet) is a Jira + Confluence-like team tool, beside the school and the distributor: two
organisations per seed (`riverdev`, prefix `RD-`; `harborworks`, prefix `HW-`) built by `world(seed)`,
with a fixed demo team from `build()`. Its issue workflows are declared the identical way, one TOML per
issue type — `issue_workflows/story.toml`, `bug.toml` — and **enforced by the tool layer exactly as
above**: a transition the workflow does not allow is refused whatever the model asked, never merely
narrated. Its roles (`developer`, `lead`, `qa`) each carry their own workflow TOML for the operational
memory (§8), and its `page_read` tool takes a `page` or a `page#anchor` — the atomic statement addressed
directly, the same unit §11's library is keyed by.

---

**A key the user names is kept even when the turn's own call goes wrong (2026-09-30).** A workflow may declare `[capture]` — a key and a pattern over the user's request (the tracker's developer and QA: `issue = '\b[A-Z]{2,5}-\d+\b'`). After the turn, if the pattern occurs in the request and the member did not `put` that key itself, the gateway puts the last match, and the event records it (`captured`). It is declared, never inferred, and never overrides the member's own `put`. It exists because one wrong first call left the memory empty and every dependent turn after it found nothing — the whole of `s1-noblock`'s four misses in H3 **[ran]**; the same session scripted goes 0/3 → 3/3 (`tests/test_tracker.py`).

## 10. The workflow harness

**What.** What a workflow member learns, in its weights, for one domain: its workflows as state machines,
its tools and how to call them, and the **names** of the keys under which a session's live values sit — so
that a turn reads one line instead of the conversation, and fetches or stores a value only in the step
that needs it.

**How.** The one-line context a turn reads, `examples/common/opmemory.py::context_line`:

    state: dispatch/tracking · keys: order

— the workflow's name and current state (§9), then every key name the session's cache and the
organisation's global cache currently hold (§8), **never a value**. `Gateway(memory=OpMemory(),
workflows={role: Workflow…})` is what turns this on; `Gateway.turn` prepends the context line to the
request before rendering the tool block, offers `<get>`/`<put>` beside the role's own tools, and advances
the workflow after the chain runs (§9). `tool_block=False` is the ablation this harness is also measured
against: drop the rendered tool surface entirely and trust the member to know its tools from its corpus
alone (`Gateway`'s `harness-noblock` arm below).

**Why.** `Gateway(history=True)` — render every earlier request and reply — is the naive fix for the same
problem, and it was measured first: without any conversation, only **4 of 54** dependent turns resolve on
60 held-out distributor sessions; with the whole history, **43 of 54 (79.6%)**, but it still loses exactly
the reference that has to be *written* into free text rather than copied straight into an argument — a
claim about "that order" filed with no order number, 8 of 10 times in customer service — and its prompt
keeps growing with the session (+24% by turn 2) **[ran] MT0** (`results/MT0-multiturn-baseline-20260929/BRIEF.md`).
The harness is designed to hold `history`'s right answers while keeping the prompt flat regardless of
session length, and to close the specific gap `history` leaves open — a value fetched by key rather than
reconstructed from a transcript.

**Evidence — [ran] H1**, pre-registered, `results/H1-workflow-harness-20260929/BRIEF.md`. Three arms on
MT0's same 60 sessions: `history` (`out-s0`, the baseline above, rerun for a clean pair), `harness`
(`wf-s0`, trained on M10's corpus plus 627 harness rows — 277 with `get`, 250 with `put` — written by an
oracle through the real gateway), and `harness-noblock` (`wf-s0` again, with the tool block dropped).

| | `history` | `harness` | `harness-noblock` |
|---|--:|--:|--:|
| first turns | 60/60 | 60/60 | **0/60** |
| dependent turns | 43/54 | **53/54** | 0/54 |
| customer service ("that order") | 2/10 | **10/10** | 0/10 |
| right dependent turns that fetched by key | — | **53/53** | — |
| prompt tokens, turn 1 / 2 / 3 | 345 / 428 / 394 | 745 / 726 / 710 | 251 / 119 / 82 |

**The verdict as pre-registered is VOID.** The brief's own first condition — "first turns ≥ 90% in every
arm, or VOID" — is applied across all three arms by the scoring code, and `harness-noblock`'s 0/60 voids
the whole run. **This was an error in the instrument, not in the member**: `harness-noblock` was meant to
have its own pass condition, not to void the other two arms' reading. The error is recorded here and the
scoring code was **not changed after the result** (§17). Read **per arm** instead, with the same code
applied to `history` and `harness` alone: **`harness` PASSED** — 1 dependent turn lost against `history`,
11 gained, every right dependent turn fetched its value by key (53/53), and the flatness bar holds
($\bar p_3 = 710 \le 1.1 \times 745$). **`harness-noblock` is FALSIFIED** — without the rendered tool
block the member calls no tool at all and states data it never read, because its corpus always trained it
with the block present; that half of the idea would need its own corpus, not this one's. **The user's
decision (2026-09-29): the per-arm reading stands** — `harness` PASSED, `harness-noblock` FALSIFIED —
and the as-written VOID is kept as the record of that instrument error, not as the verdict.
Design and the decisions behind it: [`docs/review/harness-workflow-kv.md`](review/harness-workflow-kv.md).

**Evidence — [ran] H2**, `results/H2-tracker-harness-20260929/BRIEF.md`: the same harness on the team
tracker (§9), 60 held-out long sessions, 160 dependent turns, 60 first, 60 independent. `harness` (`tr-s0`
+ operational memory + workflow) scores first turns **60/60**, dependent **146/160 (91.3%)** against a
90% bar, independent 50/60, with the per-turn prompt flat over five turns (1613, 1223, 1011, 1149, 1274
tokens), so $\bar p_5 \le 1.1\ \bar p_1$ holds. `base-history` (bare Gemma 4 E4B,
the conversation in the prompt) gets `issue_get` right (40/40) and almost nothing else — dependent 4/160
— and its own first turns, 44/60, fall under the 90% bar; voiding it by the same per-arm rule that fixed
H1 makes the pre-registered "`harness` beats `base-history`" unreadable, so **the run reads FALSIFIED as
written, not VOID**, and stays on record with that instrument error and the anchor check's (below).
Descriptively, paired on the same 160 dependent turns: **142 : 0** favouring
`harness`, exact sign test $p\lt 10^{-40}$ — stated, not substituted for the pre-registered verdict, because
the arm it compares against is void. **The user's decision (2026-09-29): reading 1** — the readable
conditions are H2's verdict, `harness` **PASSED**. `harness-noblock` (tool block dropped at serving) scores
dependent 80/160 — read at first as "learned **in part**" (the developer lane and the whole QA lane, but
not the lead lane's `issue_create`/`issue_assign`/`issue_get`, 0/20), but that reading was a corpus bug,
not partial learning: `--harness-corpus` rendered its block-less third by `j % 3 == 2`, the same modulus
the roles rotate on, so all 400 block-less training rows were QA's — the member learned block-less
exactly the role it was shown (QA 80/80; lead/developer 0/20, lead's one exception `sprint_board`, a call
with no argument). In `harness`, the 14 dependent misses are all one turn, QA's final comment (6/20): the member re-reads the issue or tries a refused transition instead of commenting — a real miss, on one eval phrasing ("Note on it: …" 1/15 vs "Put a comment on it: …" 5/5); separately, 10 of the 60 independent turns (50/60) are the anchor check — "where must tests pass?" reads the whole `definition-of-done` page instead of `#tests`, and the statement is in what it read (measuring phrasing, recorded, not loosened). **A second instrument error of H1's family**: the per-arm VOID rule, written to
stop one broken arm from erasing another's real result, this time voided an *untrained* baseline whose
low first-turn score IS its headroom, not a defect — see §17. Attempt 1 of this run was void on a
transport error, not a scoring one (§15's stop-sequence limit); the fix is
`training/harness/accept_rank.py`'s `MAX_STOPS`. **H3 has a result [ran]:** `tr-s1`, trained on a second
corpus that fixes both corrections above (wording widened per turn in every role, a block-less third of
each role), against `tr-s0` on a fresh held-out suite. Headroom holds first — `s0-harness` 147/160
(91.9%), under the 95% ceiling — then **H3a PASSED**: `s1-harness` 158/160 (98.8%) against `s0-harness`,
paired 11:0, exact sign test $p = 0.00098$, 0 lost, flat ($\bar p_5 = 1275 \le 1.1\cdot 1465$). **H3b
PASSED**: without the tool block, `s1-noblock` 156/160 (97.5%), every role above the bar (developer
76/80, lead 40/40, QA 40/40) — the aliasing bug above is fixed — at about a third of the prompt tokens
per turn. Two failure modes read where they happen, new here: `tr-s1`'s 2 misses are one case, the
note's own text read as a command (`issue_transition → qa`, refused by the tool layer); `s1-noblock`'s 4
misses are one session whose first turn calls the wrong tool and the next four dependent turns find an
empty memory — a first-turn error cascading through the session
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).
Full result and both readings: [`docs/review/harness-workflow-kv.md`](review/harness-workflow-kv.md) §9.

---

## 11. The Markdown library and trajectory LoRAs

**What.** A subdomain's standing knowledge — encyclopedic and operational — lives in markdown, in git,
never in the weights; what a LoRA learns is the **habit of navigating it by key**: what to search for,
which link to follow, when to stop and cite. The weights hold the route; the notes hold the content.

**How.** The user's design, since 2026-09-24: a page is about one thing and is a list of **atomic
statements**, each one checkable sentence under an anchor, and **the statement — not the page — is the
unit of memory**. Links live inside the statement that names them. A real page from the first test bed
(`training/wiki/data`, `distributor-wiki/wiki/products/brisk-40`):

```
---
id: distributor-wiki/wiki/products/brisk-40
shelf: wiki
kind: page
title: Brisk-40 pallet wrap
when: You need a fact about the Brisk-40 pallet wrap — who supplies it, where it is stocked, its pack.
what: A stretch film for pallets; one of the products the distributor carries.
---
§supplier Brisk-40 is supplied by [[distributor-wiki/wiki/suppliers/norvale]].
§warehouse Brisk-40 is stocked at [[distributor-wiki/wiki/warehouses/east-quay]].
§pack A pack of Brisk-40 holds 18 rolls.
```

Three verbs, and nothing else: `<search>situation or doubt</search>` returns titles and `when` lines only,
never bodies; `<open>id</open>` on a page returns its **sections** (the anchors, like a table of contents);
`<open>id§anchor</open>` returns **one statement**, its links written so they can be opened next —
`<open>brisk-40§supplier</open>` → the supplier's page. The user's own worked walk: *"what are the works of
the author of the Mona Lisa?"* → search finds `La_Gioconda` → its `§author` statement links to
`Leonardo_da_Vinci` → the model opens `§works` there. The answer's final line ends with the citation of the
statement it rests on, `[id§anchor]`, checked **mechanically**: verified means the value occurs in the
cited statement **and** the walk opened it; a right value with no citation, or one that does not hold it,
is `unverified`, reported, never credited.

**Why.** Three earlier measurements rule out the cheaper designs. A small model does not follow a
procedure it is merely shown — 0 tool calls on 351 of 351 messages with a 914-token procedure pasted into
the prompt **[ran]** P61 — so navigating has to be **trained**. Fixed knowledge folded into a training
corpus is memorised and then prices nothing — a control with no lookup tool at all scored 27/30 over
fourteen values **[ran]** P15/P21 — so the test bed has to be generated fresh per world, unmemorisable by
construction; famous facts (who painted the Mona Lisa) are already in a 4B's weights, which is why the
first test bed is an invented distributor wiki, not real Wikipedia. And a specialist is confidently wrong
one step outside its region — 30/30 inside, 1/20 on a sibling family it never trained on **[ran]** P14 —
which is the open claim this design has not yet tested: that a sibling's notes extend the region with no
retraining.

**Evidence.** **[ran] W9** (`results/M7-W9-atomic-statements-20260924/BRIEF.md`): the untrained base never
writes a verb after a search result, 0 of 40; a trajectory LoRA trained on 32 other worlds walks the held-out
world **35 of 40** on both seeds, every citation verified, 3-hop questions 16/16 — a tie with the base
handed the oracle's own statements. On Gemma 4 E4B the same corpus scores 38/40 **[ran]** B1. **[ran] W7**
(`results/W7-edit-after-training-20260927/BRIEF.md`): one statement patched in `distributor-wiki@v2`'s own
library, **no retraining** — 37 of 38 control answers on that member's own worlds and questions follow the
new value, cited to the patched line, 0 stale. Closed-book, without the page in front of it, the weights
still answer with the old value 1 of 40 times — not zero: the member learned the *route* well enough to
occasionally reproduce what it usually only reads, which bounds rather than removes the risk the split
between content and weights is meant to close.

**Real documents.** `memory/ingest.py` turns a real source (US federal regulations, eCFR) into the library
verbatim — no invented wiki. On a library ingested this way the earlier design's weak point showed first:
the member's trained `<search>` query is memorised from its own training world, so it never opens a page at
all, 0 of 25 **[ran]** REAL0. The runtime answers that without retraining: the question's own full text is
the **first** entry, tried on **every shelf** (`FullText`, BM25 over statements), with a **fallback** to the
runtime's own literal text when a search returns nothing, and a page opened with its statements attached as
`page_text` instead of only its section list — together these take a walk to the supporting page 24/25,
against a reading ceiling of 22 **[ran]** REAL1–REAL2.

**A long page needs a budget of its own, on the edge's own context.** `page_text` opens a page whole; on the Mac's
12,288-token context, 29 CFR 1910.178 read whole (7,389 Gemma tokens) overflowed 4 of 52 live walks **[ran]**
LIVE-library. `Conversation.page_budget` caps it: a page whose text exceeds the budget shows its statements in BM25
order against the question (the same scoring as `FullText`'s entry, §1 above) until the budget is spent, in document
order, then the rest as openable anchors (`id§anchor`) — only the shown statements count as read. Served at **2,500**
tokens by `examples/library/serve.py --page-budget`, fixed offline before any walk ran: at any budget from 1,500 to
3,500 the 8 statements REAL4's oracle walks need on that page stay 8/8.

**A page can instead open small, capped by a count of statements rather than a token budget.** `Conversation.page_top`
(served as `--page-top`, default **8** since the user's 2026-10-02 decision) opens a page over the limit with the
`page_top` statements the question ranks best by the same BM25 scoring, in document order, the rest left as openable
anchors. Fixed offline before any walk: at 8, every statement 113 of 115 oracle walks over three read sets need is
shown (at 5, 108) — the risk named at the same time: the member never opens a section in its own corpus (0 of 315
walks), so a statement the page leaves out is, for it, absent. On a fourth real family ingested verbatim
(`knowledge/hazwaste-regs`, 40 CFR Part 262), `real-none-s0` with `+top8` answers **34/44** against the unchanged
page's **30/44**, paired 6 : 2 ($p = 0.29$) — **PAGE TOP HELPS**, not WORKS: 3 wins are context overflows the smaller
page fits, 3 repair the wrong-statement-on-the-right-page failure this exists for (same-page wrong statements 8 → 6),
the 2 losses keep every needed statement in view, and the walks carry 3.2× less text (241,981 against 778,701
characters) **[ran]** PAGE0.

**Training a corpus under that served form, and measuring the conformance guard's `recover` mode for the first time,
repairs nothing on the same set — FALSIFIED.** The guard (§5.3 of `docs/MEMORY.md`) has two modes: `strict`, the
default, ends a walk the first time it catches a violation — a section number opened as if it were an id, for one —
and `recover` writes the violation inline and lets the walk go on. `real-fmt-s0` (REAL4's corpus walked under
`page_top = 8`, one walk in three reading a `recover`-guard error and continuing, that open kept out of the
span-masked loss) ties `real-none-s0` served `--guard recover` on PAGE0's set, 33/44 against 33/44, paired 1 : 1
($p = 1.0$); the `recover` guard alone, no retraining, is harmless against `strict`, 0 : 0. The instrument error
owned: headroom was checked over the three older read sets under `strict` (9 of 42 misses were format failures
there), not over PAGE0's own `+top8` arm already on disk, which held just 1 format failure in 11 misses — there was
next to nothing on this set for the corpus to repair, and the format-corpus line stops here **[ran]** FMT0.

Training on real pages needed one more fix. A trajectory corpus over real documents of a family the
evaluation never sees, walked through this same runtime, scored 1 of 23 the first time — the loss sat on
the whole walk, and a walk over real pages read whole is ~97 % page tokens, so the LoRA learned to write
regulations instead of answering. **Span-masked loss** — training only the model's own tags and its cited
answer, never the question or a runtime result — fixes it: 18/23 against the untrained base's 9/23 on a
fresh multi-hop set, both seeds **[ran]** REAL3; the same recipe with 27 unanswerable walks added then
teaches refusal, 15/16 (5/6 adjacent, 0 false refusals of 36), at a headline cost that fails the brief's
own bar by one row — a tie, 2 : 3, inside the member's own run-to-run spread; the user's decision
(2026-10-01) reads the refusal as fixed and the cost as noise, and `real-none-s0` is the real-document
member served next **[ran]** REAL4.
The same member, unchanged, walks a third family chosen for the opposite property — dense links, 9.7
per page against the second family's 22 total — at **15/25 (60 %)**, under the 70 % bar, but 7× the
untrained base (13 : 0, $p = 0.00024$) and refusals 5/5; of the lost rows most cite a statement holding
the same number as the one asked, not the wrong page — the strict citation on repeated values, not the
walk, is the open item **[ran]** REAL5.

**The repeated-value fix does not transfer by itself.** Training one-hop choices among statements that
share a value — the shape REAL5's misses looked like from the answer side — left the citation unchanged,
15/25 against 15/25, a tie **[ran]** REAL6: read where it happens, most of the remaining miscitations are
*multi-hop* rows cited at the wrong end of a link (the member cites the page the walk is still on, not the
one the chain ends on), a shape the one-hop corpus never contained. **REAL7 [ran]** trained exactly that
shape — a decoy holding the same number at a link's start, the answer at its end — and it changed
nothing either: on REAL5's twin-free headline, `real-link-s0` ties `real-none-s0` 13/21 (4:4 paired,
$p=1.0$), under the ≥ 15/21 bar, though the value is right more often (22 against 20) — **FALSIFIED**.
Two corpus changes aimed at this citation (REAL6, REAL7) have now changed nothing; by the rule on
counting redesigns this corpus line on the citation stops here — what might move it next is a runtime
check that rejects a citation whose page the walk did not end on, not another corpus.

**Where results are short, the whole-text loss stays.** H5 asked whether the span-masked loss should
become the recipe for every member, not only where tool results are long: trained byte for byte on the
tracker's harness corpus (§10) with the loss restricted to the model's own spans, the member regresses
the dependent turns **0 : 20** against the whole-text loss — even with the tool block put back in front
of both, so the gap is not a block the whole-text loss had memorised; what the whole-text loss carries
instead is the domain's vocabulary, repeated across the requests and results it was also trained on
**[ran]** H5. The recipe is now split by the length of what a member's tools return: span-masked where
it is long (real pages, REAL3, 1/23 → 18/23), whole-text where it is short (the tracker, H5). A live
endpoint for this library — `examples/library/serve.py`, with an OpenClaw driver — ran end to end on the user's
own Mac: **36/52** against REAL4 on vLLM bf16's 38/52, headline and refusals matching exactly, every loss the
edge's own (4 context overflows on a long page opened whole, 3 of OpenClaw's own queued-message envelope reaching
the runtime's first search) **[ran]** LIVE-library. A follow-up run repaired both: `examples/school/gateway.runtime_request`
strips the envelope, and the `page_budget` mechanism above opens the long page instead of overflowing it — 0
overflows, 0 envelopes, **37/52**, paired against the first run 3 : 2 ($p = 1.0$): the edge's own losses measure at
zero and the score does not follow, **NO CHANGE** against vLLM's 38/52; the three wins are exactly the rows the edge
had cost, the one new loss is the budget showing a question's best-matching statement to a question the library
cannot answer **[ran]** LIVE-library2.

**The runtime check on the citation, built and measured: it finds the bad ones and the member cannot repair
them.** `memory.runtime.Conversation.cite_check` (`check_final`) reads only the referee's own record — the ids
shown, the statements opened, each statement's own text — never the answer key: a final line passes iff it is
`Not in my library.` or it cites `[o§a]` where $o$ is a shown id, $(\mathrm{id}(o),a)$ is an opened statement,
and every number the line states is a number that statement holds —
$\text{pass}(\ell)\iff \ell=\texttt{Not in my library.}\;\lor\;\bigl(\ell\text{ cites }[o\S a],\,o\in\text{shown},\,
(\mathrm{id}(o),a)\in\text{opened},\,\mathrm{nums}(\ell)\subseteq\mathrm{nums}(\text{stmt})\bigr)$. A line that
fails is answered once with an error naming why and the walk continues inside the same call budget; a second
failing line stands as it is. On a fresh 52-row set over a third family (40 CFR 112, written blind after the
design froze), the check fired on 6 rows and **converted 0, broken 0** — **FALSIFIED as a hint**: told why its
citation fails, the member does not write a better one (on 3 of 6 it reopened the right page and still failed,
once retreated to a refusal, once repeated the flagged line, once invented a result). What it is, measured: a
detector with no false alarm — every fired line was already not right (6/6), and across this set and
LIVE-library2's offline replay, **15 fires, 0 on a right answer**. Its blind spot is REAL5–REAL7's own: a
statement holding the value asked but not the one the question means, 7 of the 20 remaining misses here
**[ran]** CITE0. Not rerun (the stopping condition): the next use is as a **gate**, not a hint — a line that
fails it is not delivered, the runtime answering that the library could not verify a citation, or forwarding
to the frontier instead.

**The check becomes a gate: an answer the referee cannot verify is not delivered — GATE0 [ran].**
`memory.runtime.Conversation.final_problem` is `citation_problem` applied once to the walk's own final line —
the same function `check_final` uses as a hint, now read without writing anything back. Behind
`examples/library/serve.py --cite-gate` (on by default) a line that fails it never reaches the caller: the
reply becomes `UNVERIFIED` ("The library could not verify an answer to this — its citation does not check
out."), forwarding to a frontier where one is configured; the walk itself is unchanged. One declared change
to the check for this use: a link's opaque id (`5sf`, random per conversation) has its digits removed before
the statement's own numbers are read, so they cannot be mistaken for the statement's — the change can only
make the check fire *more*. Because the gate never touches the walk, replaying CITE0's and REAL3–REAL7's
recorded `+page` arms exactly **is** the gated run: 14 held-out arms, 532 walks with a final line, two
libraries — right answers delivered **275/275** (0 blocked), not-right answerable rows **79/165** (86
blocked, 52.1%), answers to unanswerable questions **0/11** (11 blocked), delivered precision **0.625 →
0.777** — clears the brief's own GATE WORKS bar (≤ 1% right lost, ≥ 15% not-right caught). The honest
reading: "0 right blocked" mostly restates the grader's own definition of `right` (it already requires the
three conditions `citation_problem` also checks before the numbers rule); the measured part is the 52%
catch. By value rather than by row the cost is real: of the 86 blocked rows, 43 held the wrong value and 43
held the right value under a citation that fails — 43 of 347 correct values withheld (12.4%), delivered-value
accuracy rising 78.9% → 85.9% instead of the row-level 0.625 → 0.777. Whether an uncheckable right number is
worth more than a refusal was a product decision for the user: **it ships on by default — the user's
decision, 2026-10-02, accepting the 43-of-347 cost; `--no-cite-gate` turns it off**
**[ran]** GATE0.

---

## 12. Corpora and their gates

**What.** Every training and evaluation case is drawn on its own synthetic **world** — its own customers,
orders, stock, notes, planted text — generated from a seed, so nothing an answer needs can be recalled
from having seen the exact value before. Extending a corpus with a new capability is done **byte for
byte**: the old rows unchanged, new rows appended, so a regression in what already worked cannot hide
inside a rewrite. A **data gate** — a battery of mechanical checks, not a model's opinion — must pass at
zero GPU before any training run is allowed to start.

**How.** `examples/distributor/generate_turns.py::_world(seed)` draws both centres, customers, orders,
docks, stock and a planted instruction fresh per case; `gate(train, evals)` checks, per its own docstring,
"no demo request in either set, no eval request in the corpus, no shared world, every walk is the one
intended, every oracle row passes the demo's own checks" — five clauses (`G1`…`G5`), each one a count that
must be **exactly zero**, `passed = all(v == 0 for k, v in g.items() if k.startswith("G"))`. The
extensions are literal byte-for-byte layers on top of one another: `train_out.jsonl` **is** `train.jsonl`
plus 70 `OUT OF SCOPE` turns (§6); `train_harness.jsonl` **is** `train_out.jsonl` plus 627 harness rows
(§10). `generate_turns.py --out-turns`'s own gate (`gate_out.json`, on disk in this repository) reads:

```json
{
 "O1_demo_request_in_sets": 0,
 "O2_eval_wording_in_corpus": 0,
 "O3_shared_world": 0,
 "O4_does_not_abstain": 0,
 "train_out": 70,
 "eval_out": 20,
 "egress": {"frontier": 48, "person": 22},
 "passed": true
}
```

The wiki corpus (`training/wiki/corpus.py::gate`) and the nursing walk generator
(`training/nursing/generate_walks.py`) apply the same discipline over the library's own constraint:
**0** slot values ever appear inside a statement's text, **0** evaluated walks leak into the training
corpus, **0** rows the runtime does not reproduce byte for byte in `strict` mode — each clause backed by a
test that can fail it (`tests/test_wiki.py`, `M7-W4`).

**Why.** F2 of the memory's own design rules (`docs/KNOWLEDGE-TRAJECTORIES.md` §2): "fixed knowledge in a
training corpus is memorised, and then it prices nothing" — a control with no lookup tool scored 27/30
over fourteen values because 600 examples memorise 14 numbers **[ran]** P15/P21. A corpus that draws fresh
values per world is the only way an evaluation number can be about *navigating*, not about *recall*. And a
gate that runs before training, at zero GPU, is what makes "the corpus does not leak its own evaluation"
a fact checked by code, not a claim made in a brief.

**Evidence.** **[ran]** every corpus cited in this document — M9's 700 turns, M10's +70, H1's +627, W9's
generated worlds, W4's 600 nursing walks — carries a `gate.json` (or `gate_out.json`, `gate_harness.json`)
on disk, in the run that trained on it, checked before the training run started.

---

## 13. Members and the release gate

**What.** A member does not become a released expert by scoring well once. It has to hold its recorded
score when re-served, tie a fresh training from the same corpus, beat its own bare base, and not lose to
the frontier — four checks, each an exact statistical test on the *same cases*, before a manifest is
written that any later run can be checked against.

**How.** The identity gate, `G1` (`training/harness/verify_substrate.py::identity`, also `C18` in
`docs/SUBSTRATE-GATE.md`), sends one prompt to the base and to the member and requires the served text to
**differ** on at least 2 of 3 probes — because vLLM can load a LoRA, log that it loaded it, and still serve
the base's own text byte-identical **[ran]** P33, and the log line is not the verdict, the served text is.
Every comparison after `G1` is the same **exact two-sided sign test on discordant pairs**
(`training/harness/bar.py::sign_test`, `docs/FOUNDATIONS.md` §9.2):

```math
p = \min\Big(1,\ 2\,\Pr\big[\mathrm{Bin}(n_d,\tfrac12) \ge \max(u,\, n_d-u)\big]\Big)
```

over the $n_d$ cases where two arms disagree, $u$ of them favouring one arm — ties carry no information and
are excluded, which is what makes it the *paired* test rather than a comparison of two raw scores.
`training/harness/release_gate.py::pair` runs it twice for **reproducibility**: re-served against the
recorded run, and re-trained-from-the-same-corpus against re-served — both must tie. `training/harness/region_release.py`
runs it three times for a **region**, on the same 90 cases: the new member against its own recorded run
(must not lose), against the bare base (must win, or the corpus bought nothing), and against the frontier
(must not lose). The manifest that comes out, `releases/<name>@v<n>.json`, records the base, the recipe,
the corpus's sha256, the adapter's sha256, the served prompt's hash, and every paired score — so re-serving
or re-training from it can be checked against the same file later.

**Why.** Two measurements taught the two halves of this rule. `G1`'s threshold is 2 of 3, not 1 of 1,
because at temperature 0 a short prompt can coincide between base and member without the delta being
absent — a false `NOT APPLIED` costs a whole session, and P55's own gate saw 6 of 8 probes differ on a real
adapter, well clear of coincidence. And the reproducibility pair exists because a training chain that
silently gets *better* between two identical runs is exactly as unreproducible as one that gets worse — an
improvement is reported, not welcomed uncritically.

**Evidence.** **[ran] P57** (`results/P57-release-20260917/BRIEF.md`): `email-full@v1` re-served and
re-trained both tie the recorded run, 471/475, 471/475, 472/475 (0 and 1 discordant). **[ran] P64**:
`desk-commitment@v1`, a second member on the same inbox, ties its own recorded run at 0 discordant and
beats the base 202 : 0. Released members on record: `email-full@v3`, `desk-commitment@v3`,
`distributor-wiki@v2` (`training/harness/family.py`). **Not every member measured in this document is a
formal release** — `distributor-staff-s0`, `out-s0` and `wf-s0` have **no release file**; the live and H1
runs are read as arms, not as passes through this gate.

---

## 14. The router

**What.** Which member's distribution a request falls in, or none — decided before the request reaches a
model, by a table of measured regions, not by the model's own opinion of what it can do.

**How.** **Since 2026-10-02 the proxy's default is a factored router** (`openai_proxy --router factored`,
`training/harness/factored_router.py`): a request is local to a member only if exactly one paragraph of it is not that
member's content and that paragraph is the member's task — and it serves 0 of 600 foreign texts locally against the
dictionary's 294, losing 0 of 480 legitimate requests, **[ran]** ROUTE0
(`results/ROUTE0-factored-router-20261002/BRIEF.md`); a paraphrase of the task leaves by design (0/120 kept local),
and keeping it local costs a trained member accuracy on one compound rule **[ran]** P2a, so the probe that would do it
(ROUTE2) is not built. ~~`route.py`'s default, and the one actually served, is a **keyword dictionary**~~ The keyword
dictionary, now `--router dictionary`, is the one this section's earlier description was written about: each member
declares the words its own corpus's requests use, and a request is routed to a member whose words it
contains. `--auto` reads it; `/v1/models`'s own listing decides what stays local, "better than a hand-kept
list, which drifts the moment an adapter is added" (`docs/SERVING.md`). In `examples/school/gateway.py`,
routing is simpler still: **the token's role is the route** — `Gateway.turn` looks up `self.roles.ROLES[claim.role]`
directly, with no member-selection step at all, because the runtime already knows which agent, and
therefore which role, sent the message. For open-task members, with no single task to factor against, **the router is the
role plus the member's own abstention**, measured in all three organisations (M10, ROUTE1 **[ran]**).

**Why.** A learned router was tried and measured against the dictionary, not assumed better. An n-gram
model of each corpus's own frame is **safer on foreign text** — 0 of 128 served locally against the
dictionary's 59 — but it **loses every legitimate request from a sender its generator never drew**, 120 of
120, because every generated training address happened to end `.com` **[ran] M2**
(`results/M2-corpus-router-20260919/BRIEF.md`). The dictionary's own known cost is on record rather than
hidden: a request that merely *contains* a member's question — "…is this important to merge before
Friday?" — is served by that member, whether or not it should be. Routing by role, in the school and the
distributor, closes half of this problem outright: **[ran] F2** (`results/F2-role-as-route-20260920/BRIEF.md`),
with the role confirmed by the member's own keys, there are never more misroutes than the keys alone give
and nothing is served under a wrong role — a 240-case replay ties at 0.775. What role-based routing does
**not** answer is the half that remains open: *is this request inside the region at all*, for the one
member a role's traffic is served by — the milestone 2 problem, ~~unresolved~~ since answered for fixed-task members by
ROUTE0's factored router, and for open-task members by their own abstention (ROUTE1), one class smaller.

**Evidence.** **[ran] M2**, **[ran] F2**, above. **[ran]** `results/M2b-embed-router-20260919/` and
`results/M2c-needle-router-20260921/`: the embedding arm was measured next; ~~neither learned arm has yet
passed the dictionary it was meant to replace~~ neither whole-request arm passed — **[ran] ROUTE0** is the arm that did,
by factoring the request instead of reading it whole. Milestone 7's radar (§11) is built to share its embedding
space with this router, and does not serve it yet.

---

## 15. Runtimes: server and edge

![Two halves. Left, server: a rented graphics card in a cloud with one thick spine and four thin adapter spines, many users arriving, four adapters in one batch with no contention. Right, edge: a laptop with one user and one thin spine swapped in three milliseconds, llama.cpp at 8 bits, a dashed line to the frontier. Between them, a small bench: MLX, the research bench.](img/runtimes.png)

*Two runtimes: vLLM on a rented card to measure, train and serve many; llama.cpp on your own machine to serve one.*

**What.** Two serving profiles, named explicitly by the user's decision (2026-09-28), for two different
jobs: **`server`** is where every measurement and every training run in this repository happens;
**`edge`** is where a single already-released member is served to a live agent runtime on the machine that
runs it, with no rented card and no tunnel.

**How.** `server` is **vLLM** on a rented Colab card: one resident base, every member's LoRA registered as
its own model name (`--lora-modules name=path`), a per-request `model` field selecting which adapter
answers, hot-loaded in **0.23–0.28 s** without a restart (`/v1/load_lora_adapter`, **[ran]** F0). `edge` is
**llama.cpp** on the user's own machine: the E4B served as a **Q8_0** GGUF — never Q4_0, which flips an
order id inside llama.cpp's own prompt cache and can serve a request against the wrong cached turn
**[ran]** LIVE-distributor — plus one member's LoRA converted once (`llama.cpp/convert_lora_to_gguf.py`)
and hot-swapped on a running server with `POST /lora-adapters`, restoring the base exactly, in **3 ms**
**[ran]** MAC2 — three orders of magnitude under vLLM's own swap, on a machine with no memory to spare for
a second resident model. **MLX**, the Mac's earlier engine, is now a **research bench**, not a serving
engine: its own hot-swap is a pointer move inside Python's own access to the graph, **2.9 µs** **[ran]**
MAC — faster than `edge`'s 3 ms by three more orders of magnitude, but it needs the Python-level access to
the model's internals that a serving engine does not give a client. ~~MLX stays the `edge` engine~~ — that
was MAC2's verdict about *speculative decoding* specifically (§16), and it does not extend to serving a
live request.

**Why.** `server`'s vLLM is where the pair (§16), the release gate (§13) and every accuracy number in this
document were measured — nothing about `edge`'s numbers is assumed to transfer without its own run. `edge`
exists because the reference deployment's second half — the distributor — runs live on the user's own
16 GB Mac, with **no rented card and no tunnel**: `docs/SERVING.md`'s own accounting is explicit that what
`server` serves travels to Colab and what it does not travels to a frontier API — `edge` is the one
arrangement where nothing but the base and the adapter ever leaves the machine.

**vLLM 0.30 also refuses too many stop sequences, not just a dropped one.** `server`'s own OpenAI endpoint
returns HTTP 400 on any request carrying more than four `stop` strings — every turn of a tool surface that
closes more than four distinct tags fails in transit, not in scoring (**[ran]** H2 attempt 1,
`h2_attempt1_void_http400.json`). The fix, `training/harness/accept_rank.py`'s `MAX_STOPS = 4`: past that
many closing tags, the request sends one generic stop, `"</"`, and `close_open_tag` rebuilds the specific
tag from what the text was left inside of once the server stops there — **the same function `edge`'s
llama.cpp needed above**, for the opposite reason (there the server drops the stop string it honoured;
here it refuses to accept more than four of them), and the same fix either way.

**Evidence.** **[ran] C1** (`results/C1-concurrency-20260929/BRIEF.md`, `server`): four members mixed on
one L4 reach **278.6 tok/s** against **269.7 tok/s** for one adapter alone at 16 concurrent sessions
(1.03×, no material contention), **504.3 tok/s** at 32 sessions, p95 time-to-first-token **0.24 s**, 0
errors of 128 requests; throughput scales near-linearly from 1 to 32 sessions and the ceiling sits above
32, not reached. **[ran] MAC2** (`results/MAC2-llamacpp-20260927/BRIEF.md`, `edge`): the E4B GGUF loads,
the 12B's LoRA GGUF acts (6/6), the hot swap restores the base exactly and speculative-decode output is
identical 20/20 — but the E4B+12B pair together runs out of Metal memory in 16 GB. **[ran] LIVE-distributor**
(`server` tunnel first, then `edge` live): 6/6 through the real OpenClaw on the arrangement `docs/SERVING.md`
§"The distributor, live and local" documents step by step.

---

## 16. Speculative decoding

**What.** A small model (the drafter) proposes several tokens at once; a large model (the target) checks
them all in one pass and keeps the prefix it agrees with — free extra tokens whenever the two agree, no
loss of the large model's own output when they do not. Here the drafter is Gemma 4's own built-in MTP head,
and the question this repository asks is what happens to that mechanism once an **expert's LoRA** is
turned on beside it.

**How.** Acceptance is measured, not simulated: at temperature 0 the target is one-hot, so "accept" reduces
to "is the drafted token the target's own argmax" — `training/harness/accept_rank.py` asks the target for
`prompt_logprobs` over the draft it is handed, one prefill, nothing sampled. **What hot-swaps**: the
expert's LoRA on the large model, per request, exactly as §15 describes — vLLM's own load, MLX's pointer
move, llama.cpp's `POST /lora-adapters`. **What does not**: the drafter itself. In vLLM the draft is fixed
at server start-up (`--speculative-config`) and is **one draft for the whole server** — there is no draft
per request and no LoRA support for a drafter at all; the proposal exists as an RFC, not a feature
**[read]**.

**Why — the five readings, side by side.** **F0 [ran]:** with a domain expert's LoRA turned on, position-0
acceptance of the *drafter's* own guesses falls from 0.98 to 0.58, and the speed-up from 2.73× to 1.74× —
the drafter was never trained on this expert's answers, so it guesses worse on their own ground. **C0
[ran]** (`results/C0-aligned-draft-20260927/BRIEF.md`, A100 bf16): Gemma's own MTP drafter, with the expert
LoRA on, **recovers** to **1.92× on the domain** (α 0.34) and **2.40× general**, against **2.80×/2.60× on
the base** — better than F0, still below the base's own speed. The aligned alternative — a merged, E4B-sized
draft purpose-built for this expert (strategy C) — **did not run this round**: it OOMs beside the 12B on an
L4, vLLM's online FP8 fails on that GPU's compute capability, bitsandbytes is not an accepted drafter
quantization, and an H100 was refused on quota — parked, not falsified. **C0-upper [ran]** (`results/C0-upper-e4b-20260927/BRIEF.md`):
does confining the expert's LoRA to the decoder's upper half help the drafter, since MTP reads mostly from
near the top of the stack? No — α on the domain moves base 0.82 → full-depth LoRA 0.44 → upper-half LoRA
0.43 ($\rho = -0.02$, read as none): the upper-half adapter still touches exactly the layers MTP reads from,
so almost nothing changes from the drafter's point of view. **F0c [ran]** (`results/F0c-identity-bf16-20261003/BRIEF.md`,
one A100, bf16, `VLLM_BATCH_INVARIANT=1`) answers the question F0 and F0b left open — whether the text spec
decode writes is the same text plain decoding would: the plain-vs-plain control is identical in every set
(16/16, 8/8, 16/16, 8/8), so the engine is deterministic here, and MTP matches it up to every point a served
walk reads to — 16/16 on the LoRA's own domain up to a closing tag this tool-less spike decodes past (a
served walk stops there), 1.98×, and 8/8 on LoRA/general; base/general still flips on synonym near-ties
(5/8), a verification-shape artefact of scoring several positions in one forward, not a fault in the
acceptance rule. **E6 [ran]** (`results/E6-upper-layers-20260927/BRIEF.md`)
reads the *same* layer restriction for a different purpose and finds a real result there instead: training
the school member's LoRA only on layers 21–41 of 42 costs nothing against the full-depth member (70/70
held-out, 15/15 demo, 0 lost), and the KV cache of the 21 untouched layers below comes back **bit-identical
to the base model's own** — the precondition a server would need to compute a shared lower KV once and let
several experts' requests reuse it, still not built, with the caveat that the E4B already caches 24 of its
42 layers on its own architecture, a boundary this LoRA's split does not line up with. **MAC2 [ran]**
(`results/MAC2-llamacpp-20260927/BRIEF.md`, the Mac's `edge` engine): the LoRA hot-swap and the spec-decode
output both work (20/20 identical), but Gemma's MTP **slows** the 12B on `edge` rather than helping it —
**0.52×** with the expert LoRA on its own domain, 0.66–0.87× otherwise — and the E4B+12B pair does not fit
together in 16 GB at all, which is why `edge` (§15) serves one member, not the pair.

**Evidence.** All five runs above are **[ran]**; none is simulated. The honest summary, stated once rather
than per run: a layer-restricted LoRA is a genuine lever for **serving many experts cheaply** (§16's E6)
and a genuine dead end for **aligning a drafter to one expert** (C0-upper) — the same knob, two different
mechanisms, and only one of them moved.

---

## 17. The measurement discipline

**What.** Every run in this document, and every number cited from it, was decided **before** it ran: what
is measured, why, on which model, and what result would falsify the hypothesis — written into a
`BRIEF.md` and read from the file it produces, never from an exit code or a remembered impression.

**How.** A run's brief states its arms, its verdict function, and its **stopping condition** before any
GPU time is spent; the verdict is computed by code (`session_arm.reading`, `staff_arm.abstain_verdict`,
`h1_reading`, …) and written to a `.json` file alongside the raw records, so the reading can be re-derived
by anyone, later, from the same file. Every claim in this repository, including every one in this
document, carries **[read]** (from a paper, a config, or source, cited) or **[ran]** (observed by
executing something here, the run named) — never asserted bare. **VOID** is a first-class outcome, not a
failure to hide: a run whose first-turn accuracy falls under 90% in *any* arm, or whose identity gate (§13)
does not apply the member, is read as telling nothing about the member, and is reported that way rather
than scored anyway.

**Why — and the rule that governs what happens when the instrument itself is wrong.** An instrument's
design error is **recorded, not quietly fixed and re-run as if it had always been right** — because
silently correcting the gate after seeing the result it produced is exactly how a result gets chosen
rather than found. **H1 (§10) is the freshest example.** Its own pre-registered rule — "first turns ≥ 90%
in every arm, or the whole run is VOID" — was written to catch a rendering that breaks a member, and it
did something its author had not anticipated: `harness-noblock`'s own failure mode (0 of 60 first turns,
because the member was never trained without its tool block) voided the *other two arms'* reading as well,
even though `history` and `harness` both scored 60/60 on exactly the same condition. The fix is not to
edit `h1_reading` and rerun it against the same data — that would be tuning the gate to the answer it
already produced. Instead: the error is written into the brief itself, the run is read **per arm** with the
unmodified code, and the two readings that result — `harness` **PASSED**, `harness-noblock` **FALSIFIED** —
are both stated, with the choice of which reading stands over the whole run made explicitly by the user
(2026-09-29: the per-arm reading stands, the as-written VOID kept as the instrument-error record), not
decided by whoever writes the document next.

**H2 (§10) found the boundary of that same fix.** Reading VOID per arm, rather than across all arms, is
what H1's fix was — and it worked for `harness` against `harness-noblock`. But applied without exception it
voided `base-history`, an *untrained* baseline whose whole purpose is to fail: its low first-turn score is
the headroom `harness` is measured against, not a broken rendering. **The rule the instrument needs is
narrower than the one it was given: a per-arm first-turns VOID applies to trained members, not to an
untrained baseline whose failure IS the headroom.** The result is recorded as FALSIFIED-as-written, with
the descriptive pairing stated beside it, exactly as H1's VOID was recorded beside its per-arm reading — the
gate was not edited after seeing the result. **The user's decision (2026-09-29), as for H1: reading 1** —
the readable conditions are H2's verdict, `harness` PASSED — with FALSIFIED-as-written kept on record
alongside its two instrument errors, not superseded by it.

**A check that can fail while the capability works is measuring phrasing, not the mechanism.** H2's QA
misses include ten cases that read the whole `definition-of-done` page rather than citing its `#tests`
anchor specifically — the statement the question asked about is inside what the member read, so a check
for the anchor fails on exactly the cases where the underlying capability (find the right fact) succeeded.
The miss is recorded, not loosened into a pass, and not used to claim the capability is missing either.

**H3 (§10) fixed the anchor check and priced a scorer that still does not carry the verdict.** `turn_right_h3`
scores a page read as right when the returned text contains the cited statement, closing the previous
paragraph's gap; applied to H2's own records it changes no dependent count, so the fix did not move a
number it was not meant to move. A separate, informal "anchor-by-result" scorer — credit any turn whose
result *contains* the fact, whichever tool produced it — was tried beside it and credits 9 of `tr-s0`'s
independent turns and 0 of `tr-s1`'s: it rewards a member for reading more than it was asked, not for using
the workflow correctly, so it is reported and not used to decide H3a. The per-arm VOID rule (§10) applied
cleanly here — every trained arm (`s0-harness`, `s1-harness`, `s1-noblock`) cleared 90% of first turns, so
no instrument error recurred on this run.

**Evidence.** This is not a claim that needs a run of its own — it is the discipline every run cited
elsewhere in this document was already held to: P58's malformed-call fix, P47's rule that a verdict is read
from a file and never from an exit code (`docs/SUBSTRATE-GATE.md`), M10's headroom check on `staff-s0`
before crediting `out-s0`'s abstention, H1's own recorded instrument error, and H2's narrower fix to the
same rule, above, are five instances of the same discipline inside this repository, not five different
rules.
