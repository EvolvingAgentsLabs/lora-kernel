# P45 — where does a small expert stop being sufficient?

**Written before the run.** 2026-09-15.

## What is being asked

Not *does the expert match the frontier* — that question was already answered
(0.122 vs 0.733) and it turned out to be a question about one difficulty band. The
suite's oracle solutions are **6, 7 or 9 steps with no case below six**, and each
family is pinned at one depth **[ran]**, so *too weak* and *too hard* were the same
number.

**This asks:** on a ladder from 1 to 9 steps in the same domain, with the same three
tools and the same unmemorisable per-case handbook — **at what depth does the expert
stop being sufficient?**

## The arms, in the order that can end it soonest

| # | arm | what it decides |
|---|---|---|
| 1 | **bare base**, `Qwen/Qwen2.5-3B-Instruct`, no adapter | the ceiling check per rung. A rung the base already clears cannot show an adapter anything |
| 2 | **`fluids-full` unchanged**, carried in from P41 | the curve. This IS the question, and it costs inference only — nothing is trained |

**No frontier arm.** The frontier is a ceiling check on the ladder, run separately
if a rung looks broken, and it is never the gate.

**Nothing is trained in this run.** The adapter exists; this is 100% inference.

## Model, provider, cost

- **Model:** `Qwen/Qwen2.5-3B-Instruct` + the `fluids-full` LoRA from
  `results/P41-routing-20260915/adapters.tgz`.
- **Provider:** vLLM on a rented Colab **L4** — one 3B and one rank-16 adapter,
  which does not need an A100.
- **n = 140** over 7 rungs (1, 2, 3, 4, 6, 7, 9) ≈ 20 per rung. Seed 454545, which
  is **not** P41's 616161: the hard rungs are re-drawn rather than re-scored, so
  this is not the same 90 cases with four easy families bolted on.
- **Cost:** ~45 min of an L4, two arms.

## The gate: absolute, and 0.90

A sufficiency claim is **not** gated on the frontier's score. It is gated on what
makes an expert usable with nothing checking behind it. **0.90**, pre-registered: at
0.80 one answer in five is wrong and every answer has to be verified by hand, which
removes the reason to have the expert.

Per rung, not averaged — an expert that clears 0.90 at one step and 0.40 at four is
a useful expert with a known edge, and one average would hide the edge.

## What falsifies it

**A flat curve.** If the expert fails a one-step lookup at roughly the rate it fails
a nine-step chain — easy end within **0.15** of the hard end — then difficulty is not
what blocks it, the analysis that bought this run is wrong, and the failure is
something the ladder does not measure. `verdict_of()` computes this and prints
`FALSIFIED`; it is not left to a reading.

## What would also end it early

- **C18.** If the adapter is logged as loaded and does not apply, both arms are the
  base. The run stops at the identity gate and writes `stopped_at_gate`.
- **The base clearing 0.90 on rungs 1-4.** Then the easy end has no headroom, the
  ladder needs to start higher, and arm 2's numbers there say nothing about the
  adapter. Reported as `base_already_clears`.

## What this cannot conclude

- Nothing about **training** a narrow expert. This measures an expert that exists.
- Nothing about **other domains**. The ladder is fluids.
- Every number is a **lower bound**: Qwen 2.5 is forced by C18/P33, not chosen.
