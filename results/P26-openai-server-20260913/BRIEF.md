# P26 — the pool behind an OpenAI-compatible endpoint

**Pre-registered 2026-09-13, before anything was served.**

## Why now

The architecture's layer 1 is "one resident base, adapters swapped per request".
Everything measured so far has been `transformers` loading one adapter at a time,
or vLLM's **offline** `LLM` class. An agent runtime — OpenClaw, Hermes, anything
that speaks OpenAI — cannot call either of those. It calls
`POST /v1/chat/completions` with a `model` name.

vLLM's server registers each adapter as its own model name, which is exactly that
shape. **Nobody has run it.** This step runs it, and buys a second thing with the
same session: the mixed-batch cost, which P3 explicitly voided because the serial
loop it used measured round-trips instead of batching. Concurrent clients against
one server are what that measurement needed.

## The gate that comes first, and it is not throughput

**C18: vLLM 0.28.0 accepted a valid `LoRARequest` and served the base model — no
error, no warning, byte-identical output [ran]** `results/P3-vllm-20260908/`. Had
that step measured only throughput it would have reported three adapters served at
90 prompts/s and called the substrate proven.

So before any number is recorded:

1. `/v1/models` lists each adapter as its own model name.
2. **The same prompt to the base and to an adapter must produce different text.**
   Identical output means the adapter is not applied, and the run stops there and
   reports that rather than measuring anything.
3. The adapter's accuracy through the API must match what `transformers` measured
   on the same cases. A different number means one of the two stacks is wrong, and
   every earlier result is in question.

## The arms, in order, killing arm first

| # | arm | what it answers |
|--:|---|---|
| 1 | **serving identity** | does an adapter change the output at all — the C18 gate |
| 2 | **accuracy through the API** | do the numbers survive the serving stack |
| 3 | **pure vs mixed concurrency** | what holding a pool costs, measured inside one scheduling pass |

Arm 3 is bought only if 1 and 2 pass. A throughput number from a server that is
quietly ignoring its adapters is the exact failure C18 exists to prevent.

## Falsification

- **The substrate is unproven** if the base and adapter outputs are identical, as on
  `Qwen3.5-2B`. This is a real possible outcome and it stops the step.
- **The serving stack is wrong** if accuracy through the API differs materially from
  `transformers` on the same cases.
- **Per-request swapping is not a serving strategy** if a mixed batch costs so much
  more than a pure one that a pool has to be partitioned by model anyway.

## What this step does NOT do, said plainly

It does **not** give an agent runtime a working tool loop. The adapters emit
`<lookup>…</lookup>` in the message body; OpenAI clients expect `tool_calls`. An
agent pointed at this endpoint would receive prose containing tags and see no tools
at all.

**Bridging that is a separate question and it is not only plumbing**: the protocol
this project put into weights is a text protocol, and a translation layer that
converts it to `tool_calls` reintroduces the hand-written harness the weights were
meant to replace. **P26 serves the pool. Whether `harness.lora` survives contact
with function-calling is the next brief, not this one.**
