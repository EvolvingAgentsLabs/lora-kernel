# C0-upper — does the MTP drafter's acceptance recover when the expert's LoRA leaves the lower half? (pre-registered 2026-09-27)

**Why.** C0 **[ran]**: on the 12B, the native MTP drafter keeps 0.79 of its drafts on the base and **0.34 with the expert's
LoRA on**. The drafter reads the target's final activations, and the LoRA shifts them. E6 **[ran]** produced an expert
with its LoRA on layers 21…41 only (`upper-s0`) that loses nothing against the full member (`school-s0`), from the same
corpus and recipe. If a LoRA confined to the upper half shifts less of what the drafter reads, part of the lost
acceptance comes back, at no cost to the expert.

**What.** `spec_lora_spike --profile e4b-school --configs nospec,mtp`. One vLLM 0.30 server per configuration, serving
`google/gemma-4-E4B-it` in bf16 with both members (`school-s0`, `upper-s0`). The drafter is the E4B's own MTP,
`google/gemma-4-E4B-it-assistant`, 4 speculative tokens. Arms: base, `school-s0` and `upper-s0`, each × {no speculation,
MTP}.

**Prompts.** 16 of the school's held-out turns, rendered exactly as the gateway does (the role's system prompt + SCOPE,
the request with the role's tools), plus the spike's 8 general prompts. Temperature 0, 160 tokens, batch 1 and 8. No stop
at the closing tag: every arm writes past its first call, alike.

**Model and provider.** E4B bf16 on a Colab L4, one session; the adapters are carried in from E6.

**Reading, written first (`spec_lora_spike.recovery`).** On the domain set:

```math
\rho = \frac{\alpha_{upper}-\alpha_{full}}{\alpha_{base}-\alpha_{full}}
```

the fraction of the acceptance the full LoRA costs the drafter that the upper-half LoRA gives back.

| outcome | reading |
|---|---|
| $\rho\ge 0.5$ | **MOST** comes back: restricting the LoRA's layers is a lever on speculative decoding too |
| $0.1\lt\rho\lt 0.5$ | **PARTIAL** |
| $\rho\le 0.1$ | **NONE**: the shift lives in the upper layers, where the drafter reads |
| $\alpha_{base}\le\alpha_{full}$ | **UNDEFINED**: on the E4B the full LoRA costs the drafter nothing, and the premise does not hold here |
| MTP does not start for the E4B, or G1 fails for a member | **VOID** |

Beside it, per arm: the speed-up with and without MTP, mean accepted length, and identical texts. Output identity is not
gated (F0b).

**Stopping condition.** One session and one reading; no redesign after the result.

**Not in this run.** The 12B: its LoRA is not upper-half, and a new one would mean retraining it. Other values of $k$. The
Mac: MLX or llama.cpp with `upper-s0`, the next step if $\rho$ is MOST.
