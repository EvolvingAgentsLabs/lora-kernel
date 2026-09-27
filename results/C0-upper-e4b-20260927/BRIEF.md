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

## Result **[ran]** 2026-09-27 — **NONE: $\rho = -0.02$.** The upper-half LoRA shifts what the drafter reads exactly as much as the full one

Two L4 sessions. The first scored `nospec` and ran out of its 60 minutes during the MTP server's boot. The second resumed
with `mtp` only, as the spike resumes by configuration. vLLM 0.30, E4B bf16, drafter `google/gemma-4-E4B-it-assistant`.
G1: both members applied, in both servers. `spike.json`, `chain.log`, `chain2.log`.

| arm / prompts | α (MTP) | mean accepted length | speed-up b1 | speed-up b8 | identical to no-spec |
|---|--:|--:|--:|--:|--:|
| base / school | **0.816** | 4.27 | 2.60× | 2.17× | 16/16 |
| `school-s0` (full) / school | **0.440** | 2.76 | 2.43× | 2.09× | 15/16 |
| `upper-s0` (layers 21–41) / school | **0.432** | 2.73 | 2.41× | 2.11× | 16/16 |
| base / general | 0.349 | 2.40 | 2.21× | 1.91× | 3/8 |
| `school-s0` / general | 0.340 | 2.36 | 2.23× | 1.76× | 6/8 |
| `upper-s0` / general | 0.341 | 2.36 | 2.21× | 1.89× | 3/8 |

```math
\rho = \frac{0.432 - 0.440}{0.816 - 0.440} = -0.02
```

**By the table written first: NONE.**

**Reading.**
1. **Confining the LoRA to the upper half does not help the drafter at all.** The MTP head reads the target's last hidden
   state, and every layer where the LoRA still sits lies between the unadapted lower half and that state. E6 moved the
   adapter off layers the drafter never reads directly. The shift the drafter sees is made in the upper layers, and both
   members put it there.
2. **The E4B repeats C0's drop:** on its own domain the expert costs the drafter about half its acceptance (0.82 → 0.44;
   the 12B went 0.79 → 0.34).
3. **Unlike the Mac, on an L4 the E4B's MTP still pays with the LoRA on:** 2.4× at batch 1 and 2.1× at batch 8 on the
   domain. At α 0.44 the drafter is cheap enough relative to the target on this GPU. On the Air, llama.cpp's MTP lost speed
   at α 0.37 (MAC2).
4. **Side observation [ran], `nospec`:** `upper-s0` runs at exactly the full member's speed (23.3 tok/s b1, 138 b8). vLLM
   appears to apply the LoRA kernel in every layer, zero-filling the unadapted ones [read, not verified]. In vLLM, half an
   adapter saves memory, not time.

**What it closes.** Layer-restricted LoRAs remain a lever for sharing the lower KV (E6) and for a frozen lower half. They
are **not** a lever for drafter alignment. That stays with an aligned drafter: strategy B (a LoRA on the drafter) or the
merged-E4B pair on hardware where it fits.
