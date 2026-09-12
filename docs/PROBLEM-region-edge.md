# An open problem: a specialist that cannot feel the edge of what it knows

**This document is written to be handed to someone — or something — with no prior
context, in the hope of getting proposals we have not thought of.** It states a
problem we have measured, lists what we tried and what each attempt ruled out, and
says precisely what a solution would have to satisfy and how we would test it. If
you are reading it to propose an approach, the last two sections are the ones that
constrain you.

## 1. The setting, in as few words as it takes

A large AI model is expensive to run. A small one is cheap and worse. We are
testing whether you can get most of the way to the large model by keeping **one**
small model in memory and applying a tiny, swappable **patch** — a few megabytes of
weight adjustments that make it behave like a specialist while applied, removable
in milliseconds.

The economics only work if you can eventually **stop paying for the large model**.
So the design has two phases:

- **Phase A.** The large model does the work. The specialist watches and is scored
  on how often it would have produced the same thing. That score accumulates into a
  map of *what this specialist is good at*.
- **Phase B.** Where the map says the specialist is good enough, the specialist
  takes over and **the large model is dismissed for that kind of work**.

The unit of that decision is a **region** — a kind of task the specialist has
proven itself on. Phase B is the entire point. Everything else is scaffolding.

## 2. The problem

**A specialist has a hard edge, and cannot feel it.**

We trained a specialist on six kinds of fluid-mechanics problem. We then gave it
two kinds it had never seen — same subject, same style of question, differing only
in which physical relation they need.

Inside its six kinds, scoring its **formulas** (not its arithmetic), it is right
**30 times out of 30**. On the two it never saw, **1 out of 20**.

The drop is not gradual. And here is the part that matters more than the number:

**Nothing in its output marks the difference.** Same numbered structure, same
confident phrasing, same plausible vocabulary. It invents the physics:

    2. Volume fraction: 4/3 * pi/6 = 0.698132
    4. Stokes regime? v*d/(rho*mu) = 3.88*0.304/(998.0*0.001002) = 1.12832 < 1
    6. Drag force F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)

A "volume fraction" that is not one. A regime test that is not the regime test. A
force law that is not the force law. The same specialist that scores perfectly on
its own material wrote that, in the same voice.

**So Phase B is a promise the system cannot keep.** It says "proven on this
region", and the first request from just outside that region gets a confident wrong
answer with nothing watching. Worse: the evidence available at the moment of the
Phase B decision is the map from Phase A, which records **where the specialist has
been tested** — not where it stops working. Those are different sets, and the
difference between them is exactly where the confident wrong answer lives.

## 3. What we tried, and what each attempt ruled out

**Attempt 1 — ask the model how confident it is.** Not bought, because our own runs
already answer it: the wrong answers arrive with the same fluency, structure and
vocabulary as the right ones. There is no visible difference to key on, and
self-reported confidence is known to be unreliable in general. This is not a
promising direction and we did not spend on it.

**Attempt 2 — watch the process instead of the model.** This was our idea and it
looked good. The specialist works by calling tools (a calculator, a lookup, a unit
converter), and a harness answers those calls. Outside its region, the specialist
names quantities it does not understand, and the tool layer has to turn those names
into valid calls. Perhaps the *tool layer's* failures mark the edge that the prose
does not.

We listed six candidate signals **before looking at any of them** — calls per
problem, rejected calls, rejection rate, number of steps, chains with nothing
evaluable, transcript length — and checked all six over transcripts already on
disk. Only one separated on both configurations we tested: **the rate at which the
tool refuses what the chain asks for.** Inside the region, 15% of requests; outside,
63%. A single threshold classified 86% of cases.

**And then it failed confirmation.** The signals had been chosen with the answers
visible and the threshold fitted on the same fifty problems that scored it, so we
pre-registered a confirmation: two *new* kinds of problem no run had used, with the
threshold **fixed** rather than refitted. Result: outside the region the tool
refuses calls at **0.18**, against **0.15** inside. The guard scores 0.62 where
chance is 0.60.

**So the 86% was a property of those two particular kinds of problem, not of a
boundary.** The signal is dead, and with it the cheap direction: *read the process
rather than the model* was the idea, and the process does not know either.

## 4. What is left, and why each is unattractive

**A second specialist, trained on a different region; treat disagreement as an
edge signal.** Plausible, and it doubles the cost of every request it guards. It
also only detects an edge where some *other* specialist happens to be competent —
which is not the same set as "outside this specialist's region", and may be a small
fraction of it.

**Sample the large model after Phase B and compare.** This is the industry answer
and it works. It also costs money forever, on every guarded request, which is
precisely the cost Phase B exists to remove. It converts a step change into a
discount.

**Shrink the regions until the edge is far away.** Makes every region cheap to
prove and multiplies the number of specialists and the routing burden, and it does
not remove the problem — it just makes the first out-of-region request rarer and no
less confident.

None of these is obviously right. That is why this document exists.

## 5. What a proposal has to satisfy

These are not preferences. Each one is there because something we tried failed on
it.

1. **It may not consult the large model on the guarded path.** A guard that pays
   for the thing it replaced is not a guard. (Sampling *some* fraction offline is a
   different proposal and is allowed, but then its cost must be stated as a fraction
   and defended.)
2. **It may not rely on the specialist's self-report.** Measured: wrong answers are
   indistinguishable in presentation from right ones.
3. **It may not need the correct answer at serving time.** If it did we would not
   need the specialist.
4. **It must distinguish "outside the region" from "inside and difficult".** A
   detector that fires on every hard problem costs the deployment its throughput and
   will be switched off.
5. **Its threshold, if it has one, must be fixable in advance.** A threshold tuned
   on the material it is tested on is the mistake that killed our last candidate.
6. **It must be cheap enough to run on every request**, or its sampling rate has to
   be part of the proposal.

## 6. How we would test a proposal, and what already exists to test it with

We can evaluate a proposal quickly and honestly, because the instruments are built:

- **Problems with known answers**, generated from closed-form formulas, in six
  "in-region" kinds and four kinds no specialist was trained on. Ground truth is
  exact and available for scoring, and never visible to anything being scored.
- **Trained specialists**, and transcripts from many configurations, with each
  chain's correctness already known.
- **A judge that is right 82% of the time** without seeing the answer, plus a
  procedural check that re-executes a chain's own arithmetic. Requiring both to
  accept catches 98% of wrong work that looks clean, which may or may not be useful
  to a proposal here.
- **A pre-registration discipline**: signals and thresholds are written down before
  they are scored, and a candidate found by searching a space is treated as a
  hypothesis until it survives material it was not found on.

**What we would report for any proposal:** its accuracy separating in-region from
out-of-region material, on kinds of problem it was not developed against, with any
threshold fixed beforehand — and the rate at which it fires on hard-but-in-region
problems, because a guard that cannot tell those apart is unusable however good its
headline looks.

**The bar is low and nothing has cleared it.** Our best candidate scored 0.62 where
chance was 0.60.

## 7. The honest framing of the question

We are not asking "how do we make a model know what it does not know", which is a
research programme. We are asking something narrower:

> Given a specialist that has been measured as competent on a set of examples, and
> a new request, is there anything cheap and observable — in the request, in the
> specialist's behaviour, in the tools it uses, or in cheap comparisons that do not
> involve the expensive model — that distinguishes a request the specialist will
> handle from one it will answer confidently and wrongly?

We have measured that the answer is not the model's confidence, and not the tool
layer's failure rate. We do not know what else to look at.
