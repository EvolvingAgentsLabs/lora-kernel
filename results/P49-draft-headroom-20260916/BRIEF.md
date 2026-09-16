# P49 — does a larger model write better drafts than the bare base?

**Pre-registered 2026-09-16, before the run.**

## Why this before three corpora

The close-experts design selects drafting experts by **acceptance against a larger
target**. If the target is not better than the base, acceptance against it ranks
nothing and all three arms tie — which is exactly how P42's third-party adapter
scored **0.825** against a base already at **0.815** **[ran]**.

**So this runs first and trains nothing.** It can end the design for the price of
one session, before three corpora and three training runs are bought.

## Arms

| # | arm | model |
|---|---|---|
| 1 | **target** | `Qwen/Qwen2.5-32B-Instruct-AWQ` — 19.3 GB, **byte-identical tokenizer** to the base **[ran]** P48 |
| 2 | **base** | `Qwen/Qwen2.5-3B-Instruct` |

**The target runs first**, because a target that cannot carry the facts itself ends
the design without the base ever being served.

**One model at a time on one card.** Holding 19.3 GB and 6 GB resident together would
need memory tuning to answer a question that does not need them simultaneous.

## The deliberate simplification, stated rather than hidden

**Both models are handed the thread inline. Neither calls a tool.** The product
configuration reads the thread through `thread_history`, and adding that here would
put a second skill — operating the protocol — inside a question about writing.

**It can only make the gate easier to clear**, which is the conservative direction:
if the target is not better with the facts handed to it, it is certainly not better
having to fetch them.

## What is measured, and why it is not a quality score

There is no rule that says a draft is good — that is the whole reason the design
reaches for acceptance. What **is** mechanical is whether the draft carries the facts
the reply depends on: the reference, the date, the amount. `drafting.carries()`.

**A floor, not a score.** It catches the failure acceptance alone cannot see — two
models agreeing at length on a reply that commits to no date and names no reference.

Reported per draft (**all** facts present) with the per-fact rate beside it, because
a floor moving from 0.1 to 0.9 facts while completeness stays at 0 is a different
situation and one number would hide it. And per temática, because a flat average
hides a temática that fails entirely.

## Model, provider, cost

vLLM on a rented **A100**. `n = 90` cases, 30 per temática, seed **606060**.
Two model loads, ~40 min. **No training.**

## The gate, pre-registered

**The design is bought** if the target's complete-draft rate exceeds the base's by
**≥ 0.10**. Below that, acceptance against this target would rank nothing and the
three experts would tie — and the honest move is to say so and not build the corpora.

The margin is **rounded before it is compared**, so a result sitting exactly on the
threshold is decided by the number that was written down rather than by float noise.

## What voids it

- Either arm never coming up, or a large share of `errors` — that measures transport,
  not writing. The count is reported, never folded silently into the score.
- A base that already scores near 1.0: then there is no headroom to measure and the
  suite is too easy, which is the mirror failure and just as fatal.

## What it cannot conclude

- **Nothing about acceptance.** This measures whether a *target worth accepting
  against* exists. Whether acceptance ranks three close experts is P50.
- **Nothing about tools.** By construction.
- **Nothing about draft quality.** The check is a floor; a draft can carry every fact
  and still be a bad reply.
