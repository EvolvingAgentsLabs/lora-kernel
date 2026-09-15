# P44 — is the confidence this pool already has worth reading?

**Pre-registered 2026-09-15, before the run. A headroom check that can cancel what
comes after it.**

## Why this runs before any typed adapter is trained

`docs/analysis/typed-adapters.md` recommends building one, and the proposal rests on
a claim taken from the brief: that a first-token logprob is *"a poor proxy — biased
by format, tokenisation and prompt"* **[read]**. **That is testable on our own model
today, without training anything.** `email-full` already answers `IMPORTANT` /
`NOT IMPORTANT`, so the mass it puts on that first token *is* a confidence and it is
already on the wire.

**This is the rule P42 forced into existence**, applied before the spend rather than
after: that run bought an accuracy arm against a base already at 0.815 and it was
unresolvable before it was purchased **[ran]**.

## What is measured, and why it is not accuracy

P43 settled accuracy — 260/351, exact p = 0.00036 **[ran]**. This asks the question
a **router** needs and P41 found no cheap answer to: *can a caller trust the number
the model attaches to its own answer?* Both escalation rules delivered **less** than
routing by region, and the one signal that worked — agreeing with the frontier —
requires calling the frontier **[ran]**.

Three numbers, and **AURC is the one that decides**:

| | says | matters because |
|---|---|---|
| ECE | the number means what it says | a threshold like `p > 0.9` can be set |
| Brier | it is sharp as well as true | always saying 0.5 is calibrated and useless |
| **AURC** | it **orders** the errors | **a router does not need a calibrated number, it needs the wrong answers at the bottom** |

AURC is read against an **oracle floor**, because an AURC alone is unreadable: on an
easy suite a useless confidence still scores well.

## Falsification, written before the number

- **The typed arm is cancelled** if the existing confidence already orders the
  errors — an `aurc_gap` near zero means a typed head has nothing to add *here*, and
  the honest move is to say so and stop.
- **The typed arm is bought** if the gap is large: the confidence is on the wire and
  useless, which is exactly the claim the proposal makes.
- **A large ECE with a small gap is the interesting middle**, and it does **not**
  justify a typed head. It justifies **temperature scaling**, which is a
  post-processing step costing no training at all. *Saying this now is what stops a
  badly-calibrated-but-rankable result being spent on a model.*
- **The run is void** if the served model returns no `top_logprobs`, or if the
  confidence cannot be read for a large share of cases — that would measure the
  serving path, not the model.

## What it will not claim

**Not that a typed adapter would be better.** This measures what exists. Whether a
restricted softmax trained with a proper scoring rule beats it is the next arm, and
it is only worth buying if this one leaves room.
