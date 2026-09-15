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

---

# Result — 2026-09-15 **[ran]**

## The gate decides now, and the expert clears it

`arm_email_475.json`, scored **on the VM** so the run did not depend on the user's
machine staying awake — which it did not: the laptop was paused mid-session and an
earlier 475-case attempt died with it.

| | |
|---|--:|
| human messages | **260/351 = 0.741** |
| majority-class bar | 0.655 |
| passes at | 246 |
| **exact one-sided p** | **0.00036** |
| tool calls · refused · undecided | 1185 · 6 · 0 |
| power for the pre-registered effect | **87%** (it was **47%** at n = 113) |

**It clears by fourteen cases, not by one.**

**And the accuracy barely moved**: 0.726 → 0.741, inside the spread three earlier
runs already showed. What changed is **the gate's ability to decide**. The 84, 81,
82 were never the model wavering; the suite was too small for the effect and the
threshold sat inside its own dispersion.

**Why this is not a search for a size that passes.** `bar.n_for(0.655, 0.071)`
returned 358 human messages *before the run*, using the power rule P42 forced into
existence, and this brief pre-registered that landing near the threshold again
would be read as **a smaller effect, not a bigger suite**.

## The end-to-end runs, and here is exactly what it shows

OpenClaw on the user's Mac → local proxy → cloudflared → vLLM on an L4 → the
`email-full` QLoRA → back:

    [model-fetch] response provider=lorapool model=email-full status=200
                  elapsedMs=4009 contentType=text/event-stream
    NOT IMPORTANT
    [agent] run ... ended with stopReason=stop

**Zero requests left the machine** — the proxy announced nothing, because
`email-full` is local.

**What it does not show, and this matters.** The OpenClaw turn made **no tool
calls at all** — checked on both sides. OpenClaw sends *its own* tools, not the
inbox's, so the expert answered from the listing alone, which is what the base does
and what P31 measured at 0.345. **The 0.741 comes from `agent_sim`, which supplies
the three inbox tools and executes them.** The agent turn demonstrates the
transport; the suite demonstrates the expert. Wiring the inbox tools into OpenClaw
is real work and is not done.

## Three things running it found that no test could

- **A doubled `/v1`** in the fallback URL — every test until then stubbed the fetch.
- **`config patch` takes `--file` or `--stdin`**, never a positional argument; the
  manual had it wrong two hours after being written.
- **OpenClaw streams by default** and its per-model `streaming: false` did not take.
  The proxy's refusal — *refuse rather than fake* — was right while the alternative
  was a misleading measurement and wrong when the alternative was **being unusable**.
  It now delivers one buffered SSE chunk carrying `x_buffered: true` in the payload.
