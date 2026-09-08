---
name: alpha-surface
description: Measure the acceptance surface — how much of a target model's greedy continuation a candidate drafter reproduces, per case and per region — using the alpha/ instrument. Use for any step that needs α, an α-versus-verified-score correlation, or a promotion decision.
---

# The acceptance surface

## What α is here, exactly

At temperature 0 the target's distribution is one-hot, so speculative decoding's
acceptance test reduces to equality: **the accepted prefix is the longest common
prefix between the draft and the target's greedy continuation.** Greedy decoding
is prefix-consistent, so a single target generation per task carries the ground
truth continuation at *every* position in it. One frontier call per case buys the
whole surface, for any number of candidate drafters.

That identity is the reason this measurement needs no GPU, no vLLM and no
`LoRA-as-drafter` support.

## The promotion criterion is SEMANTIC, decided 2026-09-07

Character acceptance was measured scoring a **correct** compact answer 0.00
against an indented target, and an indented copy of the same answer 1.00 **[ran]**.
It measures layout across model families.

So promotion is decided on **semantic answer agreement** — both answers parsed
and compared as answers (`alpha/report.py::semantic`) — and character α is
reported beside it and **ranks nothing**. Whether pinning the format with
`harness.lora` reconciles the two is S6's own win condition, not an assumption
this metric is allowed to make.

Report `same answer` and `answer f1` as the criterion, α@0 and payload α as
context, and never let a reader take the second pair for the first.

## Two things to state every time, because they bound the claim

- **Cross-tokenizer.** A frontier target does not share the base model's
  vocabulary, so token-level acceptance against it is undefined. α is measured on
  characters and reported as such. This is sound as a distillation score and
  **unsound as a speedup claim** — never convert one into the other.
- **α is not one number.** It is a number per candidate **per region** of the
  problem space, at a stated `k`. A single pooled α hides the only structure the
  architecture uses: withdrawal happens per region.

## Running it

```bash
python3 -m alpha.measure --target <tag> --drafters <tag,tag> --split held_out \
    --n <cases> --k <draft length> --run-dir results/<step>-<date>
python3 -m alpha.report results/<step>-<date>
```

The measurement streams one line per case to stderr and writes each case to disk
as it lands. Do not pipe it through `tail`: a run whose position nobody can see
cannot be stopped early.

## Reporting it

Always together, never separately:

| what | why |
|---|---|
| α with its `k` | α falls as `k` grows; a number without `k` is not comparable |
| n and the split | held-out or not decides what the number licenses |
| the **verified task score** of the same configuration | promotion is decided on both, and α alone has been anti-correlated with expertise before |
| the target, by exact tag and provider | α means agreement *with whatever verified*; change the target and the metric changes meaning silently |

## The trap this instrument exists to avoid

Verify against the shared base model and a high α means *this expert drifted
least* — anti-correlated with the specialisation you are trying to detect. It is
only a distillation score when the target is stronger than every candidate. If
the target is not clearly stronger, the surface is measuring similarity, not
capability.
