# P36 — is the margin reachable at all?

**Pre-registered 2026-09-15, before the adapter was trained.**

## Why this is bought before composition, a judgement adapter, or a better corpus

Three arms have now run on the email suite and **none has cleared the gate**:

| arm | asked in | refused | human messages |
|---|--:|--:|--:|
| base (P31) | 0/150 | 0 | 39/113 |
| kernel-mt, physics tools (P34) | 123/150 | 127 | 39/113 |
| kernel-email (P35) | 22/150 | 0 | 42/113 |

The suite's **0.320 of margin is unclaimed**, and **nobody knows whether it is
reachable**. If a purpose-built adapter cannot take it, no split of adapters will
either — and composition, a judgement adapter and a wider protocol corpus would be
three purchases made against a number that was never there. That is the headroom
rule, and this is the cheapest way to apply it.

## The monolith is the ceiling, not the thesis

One adapter that learns **the tools and the judgement together** — the analogue of
what P8 used in fluid mechanics, *one adapter that learned the physics and the
`<calc>` syntax together, at 40/40* **[ran]**.

**A monolith that clears the gate is permission to keep measuring, not a result
about the architecture.** The thesis says separate, swappable adapters should match
a monolith; the monolith only says the target exists. This is written here because
the number is otherwise very easy to quote as a success for the pool.

## What the corpus does, and the leak it had

Each example is a real triage case: the listing, the three tool calls that supply
what the listing withholds, then the verdict from `inbox.important` itself — so the
corpus and the scorer cannot drift apart. An **automated** message is settled
without spending a call, because the sender is visible at a glance and a corpus that
queried three tools for everything would teach the model to spend calls it does not
need.

**Excluding the evaluation's seed was not enough.** Message ids run
`msg-000..msg-029` and subjects come from a fixed list, so a different draw
reproduces a listing by chance. The first version of the leak test matched id and
subject anywhere in the corpus and reported **16** hits — most not exploitable at
all. The number that matters is *the same listing carrying the same verdict*, and it
was **2 of 150** **[ran]**: inside the gate's noise, and cheap enough to remove
outright, which the generator now does by content rather than by seed.

## The gate

The **exact one-sided binomial test** against the majority class at α = 0.05 on the
human messages — **83/113** on this draw. Accuracy above the bar is not a pass.

## Falsification

- **The margin is reachable**, and the pool question becomes *"can the split match
  it?"*, if the monolith clears 83/113.
- **The margin is not reachable over this base**, and **no pool arrangement should
  be bought**, if it does not. The next purchase would be a different base or a
  different suite, and this arm would have saved three.
- **The arm is void** if the served adapter does not apply — `triage_run` runs the
  identity gate first, so this cannot pass unnoticed.
- **A monolith that clears while asking for nothing** would mean the judgement is
  readable from the listing after all, contradicting `tests/test_email.py`. Tool
  calls are reported beside the score for exactly this reason.
