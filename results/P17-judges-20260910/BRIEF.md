# P17 — using our oracle to grade the graders

**The problem.** Every trustworthy number in this project exists because the
problems were generated from closed-form formulas, so the exact answer was known
before the question was asked. Real work does not come with an answer key. The
self-improvement half of the design — the tournament, `w₁`, everything downstream
of S5 — needs a grade, and if that grade comes from anything inside the loop, the
loop optimises the grader instead of the work.

**The idea that makes this cheap.** We have a domain *with* an oracle. Hide it, let
candidate judges score work whose correctness we already know, and compare their
verdicts against the truth. That measures **judge quality with ground truth
available to judge the judge**, and it costs no new domain.

**The material, already on disk.** 100 chains from P13 and P14 whose correctness is
known: 30 in-region sequential, 30 in-region control, 20 held-out sequential, 20
held-out control. **33 correct, 67 incorrect.**

## The bar, stated before any judge runs

**67%** — the majority class. A judge that answers "incorrect" every time scores
that, and a judge that cannot beat it is not a judge. Accuracy alone is not enough
either: a useful grader has to find the *correct* work too, so recall on the
correct class is reported beside it and a judge that never says "correct" is called
what it is.

## The judges

| # | judge | what it costs, and what it risks |
|---|---|---|
| 1 | **`gemini-3.8-flash`** — the frontier, shown the problem and the chain, never the answer | ~$0.05. Shares the blind spots of the thing it grades |
| 2 | **`qwen3.5:4b`** — a peer of the model being graded | free, local. Shares them harder |
| 3 | **procedural** — no model at all: re-evaluate every step exactly and check the final answer follows from the chain | free. Catches arithmetic, is blind to a wrong formula |
| 4 | **always "incorrect"** | free. The bar |

Judge 3 is the interesting one, and it is the reason the tool layer keeps
reappearing in this project: it never asks a model anything, so it cannot be
flattered by one.

## Falsification, written before the run

**If no judge beats 67% by a margin worth acting on, there is no judge and S7 stays
blocked** — and that is a finding, not a delay: it would say the self-improvement
half of the design cannot be built on a domain without an oracle, and the project
should say so instead of assuming a grader appears.

**And if a judge does beat it, that is still not enough on its own.** A grader used
in a loop has to be right about the *correct* class too, or the loop discards good
work. Both numbers are reported.

**Redesign count: 0.**

---

## Outcome (2026-09-10) [ran]

| judge | accuracy | finds the right work | finds the wrong | said "correct" | abstained |
|---|---|---|---|---|---|
| always "incorrect" — **the bar** | 0.67 | 0.00 | 1.00 | 0 | 0 |
| procedural (no model) | 0.66 | 0.94 | 0.52 | 63 | 0 |
| `qwen3.5:4b` — a peer | **0.82** | 0.97 | 0.75 | 49 | 0 |
| `gemini-3.8-flash` — the frontier | **0.89** | 0.89 | 0.89 | 32 | 7 |

**A judge exists.** The frontier is balanced at 0.89 on both classes and says
"correct" 32 times where the truth is 33 — nearly calibrated, and far above a bar
that only clears by refusing everything.

**And the finding that matters is the peer's.** `qwen3.5:4b` **solves** these
problems at **0.467** and **judges** them at **0.82** **[ran]**
`results/P10-baseline-recheck-20260909/`. **Judging is easier than solving**, by a
wide margin, for the same model on the same material. That is what makes a
tournament buildable *after* the frontier is withdrawn: the grade does not have to
come from something that could have done the work.

**The procedural judge is the honest disappointment, and its shape is the lesson.**
It ties the trivial bar on accuracy while having the opposite error profile —
finds 94% of the correct work, only 52% of the wrong. It sees arithmetic and is
blind to a wrong relation, exactly as designed, and a wrong relation is what an
expert outside its region produces. It cannot be the guard on its own.

## The limitation this run cannot escape

**The frontier judges well here partly because it can solve the problem** — it
scores 1.000 on this material. Where no available model can solve the work, judging
is untested, and this run says nothing about that case. The peer result is the one
that generalises further, because 0.467 is not a model that can solve its way to a
verdict.

**A second limitation, stated rather than hidden**: 7 of the frontier's 100 replies
were not a verdict and are recorded as abstentions rather than folded into
"incorrect", which would have handed it the majority class for free.

## The instrument fault caught on the way

The first run gave the frontier **8 tokens** for a one-word verdict. A reasoning
model spends that in its thinking channel and returns an empty answer, so it
abstained on **100 of 100** and read as "cannot judge". Both judges were re-run at
400 tokens; the comparison would otherwise have been between token allowances.

**Redesign count: 0.** The bar and the judges were fixed before the run; only the
token budget changed, and the arm it invalidated was thrown away rather than
reported.
