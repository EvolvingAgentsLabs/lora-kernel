# P34 — does one protocol adapter serve a pool, or does every domain need its own?

**Pre-registered 2026-09-14, before the adapter was served.**

## The question this repository exists to answer

The thesis is that the whole agentic system is **a pool of QLoRAs over one resident
base**. That only pays if a capability learned once is reusable — and the most
reusable thing there is would be **the protocol**: knowing that a needed value is
asked for rather than guessed.

P8 measured that the protocol is separable **[ran]**: a kernel with no physics in its
corpus makes the base ask far more often (44 → 169 tool calls on 30 cases), and a
domain adapter with no protocol suppresses asking to zero. **What P8 did not test is
whether the protocol survives a change of vocabulary.**

So: the `kernel-mt` adapter, trained on `<calc>`, `<lookup>` and `<convert>` over
fluid mechanics, served over Qwen2.5-3B against the **email** suite, whose tools are
`<thread_history>`, `<sender_stats>` and `<message>`. **It has never seen these tool
names, this domain, or this task.**

## The headroom is at the floor, and that is checked, not assumed

P31 measured the base alone on this suite: **0 tool calls out of 150** **[ran]**.
There is no ceiling problem on the metric that matters here, and no floor problem
either — 0 is the floor, so any rise is visible.

## The primary measure is asking, not scoring

**Tool calls, not accuracy.** Answering correctly needs the protocol *and* the
judgment; asking at all needs only the protocol, and that is the thing P34 is about.
Accuracy is reported beside it and read against P31's gate, but it does not decide
this step.

## Three outcomes, all distinguishable before the run

| what comes back | reading |
|---|---|
| **~0 calls** | the protocol does not transfer across vocabularies; the pool needs a protocol adapter per tool set, and the "learn it once" claim is much weaker |
| **calls, mostly refused** | the *form* transferred and the *vocabulary* did not — it asks in the shape it learned, with names this suite does not have |
| **calls, accepted** | one protocol adapter serves tools it was never trained on: the strongest version of the pool thesis |

The middle row is why refusals are counted separately. Collapsing it into either
neighbour would lose the most informative outcome there is.

## Falsification

- **The pool thesis is weakened** if calls stay at or near zero. That is a real
  result and gets written as one.
- **A rise in calls with no gain in accuracy is still the finding**, and is reported
  as such rather than buried for being unflattering. The step asks whether the
  adapter reaches for the tools, not whether it wins.
- **The arm is void** if the served adapter does not apply — which is why the P33
  identity gate runs first and is not assumed.

## What it is not

Not a comparison against a protocol adapter trained on email; none exists yet.
Whether to build one is precisely what this step decides.
