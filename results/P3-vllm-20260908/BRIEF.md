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


---

## Result — the pool is not servable, and it fails silently

| arm | accuracy | throughput |
|---|---|---|
| base, no adapter | 0.100 | — |
| pure batch · `all-clinics` | **0.100** | 90.2 prompts/s |
| pure batch · `alpha` | **0.100** | 93.3 prompts/s |
| pure batch · `beta` | **0.100** | 92.7 prompts/s |
| mixed batch, round-robin | not scored | 6.2 prompts/s |

Every adapter scores **exactly the base's 6/60**, and a direct two-prompt
comparison returned **`RESULT IDENTICAL`** on both: the served text is byte-for-byte
the base model's. vLLM accepted every `LoRARequest` **without an error or a
warning** and applied nothing. **[ran]**

**What is ruled out.** The adapter files are valid — `adapter_config.json` and a
43 MB `adapter_model.safetensors`; `base_model_name_or_path` matches the served
model; `max_lora_rank` matches `r`. And there is no engine to fall back to:
`VLLM_USE_V1` is an *unknown variable* in 0.28.0, V0 is gone.

**What is open.** LoRA on the V1 engine is documented as experimental **[read]**;
the adapters adapt `q_proj`/`k_proj` under Qwen3's QK-norm, which is exactly the
mapping a serving stack has to rebuild; or this is a regression in 0.28.0.

**Why this matters more than a failed step.** The arm that caught it is the one
whose only job was to check that the same numbers come out — the arm that looks
redundant right up until it is not. Had P3 only measured throughput, it would
have reported three adapters served at 90 prompts/s and called the substrate
proven.

**What it costs the plan.** P4, P5 and P6 all serve adapters. None of them can be
bought until an adapter demonstrably changes vLLM's output.


---

## Path 1 — forcing the text-only class — is dead, and it says why

`hf_overrides={"architectures": ["Qwen3_5ForCausalLM"]}` fails at weight load:

    ValueError: There is no module or parameter named 'visual' in Qwen3_5Model

The checkpoint is **multimodal**, so the text-only class cannot load it. And the
parameter dump names the other half of the problem: `layers.*.linear_attn.*` on
most layers, `layers.23.self_attn.qkv_proj` on the few full-attention ones.
`Qwen/Qwen3.5-2B` is **hybrid and multimodal**, and the class that declares
`SupportsLoRA` is neither. **[ran]**

So the base has to change. `Qwen/Qwen2.5-3B-Instruct` is `Qwen2ForCausalLM` —
which declares `SupportsLoRA` in vLLM — with **36 full-attention layers and no
vision tower**, and it is the size the 2B was. Retraining the pool there is not
lost work: it re-establishes S4 on a second base, which tests the specialisation
claim again rather than repeating it.
