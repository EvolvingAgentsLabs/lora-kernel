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
