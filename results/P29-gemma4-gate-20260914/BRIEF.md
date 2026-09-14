# P29 — can vLLM apply a LoRA to Gemma 4 E4B at all?

**Pre-registered 2026-09-14. The cheapest arm in the project, bought before anything
else about this base.**

## Why the question is asked this way

The temptation is to train an adapter on a second base and compare numbers. **P3
already paid for that order.** vLLM 0.28.0 accepted every `LoRARequest` on
`Qwen/Qwen3.5-2B` **without an error or a warning** and served the base model —
byte-identical output, three adapters apparently running at 90 prompts/s. Had that
step measured only throughput, it would have reported a working substrate **[ran]**
`results/P3-vllm-20260908/`.

The cause was the base: **hybrid and multimodal, and the class that declares
`SupportsLoRA` is neither.** `gemma-4-E4B` is dense but **multimodal — vision and
audio [read]** (unsloth's Gemma 4 page), which is one of the two properties that
broke it. And that same page says Gemma 4 **"is not supported by vLLM"**, offering
unsloth's own `fast_inference=False` instead — which is not an OpenAI-compatible
server and is therefore not the thing S8 needs **[read]**.

So the order is: **ask whether an adapter changes the served output, before training
one to find out.**

## The design, and it is deliberately tiny

One session. Serve `google/gemma-4-E4B-it` with **the adapter this project already
has**, and send one prompt to the base and to the adapter.

**The adapter is trained for a different base and will produce nonsense.** That is
fine and it is the point: this measures *whether vLLM applies weights*, not whether
they help. A rank-16 delta on mismatched dimensions will either be rejected loudly —
a result — or applied and produce garbage — also a result. **Silence is the only
outcome that means what P3 found.**

Nothing is trained. Nothing is scored.

## Falsification

- **The base is usable** if the served text differs between base and adapter, and
  `/v1/models` lists the adapter. A second base becomes available for replication.
- **The base is not usable** if the outputs are byte-identical. That confirms the
  constraint is *multimodal*, not *Qwen3.5*, and it fixes which bases this
  architecture can serve — a finding worth having whichever way it lands.
- **The step is inconclusive, not negative**, if vLLM refuses the adapter with an
  explicit error about shapes or ranks. That is a dimension mismatch from a
  deliberately foreign adapter, and it says nothing about whether a *native* adapter
  would apply. It would cost one training run to resolve, and that run is bought only
  then.

## What it cannot settle

Whether Gemma 4 is a better base. It measures one thing: **does the serving stack
apply the weights.** Everything else is downstream of that answer and none of it is
bought yet.
