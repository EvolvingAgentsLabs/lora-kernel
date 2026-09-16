# P54 — step zero passes, for real, and the suite is exhausted by it

**[ran]** 2026-09-16, one A100. Session stopped cleanly. Brief: [`BRIEF.md`](BRIEF.md).

## The numbers

| arm | correct | did not run |
|---|---:|---:|
| `Qwen/Qwen2.5-3B-Instruct` | **27/197 = 0.137** | 56 |
| + `code-python` (retrained on 633) | **197/197 = 1.000** | **0** |

Paired over the same 197 cases: the adapter wins **170** the base loses and loses
**0**; exact sign test **p < 1e-5**. Delta **+0.863**.

## The leak check first, because P53 taught that

| | P53 | P54 |
|---|---:|---:|
| held-out completions verbatim in training | **180/180** | **0/197** |
| distinct completions produced by the adapter | — | **197 of 197** |

**This is not P53.** Every completion the adapter produced is different, and none was
in its training set. It generalised across constants drawn from the full 32-bit space.
**That is learning, and the +0.863 is real.**

## And what it learned is narrower than the number sounds

With the constants blanked, the 197 completions collapse to **6 distinct skeletons**:

    37 ×  def next_value(): … t = (x ^ ((x << N) & M)) & M …
    34 ×  x, y, z = y, z, w … w = ((w ^ (w >> N)) ^ (t ^ (t >> N))) & M …
    34 ×  for byte in data: reg ^= byte … for _ in range(N) …

Two families × three cut depths is about six (family, cut-point) combinations, and
each has exactly one correct skeleton. **The task is: recognise which of six applies,
and fill in constants that are readable in the spec comment.** An adapter trained on
633 examples of precisely that reaches 1.000.

**The base still only reaches 0.137**, so the task is not trivial — a model that has
seen far more code than our 633 examples cannot do it. What the adapter learned is
real. It is *this template family*, not "code completion".

## So what step zero actually established

**Yes.** A base model with the right LoRA does learn a completion task on this
predicate and does beat the base by a wide, paired, significant margin. That was the
question and it is answered.

**And nothing downstream can be measured on this suite.** An expert at 1.000 cannot be
ranked against another expert, and acceptance has nothing left to discriminate. This
is P42's ceiling arriving from the treatment side.

## What the next suite needs, named precisely

**Structural variety, not more constants.** The fix that failed twice was to vary the
*values*; what has to vary is the *shape* of the tail — loop form, decomposition,
naming, helper structure — so that recognising the family does not determine the
answer. More families would also work and is cheaper to write.

**A rough target:** the number of distinct skeletons should be of the order of the
number of cases, not six.

## Two process failures worth recording

- **`compare` takes two maps, not two counts.** The same `TypeError` ended P53 and
  then ended P54, because the first time it was **worked around** — the verdict was
  computed by hand — rather than repaired. A bug diagnosed and not fixed costs the
  same twice. Fixed now, with a test.
- **The brief's own warning was the thing that saved the reading.** It said *a perfect
  score is a warning, not a result, and the first thing to do with it is look for the
  leak*. That is why the leak check ran before the delta was reported, and why this
  result is a qualified yes rather than a headline.

## What survives for the next run

The machinery, again and entirely: subprocess training (vLLM started with no memory
complaint this time), C18, execution-based verification over 394 completions with zero
transport errors. And a base number of **0.137** on a suite that is honest about
depth — with **56 of 197** completions failing to run at all.
