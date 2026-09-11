# P19 — S7, the tournament: does a judge's grade pick the better variant?

**Why this is buyable now.** P17 measured that a judge exists and, more usefully,
that **judging is easier than solving**: `qwen3.5:4b` solves this material at 0.467
and judges it at 0.82 **[ran]**. So the grade the tournament needs does not have to
come from something that could have done the work — which is the only way a
tournament can run *after* the frontier is withdrawn.

**But per-item accuracy is not selection.** A judge that is right 82% of the time
can still rank two variants the wrong way round if its mistakes lean one way. The
tournament's actual requirement is **ordering**, and nothing so far measures it.

## The design, and why it costs nothing

The spec's fitness is `w₁·verified success + w₂·α − w₃·tokens`. `w₂` needs a
frontier and is dropped here; what is measured is whether `w₁`, supplied by a judge
the loop cannot influence, **orders candidates the way the oracle does**.

The candidates already exist. Every arm of P13, P14 and P15 is a configuration with
outputs on disk and a **true accuracy known from the oracle**. Scoring them with the
peer judge and comparing the two rankings is arithmetic plus one local model, and no
GPU.

| candidate pool | true accuracies span |
|---|---|
| P13 · sequential, control | 9/30 and 23/30 |
| P14 · the same two, outside the region | 0/20 and 1/20 |
| P15 · kernel, rule, no-tool-layer | 10/30, 6/26, and the third when it lands |

**Pairs are compared only within a shared evaluation set**, because two arms scored
on different problems are not candidates for the same tournament.

## Falsification, written before the run

**If the judge's ranking disagrees with the oracle's on half the comparable pairs,
selection fails and S7 fails with it** — a judge accurate per item but useless at
ordering. That would be a finding worth more than a working tournament, because it
would say the fitness function in the spec cannot be built the way it is written.

**A second thing to watch, and it is reported either way**: the token term. If
`w₃ > 0` flips a pair the grade got right, the fitness function punishes the
behaviour that makes an expert correct — and P13 already showed that delegating
more is what correlates with getting the answer right.

## What this is not

**It is not a tournament yet.** Seven candidates the loop did not breed are a
selection test, not evolution. The machinery that generates variants and iterates
is the second half, and it needs a GPU; this half decides whether it is worth
building at all.

**And the sample is small and stated up front:** at most five comparable pairs.
A ranking that agrees on five pairs is encouragement, not proof.

**Redesign count: 0.**
