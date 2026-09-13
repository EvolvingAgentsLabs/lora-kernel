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

**And two patches do compose, provided they take turns.** Applied at once they
fight for every word; alternated — the specialist names the next quantity and
stops, the procedure patch writes the request, the tool answers, the specialist
resumes — asking goes from 0.6 times per problem to **4.7**. The competition was
never a property of the patches. It was a property of making them produce the same
word.

**And there is now material where the tools are genuinely necessary.** An earlier
suite failed its own purpose: the specialist had memorised the fourteen table values
it needed, so it scored 27 of 30 while asking for nothing, and a suite whose tool
calls can be recalled cannot measure what a tool layer is worth. Giving each problem
its own handbook — a substance with an invented name and properties that exist only
in that problem — drops the same specialist to **6 of 30 when it cannot ask**. The
value was not in training and is not in the question, so it has to be requested.

**There is real room to improve.** An expensive model scores perfectly on this
material and the small one scores under half, so there is a genuine gap for a
specialist to close. (We nearly fooled ourselves here, and the story is in
["How to read the numbers"](#how-to-read-the-numbers-in-this-document) below.)

So: the two halves exist, each is healthy on its own, and putting them in one
patch works. The problem is putting them in **two** patches, which is the entire
point of the design.

## Where this stands, 2026-09-12

Three of the four problems below have moved since they were written, and one of
them closed. The sections keep their original text — that is what makes them worth
re-reading — and this is the delta.

**Problem 1 is closed twice over.** Taking turns solved the composition, and the
suspicion that survived it — that the tool calls were memorisable, so the tool
layer was decoration — was tested and removed: with a handbook drawn per case, a
control with **no tool layer at all** falls from 27/30 to **6/30**. On that
material a learned protocol reproduces **94 of 96** of the oracle's calls against a
hand-written rule's **93 of 96**. The brief fixed before the run that three values
is a tie, so it is reported as a tie, and the remaining difference is character
rather than score: the rule makes 96 calls with **none refused**, the kernel makes
116 with **20 refused**. `results/P21-handbook-20260911/`.

**Problem 2 is unchanged and Problem 3 has a signal it did not have.** The
behavioural guard stays falsified. A **structural** one survives: dimensional
algebra over (kg, m, s) flags **0.80** of out-of-region work on families sealed
before the checker existed. Alone it false-alarms on 0.22 of correct in-region
work, which is unusable — but escalating only when the dimensional **and**
mechanical checks both fail **never fires in region at all** (0 of 60) and still
catches 0.35 of the work outside it. `escalate.has_left_its_region` is that rule;
`escalate.is_probably_wrong` is the wider one, which takes delivered accuracy from
0.53 to 0.83 in region and sends half the in-region work away to do it. **Which is
right depends on what escalation costs, and this repository has not measured that.**
`results/P22-dimensions-20260912/`.

**Problem 4 has its criterion.** Agreement with a target that is genuinely ahead
orders four candidates the way verified quality does — **6 of 6 discriminable
pairs**, including the pair a parameter count gets backwards, where a 12B model
ranks below a 4B. The honest half: only the **17** cases the target got wrong can
separate the criterion from the oracle, and on those alone it is 4 of 6 with two
unresolved and none inverted, off three reproduced errors.
`results/P23-ranking-20260912/`.

**What is still true of all four**: nothing here has been measured outside fluid
mechanics, and the hand-written rule a learned protocol ties is 144 lines that know
this suite's vocabulary. **Portability is the unbought experiment**, and it is the
one the tie in Problem 1 actually turns on.

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

## Problem 3 — a specialist that cannot feel the edge of what it knows

**This is the problem that blocks the product, and it is stated here in full so it
can be handed to someone with no other context.**

### What we see

We trained a specialist on six kinds of fluid-mechanics problem, then gave it two
kinds it had never seen — same subject, same style of question, differing only in
which physical relation they need.

Scoring its **formulas** rather than its arithmetic: **30 out of 30** inside its six
kinds, **1 out of 20** on the two it never saw. The drop is not gradual.

And the part that matters more than the number: **nothing in its output marks the
difference.** Same numbered structure, same confident phrasing, same plausible
vocabulary. It invents the physics:

    2. Volume fraction: 4/3 * pi/6 = 0.698132
    4. Stokes regime? v*d/(rho*mu) = 3.88*0.304/(998.0*0.001002) = 1.12832 < 1
    6. Drag force F = rho v^2 C_d / (2 S) = 998.0*3.88**2/(2*0.698132)

A "volume fraction" that is not one. A regime test that is not the regime test. A
force law that is not the force law. The specialist that scores perfectly on its own
material wrote that, in the same voice.

**So the second phase of the design is a promise the system cannot keep.** It says
"proven on this region", and the first request from just outside gets a confident
wrong answer with nothing watching. Worse, and structurally: the evidence available
when that decision is made is the record of where the specialist **has been
tested**, not where it **stops working**. Those are different sets, and the
difference between them is exactly where the confident wrong answer lives.

### What we tried, and what each attempt ruled out

**Ask the model how confident it is.** Not bought, because our own runs answer it:
wrong answers arrive with the same fluency, structure and vocabulary as right ones.
There is nothing visible to key on.

**Watch the process instead of the model.** The specialist works by calling tools,
and a harness answers those calls. Outside its region it names quantities it does
not understand, so perhaps the *tool layer's* failures mark the edge that the prose
does not.

Six candidate signals were listed **before any was looked at** — calls per problem,
rejected calls, rejection rate, steps, chains with nothing evaluable, transcript
length — and all six checked. One separated on both configurations: **the rate at
which the tool refuses what the chain asks for**, 15% inside against 63% outside,
classifying 86% of cases with a single threshold.

**And it failed confirmation.** The signals had been chosen with the answers visible
and the threshold fitted on the same fifty problems that scored it, so a
confirmation was pre-registered: two *new* kinds of problem, threshold **fixed**.
Outside the region the tool refuses at **0.18** against **0.15** inside, and the
guard scores 0.62 where chance is 0.60.

**The 86% was a property of those two kinds of problem, not of a boundary.** The
cheap direction — read the process rather than the model — is exhausted: the process
does not know either.

### What is left, and why each is unattractive

**A second specialist whose disagreement flags the edge.** Doubles the cost of every
guarded request, and only detects an edge where some *other* specialist happens to
be competent — not the same set as "outside this one's region", and possibly a small
fraction of it.

**Sample the expensive model after withdrawal.** The industry answer; it works, and
it costs money forever on every guarded request, which is the cost withdrawal exists
to remove. It turns a step change into a discount.

**Shrink regions until the edge is far away.** Multiplies specialists and routing
burden, and does not remove the problem — it makes the first out-of-region request
rarer and no less confident.

### What a proposal has to satisfy

Each of these is here because something we tried failed on it.

1. **No consulting the expensive model on the guarded path.** A guard that pays for
   what it replaced is not a guard. Sampling a fraction offline is a different
   proposal, allowed, but its cost must be stated as a fraction and defended.
2. **No relying on the specialist's self-report.** Measured: wrong answers are
   indistinguishable in presentation from right ones.
3. **No needing the correct answer at serving time.** If it had that, the specialist
   would be unnecessary.
4. **It must separate "outside the region" from "inside and difficult".** A detector
   that fires on every hard problem costs throughput and will be switched off.
5. **Any threshold must be fixable in advance.** A threshold tuned on the material
   it is tested on is the mistake that killed the last candidate.
6. **Cheap enough to run on every request**, or its sampling rate is part of the
   proposal.

### How we would know it was solved

Accuracy separating in-region from out-of-region material, **on kinds of problem the
proposal was not developed against, with any threshold fixed beforehand** — reported
beside the rate at which it fires on hard-but-in-region problems, because a guard
that cannot tell those apart is unusable however good its headline looks.

**The bar is low and nothing has cleared it: our best candidate scored 0.62 where
chance was 0.60.**

The instruments exist: problems with exact ground truth in kinds no specialist was
trained on, transcripts whose correctness is known, a judge that is right 82% of the
time without seeing the answer, and a pre-registration discipline that treats a
candidate found by searching as a hypothesis until it survives material it was not
found on.

### The narrow version of the question

Not "how does a model know what it does not know", which is a research programme,
but:

> Given a specialist measured as competent on a set of examples, and a new request,
> is there anything **cheap and observable** — in the request, in the specialist's
> behaviour, in the tools it uses, or in comparisons that do not involve the
> expensive model — that distinguishes a request it will handle from one it will
> answer confidently and wrongly?

We have measured that the answer is not the model's confidence and not the tool
layer's failure rate. We do not know what else to look at.

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

**A judge exists, and that much is now measured.** Over 100 chains whose
correctness was known — 33 right, 67 wrong, so answering "wrong" every time scores
0.67 — a large model grades at **0.89**, balanced on both classes, and a model the
same size as the one being graded manages **0.82**.

**And the useful half is the small model's pair of numbers.** It *solves* this
material at 0.467 and *judges* it at 0.82. **Judging is easier than solving**, by a
wide margin, for the same model on the same problems. That is what makes the
improvement loop buildable after the expensive model leaves: the grade does not have
to come from something that could have done the work.

**One combination is better than either judge alone.** A purely mechanical check —
re-run the chain's own arithmetic and ask whether its answer follows — accepts 94%
of correct work and only 52% of wrong work, the opposite error profile to the model
judge. Requiring **both** to accept drops false acceptance of clean-looking wrong
work from **41% to 2%**, at a cost of six points of correct work, and it comes out
nearly calibrated.

**What we still do not know is the case that matters most.** The large model judges
well here partly because it can *solve* this material — it scores perfectly on it.
Where nothing available can solve the work, judging is untested, and that is
precisely the domain where a specialist would be worth having. Nothing in these runs
speaks to it.

**And selection is not accuracy.** A judge right 82% of the time can still rank two
candidates the wrong way round. On pairs with a real gap the conjunction orders them
correctly, but that is two pairs, and the candidates were not produced by an
improvement loop — so nothing shows that repeated selection converges, or that a loop
optimising this grade would not learn to satisfy both judges while being wrong.

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
  a real gap between the expensive model and the small one, and a judge to compare
  it against. The earlier test was run against near-equals, where there was nothing
  to rank. The instrument exists and the material exists, and this has been listed
  here long enough to be embarrassing.
- **Measuring the acceptance rate the design is named after.** The architecture
  rests on how often a small model produces exactly what a large one would, and we
  have never computed it — we substituted a coarser answer-level agreement because
  models of different families cut text differently. Within a single family the
  fine-grained version is measurable, we have the models, and it has never been
  bought. This is the most conspicuous gap in the project.
- **Forbidding the malformed call outright.** A tool request can be made
  syntactically impossible rather than merely unlikely, by constraining what the
  model is allowed to write at each step. It was set aside when syntax was not the
  dominant failure; it has since cost 19 of 118 requests in one run, which is a
  different argument than the one that shelved it.
- ~~Measuring the boundary problem properly.~~ **Done, and it is worse than the
  cut-short run suggested**: formulas exact 30 times out of 30 inside the region and
  once out of twenty outside it. What is left is not a measurement but a guard, and
  the first candidate is in Problem 3.
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
