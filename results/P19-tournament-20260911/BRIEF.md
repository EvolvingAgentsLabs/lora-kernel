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

---

## Outcome (2026-09-11) [ran]

| candidate | true | judge fitness | taxed | chains showing an error |
|---|---|---|---|---|
| P13 · control | **0.767** | **1.000** | 0.931 | 8/30 |
| P13 · sequential | 0.300 | 0.567 | 0.488 | 11/30 |
| P14 · control | 0.050 | 0.000 | −0.064 | 16/20 |
| P14 · sequential | 0.000 | 0.100 | 0.002 | 16/20 |
| P15 · kernel adapter | **0.333** | 0.300 | 0.200 | 14/30 |
| P15 · hand-written rule | 0.231 | **0.538** | 0.448 | **0/26** |

**The judge orders 1 of 3 comparable pairs the way the oracle does — and the three
pairs are not equal.**

| pair | true gap | judge |
|---|---|---|
| P13 sequential vs control | 0.467 | **correct** |
| P15 kernel vs rule | 0.102 | wrong |
| P14 sequential vs control | 0.050 — **one case in twenty** | wrong, and meaningless |

Selection works on a wide gap and fails on a narrow one. The P14 pair should not be
counted at all: a difference of one problem out of twenty is noise given a judge
that is 82% accurate per item.

## Why the P15 pair went the wrong way, and it is not what it looks like

The obvious reading is that the judge punishes visible errors, and the arm that
cannot malform a call therefore looks better. The data says the opposite about
errors and something worse about the judge:

| among chains that are… | showing no error | showing an error |
|---|---|---|
| **actually correct** | judged correct 98% | 89% |
| **actually wrong** | judged correct **41%** | 7% |

**A visible error is a legitimate signal, not a bias.** It costs correct work
almost nothing (98 → 89) and lets the judge reject wrong work (41 → 7).

**The weakness is the other cell: the judge accepts 41% of wrong work that looks
clean.** The rule arm cannot malform a call — 0 of 26 chains show an error — so it
sits entirely in the cell where the judge is weakest, and its fitness is inflated
by false acceptance.

**So a fitness built on a transcript-reading judge selects for failing invisibly,
not for being right.** A variant whose mistakes are silent outranks one whose
mistakes are legible, even when the legible one is more often correct.

## What follows, and it is the same signal twice

The fix is not a better judge. It is to stop throwing away what the tool layer
already knows: **the count of calls it refused**. P16 found that same number marks
a region's edge; here it marks the difference between a variant that fails loudly
and one that fails silently. A fitness function that reads the judge *and* the tool
layer's rejections would not have preferred the rule.

That is a design change to `w₁`, and it is not made here — it is what this run
says the next one should test.

## Limits

**Three pairs, one of them noise.** This is encouragement and a mechanism, not a
result about tournaments. And the candidates were not bred by a loop, so nothing
here shows that selection *repeated* converges anywhere.

**The bug that nearly ended S7 on a dictionary key**: `phys-0000` is a hydrostatic
gate among the trained families and a falling sphere among the held-out ones. A
problems dict keyed on the case id alone let one overwrite the other, the judge was
shown the wrong problem for all sixty of P13's chains and called every one
incorrect, and the run read as "selection fails". It was caught because P17 had
measured the same judge at 0.97 recall on those same records, and 0.000 cannot live
beside that. The key now includes the pool and an assertion fails the run if any
chain lacks its problem.

**Redesign count: 0.** One bug fixed, the poisoned verdicts deleted rather than
reused.
