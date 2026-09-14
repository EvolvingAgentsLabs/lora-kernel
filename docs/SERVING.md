# Serving the pool to an agent runtime

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

## What is measured, and where

| | result | step |
|---|---|---|
| each adapter is its own model name, and **is applied** | base and adapter answer differently | P26 |
| tags → `tool_calls` | **0 of 38** lines naming a domain; **604/604** round trips | P27 |
| `tools=[…]` → tag surface | costs **0.188** on the oracle's tool values | P27 |
| the arity convention | recovers **55%** of that, refusals **88 → 17** | P28 |
| declaring allowed values (`enum`) | **made it worse** — off by default | P28 |

## What is assembled and not measured

**The multi-turn loop.** An agent sends back `role: "tool"` results and the proxy
folds them into the transcript as `= value`, where the adapter was trained to read
them. **Every measurement so far has been a single turn** — P27 arm 3 explicitly so.
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
