# P54 — step zero, on a suite where the answer depends on the instance

**Pre-registered 2026-09-16, before the run.** Third of four granted sessions; two
remain after this one.

## Why P53 is being re-run rather than believed

P53 scored the adapter **180/180** against the base's **56/180**, paired, p < 1e-5 —
and **every one of those 180 held-out completions was already in the training set,
word for word**. The prompts all differed because the constants differed; the
completion was identical because the constants were named in the prefix. The adapter
memorised one tail per family.

**The root error was mine and it was a design decision, not a slip:** the varying part
of a case and the written part were disjoint. A completion task where what varies is
never what gets written can only measure memorisation of the template.

## What changed

| | P53 | now |
|---|---:|---:|
| held-out completions already in training | **180/180** | **0/197** |
| constants drawn from | 30 combinations | the full 32-bit space |
| deduplicated on | the prompt | the prompt **and the completion** |
| longest copied run, max | — | **0.100** (limit 0.60) |

Depth 1 vanished entirely, and that is honest: at the shallowest cut the tail carries
nothing specific to its instance, so those cases were exactly the degenerate ones.

**One caveat stated rather than hidden.** Of the 294 drawn literals appearing in
completions, **196 are also readable in the prefix's spec comment**. That is by
design — the specification names the polynomial, and a completion task with secret
constants would be unanswerable. So the task has two parts: **produce the structure**,
which is 94% of the tail and cannot be copied, and **place the right constant**, which
can be transcribed. Execution decides, so right constants with wrong structure fail.

## Arms

| arm | model |
|---|---|
| base | `Qwen/Qwen2.5-3B-Instruct` |
| adapter | the same base + `code-python`, retrained on **633** drawn completions |

**197 held-out cases**, different seed, deduplicated on prompt and completion.
Verified by **execution**. **Paired** — `bar.compare` over the same cases.

**The adapter is retrained**, because the corpus changed. P53's weights are for a
corpus that no longer exists and reusing them would measure the old suite.

## The gate, unchanged from P53

**Delta ≥ 0.10 and the paired test calls them different.** Both, not either.

## What would now make me disbelieve a pass

P53 passed the gate and meant nothing, so the checks that were missing are part of the
gate now:

- **Held-out completions in training must stay at 0.** Asserted by
  `tests/test_code_corpus.py`, which fails on the old suite.
- **A perfect score is a warning, not a result.** 1.000 on held-out cases means the
  tail is recoverable without computing, and the first thing to do with it is look for
  the leak rather than report the delta.

## Cost and safety

One session: retrain ~633 examples in **its own process** — P53 held 6.7 GiB and vLLM
refused to start beside it — then two arms over 197 cases. Model-written code is
executed on a disposable rented VM, with a timeout and no shell. There is no sandbox.
