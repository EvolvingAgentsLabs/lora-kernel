# P53 — step zero: does a base model with the right LoRA complete these programs?

**Pre-registered 2026-09-16, before the run.**

## Why this before the profile

The order was wrong. P52 would have profiled where the difficulty sits — useful, but
it is an instrument step. **The smallest thing that shows the idea works or does not
is one expert on one language**, and if that fails nothing downstream is worth buying:
not a pool, not acceptance, not ranking.

## And the first definition could not run it

`reference.py` holds **fifteen hand-written programs**. That is an evaluation set; it
trains nothing. The definition had no answer to *where does the corpus come from*, so
step zero was literally unrunnable as written.

**`families.py` draws them instead.** The family fixes the shape — a reflected CRC
over a byte string, a xorshift with three shift amounts — and the instance fixes the
**constants**: this polynomial, these shifts, this input. So there is as much corpus as
we want, and **the expected output did not exist before the case was generated**, which
is P15's lesson: a suite whose values could be recalled was answered **27/30 without
using the tools at all**.

## What is measured

| arm | model |
|---|---|
| **base** | `Qwen/Qwen2.5-3B-Instruct` |
| **adapter** | the same base + `code-python`, trained on 600 drawn completions |

**180 held-out cases**, drawn from a different seed and de-duplicated by content.
Verified by **execution**: the completion is concatenated onto the prefix, run, and its
stdout compared to the answer the generator computed from an oracle written separately
from all three implementations.

**Paired**, because both arms answer the same 180 cases — `bar.compare`, a sign test.
Two accuracies side by side is how a run-to-run spread gets read as an effect: the same
adapter, the same cases, temperature 0, scored **84, 81, 82** across three runs
**[ran]** P36/P38/P40.

## The gate, pre-registered

**The adapter must beat the base by ≥ 0.10 and the paired test must call them
different.** Both, not either.

**Power, checked before the arm rather than after:** at n = 180 against a 0.30
baseline, a +0.10 improvement is seen **87%** of the time — above the 80% this
repository requires **[ran]**. P42 bought an arm that could not resolve its own effect
and found out afterwards.

**C18 first.** vLLM loads a LoRA, logs that it did, and can serve the base anyway.
Without that gate the two arms are one model and the sign test reports a tie truthfully.

## What falsifies the whole line

**A delta below 0.10, or a paired test that cannot separate the arms.** Then the
adapter has not learned the shape on the predicate chosen precisely because it
constrains — and the pool has nothing to be built from. That is worth knowing for one
session rather than three.

## One bug this brief exists because of

The corpus split found that at the deepest truncation a CRC program was reduced to its
constants and **lost the line holding its input**, so two programs with different
inputs produced an **identical prompt with different answers** — 5 of 180. No model
can be right about both. The cut now begins where the *implementation* begins;
everything above it states the problem and is never removed. **0 collisions in 600.**

## Cost and safety

One session: training ~600 examples, then two arms over 180 cases. Model-written code
is executed — on a disposable rented VM, with a timeout and no shell. There is no
sandbox, and saying otherwise would be worse than saying so.
