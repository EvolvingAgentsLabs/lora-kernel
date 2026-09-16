# P53 — step zero: the number is +0.689 and the number is void

**[ran]** 2026-09-16, one A100. Session stopped cleanly.
Brief: [`BRIEF.md`](BRIEF.md).

## What the arms said

| arm | correct | did not run |
|---|---:|---:|
| `Qwen/Qwen2.5-3B-Instruct` | **56/180 = 0.311** | 38 |
| + `code-python` | **180/180 = 1.000** | **0** |

Paired over the same 180 cases: the adapter wins **124** the base loses and loses
**0** it wins; exact sign test **p < 1e-5**. By the pre-registered gate — delta ≥ 0.10
**and** the arms differ — **step zero passes.**

## And the number does not mean what it says

| check | result |
|---|---:|
| held-out **prompts** appearing verbatim in training | **0 / 180** |
| held-out **completions** appearing verbatim in training | **180 / 180** |
| similarity to the nearest training completion, median | **1.000** |

**Every held-out completion is already in the training set, word for word.** Two
different held-out programs, different polynomials, different inputs:

    POLY = 0x9823B6E1 | INIT = 0xFFFFFFFF | FINAL = 0x00000000 | DATA = b"ghdkvdnakt-"
    POLY = 0xEB31D82E | INIT = 0x00000000 | FINAL = 0xFFFFFFFF | DATA = b"tlebauifelnhl"

— and an identical completion:

        reg = (reg >> 1) ^ (POLY if reg & 1 else 0)
    return (reg ^ FINAL) & 0xFFFFFFFF

    print(crc(DATA))

**The adapter did not learn to compute anything.** It learned that after
`def crc(data):` come exactly these lines — and because the constants are referenced
**by name**, that one tail is correct for every instance of the family.

## And I caused it, with the previous fix

The corpus split found that the deepest cut removed the line holding a program's
**input**, so two programs produced an identical prompt with different answers. The
fix moved the cut so that *everything above the implementation is never removed*.

**That put every varying value in the prefix and left the tail constant.** The repair
for the collision created the memorisation. Parameterising the *constants* did nothing
about it, because the constants are the part that never has to be written.

**So the +0.689 measures one memorised tail per family.** It is not evidence that a
LoRA learns to complete code on this base, which is the only thing step zero was for.

## What survives

- **The mechanism runs.** Training in a subprocess, the adapter loading, C18 passing,
  execution-based verification over 360 completions with **zero transport errors**.
  Every piece of machinery works.
- **The base's number is real:** 0.311, with **38 of 180** completions failing to run
  at all. That is a usable baseline for a suite that is not broken.

## What has to change, and it is one thing

**The completion has to vary with the instance.** Inline the constants at their use
site instead of naming them at the top, so the tail itself carries `0x9823B6E1` and
two programs of one family never share an answer. The problem statement stays in the
prefix as a comment; what is *written* becomes unique per case.

That is a suite change. **It is the second post-result redesign of a suite today**, and
the counter is now at two — once is fine, twice is suspicious, three times is looking
for the result.

## The honest classification

Today's failures were mostly implementation — a missing `trl`, an unwatched prefix,
tool-call flags, held GPU memory. **This one is not.** It is a design error in the
examples, it was introduced by a fix to another design error in the examples, and it
would have been invisible in the number: a clean +0.689 with p < 1e-5 that means
nothing.

**It was caught by asking what the number meant rather than by reading it.**
