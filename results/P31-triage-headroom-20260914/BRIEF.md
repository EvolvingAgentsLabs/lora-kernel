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

## The gate was wrong, and it was rewritten before the run — 2026-09-14

The rule above said *"beats 0.680"*. **A model sitting exactly at the bar — guessing
the majority class and nothing more — clears that 45% of the time**, on any suite
size, because its entire margin is one case **[ran]** `tests/test_bar.py`. It would
have authorised a day of training on a coin flip, and no amount of extra data fixes
it: the threshold is what is wrong, not the sample.

**The other direction was worse.** At `n = 30` the suite carries 24 human messages.
With a correct threshold, a base genuinely working at 0.80 clears it **26%** of the
time — the arm built to kill the phase would have killed it by accident in three
runs out of four.

| n | human msgs | bar | passes at | detects 0.80 | false alarm |
|--:|--:|--:|--:|--:|--:|
| 30 | 24 | 0.667 | 21/24 | **26%** | 2% |
| 100 | 77 | 0.701 | 61/77 | 63% | 5% |
| **150** | **113** | **0.655** | **83/113** | **96%** | **4%** |

**[ran]** 2026-09-14, exact binomial. 150 is where both errors land near 4%, so that
is the size this arm is bought at — one redesign, before the run, recorded here.

## Falsification

- **The base can do the job**, and phase 2 is worth buying, if its human-message
  score clears an **exact one-sided binomial test against the majority class at
  α = 0.05** — computed on the sample it was actually scored on, since the bar moves
  with the draw (0.667 at n=30, 0.707 at n=200).
- **The base cannot**, and the next purchase is a **different base rather than a
  training run**, if it does not clear that test. An adapter teaches a policy; it
  does not teach a model to hold a six-turn tool conversation it cannot hold.
- **A score above the bar that does not clear the gate is reported as such**, in
  those words, rather than as a pass.
- **The arm is void** if the loop does not close — refusals or undecided verdicts in
  quantity. That would measure the harness, and P30 already showed the harness closes
  at 24 calls, 0 refused, 0 undecided against a stub.

## What it is not

**Not a comparison with the adapters.** Nothing is trained here and nothing is
compared; this is the floor check that decides whether the comparison is worth
running at all. A number that beats the bar is permission to continue, not a result
about the architecture.
