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
        --prune \
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

**It is off by default.** Every measurement before today ran without it, and an
instrument that quietly changes what the model sees stops comparing to itself.
`--prune` on and off is the pair of arms the question needs.

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
