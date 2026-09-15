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
        --fallback https://api.openai.com/v1

It prints what stays and what leaves before serving a single request:

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
