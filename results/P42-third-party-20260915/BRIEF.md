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

---

# Result — 2026-09-15 **[ran]**

`third_party_results.json`.

## The substrate generalises — a stranger's LoRA joins the pool

```
[3p] gate email-full (ours):  applied
[3p] gate arc        (theirs): applied
[3p] members differ from each other: True
```

A LoRA trained by someone else, published on HuggingFace, downloaded onto the VM and
served **beside ours in one vLLM** — both distinct from the base and from each other.
Their replies to the same probe say it without ambiguity:

| member | "In one sentence, what are you?" |
|---|---|
| `email-full` (ours) | *"I am an artificial intelligence designed to answer questions and provide information."* |
| `arc` (theirs) | *"I am an AI assistant created by Alibaba Cloud."* |

**The substrate is not ours; it is vLLM's.** Every pool result before this used
adapters from one script, at one rank, on the same seven modules. This is a claim a
third party can now reproduce.

## Half the candidates could not be loaded safely

```
persona: refused — no adapter_model.safetensors:
         a .bin adapter is a pickle and is not loaded
```

The persona adapter is published as a **pickle**; loading it runs whatever is inside
it, on a VM that had an API key in its environment. **The check fired on the first
stranger's file this project ever touched**, and it refused one of the two
candidates. For a deployment that mounts public adapters this is a required filter,
not a laboratory precaution.

## The accuracy arm should have been cancelled, and my rule bought it

| | |
|---|--:|
| base on ARC | 163/200 = **0.815** |
| their adapter | 165/200 = 0.825 |
| paired | 6 : 8 discordant, **p = 0.791 — a tie** |

The rule read *cancel if less than 0.10 of accuracy is left above the baseline*.
0.185 was left, so it **bought**. But at n = 200 over a 0.815 baseline the power to
see a **+0.05** adapter is **55%**, and to see the **+0.01** that actually appeared,
**8%**. **The arm was unresolvable before it was purchased.**

**Margin was never the right quantity.** The same margin buys very different
resolution depending on where the baseline sits — variance is largest near 0.5 and
collapses near 1.0. `bar.resolvable()` now asks the question the buyer has, and
`bar.n_for()` reports the suite that *would* have resolved it: **466 cases**, not
200.

## What this does not claim

**Not that the third-party adapter is useless** — the arm could not tell. Its own
card reports a gain on ARC; this run neither confirms nor contradicts it, and says
so rather than reporting a tie as a refutation.

**Not a second useful pool member.** Applying is not being useful. That problem is
exactly where it was.
