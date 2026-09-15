# P43 — the end-to-end through a tunnel, and a gate that can actually decide

**Pre-registered 2026-09-15, before the session was started.**

## Two things in one session, because the card is the same card

**1. The gate the email expert has been judged by cannot decide.** Three runs of the
same adapter, the same cases, temperature 0, scored **84, 81, 82** against a
threshold of **83** — every pair a tie **[ran]** P36/P38/P40. That was read as vLLM
nondeterminism, which it is, but the deeper reason is that **the suite is too small
for the effect**: at n = 113 human messages, the power to resolve a +0.071
improvement over a 0.655 bar is **47%**. A coin.

`bar.n_for(0.655, 0.071)` returns **358** human messages — about **475** drawn. That
number is fixed here, before the run, by the power rule this project adopted
today. **It is not a search over sizes until one clears.**

| n human | passes at | power |
|--:|--:|--:|
| 113 | 83 | **47%** |
| 200 | 143 | 67% |
| **358** | — | **80%** |

**2. The end-to-end, through a tunnel, on synthetic data.** OpenClaw on the user's
Mac, the pool on the rented card, the proxy in between. Synthetic suite by the
user's explicit choice, so **nothing of theirs leaves anywhere**.

## Falsification

- **The gate decides**, and the email expert's verdict stops being a coin, if the
  larger run lands clear of its threshold in either direction. **Either direction
  is a result**: this is not bought to make it pass.
- **It still cannot decide** if the score lands within one or two cases of the
  threshold again, which would mean the effect is smaller than three runs suggested
  and the honest statement is a smaller effect, not a bigger suite.
- **The end-to-end works** if OpenClaw gets an answer from `email-full` through the
  tunnel and the proxy announces nothing — nothing left the machine.
- **The run is void** if the tunnel changes what the model sees. The identity gate
  runs through the tunnel for exactly that reason.

## What it will not claim

**Not that the expert is good enough to deploy on real mail.** It is measured on a
synthetic inbox whose truth we wrote. That is the right suite for a substrate
demonstration and the wrong one for a decision about somebody's correspondence.
