# P42 — does a stranger's LoRA join our pool?

**Pre-registered 2026-09-15, before anything was downloaded or served.**

## What this buys, and what it does not

**It does not buy a second useful expert.** The public Qwen2.5-**3B** ecosystem has
personas without an oracle, MCQ adapters, and GSM8K work where **the base already
scores 87.6** **[read]** — a ceiling, and the mistake this project has paid for
twice. There are no public tool-using experts with a mechanical verifier at this
size. That problem stays open.

**It buys an independent test of the substrate.** Every pool result so far used
adapters trained by one script, at one rank, on the same modules. If a LoRA trained
by someone we have never met drops into the same server and applies, the claim gets
much stronger. **If it does not, the substrate is more fragile than three of our own
runs suggested — and that is the more valuable outcome.**

## The candidate drops in with no configuration change [read]

[`sumanthota/qwen2.5-3b-mcq-arc-lora`](https://huggingface.co/sumanthota/qwen2.5-3b-mcq-arc-lora)

| | theirs | ours |
|---|---|---|
| base | `Qwen/Qwen2.5-3B-Instruct` | identical |
| rank | **16** | our `--max-lora-rank 16` |
| targets | the seven projections | identical |
| weights | `adapter_model.safetensors` | **not a pickle** — no code executes on load |

A persona adapter joins as a second stranger, because *"does it talk like the
character"* is an unambiguous applied/not-applied signal that needs no oracle.

## Headroom runs FIRST, and can cancel the rest

**The base alone on ARC-Challenge, before the adapter is served.** If the base is
already strong there, the adapter cannot show anything and the accuracy arm is
cancelled — the substrate arm still runs, because it does not depend on headroom.

This is written here so that a base at the ceiling reads as *the arm was cancelled*
rather than as *the arms tied*.

## The gates

1. **Every member differs from the base** — vLLM loads a LoRA, says so, and can
   serve the base anyway (P33 **[ran]**).
2. **The members differ from each other** — two names over one adapter is the
   failure that looks most like success.

## Falsification

- **The substrate generalises** if both strangers apply and are distinct from our
  own member and from each other.
- **The substrate is ours only** if a stranger's adapter is refused, or loads and
  serves the base. Either is a finding about vLLM and about the pool claim, and it
  is reported as one.
- **The accuracy arm is cancelled, not tied**, if the base clears ARC on its own.
- **The run is void** if our own `email-full` stops applying when strangers are
  loaded beside it — that would mean three members interfere, which nothing has
  tested.

## What it will not claim

**Not that a third-party adapter is a pool member worth having.** Applying is not
being useful. The useful-second-member problem is untouched by this step and stays
open.
