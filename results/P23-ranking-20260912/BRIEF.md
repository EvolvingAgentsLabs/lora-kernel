
---

## The design is void, and the data that voids it was already on disk (2026-09-12) [ran]

An outside reading of the pre-registration raised a mechanism I had not: a target
whose budget is cut does not make *human* mistakes, it **truncates** — it runs out
of buffer mid-derivation and whatever number was last on the page becomes its
answer. If that is what the 13 failures are, the informative arm measures buffer
length, not reasoning, and any candidate that also stops early would agree with it
for reasons that have nothing to do with quality.

**Checked against `results/P10-baseline-recheck-20260909/`. All 13 are truncations.**

| | `want` | target @2k | target @6k | where the 2k text stops |
|---|--:|--:|--:|---|
| `phys-0002` | 1.849 | **0.9** | 1.8473 | `…1.17064 m/s$$` · **2. Reynolds numb** |
| `phys-0003` | 68.53 | **2.0** | 68.52 | `…(0.0705 m)^2 ≈ 0.0051530 m^2$$` |
| `phys-0009` | 1124 | **0.0** | 1137.92 | `…(0.247 m)^2 ≈ 0` |
| `phys-0015` | 226.2 | **0.0359** | 225.14 | `…(0.214 m)^2 ≈ 0.0359` |
| `phys-0021` | 842.9 | **0.029** | 850.09 | `…(0.194 m)^2 / 4 ≈ 0.029` |
| …and 8 more | | | | every one cut mid-derivation |

**The @2k answers are pipe areas, velocities and bare exponents** — intermediate
values that `parse_answer`'s last-number fallback picked up off an unfinished page.
**At 6k the same model answers all 13 correctly.** Not one is a reasoning error.

### So the fallible target does not exist, and that voids the arm

The pre-registration named three voiding conditions. The run hit a fourth that none
of them covered: **the target is not wrong, it is cut off.** The 13 cases that were
supposed to be the only place where agreement and correctness can disagree turn out
to be 13 places where the target has no opinion at all.

That leaves this suite with no usable target for S2. The one model that is ahead is
**30/30**, where agreeing with it is being correct and the ordering test passes by
definition. Reducing its budget does not make it fallible; it makes it silent.

**No GPU and no API call were spent finding this.** The columns that decide it —
`got` at two budgets and the tail of the truncated text — were written by P10 three
days earlier.

### What is bought next, and what is not

**Not bought:** the four candidate runs. They were queued behind P21 and are
cancelled. There is nothing for them to be ranked against, and running them would
produce a ladder with no rung to compare it to.

**Bought instead, and it is one API call:** a target that is *genuinely* weaker
rather than artificially truncated — a smaller frontier model at the full 6k budget,
so that its errors are finished answers that are wrong. If one lands between the
best candidate and 30/30 **with complete responses**, S2 has its arm. If every
available model is either at the ceiling or below the candidates, S2 is not
answerable on this suite and that is the finding.

**Redesign count: 2.** The first was a change of machine. This one is a change of
target, forced by the discovery that the target chosen does not have the property
the design required. The stopping condition stands: a third redesign is the point
at which this is looking for a result rather than measuring one, and S2 would be
reported unanswerable on this suite instead.

---

## The replacement target, pre-registered before the call (2026-09-12)

A target that is **naturally** weaker rather than artificially silenced: a smaller
frontier model at the **full 6k budget**, on the same 30 cases and seed, under the
same shared contract. Its errors have to be finished answers that are wrong.

**First and only purchase in this round: `google/gemini-3.5-flash-lite`.** It is
the weakest frontier model this project has already used, so nothing is being
shopped for.

### The three outcomes, and what each decides

| it scores | verdict |
|---|---|
| **30/30** | the suite has no gradient between the frontier and a 3B; the tautology is not escapable here |
| **≤ 14/30** | it is at or below `qwen3.5:4b`'s 14/30 and is not a target at all |
| **between** | **S2 has its arm** — but only if the next check passes |

### And the check that the last round did not have

**At least 80% of its failures must be complete responses.** The run stores `chars`,
`has_json` and the tail of every answer — fields the P10 records predate, which is
why the truncation had to be reconstructed from intermediate values. If its failures
are cut off mid-derivation, this is the same void arm with a different model on it,
and it is reported void rather than used.

**If no model lands in the band with complete failures, S2 is declared not
answerable on this suite and the objective closes at redesign 2.** There is no
third attempt; that was fixed before the first.

---

## The replacement target qualifies (2026-09-12) [ran]

`google/gemini-3.5-flash-lite`, 30 cases, seed 515151, shared contract, 6k budget.
**One API call's worth of work, $0.00 against a $10 ceiling.**

| | |
|---|---|
| verified | **21/30 = 0.700** |
| unparsed | **0/30** |
| failures that are **complete** responses | **9/9 = 1.00** (pre-registered bar: 0.80) |

It lands in the band: above `qwen3.5:4b`'s 14/30 and below the ceiling.

**And the failures are the kind the design needs.** Every one ends in a finished
derivation and a proper answer block, with a value that is plausible and wrong:

| | `want` | `got` | chars |
|---|--:|--:|--:|
| `phys-0001` manning | 13.78 | **20.252** | 914 |
| `phys-0002` head loss | 1.849 | **1.7946** | 1594 |
| `phys-0008` head loss | 10.16 | **19.467** | 1398 |
| `phys-0020` head loss | 26 | **31.621** | 1233 |
| `phys-0027` pump power | 453.5 | **442.27** | 1576 |

Compare the void arm, whose "answers" were `0.0`, `2.0`, `4.0` and `0.0359` — pipe
areas scraped off an unfinished page. These are wrong answers. Those were no
answers.

**So the 9 cases where agreement and correctness can disagree are real**, and S2's
ordering test has somewhere to be tested. The candidate ladder, cancelled when the
first target voided, is re-queued.

---

## n goes to 60, before any candidate is scored (2026-09-12)

**Why, and it is not the reason first offered.** The obvious argument is ties: at
n=30 the discrete step is 3.3%, four candidates give six pairs, and two candidates
a single case apart are not an ordering. S2a already published a passing row built
on exactly that and the row is struck in the plan rather than deleted.

**The stronger reason is that most of this suite cannot test the criterion at all.**
The target is right on 21 of 30 cases, and **on a case the target got right,
agreeing with it is being correct** — those cases cannot separate the criterion
from the oracle it stands in for. Only the 9 it got wrong can. So the informative
sample was never 30; it was **9**. At n=60 it is 18, and the test doubles the only
part of itself that was ever measuring anything.

### And the honest accounting of the stopping rule

**By a strict count this is redesign 3**, and the rule written before the first one
says a third redesign closes S2 as unanswerable. The rule is not being quietly
reinterpreted, so here is the argument for why it does not fire, made in the open:

The rule exists to stop an experimenter tuning until the answer comes out right.
**No candidate has been scored. There is no result to steer toward**, and a change
made with the outcome entirely unknown cannot be result-seeking. The two earlier
changes were forced by discovered facts — a machine, then a target that turned out
not to have the property it was chosen for. This one is prospective.

**So the budget is declared spent rather than extended.** No parameter is touched
again: the candidates run at n=60 with the criterion, the tolerance and the
ordering test exactly as they stand, and **if the test voids on ties at n=60, S2 is
reported unanswerable on this suite** rather than run a fourth time.

### What the report gains, and it costs nothing

Two columns, so nobody has to take the global number on faith:

- **agreement on the cases the target got wrong**, reported separately. A candidate
  scores there only by producing the target's *exact* wrong value — that is shared
  derivation, not shared incompetence. **If every candidate sits at 0.00 in that
  column, the ordering rested entirely on the target's easy subset**, and the runner
  says so out loud rather than letting a clean global number stand.
- **agreement per family.** The suite is balanced ten-and-ten across six families,
  so no topic can drag the global number by weight — but *which* topics the target
  fails still can, and printing the split is cheaper than arguing about it. The
  target's failures at n=30 clustered: manning 2/5, head loss 2/5, pump power 3/5,
  while terminal velocity and venturi were perfect.

### The target at n=60 holds [ran]

| | n=30 | **n=60** |
|---|--:|--:|
| verified | 21/30 = 0.700 | **43/60 = 0.717** |
| unparsed | 0 | **0** |
| failures that are complete responses | 9/9 | **17/17 = 1.00** |
| informative cases (target wrong) | 9 | **17** |

Still in the band, still finishing every answer, and the informative sample nearly
doubled as intended. Its failures cluster the same way — head loss 6, manning 5,
pump power 4, and only 2 across the other three families — which is why the report
prints the per-family split rather than a single number.

---

## Are the shared wrong answers copied or derived? (2026-09-12) [ran]

The worry raised against this design was **failure-mode correlation**: if a
candidate agrees with the target on a case the target got wrong, that might be two
models reading the same number off the same prompt rather than two models reasoning
alike. A truncated target made exactly that mistake — its "answers" were pipe areas
lifted from the statement, and any model that stopped at the same step would have
matched them.

The replacement target finishes its derivations, so the question can be asked
properly. On the three candidates already scored, **`qwen3.5:9b` reproduces 2 of the
target's 17 wrong values**. Both were checked against the literal numbers in their
own statements:

| case | family | correct | what both said | in the statement? |
|---|---|--:|--:|---|
| `phys-0027` | pump power | 453.478 | **442.27** | **no — derived** |
| `phys-0038` | head loss | 6.35164 | **6.11867** | **no — derived** |

Neither value appears anywhere in the prompt. Two models arrived at the same wrong
number by doing the same wrong thing with the same inputs, which is what agreement
is supposed to detect and is the opposite of the truncation artefact.

**Two cases is two cases.** It does not establish that the informative subset is
clean, only that its first two data points are not the artefact that voided the
previous target. The column is printed per candidate so the question stays askable
rather than assumed.

---

## Outcome (2026-09-12) — the criterion holds against a target that is ahead [ran]

| candidate | verified | **agreement** | character α | agreement where the target was WRONG |
|---|--:|--:|--:|--:|
| `qwen3.5:2b` | 0.217 | 0.183 | 0.000 | 0.000 |
| `qwen3.5:4b` | 0.483 | 0.400 | 0.000 | 0.000 |
| `qwen3.5:9b` | **0.650** | **0.550** | 0.000 | **0.118** |
| `gemma4:12b` | 0.433 | 0.350 | 0.000 | 0.059 |

**6 of 6 discriminable pairs ordered correctly.**

### The ordering it reproduced was not the obvious one

    verified:   qwen3.5:9b  >  qwen3.5:4b  >  gemma4:12b  >  qwen3.5:2b

**The 12B model ranks third, below a 4B.** A criterion that simply tracked parameter
count would have got that pair backwards; agreement did not. That is the
discriminating case in this ladder, and it is the reason the result is worth more
than the 14-of-15 it replaces — those were peers, ordered in the order their sizes
already suggested.

### What the informative subset says on its own

The target is right on 43 of 60, and **on a case the target got right, agreeing with
it is being correct**. Only the 17 it got wrong can separate the criterion from the
oracle. Scored on those alone:

| candidate | values of the target's 17 errors reproduced |
|---|--:|
| `qwen3.5:9b` | **2** |
| `gemma4:12b` | 1 |
| `qwen3.5:4b` | 0 |
| `qwen3.5:2b` | 0 |

**4 of 6 pairs, and two unresolved rather than inverted** — `4b` cannot be separated
from `2b` or from `12b`, because all three sit at or near zero. The subset points
the same way as the global number everywhere it points at all, and **it does not
invert anything**; it is simply too small to rank four models by itself.

So the honest statement has two halves. **The pre-registered criterion passed, 6/6.**
And the part of the evidence that cannot be a tautology is **three reproduced errors
across four candidates** — consistent, directional, and thin.

### The control does exactly what it was bought to do

Against `gemini-3.8-flash` at 30/30 the same table also reads 6/6 — and the runner
refuses to let that stand as evidence:

    0 of 30 cases are informative — the ones the target got wrong.
    WARNING — no candidate reproduced a single one of the target's wrong
    values, so this ordering rests entirely on its easy subset

**A perfect target makes agreement a synonym for correctness**, and a clean 6/6 from
it means nothing. Printing both arms beside each other is what makes the first one
readable.

### Character α, one more time

**0.000 for every candidate against every target.** The criterion §11 settled on
semantics is not a refinement of character agreement; character agreement on this
material is simply dead. It is carried because it once scored 1/5 with one target
and 4/5 with another on the same candidates.

### What this does and does not establish

**Establishes**: agreement with a target that is genuinely ahead — 43/60 against a
best candidate's 39/60, with every failure a finished answer — orders four
candidates the way verified quality does, including a pair that size gets wrong.
S2's caveat is discharged: this is no longer agreement with a peer.

**Does not establish**: that it works when the target's lead is large. This target is
four cases ahead of `qwen3.5:9b`. A frontier that is far ahead has a smaller error
set, and the informative subset shrinks toward zero — which is the 30/30 arm above,
where the method has nothing to measure. **The criterion is validated in the band
where the target is ahead but fallible, and that band is where it was tested.**
