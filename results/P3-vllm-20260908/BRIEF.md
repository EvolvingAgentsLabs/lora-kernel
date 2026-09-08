# P3 — the substrate: three adapters, one resident base, served by vLLM

**Question.** `ARCHITECTURE.md` layer 1 is "one GPU, one resident base model,
multi-LoRA serving, adapters batched per request". Every number this project has
is from `transformers` loading one adapter at a time, which is not that. Can the
pool actually be served?

**The three things it must show, in order of weight.**
1. **The pool is servable** — three adapters resident over one base, each
   answering its own requests.
2. **The same numbers come out** — an adapter scored through vLLM must match what
   `transformers` measured (42/60 in bf16). If it does not, one of the two
   implementations is wrong and **every earlier number is in question**.
3. **What a mixed batch costs** against a pure one. That difference is the price
   of holding a pool, and it is the economic claim under "swap per request".

**Falsification.** vLLM refuses these adapters, or serves them at a materially
different accuracy, or a mixed batch costs so much more than a pure one that
per-request swapping is not a serving strategy.

**The risk we know we are carrying.** These adapters adapt all seven projections,
`q_proj` and `k_proj` included — the flag meant to exclude them was read only by
the preflight **[ran]**. Qwen3 applies QK-norm and adapting those two is reported
to produce shape-incompatible tensors in some serving kernels **[read]**. It did
not bite in training. **If it bites here it is a finding about what the pool may
adapt**, not a bug to route around: it would mean the adapters have to be
retrained on five modules to be servable, and that is worth knowing before P4.

**Setup.** A100-40GB, `Qwen/Qwen3.5-2B` in bf16, the three adapters already
trained (`all-clinics`, `alpha`, `beta`, r=16), 60 `val` cases, greedy, the same
exact verifier as every other arm.

**Cost.** One A100 session, under an hour. This is the first step that needs the
expensive card, and P1/P2/P7/P8 stay off it by design.

**Abort rule.** If vLLM will not load the adapters at all, stop and report that
rather than retraining inside this step — the retrain is a separate decision with
its own brief.

**Redesign count.** 0.
