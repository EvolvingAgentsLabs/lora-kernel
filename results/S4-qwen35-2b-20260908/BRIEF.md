# S4 — the first adapters, on `Qwen/Qwen3.5-2B`

**Question, in two parts.**
1. **Does specialisation happen at all?** Does a LoRA over `Qwen/Qwen3.5-2B` beat
   that same base on cases neither was trained on?
2. **Do experts differ by region?** Does the adapter trained on clinic `alpha`
   beat the one trained on `beta` **on alpha's cases**, and the reverse?

**Falsification, written before the run.**
- No gain on `val` → specialisation did not happen; no routing scheme rescues it.
- Region experts that do not each win on their own clinic → the pool is one
  expert wearing three names, there is nothing for acceptance to route between,
  and the architecture's central claim is over.
- Either way `val_delta` travels with the number: the clinic whose unpublished
  rule **inverts**, absent from every training split. Gain on `val` with a
  collapse there is a memorised rule, not an expert.

**Why this base and not a Gemma.** The project is multi-LoRA serving in vLLM, so
a base vLLM cannot serve with adapters is disqualified however well it trains.
`gemma-4-E4B-it` uses a linear class peft cannot wrap **[ran]**; vLLM's Gemma 4
LoRA support covers the text-only class, not the `...ForConditionalGeneration`
variants **[read]**; `gemma-4-26B-A4B-it` is a 128-expert MoE needing an A100
**[read]**. Preflight on this base: **PASS, peak 6.57 GiB of 14.56** **[ran]**.

**Model.** `Qwen/Qwen3.5-2B`, **bf16** — Unsloth reports larger than usual
quantisation error on Qwen3.5, so 4-bit is avoided **[read]**. LoRA r=16 α=32 on
`v_proj,o_proj,gate_proj,up_proj,down_proj`; `q_proj`/`k_proj` are excluded
because qwen3's QK-norm makes them shape-incompatible under an adapter **[read]**.

**Scale, and what it leaves out.** 60 `val`, 30 `val_delta`, 25 per region cell,
2 epochs. Free Colab reclaimed two sessions mid-run, so the instrument is scaled
to fit a window rather than to the largest n available. The cost is width of
interval, not direction, and the smaller n is stated with every number rather
than being quietly folded in.

**Durability.** Results are written after each arm on the runtime and pulled back
to this machine after each arm, so a reclaimed session costs the arm in flight
and nothing else. The previous design only survived within one session, which is
exactly how the last two hours were lost.

**Abort rule.** If a third session is reclaimed before the adapter arm completes,
stop and report that the free tier cannot hold this run rather than buying a
fourth.

**Redesign count.** 0 for the experiment. The changes are to durability and
scale, not to what is measured.
