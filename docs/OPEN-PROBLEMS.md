# Open problems

## Start here: what this project is trying to build

A large, capable AI model is expensive to run. A small one is cheap and not very
good. The bet behind this project is that you can get most of the way to the
expensive model by keeping **one** small model loaded in memory and putting a
tiny, swappable **patch** on top of it — a few megabytes of adjustments that make
the small model behave like a specialist while it is applied, and that you can
take off again in milliseconds.

If that works, a whole system of "agents" stops being a collection of programs
calling a rented model, and becomes a **library of patches over one cheap model
you own**. You keep one copy in memory, and you switch specialists the way a
carpenter changes a bit in a drill.

The design splits the patches into two kinds, and this split is the whole idea:

- **One patch teaches *how to work*.** How to lay out a solution in numbered
  steps, when to stop and ask a calculator instead of guessing, how to carry the
  answer forward. It knows no subject matter at all.
- **The other patches teach *what is true*.** One knows fluid mechanics, another
  knows something else. They know their subject and nothing about procedure.

The reason for the split is economic. If every specialist had to also learn the
procedure, then changing the procedure — adding a tool, changing how the system
asks for one — would mean retraining every specialist you own. Splitting them
means you change the procedure patch once and every specialist inherits it.

Everything in this document is about the places where that plan does not yet
work, described as plainly as we can manage.

## What already works

These are measured, not hoped for. Each one is a real run recorded in
[`results/`](../results/), and the plan
([`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md)) names the run directory for each.

**The procedure patch is real, and it travels.** We trained one purely on
everyday arithmetic — shop receipts, averages, compound interest, the volume of a
cone. It contains no physics of any kind. We then handed it fluid-mechanics
problems it had never seen, in a domain nobody taught it, using a question that
never mentions that a calculator exists. It reached for the calculator on **all
thirty problems**, an average of nearly eight times each, and **never once wrote
a malformed request**. That is the strongest single result the project has: a few
megabytes of adjustments carrying a working procedure into a subject it has never
encountered.

**The subject patch is real too, and its knowledge is exact.** The physics
specialist writes down the right formula essentially every time. Its answers are
wrong anyway, because it cannot do the arithmetic — it will write the correct
expression for a circle's area and then compute it wrong in the fourth decimal,
and every later step inherits the error. When we take its own written formulas
and evaluate them exactly, they land on the right answer on **thirty out of
thirty** problems, against **one out of thirty** for what it actually wrote. It
does not need to be taught more physics. It needs to stop doing the arithmetic.

**Put both jobs into a single patch and the result is perfect.** One patch that
learned the physics and the procedure together, with a calculator available,
answers **forty out of forty** — matching the expensive model exactly. And it
takes both halves: the small model with a calculator and no training gets none
right despite asking fifty-three times, and the trained model without a
calculator gets four out of forty. Neither half is worth anything alone.

**There is real room to improve.** An expensive model scores perfectly on this
material and the small one scores under half, so there is a genuine gap for a
specialist to close. (We nearly fooled ourselves here, and the story is in
["How to read the numbers"](#how-to-read-the-numbers-in-this-document) below.)

So: the two halves exist, each is healthy on its own, and putting them in one
patch works. The problem is putting them in **two** patches, which is the entire
point of the design.

## Problem 1 — two specialists that would not take turns (solved; what replaced it)

### What we see

Load the procedure patch and the physics patch at the same time. Both are
present: the answer names the right physical quantities, in the right order, the
way the physics specialist would — and it does sometimes stop to ask the
calculator, the way the procedure specialist would. The two behaviours are
visibly mixed in the same answer.

But the mixture is lopsided. Alone, the procedure patch asks the calculator
almost eight times per problem. Combined with the physics patch, it asks **0.6
times per problem**. On twenty-five of thirty problems it does not ask at all.

And the asking is exactly what matters:

| when the combination... | problems | got it right |
|---|---|---|
| asked the calculator at least once | 5 | **3 — 60%** |
| never asked | 25 | 1 — 4% |

A fifteen-fold difference. **The mechanism is not broken. It almost never
fires.** Something in the combination suppresses the single behaviour the
procedure patch exists to provide.

The plainest way to describe it: two people are dictating the same sentence at
once. One says *"write the number here."* The other says *"stop, ask the
calculator, wait for the answer."* At nearly every step, the first one wins.

### What we tried, and what each attempt taught us

**Attempt one: give each patch a different part of the model to modify.** A
model is a stack of large numerical tables. A patch adjusts some of them. If the
procedure patch only ever touches tables A, B and C, and the physics patch only
ever touches D, E and F, then the two adjustments are added to different places
and cannot possibly collide. It costs one setting to try.

It made things **worse**. Asking dropped from 0.6 to 0.2 times per problem, and
the physics degraded badly as well. Two patches with **no modified table in
common** still fight.

That result is worth more than the attempt cost, because it eliminates an entire
family of proposed fixes. Everyone's first instinct — including ours — is that
this is a collision between two sets of adjustments landing on the same numbers,
and that keeping them apart will fix it. It is not that. Both patches steer the
same thing at the end: **which word the model writes next**. They can be built
from completely separate parts and still disagree about that one choice, because
that choice is where they both end up. Separating where they live does not
separate what they are arguing about.

**Attempt two: turn one patch up and the other down.** If the physics patch keeps
winning, apply it at half strength and the procedure patch at full strength.

This **worked on the thing we were aiming at, and destroyed the thing we were
trying to keep.** Asking jumped from 0.2 to 3.5 times per problem — a seventeen-
fold increase, so the behaviour is genuinely controllable by this dial. But the
physics vanished with it: the specialist's formulas, which are right thirty times
out of thirty on its own, were right **zero** times out of thirty in the turned-
down combination.

So the dial does not blend the two specialists. It picks a winner. Turn it one
way and you have a procedure with no knowledge; turn it the other and you have
knowledge with no procedure. There does not appear to be a setting in between
that gives you both, and we have no reason from the data to expect one.


**Attempt three: stop asking them to speak at the same time.** Everything above
assumes both patches are applied at once and must somehow share the sentence.
They do not have to. The specialist can write the *name* of the next quantity and
stop; the procedure patch can then be switched on, write the calculator request,
and switch off; the harness answers it; the specialist resumes. At no point are
both active, so there is nothing to argue about.

**This worked.** Asking went from 0.6 times per problem to **4.7** — eight times —
and accuracy more than doubled. The competition is not a property of the two
patches; it is a property of making them produce the same word. Take that away and
both behaviours survive.

**And it exposed a different problem, which is now the open one.** In the split we
measured, the specialist named the quantity and the *procedure patch* had to write
the formula — and the procedure patch knows no physics. A control that removed it
entirely, letting the specialist write its own chain and having a few lines of
ordinary code execute the arithmetic exactly, scored **23 of 30** against the
turn-taking arrangement's **9 of 30**.

### What we do not know

The original question is answered: two independently trained patches **do** both
express their behaviour, provided they take turns instead of sharing a sentence.

What replaces it is harder to be comfortable about. **We do not know that a
learned procedure patch is worth its weights at all.** On this material a few
lines of ordinary code beat it — and not narrowly. That is not surprising once
stated: there is exactly one tool here, and asking for it means copying an
expression the specialist has already written. Copying is what ordinary code is
for.

The procedure patch would have to earn its place somewhere the request is *not* a
copy — several tools to choose between, arguments that need shaping, a decision
about which one fits. We believe that is where the difference lives. We have not
built that material, so we cannot claim it.

There is also a measured bias in the turn-taking number that we should not hide:
the procedure patch tends to write `A = 2 * 3 = 6` inside the request, and the
calculator refuses it — 16% of its requests, touching 11 of the 30 problems, none
of which passed. Accepting every recoverable form would raise its score to around
20 of 30, still below the control. The bias is real; it does not change which
arrangement wins.

### How we would know it was solved

The composition question is closed by the numbers above. What is left needs a
different measurement: material with several tools, where choosing and formatting
the request is genuinely work. Solved would look like the learned procedure patch
beating a hand-written rule on that material — with the hand-written rule actually
built and given a fair try, because a comparison against a rule nobody wrote is
not a comparison.

## Problem 2 — choosing the right specialist, and whether choosing well is worth anything

### What we see

If the system holds many specialists, something has to decide which one answers a
given request. The design's answer is elegant: while the expensive model is still
supervising, the system is already recording how often each specialist agrees
with it on each kind of request. That record is a map of who is good at what, and
it comes free — it is a by-product of running the system, not a separate
evaluation you have to pay for.

The mechanism works. On the requests where the choice actually mattered, it picked
the right specialist nine times out of ten, and recovered almost all of the
benefit an all-knowing chooser would have gotten.

### Why the obvious test does not settle it

The trouble is the comparison. A far dumber method — reading a keyword out of the
request and looking it up in a table — did **exactly as well**. Not close: tied.

That has now happened twice, on two different sets of material, and it is not a
coincidence. Both times, the material we were testing on effectively announced its
own category in the text of the request. A request that says which department it
came from does not need a clever router; it needs a lookup. Our test material was
labelled, so the cheap method could read the label, and any comparison on that
material measures nothing.

This is a general trap and it is worth stating on its own: **when a sophisticated
method ties a trivial one, the first thing to suspect is the test, not the
method.** A test where the trivial method is expected to succeed cannot show you
anything about the sophisticated one.

### What we do not know

We do not know how to build a test where choosing well is genuinely hard — where
the right specialist for a request cannot be identified from the words in it.

That requires material where surface and substance come apart: two requests that
look alike and need different specialists, or two that look different and need the
same one. We can imagine such material. We have not built it, and we do not yet
know whether it can be built without becoming artificial in a way that makes the
result meaningless in the other direction.

Until then we cannot say what the routing mechanism is worth. We can say it works.
We cannot say it is better than a lookup table, and we have twice measured that it
is not.

### How we would know it was solved

A set of requests on which the keyword method performs at chance, and the
agreement-based method still picks correctly. Without the first half, the second
half proves nothing.

## Problem 3 — a specialist that does not know the edge of its own expertise

### What we see

The physics specialist was trained on six kinds of problem. Hand it a seventh —
still fluid mechanics, still the same style of question, just a kind it never
saw — and it produces a confident, well-formatted, wrong answer.

This is now measured properly rather than glimpsed. Scoring its *formulas* rather
than its arithmetic, the specialist is right **thirty times out of thirty** on the
material it was trained for and **once out of twenty** on two kinds it was not.
The drop is not gradual, and the problems either side of it look alike.

What the failure looks like matters more than the number. It keeps the numbered
structure, the confident phrasing and the plausible vocabulary, and makes the
physics up: a "volume fraction" that is not one, a regime test that is not the
regime test, a force law that is not the force law. The same specialist that
scores perfectly on its own material wrote that, in the same voice.

It does not hesitate. It does not say the problem is unfamiliar. It answers the
way it answers everything.

This matters more than an accuracy number, because of how the system is supposed
to be used. The whole plan is to let a specialist take over a category of work
once it has proven itself on that category, and to stop paying for the expensive
model on that category. If a specialist cannot tell when a request has drifted
outside what it proved itself on, then "proven on this category" is a promise it
cannot keep. The first request from just outside the boundary gets a confident
wrong answer with nothing watching.

### What we do not know

We do not know how to give a specialist a usable sense of its own boundary.

The obvious approach — ask it how confident it is — is known to be unreliable, and
in our own runs the wrong answers arrive with exactly the same fluent presentation
as the right ones. There is no visible difference to key on.

There is a second, quieter version of the problem. Even if a specialist could
recognise unfamiliar requests, the system needs to decide the boundary of a
category **before** it stops paying for the expensive model, and the only evidence
available at that point is the record of agreement described in Problem 2 — which
tells you where the specialist has been tested, not where it stops working. Those
two are not the same, and the difference between them is exactly the region where
a confident wrong answer will appear.

### How we would know it was solved

A specialist that declines, or defers upward, on material outside its category at
a much higher rate than on material inside it — measured on both, with the
comparison made explicit. A method that makes it decline on everything is not a
solution, and the measurement has to be built so that it cannot be passed that
way.

## Problem 4 — who grades the work once the teacher leaves

### What we see

The design has two phases. In the first, an expensive model does the work while
the specialists watch and are scored on how often they would have produced the
same thing. In the second, the specialists that scored well enough take over and
the expensive model is dismissed.

The plan also calls for the specialists to keep improving after that — variants
compete, the better ones survive. That requires a grade, and the grade has to come
from somewhere.

### Why grading yourself does not work

If the grade comes from anything inside the improvement loop, the loop optimises
the grader rather than the work. This is not a hypothetical risk; the failure is
well documented in general and this organisation has its own instance of it, where
a change that looked like a genuine capability gain on one model turned out to be
the model compensating for how it was being asked, and not a gain at all.

So the grade has to come from a judge the loop cannot influence, and that judge has
to be right often enough to be worth obeying.

### What we do not know

In our experiments we had a perfect judge for free: the problems were generated
from closed-form formulas, so the exact answer was known before the question was
asked. That is why the results in this project are trustworthy, and it is also why
they do not transfer. Real work does not come with an answer key.

We do not know where the judge comes from in a domain that has no oracle. The
candidates all have visible problems. A second AI model as judge shares the blind
spots of the thing it is judging. A human is accurate and far too slow and
expensive to close a loop with. Tests written in advance only cover what someone
thought to write down.

We have not chosen among these, and we have not designed the experiment that would
choose. This is the least-explored problem in the project and it sits underneath
the entire self-improvement half of the design.

### How we would know it was solved

A judge, in a domain with no answer key, whose verdicts agree with careful human
review often enough to act on — measured against that human review on a sample,
with the disagreements examined rather than averaged away.

## Problem 5 — the central measurement cannot be taken between different model families

### What we see

The measurement the whole design rests on is: *how often does the small model
produce exactly what the expensive model would have produced?* Done at the finest
grain, this is nearly free — it falls out of a technique where a small model
proposes text and a large one checks it, which is already used to make systems
faster, and it turns that speed trick into a continuous quality score at no extra
cost.

That is genuinely elegant, and it is the reason the architecture is shaped the way
it is.

### The substitute we use, and what it costs

It only works if both models chop text into the same pieces. Models from different
families do not: the same sentence becomes a different sequence of fragments in
each. So the fine-grained measurement cannot be taken between a small model of one
family and an expensive model of another, which is the exact pairing the design
calls for.

We measure a coarser thing instead: whether the two arrived at the same answer.
That works, and we validated it — but only after discovering the hard way that our
first attempt at a text-level version was measuring **layout**. Two identical
answers scored zero agreement because one was indented and the other was not, and
a model that got the right answer scored zero against a model that got it wrong.
Switching to compare answers rather than text fixed it, and cost us the fine grain:
we now learn one number per request instead of a signal at every word.

### What we do not know

We do not know how to recover the fine-grained measurement across model families.

Keeping to one family sidesteps it, but then the expensive supervisor has to be a
large model of the same family as the small one — which constrains the choice of
supervisor to whatever that family offers, and the whole premise is that the
supervisor should be the best available model, not the best available *relative*.

Translating between the two chopping schemes is possible in principle and lossy in
practice, and we have not measured how lossy, or whether what survives is still
worth having.

### How we would know it was solved

A fine-grained agreement score between two different families that tracks the
coarse answer-level score we already trust — measured on the same requests, so the
two can be compared directly, and the cases where they disagree examined rather
than averaged.

## What is only work, not a mystery

Not everything unfinished is unknown. These are things we know how to do and have
not done, and it is worth separating them so the genuinely open problems above
stay visible:

- **Re-testing whether agreement ranks specialists correctly**, now that there is
  a real gap between the expensive model and the small one. The earlier test was
  run against near-equals, where there was nothing to rank. The instrument exists
  and the material exists.
- **Measuring the boundary problem properly.** The 0-of-10 result on unfamiliar
  problems came from a run that was cut short and never saved. Re-running it is an
  afternoon.
- **Pricing what it costs to hold many patches at once.** Our first attempt
  measured our own test harness rather than the serving system, and is void. Doing
  it properly is known work with a known tool.
- **Sharing computation between patches.** Two specialists working on the same
  request currently repeat work that could in principle be shared. This is a real
  engineering problem with a real cost, but it is engineering, not a question
  without an answer.

## How to read the numbers in this document

Every figure here comes from a run recorded in [`results/`](../results/), and
several of them replaced an earlier figure that was wrong. That is deliberate, and
the corrections are kept visible rather than tidied away, because the way these
measurements fail is itself one of the findings.

Two examples, both from a single day, both in the direction that flattered us and
then in the direction that did not.

We reported that the expensive model beat the small one by a very large margin.
Then we noticed that every measurement of the small model had been taken while
instructing it **not to show its working**, while every measurement of the trained
version had been taken while instructing it to show its working. The same small
model scores zero out of thirty under the first instruction and fourteen out of
thirty under the second. Roughly half of the gap we had published was the
instruction, not the models. The corrected gap is still large enough to be worth
closing, and it is the one quoted above.

Immediately after that, the corrected comparison produced a much *smaller* gap —
and that was wrong too, in the opposite direction. The expensive model writes long
derivations, and it had been cut off partway through by a length limit; the
scoring then picked up a half-finished intermediate value and marked it wrong.
Given room to finish, it scores perfectly. Publishing the small number would have
been the same mistake as publishing the large one, only flattering a different
conclusion.

The lesson we draw, and the reason this section exists: **a measurement that
agrees with what you expected is not thereby verified.** Both of these were caught
by looking at what the models actually wrote rather than at the score.
