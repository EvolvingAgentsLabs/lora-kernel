# P47 — is the confidence worth reading once the tools have run?

**Pre-registered 2026-09-16, before the run. Not launched.**

## Why this and not the typed adapter

P44 measured the confidence `email-full` attaches to its answers **without tools** and
found an AURC gap of 0.400, read as room for a typed head. P46 then computed the
**ceiling**: on the full inbox both arms are already at it (room 0.030 and 0.007), and
on the human subset the best possible listing-only predictor is a **constant** — one
group, not rankable **[ran]**. A constant confidence routes nothing, so the
listing-only typed arm was cancelled before the GPU.

**With the tools the ceiling collapses.** `thread_history` gives *did I write in this
thread*, `sender_stats` gives *is this a frequent counterpart* — the two facts the
definition needs and the listing withholds. Every fact becomes recoverable, the truth
becomes decidable, and the ceiling falls to the oracle floor. **So the whole of
whatever gap is measured here is claimable.**

And nobody has measured it. P43 established accuracy in this configuration —
**260/351 = 0.741, exact p = 0.00036** **[ran]** — and never looked at the confidence,
because `triage_one` could not ask for logprobs until 2026-09-16.

## What is measured

One arm. `email-full`, the full tool chain, `logprobs: true, top_logprobs: 20` on
every turn, the confidence read off the **final** turn — the one where the model
stops calling tools and answers.

| | says | matters because |
|---|---|---|
| ECE | the number means what it says | a threshold can be set |
| Brier | it is sharp as well as true | a constant 0.5 is calibrated and useless |
| **AURC vs floor** | it **orders** the errors | **this is the routing signal P41 could not find** |

**No second arm.** The base is not run: P44 already has it tool-free, and a base that
makes one call per case and refuses 85 of 140 is not a comparison, it is a different
configuration. Arms are bought in sequence.

## Model, provider, cost

`Qwen/Qwen2.5-3B-Instruct` + `email-full` from
`results/P41-routing-20260915/adapters.tgz`, vLLM on a rented **L4**. 475 messages,
351 human, seed 717171 — **the same cases P44 and P43 used**, so the numbers are
comparable without re-drawing. **No training.** ~35 min.

## The gate, pre-registered

- **The re-aimed typed arm is bought** if the AURC gap is **> 0.10** with the tools.
  The ceiling here is the oracle floor, so a gap that size is real room and a typed
  head trained with a proper scoring rule is the candidate for it.
- **It is cancelled** if the gap is **< 0.05**: the expert's own confidence already
  orders its errors once it has the facts, and the router should read that number
  instead of anything new being trained.
- **Between the two is temperature scaling, not a typed head** — a post-processing
  step costing no training. Writing this row before the numbers is what stops a
  badly-calibrated-but-rankable result being spent on a model.

## What falsifies the premise

The premise is that *the tools carry the information the listing lacks*. It is
**falsified** if accuracy in this run lands near P44's tool-free 0.425 rather than
P43's 0.741 — that would mean the chain is not recovering the facts, and the
confidence question is premature.

## What voids the run

- **`answered_first` false on more than 20% of cases.** `IMPORTANT` and `NOT
  IMPORTANT` differ at the first token, which is why the mass there is the whole
  verdict — but a model that opens with prose puts a word there instead, and reading
  that as a confidence measures phrasing. The share is counted, not averaged over.
- No `top_logprobs` from the server, or the identity gate failing: both arms would be
  the base.

## What it cannot claim

- **Not that a typed head would do better.** This measures what exists and says
  whether there is room. Whether a restricted softmax trained with a proper scoring
  rule closes the gap is the arm after it, and only if this one leaves room.
- **Not anything about fluids.** P45 stands: that expert is locked to its training
  depth, and no confidence number changes it.
