# Serving the pool to an agent runtime

> **The system this serves is described in [`ARCHITECTURE.md`](ARCHITECTURE.md); what each
> number here rests on is in [`RECORD.md`](RECORD.md).**

This is what an agent — OpenClaw, Hermes, anything speaking OpenAI — talks to. Every
piece of it was measured before it was assembled, and the one piece that was not is
named at the bottom rather than left to be discovered.

## The shape

    agent  --(OpenAI, tools=[…], tool_calls)-->  proxy  --(tags)-->  vLLM + adapters

Two processes. vLLM holds one resident base with the adapters registered as model
names; the proxy translates in both directions and forwards everything else
untouched.

## Running it

    # 1. the pool
    vllm serve Qwen/Qwen2.5-3B-Instruct --enable-lora --max-lora-rank 16 \
        --max-loras 2 --dtype bfloat16 \
        --lora-modules kernel=adapters/kernel-mt domain=adapters/domain-mt

    # 2. the translation
    python3 -m training.harness.openai_proxy --upstream http://127.0.0.1:8000 --port 8001

Point the agent at `http://127.0.0.1:8001/v1` and set `model` to `kernel` or
`domain`. `/v1/models` lists them.

## The edge profile: llama.cpp on your own machine, beside `server`

![Two halves. Left, server: a rented graphics card in a cloud with one thick spine and four thin adapter spines, many users arriving, four adapters in one batch with no contention. Right, edge: a laptop with one user and one thin spine swapped in three milliseconds, llama.cpp at 8 bits, a dashed line to the frontier. Between them, a small bench: MLX, the research bench.](img/runtimes.png)

*Two runtimes: vLLM on a rented card to measure, train and serve many; llama.cpp on your own machine to serve one.*

Everything above is the **`server`** profile: vLLM on Colab, and every measurement and training run
in this repository goes through it. **`edge`** is a second profile, decided 2026-09-28, for serving
one already-released member to a live agent runtime on the machine that runs it — no rented card,
no tunnel **[ran]** `results/MAC2-llamacpp-20260927/`, `results/LIVE-distributor-openclaw-20260928/`.
~~MLX stays the `edge` engine~~ — that verdict (2026-09-27) was about speculative decoding only; MLX
stays a research bench, for the Python access it gives to the graph (pointer hot-swap 2.9 µs), not
the thing that answers a live request. The engine that does that on the user's Mac is **llama.cpp**.

    # once per member: its LoRA to GGUF
    python llama.cpp/convert_lora_to_gguf.py --base <gemma-4-E4B-it HF snapshot> --outtype f16 \
        --outfile lora-distributor-staff-out-s0-f16.gguf adapters/distributor-staff-out-s0
    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-distributor-staff-out-s0-f16.gguf \
        --port 8792 -c 8192 -ngl 99

**Use the E4B as Q8_0, never Q4_0.** Q4_0 is not merely a smaller file: it flips an order id inside
llama.cpp's own prompt cache **[ran]** LIVE-distributor, so a live request can be served against the
wrong cached turn. `edge` means Q8_0 until that is fixed upstream.

The adapter's strength is a per-request field on the completion call (`"lora": [{"id": 0, "scale":
1.0}]`), and the adapter itself hot-swaps without restarting the server: `POST /lora-adapters` on a
running instance swaps in a different member's GGUF and restores the base exactly, in **3 ms**
**[ran]** MAC2 — three orders of magnitude under vLLM's own 0.25 s swap, on a machine with no memory
to spare for a second resident model.

**llama.cpp drops the stop string** — a completion did not stop at the member's own closing tag the
way vLLM's does, and a live turn ran on past it inventing text; the fix is client-side, not a flag
(`accept_rank.close_open_tag`) **[ran]** LIVE-distributor. Anyone reusing `edge` needs that same
patch, not just the same command line.

**vLLM has the opposite failure at the same seam: it refuses too many stop sequences outright.** A tool
surface that closes more than four distinct tags gets every request rejected with HTTP 400 on vLLM 0.30's
OpenAI endpoint — a transport error, not a scoring one, and it voided the first attempt at H2 wholesale
**[ran]** `h2_attempt1_void_http400.json`. The fix, `training/harness/accept_rank.py`'s `MAX_STOPS = 4`:
past that many closing tags the request sends one generic stop, `"</"`, and the same `close_open_tag`
above rebuilds the specific tag from what the text was left inside of. One function, both engines, for
opposite reasons.

## The library endpoint: the real-document member as an OpenAI-compatible server

`examples/library/serve.py` serves `real-none-s0` — the member accepted after REAL4
([`ARCHITECTURE.md`](ARCHITECTURE.md) §4) — the way an agent runtime would actually talk to it: one process, one
library, REAL4's own runtime (the question's full text as the first search on every shelf, a fallback to every
shelf, pages opened with their statements). It is the `edge` profile above plus the memory's runtime in front of it,
not a third thing.

    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-real-none-s0-f16.gguf --port 8793 -c 12288 -b 512 -ub 512 -ngl 99
    python -m examples.library.serve --library knowledge/logistics-regs --upstream http://127.0.0.1:8793 --port 8766

**On a 16 GB Mac, size the context down and clear the GPU first.** 16,384 is what REAL4's own questions were
measured against on vLLM, but a 16 GB machine does not have 16,384 tokens of context to spare *and* the rest of the
stack: use **`-c 12288 -b 512 -ub 512`**, and make sure nothing else is holding GPU memory before starting
`llama-server` — the first live attempt here ran out of memory for exactly this reason, another session's
`llama-server` already holding ~8 GB; the second attempt, at 12,288, ran end to end and **PASSED** (36/52 against
vLLM's 38/52, headline and refusals exact) — the four losses it costs are walks that overflow 12,288 tokens after
opening a long page whole, read where they happen, not as the member's ([`LIVE-library`](../results/LIVE-library-20261001/BRIEF.md)).
Q8_0, not Q4_0, for the same reason as every other member on `edge` — the prompt-cache order-id flip above.

**A long page is the other half of that same context limit, and it now has its own budget.** `--page-budget`
(default **2,500** Gemma tokens) caps what a page opens with: over the budget, `memory.runtime.Conversation`
shows the page's own statements in BM25 order against the question until the budget is spent, in document order,
then lists the rest as openable anchors (`id§anchor`) — only the shown statements count as read. On this library
only 29 CFR 1910.178 (7,389 tokens whole) exceeds it, down to 2,452–2,558 tokens after. Chosen offline, before any
walk: at any budget from 1,500 to 3,500 the 8 statements REAL4's oracle walks need on that page stay 8/8
([`LIVE-library2`](../results/LIVE-library2-20261002/BRIEF.md)).

**The egress rule is the same as the gateway's (§6 of [`OPENCLAW.md`](OPENCLAW.md), [`MECHANISMS.md`](MECHANISMS.md)
§6): closed by default.** `serve.py` installs `examples.common.egress` before anything else loads, allowed only to
the `llama-server` upstream and loopback, with `HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE` set so loading the tokenizer
never reaches the model hub — the same hardening the gateway got from #310, applied to this second front door.

**Pointing OpenClaw at it is a provider, not a patched agent.** The endpoint writes its own OpenClaw patch on start
(`--openclaw-patch`, default `~/.config/lora-kernel/openclaw/library-reader.json5`):

    {
      models: { providers: { library: { baseUrl: "http://127.0.0.1:{port}/v1", api: "openai-completions",
        auth: "api-key", apiKey: "local", models: [ { id: "auto", name: "regulations library — real-none-s0" } ] } } },
      agents: { defaults: { model: "library/auto" } }
    }

One request in, one walk out: the reply carries the answer with its citation rendered as `[page title §anchor]`, or
`Not in my library.`, and the response's own `x_walk` field carries the whole walk — ids shown, statements opened —
so a driver can grade the citation exactly as the measurement did, rather than re-parsing the reply text.
`examples/library/live_library.py` is that driver: it sends REAL4's 52 questions through `openclaw agent --local`,
one fresh session each, and grades the endpoint's own walk record with REAL4's grader. **Built, tested offline, and
now run end to end on the real server: PASSED** — 36/52 against REAL4 on vLLM bf16's 38/52 (headline 16/23 and
refusals 15/16 match exactly, one-hop 5/13), 22.5 minutes, 2026-10-01 ([`LIVE-library`](../results/LIVE-library-20261001/BRIEF.md))
— see [`OPENCLAW.md`](OPENCLAW.md) for how it is pointed at a running OpenClaw instance.

**A follow-up run repaired both edge losses and read NO CHANGE.** OpenClaw also re-sends a slow question wrapped in
its own queued-message envelope, which the runtime's first search then ran on; `examples/school/gateway.runtime_request`
now strips it before the runtime reads the question. With that and the page budget above, the same 52 questions:
**37/52** — headline 16/23, refusals 14/16, one-hop 7/13 — against this run's 36/52 and REAL4 on vLLM's 38/52; **0**
context overflows (4 before), **0** envelopes (3 before), paired against this run **3 : 2** ($p = 1.0$). Verdict as
written: **NO CHANGE** — 0 overflows but 37 < 38, not REGRESSED
([`LIVE-library2`](../results/LIVE-library2-20261002/BRIEF.md)).

**The endpoint always answers, even when the walk itself raises.** A context overflow or a dead upstream used
to close the socket with no response; OpenClaw read that as a transport failure and re-sent the turn wrapped
in its own `[Queued user message from a previous active turn …]` envelope — up to five times, none of them
logged. `serve.py`'s handler now catches the exception and answers 200 with `NO_ANSWER`, the error logged
beside the walk: one request in, one answer out, whichever way the walk ends.

**`--cite-gate`: the citation check as a gate, on by default.** `memory.runtime.Conversation.final_problem`
is the same check CITE0 measured as a hint (`citation_problem`, reading only the referee's own record: the
ids shown, the statements opened, their own text), applied once to the walk's final line; behind
`--cite-gate` a line that fails it is not delivered — the reply becomes `UNVERIFIED` ("The library could not
verify an answer to this — its citation does not check out.") instead of the walk's own text, forwarding to a
configured frontier where one exists. The walk itself does not change; the gate reads the same record
`cite_check` already wrote. Replayed exactly over 14 held-out `+page` arms of REAL3–REAL7 (532 walks, two
libraries): 0 of 275 right answers blocked, 86 of 165 not-right answers blocked (52.1%), 0 of 11 answers to
unanswerable questions delivered, precision 0.625 → 0.777 — GATE WORKS by the brief's own bar. The honest
remainder: of the 86 blocked, 43 held the right value under a citation that fails (43 of 347 correct values
withheld, 12.4%) — **it ships on by default, the user's decision of 2026-10-02 accepting that cost;
`--no-cite-gate` turns it off** ([`GATE0`](../results/GATE0-cite-gate-20261002/BRIEF.md)).

## What live serving costs: order beats size, and two adapters are not twice the cost

Two findings from the same run price the engine itself, on `server` and `edge` alike, because both
serve through a prefix cache and a multi-adapter batch.

**A tool block placed after the request is never a shared prefix.** A member's corpus puts the
request first and the (large) tool surface after it — the shape the corpus taught, not an accident —
so no two requests share that block as a prefix even with caching on. Serving OpenClaw's real 54-tool
block (7,205 Gemma tokens) this way, after the request, on the school member (E4B, vLLM 0.30) takes
time to first token from 0.10 s to 1.70 s (16.8×) and throughput at 8 in flight from 132 to 108
tok/s, beside accuracy falling 70/70 → 39/70 **[ran]** `results/E5-engine-baseline-20260928/`. Where
the whole prefix recurred instead, the same block cost nothing (0.09–0.11 s) — **the cache is beaten
by the order the corpus put things in, not by the block's size.**

~~**Two LoRAs in one batch keep 0.88 of one's own throughput.** A burst of 16 requests split across two
adapters served together loses 12% against serving the same 16 apart — contention, not a wall, and
worth pricing before sizing one server for more than one member at a time **[ran]** E5.~~

**Superseded — C1 [ran] 2026-09-29: under steady load, four members mixed cost no throughput against
one.** E5's 0.88 was one burst of 16 requests; C1 (`training/harness/load_test.py`, one L4, vLLM 0.30,
`google/gemma-4-E4B-it` bf16, four members: `school-s0`, `upper-s0`, `staff-s0`, `out-s0`) ran the same
question as a curve. At 16 concurrent sessions, four adapters mixed deliver **278.6 tok/s** against
**269.7 tok/s** for one adapter alone — a ratio of **1.03**, against a contention bar of 0.8. At 32
sessions, four adapters reach **504.3 tok/s** at **p95 time-to-first-token 0.24 s** and **0 errors of
128** requests. Throughput scales near-linearly with sessions (22.7 → 135 → 270 → 500 tok/s for 1 → 8 →
16 → 32), and the ceiling sits above 32 sessions, not reached
[`results/C1-concurrency-20260929/BRIEF.md`](../results/C1-concurrency-20260929/BRIEF.md). **Not
measured:** more than four adapters, sessions past 32, the gateway's own overhead, longer generations.

## The gateway's serving options: `history=`, `memory=`, `workflows=`, `tool_block=`

`examples/school/gateway.py`'s `Gateway` is the pool's second front door — one organisation per process,
walked through end to end in [`OPENCLAW.md`](OPENCLAW.md) §6. Three organisations are registered in
`ORGS` and selected with `--org`: `school`, `distributor`, and, since 2026-09-29, `tracker`
(`examples/tracker`, a Jira + Confluence-like team tool — see `docs/MECHANISMS.md` §9). Four constructor
options decide what a turn reads, beside the role's own prompt and tools:

| option | default | what it does |
|---|---|---|
| `history=True` | `False` | renders every earlier request and reply before the current one — the naive way to carry a multi-turn conversation, `out-s0`'s `history` arm in MT0 below |
| `memory=<OpMemory>` | `None` | turns on the workflow harness (`examples/common/opmemory.py`): a turn reads one context line — the role's workflow state and the key **names** of its session and organisation caches, never their values — and the member fetches (`<get>`) or stores (`<put>`) a value only in the step that needs it |
| `workflows={role: Workflow}` | `{}` | maps a role to its declared state machine (`examples/<org>/workflows/*.toml`); the gateway advances the state from the calls the tool layer **ran**, never from the model |
| `tool_block=False` | `True` | drops the rendered tool surface from the turn — the member trusted to know its tools from its corpus alone (H1's `harness-noblock` arm, **0/60**: its corpus always had the block, so removing it at test time left it calling nothing) |

From the command line (2026-09-30): `--memory` turns on the operational memory with the organisation's declared workflows (`examples/<org>/workflows/*.toml`), `--no-tool-block` sets `tool_block=False`, `--max-calls N` bounds a turn's tool calls; `--state-dir` persists what waits for a person (approvals, handoffs) and egress is closed to the configured hosts unless `--open-egress` (`docs/MECHANISMS.md` §5, §6). The memory's session is the client's `X-Session-Id` header or the request's `user` field, else one per token (`tests/test_tracker.py`: two sessions of one user do not share a key). The tracker's member is served that way live in [`results/LIVE-tracker-openclaw-20260930/BRIEF.md`](../results/LIVE-tracker-openclaw-20260930/BRIEF.md) — **[ran] PASSED, 14/14 turns, dependent 8/8** on the user's Mac. On `edge` the many-tags stop (`"</"`) is dropped too, like any stop string: `accept_rank.completion` rebuilds the tag on either server (LIVE-tracker attempt 1, void).

`history=True` and `memory=…` answer the same problem two different ways and are not meant to run
together: history is the baseline the workflow harness is measured against, not a second copy of it.
H1 (`results/H1-workflow-harness-20260929/`) scored both against it on vLLM (one L4): `harness` (the
block kept) reached 53/54 dependent turns against history's 43/54; `harness-noblock` collapsed, for the
reason above. Read per arm, `harness` PASSED and `harness-noblock` FALSIFIED, but the run's own gate
voids it as written — the user's decision (2026-09-29): the per-arm reading stands, the as-written VOID kept
as the record of that instrument error. A second run, **H2** on the `tracker` organisation above, found the
same rule mis-applied a second way — voiding an untrained baseline rather than a broken arm — and reads
FALSIFIED as written, kept on record with that and the anchor-check instrument error. **The user's
decision (2026-09-29), as for H1: reading 1** — the readable conditions are H2's verdict, `harness`
**PASSED** (146/160, flat, descriptively 142:0). `harness-noblock` (80/160) is a corpus bug, not partial
learning — its block-less third shared a modulus (`% 3`) with the role rotation, so all block-less rows
were QA's. **H3 [ran], both bars PASSED**: `tr-s1`, trained on a second corpus (wording widened per turn
in every role, an even block-less third of each role), beats `tr-s0` 158/160 against 147/160 on a fresh
held-out suite (paired 11:0, $p = 0.00098$, flat), and without the tool block holds 156/160 across every
role at about a third of the prompt tokens — the compact-context member now works
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).
**The harness has since run live through OpenClaw**: `tr-s1` block-less, on `edge` (llama.cpp on the user's own
Mac), over three sessions (lead, developer, QA) — 14 of 14 turns, dependent 8 of 8
([`LIVE-tracker`](../results/LIVE-tracker-openclaw-20260930/BRIEF.md)); see [`OPENCLAW.md`](OPENCLAW.md) for the
multi-turn story and `docs/review/harness-workflow-kv.md` §§8–9 for the full results and the chosen readings.

## The base has to be one vLLM actually applies adapters to — check, do not assume

**vLLM can accept a LoRA, log that it loaded it, and serve the base.** No error, no
warning. On `Qwen/Qwen3.5-4B` the server prints

    Loaded new LoRA adapter: name 'tiny', path 'adapters/tiny-subject'

and then returns text **byte-identical to the base** for every request **[ran]**
`results/P33-lora-matrix-20260914/`. The adapter in that run was real — trained on
that base, `lora_B` moved, and it changed the model's output in process. A
deployment reading that log line would believe it was serving an expert.

**So the first thing to run against a new base is the identity gate**, before any
accuracy number is collected:

    python3 -m training.harness.serve_openai --base <model> \
        --adapter tiny=<adapter> --gate-only --out gate.json

It sends one prompt to the base and to each adapter and compares. Read
`gate_verdict` **from the file** — the process exits 0 on a clean run whose gate said
*not applied*, so a return code is not the answer.

| verdict | meaning |
|---|---|
| `applied` | the served text differs from the base; go on |
| `not applied: served text is identical to the base` | **stop**; every number after this measures the base |
| `inconclusive: the adapter was refused out loud` | a shape or rank mismatch, not a silent no-op |

**The families this repository has checked:**

| base | adapters applied by vLLM 0.29.0 |
|---|---|
| `Qwen/Qwen2.5-3B-Instruct` | **yes** — the pool runs on it |
| `Qwen/Qwen3.5-4B` | **yes, once the adapter's tensors are named for the class vLLM serves** — as PEFT writes them through `AutoModelForCausalLM`, **no, silently** |

**Why the same base gives both answers — D2 [ran] 2026-09-19**,
`results/D2-rekey-20260918/`. vLLM serves `Qwen3.5-4B` as
`Qwen3_5ForConditionalGeneration` and activates adapter weights by
`language_model.model.layers.N…`; an adapter trained through the text-only class names them
`model.layers.N…`. Loading validates only the last component of each name — hence the
*Loaded* line — and activation, finding no module by that full name, resets the slot behind
a debug message. The same weights with 496 tensors renamed, not retrained, come back
`applied`:

    python3 -m training.harness.rekey adapters/<as-trained> adapters/<renamed>

Read for five days as a serving-stack limit, it was a naming mismatch. The lesson the gate
teaches is unchanged and sharper: **the log line is not the verdict — the served text is.**

## Routing what the pool cannot do — the end-to-end that runs today

**This is the configuration to actually use.** The pool serves what it is measured to
be good at; everything else is forwarded to a frontier model on your own account.

    # 1. the pool
    vllm serve Qwen/Qwen2.5-3B-Instruct --enable-lora --max-lora-rank 16 \
        --max-loras 2 --dtype bfloat16 \
        --lora-modules email-full=adapters/email-full

    # 2. the translation, with a route out
    export OPENAI_API_KEY=...        # never on the command line: `ps` sees that
    python3 -m training.harness.openai_proxy \
        --upstream http://127.0.0.1:8000 --port 8001 \
        --fallback https://api.openai.com/v1

Point the agent at `http://127.0.0.1:8001/v1`. Ask for **`email-full`** and the local
expert answers; ask for **any other model name** and the request is forwarded.

**What stays is what the pool serves**, read from the upstream's own `/v1/models` —
better than a hand-kept list, which drifts the moment an adapter is added. Override
it with `--local a,b` when you want to be explicit.

**What decides the route today, and what was tried instead [ran] M2 2026-09-19.** `--auto` uses
the keyword dictionary in `route.py`. A model of each member's corpus — the design's router — was
measured as an n-gram model first: on foreign text it is safer (0 of 128 served by a local member
against the dictionary's 59), and it sends out **every** legitimate request whose sender the
generator never drew, 120 of 120. So the dictionary stays the default, and the known cost of that
is on record: a request that merely *contains* a member's question — "…is this important to merge
before Friday?" — is served by that member. The embedding arm is next
([`PLAN.md`](PLAN.md) milestone 2), and it will share its space with each subdomain's knowledge
base (milestone 7): **nothing in this page serves a knowledge base yet.**

**On a 3.x base the thinking channel is off for members.** The proxy sends
`chat_template_kwargs: {"enable_thinking": false}` on every member request, so the served prompt is
an exact prefix of the text the member was trained on; a template without that switch ignores it.

### The number this is worth

| | delivered | leaves the machine |
|---|--:|--:|
| everything local | 0.546 | 0% |
| **the failing region forwarded** | **0.775** | **38%** |

**[ran]** `results/P41-routing-20260915/`. On its own region the local expert beats
the base **8 : 51** on the same cases; the region it fails, it fails at 12/90 and a
frontier answers 66/90. **We pay for the part we measured we cannot do.**

### What leaves, and how you can see it

A forwarded request **leaves your machine**. For synthetic suites that is nothing;
for real mail it is the message. The proxy prints one line per forwarded request:

    [route] OUT -> gpt-5 · 4 messages · 2317 chars · 3 tools

**Shapes, never content** — the same line `openclaw_traffic.py` holds. You can see
what left without the transcript being written into a log, and a test asserts the
content does not survive the announcement.

A fallback configured without a credential **refuses to start**, rather than failing
on the first escalation.

### What this does not do

**It does not decide per case.** The route is by model name, which is the caller's
own choice. Per-case escalation is measured and currently **worse**: both available
rules deliver less than routing by region, because they look for a chain that is
inconsistent and this expert's chains are consistent and wrong **[ran]** P41. That
is an open problem, not a missing feature.

## What is measured, and where

| | result | step |
|---|---|---|
| each adapter is its own model name, and **is applied** | base and adapter answer differently | P26 |
| tags → `tool_calls` | **0 of 38** lines naming a domain; **604/604** round trips | P27 |
| `tools=[…]` → tag surface | costs **0.188** on the oracle's tool values | P27 |
| the arity convention | recovers **55%** of that, refusals **88 → 17** | P28 |
| declaring allowed values (`enum`) | **made it worse** — off by default | P28 |

## What is assembled and not measured

**The multi-turn loop — now exercised, see the worked example below.** An agent sends
back `role: "tool"` results and the proxy folds them into the transcript as
`= value`, where the adapter was trained to read them. **Every measurement before
P30 was a single turn** — P27 arm 3 explicitly so.
`tests/test_proxy.py` shows the translation is lossless and that a result lands on
the line that asked for it; it does not show the adapter continues correctly from
there. **That is a different claim and it has not been bought.**

## What this does not do

- **It does not choose the adapter.** The client's `model` field does, because S3
  measured a router tying a lookup table and there is nothing better to offer yet.
- **It does not stream.** A tag is only a tool call once it is closed, so streaming
  would mean buffering the whole reply and calling it a stream. The proxy refuses
  with that sentence rather than faking it.
- **It adds no domain knowledge.** It names no tool, no argument and no unit; a test
  fails if that ever stops being true.

## Before training anything for a new deployment

    python3 -m training.harness.openai_proxy --upstream … --log traffic.jsonl
    python3 -m training.harness.null_arm --log traffic.jsonl

Two questions, both answered from the traffic itself and neither needing a GPU beyond
the base already being served.

**Is there a region?** The architecture's claim is that a small expert beats a
generalist *inside its region* — S5 closed the withdrawal gap to 0.000 in region, and
the same expert's formulas fall 30/30 to 1/20 outside it. If the traffic is a long
tail there is nothing to specialise in, and the honest recommendation is a
generalist. The instrument says `NO REGION` when the three commonest shapes cover
less than 60% of requests, and it is written so it can say that.

**Can the base hold the protocol?** How often the base model *alone* emits a
well-formed tool call. If it cannot, an adapter over it will not fix that — the next
purchase is a different base, not a training run. And calls naming a tool nobody
offered are counted separately, because P25 measured exactly that failure at 56% of
refusals on an unfamiliar subject.

## Pointing a real agent at it

Two ways, and **the first one is worth doing before the second.**

### 1. Measure the traffic while the agent keeps working

    python3 -m training.harness.openai_proxy \
        --upstream https://api.openai.com --upstream-key "$OPENAI_API_KEY" \
        --passthrough --log traffic.jsonl --api-key "$(openssl rand -hex 16)"

In `--passthrough` nothing is translated: the request goes upstream exactly as it
arrived and the reply comes back untouched. **The agent keeps giving its usual
answers** and the run leaves a log of the shapes it sends. That log is the input the
null arm needs, and it cannot be guessed from a suite.

**Only shapes are recorded** — which tools were offered, how deep the conversation
was, and the reply text. The prompt is not written down: it is the user's, and the
measurement does not need it.

### 2. Serve the pool through a tunnel

    # inside a Colab session
    bash training/harness/tunnel.sh

It brings up vLLM with the adapters, the proxy on `:8001`, and a Cloudflare quick
tunnel, then prints a public base URL and a generated key. Point the agent at
`<url>/v1`.

**The key is not optional and the script will not run without one.** A tunnel turns a
localhost proxy into a public inference endpoint; an open one is somebody else's GPU,
and a guessable URL is not a control. The comparison is constant-time.

**What to expect from the answers.** The pool is a 3B with an adapter that knows
fluid mechanics and a kernel trained on three tools. On general agent work it will be
**bad**, and that is not a bug to report — it is the region question from the section
above, arriving as experience instead of as a number.

### When the agent's credential cannot be proxied

`--passthrough` needs a bearer token the proxy can forward. An OpenClaw talking to
ChatGPT through an OAuth session has none — putting a proxy in the middle would mean
taking the user's credential, and it is not necessary anyway:

    python3 -m training.harness.openclaw_traffic --out traffic.jsonl
    python3 -m training.harness.null_arm --log traffic.jsonl

**OpenClaw already records every run.** This reads its trajectory log and emits the
same lines the null arm consumes — **without the prompt, the assistant's text, or any
tool call's arguments.** The region question is about shapes, and none of them need
the content.

It also refuses to pretend: under fifty runs it says the sample is too small and that
three shapes covering 60% of six runs is not evidence of a region.

## A worked example: one person's morning mail

    python3 -m training.harness.agent_sim \
        --base-url http://127.0.0.1:8001/v1 --model kernel --n 12

`training/email/` is a region shaped like a real one: a narrow task repeated every
day, with an answer that is **mechanically checkable**. A message is important when
at least two of *continues a thread I wrote in*, *addressed to me directly*, *asks
something of me*, *frequent counterpart* hold — and never when it is automated.

**The two decisive facts are not in the listing.** Whether the user wrote in the
thread lives behind `thread_history`; how much real correspondence exists lives
behind `sender_stats`. A rule reading only the listing scores **0.680 against a
majority-class bar of 0.680** on the human messages — it does not beat guessing by a
single case, and a test asserts that rather than trusting it.

`agent_sim` is shaped like a client, not like a test: it speaks only OpenAI — a base
URL, a model name, `tools`, `tool_calls`, `role: "tool"` — so anything it needs that
the protocol does not provide is a gap between this project and a real runtime.

**This is what closed the multi-turn loop**: 24 calls, 0 refused, 0 undecided,
against a stub model through the real proxy. The section above no longer says that
path is unmeasured — but note what it measures. **The plumbing, not the pool.** No
trained adapter has been run on this suite yet.
