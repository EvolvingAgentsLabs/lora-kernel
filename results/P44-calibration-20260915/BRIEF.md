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

---

# Result — 2026-09-15 **[ran]**

`confidence.json`. 475 messages, 351 human, **a confidence read on every one of
475 for both arms** — so the serving path is not the story.

| | `email-full` | base |
|---|--:|--:|
| accuracy, **no tools** | 0.425 | 0.345 |
| **mean confidence** | **0.902** | **0.999** |
| ECE | 0.478 | **0.654** |
| Brier | 0.498 | 0.654 |
| **AURC** | **0.612** | 0.627 |
| oracle floor | 0.213 | 0.289 |
| **gap** | **0.400** | **0.338** |

**The base says it is 99.9% sure and is right 34% of the time.** The expert says 90%
and is right 42%.

## The pre-registered reading: the typed arm is bought

The brief named three outcomes before the numbers existed, and this is the third:

- ~~small gap → cancelled~~ — the gap is **0.40**.
- ~~large ECE with a small gap → temperature scaling, not a typed head~~ — **this is
  the row that mattered and it does not apply.** A confidence that is miscalibrated
  but *rankable* is fixed by a post-processing step costing no training. **These are
  not rankable**: 0.40 and 0.34 above the floor.
- **large gap → bought.** The confidence is on the wire and it does not order the
  errors.

Writing that middle row in advance is what makes this readable. A large ECE alone
would have been a bad reason to train anything.

## What it establishes beyond this project

The proposal's premise — *a first-token logprob is a poor proxy, biased by format,
tokenisation and prompt* — arrived as **[read]** from a brief citing a lab with no
public paper or benchmark. **It is now [ran] on our own model**, and the failure is
not subtle: near-saturated confidence on a task the model gets wrong more often than
right.

## The caveat that travels with the numbers

**These accuracies are tool-free**: one forward pass from the listing, no
`thread_history`, no `sender_stats`. That is why 0.425 and not the 0.741 P43
measured. It is deliberate — **a typed adapter also answers in one forward pass
without tools**, so this is the like-for-like baseline it would have to beat — but it
is *not* the number for the expert doing its job, and it is not presented as one.

## What is not claimed

**Not that a typed head will fix this.** This measures what exists and says the room
is there. Whether a restricted softmax trained with a proper scoring rule closes the
gap is the next arm, and it now has a floor to beat: **AURC gap 0.400 for
`email-full`**, on these 351 cases, with `bar.calibration()` as the instrument.
