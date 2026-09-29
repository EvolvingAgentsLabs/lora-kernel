# Pointing OpenClaw at the pool, step by step

**Everything here was read off the installed CLI and its own config schema**
(OpenClaw 2026.9.4), not guessed. Where a claim is about behaviour rather than
configuration it is marked **[read]** until a run marks it **[ran]**.

## Before anything: this does not touch your working setup

OpenClaw's `--profile <name>` isolates `OPENCLAW_STATE_DIR` and
`OPENCLAW_CONFIG_PATH` under `~/.openclaw-<name>` **[read]** — its own `--help`
says so. Every command below uses `--profile lorakernel`, so your `main` agent,
its accounts and its sessions are untouched and nothing has to be undone.

**Read this before running any of it, not after**: a request the pool does not
serve is **forwarded to whatever you configured as the fallback**, and for real
mail that means the message leaves your machine. The proxy prints one line per
forwarded request naming shapes and never content, so you can see what left —
[`SERVING.md`](SERVING.md).

## 1. The pool has to be somewhere

This machine is a 16 GB arm64 Mac: **it cannot serve vLLM**. So the pool runs on a
rented card and the proxy runs here, which is the arrangement that keeps your
credential on your own machine:

    your Mac                                   Colab
    OpenClaw ──▶ proxy :8001 ──(tunnel)──▶ vLLM :8000 + adapters
                     │
                     └──▶ api.openai.com   (what the pool does not serve)

**The consequence, stated rather than discovered**: what the pool *does* serve
travels to Colab, and what it does not travels to OpenAI. Neither is your machine.

## 2. Start the pool and the proxy

On the rented card, per [`SERVING.md`](SERVING.md); then, here:

    export OPENAI_API_KEY=...          # never on the command line: `ps` sees that
    python3 -m training.harness.openai_proxy \
        --upstream http://127.0.0.1:8000 --port 8001 \
        --prune --member-prompt --auto auto --auto-out gpt-5.6-sol \
        --fallback https://api.openai.com/v1

**`--prune` is what makes §4b worth doing**, and it is explained there. It prints
each member's declared tag surface:

    [prune] email-full: ['thread_history', 'sender_stats', 'message']
    [prune] fluids-full: ['calc', 'lookup', 'convert']
    [prune] domain-mt: no tools — declares none
    [prune] a model not listed above is offered every tool, unpruned

It also prints what stays and what leaves, before serving a single request:

    [proxy] local, never leaves: ['email-full', 'Qwen/Qwen2.5-3B-Instruct']
    [proxy] everything else -> https://api.openai.com/v1 (key from $OPENAI_API_KEY)

**Check that line.** It is the whole privacy contract in two lines, and it is read
from the upstream's own `/v1/models` rather than a list somebody maintained.

## 3. Register the pool as a provider

`models.providers.<name>` takes a `baseUrl`, an `api` adapter and an `auth` style
— all three read from the schema. `openai-completions` is the adapter that speaks
`/v1/chat/completions`.

**`config patch` reads from `--file` or `--stdin`, never a positional argument** —
the first version of this page had it wrong and the CLI said so. Write the patch,
validate it, then apply it:

    cat > /tmp/lorapool.json5 <<'J5'
    {
      models: {
        providers: {
          lorapool: {
            baseUrl: "http://127.0.0.1:8001/v1",
            api: "openai-completions",
            auth: "api-key",
            apiKey: "unused",
            models: [ { id: "email-full", name: "Email triage expert (local QLoRA)" } ]
          }
        }
      }
    }
    J5

    ~/.openclaw/bin/openclaw --profile lorakernel config patch \
        --file /tmp/lorapool.json5 --dry-run     # says which file it would write
    ~/.openclaw/bin/openclaw --profile lorakernel config patch \
        --file /tmp/lorapool.json5

`apiKey` is required by the adapter and ignored by the proxy unless you started it
with `--api-key`. **Start the proxy with one the moment it is reachable from
anything but localhost.**

## 4. Point an agent at it

    printf '{ agents: { defaults: { model: "lorapool/email-full" } } }\n' \
        > /tmp/agentdef.json5
    ~/.openclaw/bin/openclaw --profile lorakernel config patch --file /tmp/agentdef.json5

    ~/.openclaw/bin/openclaw --profile lorakernel models list

**Or name no member at all.** Start the proxy with `--auto auto --auto-out <frontier model>`
and register `auto` as the provider's model: the proxy reads each request's text, serves
it locally when it falls in a region a member is measured to resolve, and forwards it
otherwise — the client does not know the pool. Replayed on P41's traffic it delivers
exactly what routing by region did, 0.775 with no misroute **[ran]** P62; the line it
prints per request names the decision and the shapes, never the content.

## 5. Run one turn and watch both sides

    ~/.openclaw/bin/openclaw --profile lorakernel agent --local \
        -m "Is this important? From: Bruno Costa <bruno.costa@tallgrass.com> \
            Subject: Re: the migration  Preview: Hello, following up here. \
            Answer with one line: IMPORTANT or NOT IMPORTANT."

What a working turn looks like **[ran]** 2026-09-15:

    [model-fetch] response provider=lorapool model=email-full status=200
                  elapsedMs=4009 contentType=text/event-stream
    NOT IMPORTANT
    [agent] run ... ended with stopReason=stop

Two things should happen at once: the agent answers, and the proxy **says nothing**
— because `email-full` is local and nothing left. Ask for a model the pool does not
serve and you get the other line instead:

    [route] OUT -> gpt-5.6-sol · 4 messages · 2317 chars · 3 tools

## 4b. Give the agent the inbox tools — the step that makes the demo mean something

**Without this the demo shows the transport and not the expert.** P43's first turn
made **no tool calls at all**: OpenClaw sends *its own* tools, so `email-full`
answered from the listing alone — which is what the base does, at 0.345 **[ran]**.

OpenClaw speaks MCP, so the three tools the suite scores become tools the agent owns:

    cat > /tmp/inboxmcp.json5 <<'J5'
    {
      mcp: {
        servers: {
          "lora-inbox": {
            enabled: true,
            command: "/path/to/python",
            args: ["-m", "training.mcp.inbox_server", "--seed", "717171", "--n", "150"],
            cwd: "/path/to/lora-kernel"
          }
        }
      }
    }
    J5

    ~/.openclaw/bin/openclaw --profile lorakernel config patch --file /tmp/inboxmcp.json5

**It serves the synthetic inbox on purpose.** `training/email/inbox.generate` draws a
deterministic inbox from a seed; **no real correspondence is read, opened or
forwarded**, and the seed is the suite's own so the demo and the number are about the
same inbox. Pointing it at real mail is a different program with a different review.

### Attaching the server is not enough — the surface has to be pruned

**Offering the three tools does not remove the problem P43 found; it adds three lines
to it.** An agent runtime sends its *whole* toolbox, so the expert sees its own three
tags among dozens it has never met — and two separate things are then wrong with what
it reads:

| | what goes wrong | what it costs, measured |
|---|---|---|
| **volume** | dozens of tag names the weights never saw | P25: on an unknown surface the adapter reaches **27 of 63** — it knows a step needs a lookup and gets the name wrong **[ran]** |
| **renaming** | the three it *does* know arrive as `mcp__lora-inbox__message` | a tag it has never written, so knowing the tool does not help |

`--prune` fixes both, and it does it **without the proxy learning a single tool
name**. Each pool member declares the tags its corpus taught it — the same place its
difficulty band lives, in `contract.py` — and the proxy keeps only the offered tools
that match one, by exact name or by the last segment of a namespaced one
(`mcp__…__`, `.`, `/`, `:`). A call the adapter writes leaves under the name the
agent offered, so the agent can still route it.

**What arrives at the model is then byte-for-byte the block it trained on** —
`tests/test_prune.py` asserts exactly that against the corpus, and asserting it is
what caught the first version alphabetising the three lines into an order the adapter
had never read **[ran]** 2026-09-16.

Two things this deliberately does not do:

- **It does not re-offer what it dropped.** A member that recognises none of the
  offered tools gets none, and the request log says so in `tools_offered` against
  `tools`. Falling back to the full surface would be re-offering the one P25 priced.
- **It does not guess between two servers.** If two offered tools end in the same tag
  the tag is dropped, because calling the wrong one of two tools is worse than
  calling neither.

**Measured, P59 [ran] 2026-09-17**, on the surface OpenClaw actually sends (54 tools,
recorded from one turn): **unpruned, the expert copies tags off the block** — it calls
`agents_list`, `apply_patch`, `ask_user`, `browser` — 225 of 227 calls refused by the
inbox, and inside OpenClaw those would have *executed*. Pruned to its three: 1160 calls,
8 refused. Accuracy 0.664 → 0.729 on human messages, 87 : 64, $p = 0.073$ — a tie at
$n = 475$; the behaviour is not. The block is **~7,956 tokens** unpruned, **~77** pruned.

**And it costs latency, prefix caching or not — E5 [ran] 2026-09-28.** A member's corpus puts the tool block *after*
the request, so no two requests share it as a prefix: on the school member (E4B, vLLM 0.30, cache on) the 54-tool block
(7,205 Gemma tokens) takes the time to first token from **0.10 s to 1.70 s** (16.8×) and throughput at 8 in flight
from 132 to 108 tok/s; accuracy 70/70 → 39/70. Where the whole prefix recurred, the same block cost nothing (0.09–0.11 s),
so it is the order, not the size, that the cache cannot absorb ([`E5`](../results/E5-engine-baseline-20260928/BRIEF.md)).

**So: start the proxy with `--prune`.** It stays a flag so the unpruned arm can be
bought again; it is no longer the default this page recommends against.

### What the live turn found, and why three flags are now the default for a member

**Measured, P63 [ran] 2026-09-18**, 40 live turns from this very set-up: with the inbox
tools offered and pruned, **under OpenClaw's own 37 KB system prompt the expert called a
tool on 2 of 32 human turns and scored 0.281** — the bare base's behaviour with the
tools in reach. Served under the prompt its corpus taught (`--member-prompt`, the
contract's `system`), with generation cut at its closing tags, six round-trips at most
and 256 tokens per step — the corpus loop's own bounds — **it called a tool on 19 of 32
and scored 22/32 = 0.688 against the 0.655 bar**, 40/40 turns local, 3.5 s each. Six
faults of the live path were found on the way and are fixed with tests: the router
reading the runtime's system prompt and its internal-context envelope, the expert's
echo of the tool block executed as calls, no stop at `</tag>` (it invented the tool's
answer), no round-trip cap, no token bound, a killed turn's stale gateway lock. The
ledger is `results/P63-openclaw-live-20260918/BRIEF.md`.

**So a member is what its corpus taught — the block *and* the prompt.** `--prune`,
`--member-prompt` and `--auto` are what the command above starts with.

**Two members on one inbox, P64 [ran] 2026-09-18.** `desk-commitment@v1` is served beside
`email-full@v1` from the same vLLM, and both read `From: / Subject: / Preview:`. Keyed on
those markers, `--auto` sent desk prompts to the triage member 15 of 60 times; keyed on
what is *asked* — "is this important" against "did you commit" — it separates them, and
live it served each probe with the right member. **A region is its question, not its
listing**: when a task's profile adds a member, add the question it answers to
`route.REGIONS`, never a marker another member's prompts also carry.

### Streaming, and why it is buffered

**OpenClaw streams by default**, and setting `agents.defaults.models.<model>.streaming`
to `false` **did not take** **[ran]**. The proxy used to refuse `stream` outright, on
the grounds that a tag is only a tool call once it closes and buffering the whole
reply is not streaming. That principle was right while the alternative was a
misleading measurement; it was wrong here, where the alternative was **the pool being
unreachable from any real agent runtime**.

So a streamed request is fetched whole and delivered as **one valid SSE chunk**, and
every chunk carries `x_buffered: true` **in the payload** — not only in a comment.
A client gets correct SSE and a correct answer. What it does not get is incremental
delivery, which is latency and not correctness.

## 6. One gateway, one organisation per process

The gateway (`examples/school/gateway.py`) is itself an OpenAI-compatible endpoint, and **since
2026-09-28 it serves one organisation per process** — `--org school` or `--org distributor`, sharing
the roles/tools/store shape but not the prompt each organisation's member trained on: the school's
corpus ends in `SCOPE` and teaches `OUT OF SCOPE`; the distributor's runs its writes without a
director's approval, and until M10 never abstained at all. Each role's OpenClaw points at the
gateway with **its own signed token as the provider key** — the role is decided by the token, never
by the model id:

    python -m examples.school.gateway --upstream <vLLM URL> --org school --member school-s0 \
        [--frontier-url https://api.openai.com/v1 --frontier-model <model>]    # key from $FRONTIER_API_KEY
    ~/.openclaw/bin/openclaw --profile school-educador-north config patch \
        --file ~/.config/lora-kernel/openclaw/educador-north.json5
    ~/.openclaw/bin/openclaw --profile school-educador-north agent --local -m "¿Qué tiene en la agenda el alumno 1?"

`python -m examples.school.live_openclaw --org school` plays the whole scripted demo this way and
scores it with the same checks. **[ran] 2026-09-26: 15/15 through OpenClaw 2026.9.4 with the real
model (Gemma 4 E4B + `school-s0` on an L4) and Claude Haiku 4.5 as the frontier** — the wiring first
passed 15/15 with a stand-in ([`BRIEF`](../results/LIVE-school-openclaw-20260926/BRIEF.md)). One
thing the first live turn taught: OpenClaw appends its own internal context as a *last* user message
and stamps the request; the gateway reads the person's request out of that (`runtime_request`).

### The distributor, live and local — `--org distributor`

The same gateway, pointed at the `edge` profile instead of a rented card ([`SERVING.md`](SERVING.md)):
llama.cpp serving the E4B as Q8_0 with the distributor's own LoRA GGUF, on the very machine running
OpenClaw — nothing rented, nothing tunnelled.

    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-distributor-staff-out-s0-f16.gguf --port 8792 -c 8192 -ngl 99
    python -m examples.school.gateway --org distributor --upstream http://localhost:8792 --member out-s0 \
        --tokenizer google/gemma-4-E4B-it --port 8766 \
        [--frontier-url https://api.anthropic.com/v1 --frontier-model claude-haiku-4-5 \
         --frontier-key-env FRONTIER_API_KEY --frontier-budget-usd 1 --frontier-rates 1,5]
    python -m examples.school.live_openclaw --org distributor --out live.json

**[ran] 2026-09-28: 6/6 through the real OpenClaw** — five turns answered locally and the sixth, a
thank-you note to suppliers that `out-s0` recognises as `OUT OF SCOPE` (M10, held out 20/20), forwarded
to **Claude Haiku 4.5**: 10,198 + 195 tokens, **$0.0112**
([`BRIEF`](../results/LIVE-distributor-openclaw-20260928/BRIEF.md)). `out-s0` is not a formal release
(no release file) — it is the arm this live run used. Both halves of the reference diagram now run
live, on the same gateway shape: the school on a rented card, the distributor on nothing but the
user's own Mac.

### Multi-turn through the gateway — `history=True` today, the workflow harness next

**The gateway used to drop the conversation.** Every turn above reads `runtime_request` — the person's
last message, pulled out of OpenClaw's own envelope — and nothing earlier: "move it to dock 5" arrived
with no "it" to resolve. **OpenClaw itself already sends the whole conversation** on every turn, in
that same envelope; the gap was the gateway discarding everything but the last message, not the client
withholding it.

`Gateway(history=True)` renders every earlier request and reply before the current one — the naive way
to carry a conversation, and the arm it is measured against **[ran]** `results/MT0-multiturn-baseline-20260929/`:
`out-s0` on 60 held-out distributor sessions (124 turns, 54 whose argument comes only from an earlier
turn). Without history, 4/54; with it, **43/54 (79.6 %)**. It resolves a reference it can copy straight
into an argument (receiving 10/10, returns 10/10, purchasing 9/10, dispatch 12/14); **it does not
resolve one that has to be written into free text** — a claim about "that order" is filed with no order
number in 8 of 10 customer-service turns.

**The harness this design is built to replace `history=True` with — designed, H1 running, no result
yet.** Instead of the conversation, `Gateway(memory=, workflows=)` (`examples/common/opmemory.py`,
[`docs/review/harness-workflow-kv.md`](review/harness-workflow-kv.md)) renders one context line — the
role's workflow state and the **names** of the keys a session's cache holds — and the member fetches
and stores values by key (`<get>`/`<put>`) only in the step that needs them, closing exactly the
failure `history=True` leaves open: a claim that needs the order number gets it from the cache, not
from the model's own reading of the transcript. `results/H1-workflow-harness-20260929/` is
pre-registered and **running — do not read a verdict here, none exists yet.**

**Nothing about a live multi-turn run through OpenClaw exists yet.** Every live run on this page —
school 15/15, distributor 6/6 — is single-turn: one request, one reply, no earlier turn to resolve. A
live multi-turn demo is the last step of the order in `docs/review/harness-workflow-kv.md` §7, after H1
passes.

## What this is worth, measured

| | delivered | leaves the machine |
|---|--:|--:|
| everything local | 0.546 | 0% |
| **the failing region forwarded** | **0.775** | **38%** |

**[ran]** `results/P41-routing-20260915/`. On its own region the local expert beats
the base **8 : 51** on the same cases **[ran]** `results/P40-pool-retried-20260915/`.

## What to expect that is not good news

- **One expert is useful, not two.** The fluids expert follows the protocol
  perfectly and gets the physics wrong 78 times in 90 **[ran]**. It is not in the
  configuration above for that reason.
- **The route is by model name**, which is your agent's own choice. Per-case
  escalation is measured and currently **worse** than routing by region **[ran]**.
- **The gate verdict on the email expert is not reproducible run to run** — 84, 81,
  82 against a threshold of 83, every pair a tie **[ran]**. The *effect* against the
  base is not marginal; the *verdict* is.

## Undoing it

    rm -rf ~/.openclaw-lorakernel

Nothing in `~/.openclaw` was written by any command on this page.
