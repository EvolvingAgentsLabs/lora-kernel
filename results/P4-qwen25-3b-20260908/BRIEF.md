# Path 2 — move the pool to a base vLLM can actually serve

**Why.** `Qwen/Qwen3.5-2B` is hybrid and multimodal, and the vLLM class that
declares `SupportsLoRA` is neither, so adapters over it are silently ignored
**[ran]**. `Qwen/Qwen2.5-3B-Instruct` loads as `Qwen2ForCausalLM`, which declares
`SupportsLoRA`, has 36 full-attention layers and no vision tower.

**Question.** Two, and the second is the point.
1. Does the S4 result reproduce on a different base — does an adapter beat this
   base by a margin like +60?
2. **Can vLLM serve it?** The gate that P3 now enforces in code: one prompt,
   with and without the adapter, must differ before any arm is measured.

**Falsification.** No gain on the new base — then +60 was a property of
`Qwen3.5-2B` and not of the method. Or vLLM ignores this adapter too — then the
problem is not the architecture we picked and the substrate needs a different
serving stack entirely.

**Why retraining is not lost work.** It re-establishes S4 on a **second base**,
which tests the specialisation claim again instead of repeating it. A result that
survives a change of base is worth more than the same result measured twice.

**Scale.** Base and adapter arms first — 60 `val`, 30 `val_delta`, 600 training
cases, 2 epochs, LoRA r=16 on all seven projections. Region experts only if the
serving gate passes; there is no point building a pool nobody can serve.

**Cards.** Training on the L4. Serving on the A100, and only once there is an
adapter worth serving.

**Redesign count.** 0. The experiment is unchanged; the base moved because the
serving stack requires it.
