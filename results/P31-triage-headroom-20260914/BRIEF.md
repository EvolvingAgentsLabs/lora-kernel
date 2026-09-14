# P31 — the killing arm: can the base do this job at all?

**Pre-registered 2026-09-14, before the base was served.**

## Why this is bought before anything else

`docs/CASE-TRIAGE.md` puts this first for a reason paid for twice. A baseline at the
**ceiling** makes every arm tie and the tie reads as success — that is how a memory
benchmark scored its baseline 10/10 and a physics suite passed 12/12. **A baseline at
the floor costs the same in the other direction**: no adapter placed over it can move
anything, and the training run that discovers it costs a day.

So: the base model, **no adapter**, against the triage suite, through the real proxy
and the real agent loop.

## The bar, fixed before the run

On the **human** messages — where the tools decide, and where spotting `noreply@` is
not doing the work — the best rule readable from the listing scores **0.680 against a
majority-class bar of 0.680** **[ran]** `tests/test_email.py`. It does not beat
guessing by one case.

    the bar          0.680   answer "important" to every human message
    the margin       0.320   owned entirely by the tools

## Falsification

- **The base can do the job**, and phase 2 is worth buying, if it beats **0.680** on
  the human messages.
- **The base cannot**, and the next purchase is a **different base rather than a
  training run**, if it lands at or below the bar. An adapter teaches a policy; it
  does not teach a model to hold a six-turn tool conversation it cannot hold.
- **The arm is void** if the loop does not close — refusals or undecided verdicts in
  quantity. That would measure the harness, and P30 already showed the harness closes
  at 24 calls, 0 refused, 0 undecided against a stub.

## What it is not

**Not a comparison with the adapters.** Nothing is trained here and nothing is
compared; this is the floor check that decides whether the comparison is worth
running at all. A number that beats the bar is permission to continue, not a result
about the architecture.
