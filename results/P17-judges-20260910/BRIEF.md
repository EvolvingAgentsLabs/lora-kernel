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
