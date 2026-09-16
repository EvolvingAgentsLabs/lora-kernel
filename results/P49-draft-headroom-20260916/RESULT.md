# P49 — the target is worth accepting against, but only on two temáticas of three

**[ran]** 2026-09-16, one A100, two arms, 90 cases, seed 606060, **no training**.
Brief: [`BRIEF.md`](BRIEF.md). Session stopped cleanly.

## The verdict

| arm | complete drafts | fact rate | errors |
|---|---:|---:|---:|
| `Qwen2.5-32B-Instruct-AWQ` | **76/90 = 0.844** | 0.948 | 0 |
| `Qwen2.5-3B-Instruct` | **49/90 = 0.544** | 0.756 | 0 |

**Margin 0.300 against a pre-registered gate of 0.10. The design is bought** — a
target worth accepting against exists.

## And the headline hides the thing that matters

| temática | target | base | gap |
|---|---:|---:|---:|
| **client** | 0.667 | **0.033** | **0.633** |
| vendor | 0.867 | 0.633 | 0.233 |
| **team** | **1.000** | **0.967** | **0.033** |

**On `team` there is no headroom at all.** Both arms are at the ceiling — this is
P42's failure with the ARC adapter (0.825 against a base already at 0.815), isolated
to one temática of three. A third of the suite cannot contribute to any comparison
between experts, because there is nothing left to be better at.

**The 0.300 margin is almost entirely `client`**, where the base completes **1 of 30**.

## What the base actually does, read rather than inferred

It writes a perfectly reasonable reply and **omits the concrete details**:

> *"Thank you for following up on the quote. I have confirmed with our logistics
> team, and they are indeed expecting delivery on June 18th."*
> — missing: `Q-7772`, `65,306`

Across 29 of 30 client failures: the **reference** is missing 28 times and the
**amount** 25 times. The date is usually there — and `carries()` matches `June 18`
inside `June 18th`, so that is not brittleness.

**And the check is not measuring punctuation.** Of the **80** missing facts across
both arms, **0** appear in the draft written another way — no dropped commas, no
reformatted dates. The facts are genuinely absent. That was worth testing: a check
that can fail while the capability works is measuring phrasing, and this repository's
rule is to delete such a check rather than loosen it.

## What this changes for P50

1. **`team` has to be fixed or dropped.** Scoring three experts on a temática where
   both a 3B and a 32B already carry every fact measures nothing, and averaging it in
   dilutes whatever the other two show. Making it harder means adding a fact that is
   not a name — the two temáticas with headroom both require an **amount**, and the
   one without requires a **first name**.
2. **The gap is a capability gap, not a style gap.** What a drafting expert would
   have to learn is *always name the reference and the figure* — which is a policy,
   trainable, and mechanically checkable. That is a better-defined target than
   "write in the client register".
3. **Even the target misses on `client`** — 10 of 30. So there is room above the
   target on this floor, which means acceptance against it is not the same as
   correctness. P50 must keep `carries()` beside acceptance, not behind it.

## What it does not claim

- **Nothing about acceptance.** This says a target worth accepting against exists.
  Whether acceptance ranks three close experts is P50.
- **Nothing about tools.** Both arms were handed the thread inline, by design; the
  simplification can only have made the gate easier to clear.
- **Nothing about draft quality.** `carries()` is a floor. A draft can name every
  fact and still be a bad reply, and nothing here would notice.
