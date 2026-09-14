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

---

# Result — 2026-09-14 **[ran]**

`triage_results.json`, `arm_kernel.json`. `kernel-mt` served over Qwen2.5-3B by vLLM
0.29.0, against the email suite it has never seen.

| | base alone (P31) | **kernel-mt (P34)** |
|---|--:|--:|
| tool calls | 0 | **127** |
| refused | 0 | **127** |
| cases that asked for something | 0 of 150 | **123 of 150** |
| human messages | 39/113 = 0.345 | 39/113 = 0.345 |
| exact one-sided p | 1.000 | 1.000 |
| seconds | 17.4 | 91.6 |

## The middle row, which is why it was written down in advance

**The protocol transferred as behaviour and not as vocabulary.** The base alone asked
for nothing, 150 times. With a protocol adapter trained on `<calc>`, `<lookup>` and
`<convert>` over fluid mechanics, the same base reaches for a tool in **123 of 150**
cases on a domain it has never seen — and every one of those asks is refused.

Neither of the other two pre-registered readings fits:

- **not** "the protocol does not cross vocabularies" — it crosses. Zero became 127.
- **not** "one protocol adapter serves tools it was never trained on" — none of the
  127 was answered.

## What it costs, stated plainly

**Accuracy did not move: 39/113 both times, identical.** A protocol adapter that
asks and is refused scores exactly what a base that never asks scores, because after
the refusal it falls back to the same answer. **The ask is the finding; the score is
not, and it is reported rather than buried for being unflattering** — which the brief
said in advance it would be.

## What is not known, and why it was not bought

**Which name it reached for.** The record counted refusals without recording the ask,
so it cannot say whether the adapter called a tool this suite does not have (`calc`)
or the right one with arguments it could not parse. That was fixed the same session
(`agent_sim` now carries the name, the arguments and the error out of every return
path), so **the next run answers it for free**.

It was not bought as its own arm because **it does not change what happens next**.
Either failure leads to the same purchase — a protocol adapter trained on this tool
vocabulary — and a corpus built from the email tools' own schema covers both. Buying
an attribution arm that cannot change the next decision is the grid this project
does not buy.

## What this establishes for the pool thesis

**The reusable thing is the disposition to ask, and it is genuinely reusable.** That
is the non-obvious half: a LoRA trained on one domain's tools changes how a base
behaves toward tools it has never met, on a task with no overlap. What does not come
along is the vocabulary, which is cheap to teach and domain-specific by nature.

So the pool does not need a protocol adapter per domain **for the behaviour**. It
needs one that knows the names. Whether that can be one adapter covering several tool
sets, or must be one per set, is the next question — and it is now a question about
training data rather than about whether the idea works at all.
