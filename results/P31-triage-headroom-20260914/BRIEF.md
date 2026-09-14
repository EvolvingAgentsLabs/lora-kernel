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


---

# Result — 2026-09-14 **[ran]**

`triage_results.json`, `arm_base.json`. Qwen2.5-3B-Instruct, no adapter, 150
messages through vLLM 0.29.0, the proxy and the real agent loop.

| | |
|---|--:|
| human messages | **39/113 = 0.345** |
| majority-class bar | 0.655 |
| clears the gate at | 83/113 |
| exact one-sided p | **1.000** |
| **tool calls** | **0 of 150** |
| refused · undecided | 0 · 0 |

**It answered `NOT IMPORTANT` to all 150, in identical words, on the first model
call.** The 0.345 is exactly 1 − 0.655: it said "not important" to everything, and
scored the complement of the bar rather than the bar.

## The loop closed, and the tools really were offered

The void condition was written for refusals and undecided verdicts, and there were
none of either. To rule out the third way this could fail — a tool surface the model
never saw — the proxy's rendering was reproduced offline. The model was shown all
three tags and the line *"Use the tools to find out — the listing does not say"*.
**It was offered the tools, told to use them, and asked for none.**

## The falsification rule was wrong, and it is corrected here rather than applied

The rule read: *"the next purchase is a different base rather than a training run.
An adapter teaches a policy; it does not teach a model to hold a six-turn tool
conversation it cannot hold."*

**P8 measured the opposite on this exact base** — `Qwen/Qwen2.5-3B-Instruct`,
`results/P8-harness-lora-20260909/compose_results.json` **[ran]**:

| arm | tool calls on 30 cases |
|---|--:|
| base + tool | 44 |
| **kernel + tool** | **169** |
| domain + tool | 0 |

A protocol adapter nearly quadruples how often this base asks for a tool, and a
domain adapter with no protocol in its corpus suppresses asking to zero. **The
failure P31 observed — never asking — is precisely the one a protocol adapter is
built to repair.**

**The comparison is suggestive, not exact, and that is stated rather than glossed.**
P8 runs a different task through a different channel: physics, with the harness
stopping generation at `</calc>` and continuing. P31 runs email through the OpenAI
`tools=[…]` convention and the proxy. What transfers is the *within-P8* contrast —
same base, same task, same channel, 44 → 169 — not the raw count.

So "base at the floor ⇒ adapter at the floor" does not follow, and buying a
different base on the strength of it would spend money on an inference this
repository has already contradicted. **The next arm is the protocol adapter on this
suite, not a different base.**

## What this arm does establish

- **The base cannot do triage unaided**, decisively: p = 1.000 against its own bar,
  and it never consults anything.
- **The suite is not trivially answerable.** A model that reads only the listing and
  guesses lands at or below the bar, which is what the material was built to force.
- **The margin is entirely unclaimed.** All 0.320 of it still sits with the tools,
  and nothing has yet reached for it.
