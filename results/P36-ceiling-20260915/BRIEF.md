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

## Reframed 2026-09-15, before the number: this IS the thesis's first member

**Decision taken mid-run**: composition is dropped for now, and with it
`harness.lora` — the kernel adapter exists to be shared across experts, and an
expert that carries its own protocol has no use for it. **The thesis is untouched**:
a pool of self-contained QLoRAs over one resident base, swapped per request, is
still *the whole agentic system is a pool of QLoRAs*. Composition was an
optimisation — teach the protocol once — not the claim.

So the section below is superseded on one point, and the correction is written
**before the number exists** rather than after it:

- ~~a monolith that clears is permission to keep measuring, not a result about the
  architecture~~ — under this decision **a monolith that clears IS the result**: the
  first pool member scoring on its subdomain.
- The falsification gets smaller and more honest too. A monolith that fails no
  longer means *no pool arrangement will work*; it means **this base cannot do this
  subdomain**, which is a narrower claim and the right one.

**P34 is parked, not falsified.** That a physics kernel takes this base from 0 to
123 of 150 cases reaching for email tools is measured and stands. It is the only
evidence the kernel idea has legs, and if self-contained experts turn out expensive
to produce at scale, the kernel returns with that result already paid for.

## ~~The monolith is the ceiling, not the thesis~~ — superseded above

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

---

# Result — 2026-09-15 **[ran]**

`triage_results.json`. One adapter, tools and judgement together, served over
Qwen2.5-3B with the **identity gate `applied`** before a single case was scored.

| arm | asked in | refused | human messages | exact p |
|---|--:|--:|--:|--:|
| base (P31) | 0/150 | 0 | 39/113 = 0.345 | 1.000 |
| kernel-mt, physics tools (P34) | 123/150 | 127 | 39/113 = 0.345 | 1.000 |
| kernel-email, names only (P35) | 22/150 | 0 | 42/113 = 0.372 | 1.000 |
| **email-full (P36)** | **113/150** | **0** | **84/113 = 0.743** | **0.028** |

**It clears.** 84 against the 83 the exact one-sided binomial demands at α = 0.05,
and the margin the tools held — 0.320 between the bar and a perfect score — is
**28% claimed**: 0.655 → 0.743.

## What makes the number readable

- **393 calls, 0 refused.** It asks correctly every time.
- **It asked in 113 of 150 cases and in 37 it did not**, and the 37 are almost
  exactly the automated messages — the ones the corpus teaches to settle at a glance
  without spending a call. **It did not learn "always ask"; it learned *when*.**
- **97 cases at 3 calls, 14 at 6, 2 at 9.** Some go back for more; none ran out of
  turns, and **0 were undecided**.
- **0 of 150** answered from a fabricated tool result. The confound pre-registered
  in the P35 brief stays dead.
- The **identity gate** returned `applied`, so this is the adapter and not the base.

## What it means under the decision taken while it ran

This brief was bought as a **ceiling** and reframed mid-run, before the number
existed, when composition was dropped. Under that decision the reading is not
*permission to keep measuring* — **it is the result**:

> A self-contained QLoRA, trained by ordinary supervised fine-tuning on one
> subdomain, served over a resident base and swappable per request, does a job the
> base cannot do at all.

The base scores **0.345** — the exact complement of its own bar, from answering
`NOT IMPORTANT` to everything without consulting anything. **The whole of the
difference is the adapter.** No composition, no shared kernel, no tournament.

## What is not claimed

- **Not that the split could not do better.** P34 and P35 measured the two halves
  apart; nothing here compares a composed pool against this, because composition is
  parked.
- **Not a ceiling.** 0.743 against a 1.000 that nothing has reached. What the
  remaining 0.257 costs is unmeasured.
- **Not generalisation.** One subdomain, one inbox generator, one base. The pool
  thesis needs a second expert before "a pool" is a word this earns.


---

## Qualified 2026-09-15 by P40: this gate verdict is not reproducible

The same adapter, the same 150 cases, **temperature 0**, three runs: **84**/113 here,
**81** in P38's pool, **82** in P40's. Every pair is a tie (4:1, 3:1, 2:3 discordant)
and the tool-call count barely moves — 393, 393, 390. **The member does not change.**

**The gate demands 83.** vLLM is not run-to-run deterministic at temperature 0, and
this member's ±3-case spread straddles the threshold. So *"the first pool member
clears its gate"* is true of this run and is **not a stable property**: it cleared
once in three, and which side it lands on is decided by the scheduler.

**The effect is not marginal, only the verdict is.** Against the base on the same
cases: **8 : 51 discordant, p ≈ 0** **[ran]** `results/P40-pool-retried-20260915/`.
