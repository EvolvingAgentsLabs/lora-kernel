# Qwen 2.5 is not the constraint the question assumes

*Written 2026-09-16, before any of it is built. Every claim is marked **[ran]** with
its run directory or **[read]** from the code, and three claims that could not be
checked from this machine are marked **[unverified]** rather than repeated.*

The question put to this analysis: *we are on an old family because it is what
supports switching LoRAs over one resident base; the most advanced model today is
`Qwen3.8-27B`, which is also slow enough to justify speculative decoding; can small
models and LoRAs be used the way we want against it, and if the support is missing,
can we build it?*

The answer turns on one fact the question does not contain.

---

## 1. The target never needed LoRA

Speculative decoding has two models with two different jobs:

| | job | needs multi-LoRA? |
|---|---|---|
| **drafter** | proposes `k` tokens; this is where the pool of experts lives | **yes** — it *is* the pool |
| **target** | verifies the proposal in one parallel pass | **no** — it is one dense model, unchanged |

C18 — *vLLM logs `Loaded new LoRA adapter` and serves the base anyway* **[ran]**
`results/P33-lora-matrix-20260914/` — is a statement about **serving a LoRA**. It
constrains the drafter. It says nothing about a model that is never asked to hold an
adapter.

So the migration question splits in two, and the two halves have different answers.

## 2. A Qwen 3 target is available today, at zero engineering cost

P48 hashed the tokenizers rather than reading the model cards **[ran]**
`results/P48-tokenizer-compat-20260916/`:

| candidate target | vocab | ids match | extra ids | usable with a Qwen2.5-3B drafter |
|---|---:|---|---:|---|
| `Qwen2.5-32B-Instruct` | 151,643 | yes | 0 | **yes — byte-identical `tokenizer.json`** |
| **`Qwen3-32B`** | **151,643** | **yes** | **4** | **yes** |
| `Qwen3.8-27B` | 248,044 | **no** | 33 | **no — a different vocabulary** |

`Qwen3-32B` is a Qwen 3 generation model that shares our drafter's vocabulary. The
four extra ids are `151665-151668`: `<tool_response>`, `</tool_response>`, `<think>`,
`</think>`.

**Those four ids are the thinking-channel problem, showing up in our own
measurement.** They are target-only: the drafter has no column for them, so any
probability mass the target puts there is mass the drafter can never match, and the
proposal is rejected at that position. The mitigation is the obvious one — serve the
target with thinking disabled for the tasks the pool covers — and it is a serving
flag, not engineering.

**This is a free upgrade and it is not the bottleneck.** Recorded here so that when
α is finally measured, it is measured against the better target. Nothing in
`STACK.md` changes until a run justifies it.

## 3. `Qwen3.8-27B` requires moving the drafter, and the drafter is where C18 lives

248,044 ≠ 151,643. Rejection sampling compares distributions over the *same* index
set; with different vocabularies a drafter's token id does not name the target's
subword, and the comparison is not wrong, it is undefined. So `Qwen3.8-27B` as a
target forces the drafter onto the Qwen 3.x line — which is exactly where the pool
is measured not to work.

### What P33 actually observed, which is not what the proposal assumes

The proposal's diagnosis is that vLLM's multi-LoRA kernels fail to dispatch on the
hybrid language layers, and that the fix is to restrict `target_modules` to the MLP
projections. Our own log says something different. From
`results/P33-lora-matrix-20260914/vllm-subject.log` **[ran]**:

| observed | bearing on the proposal |
|---|---|
| `Resolved architecture: Qwen3_5ForConditionalGeneration` | **confirms it** — the model is wrapped in a multimodal class |
| `qwen_gdn_linear_attn.py … GDN decode kernel: cuda` | **confirms it** — Gated DeltaNet linear attention is real and is running |
| `no matching PunicaWrapper is found; visual.* will be ignored` — **every one of those lines names a `visual.` module, none names a language layer** | **contradicts it** — the modules vLLM declares it will skip are the vision tower, which our adapter does not touch |
| `Triton kernel JIT compilation during inference: _lora_expand_kernel` | **contradicts it** — the LoRA expand kernel *fired*, so a delta was being applied to something |
| P33's brief records *"the adapter touched only MLPs"* as a **withdrawn** diagnosis: the loaded module tree does carry `q_proj` | the proposed fix is the reverse of a reading this project already retracted |

And G1 passed on the subject **[ran]**: the same adapter, in process, moved `lora_B`
and changed the output. The weights are real. vLLM serves the base anyway.

**So: the failure is measured and the mechanism is not known.** That distinction is
the whole of P33's design — four earlier runs came back `IDENTICAL TO BASE` and could
not tell four causes apart, and two diagnoses were withdrawn. Adopting a mechanism
from a text that our own log partly contradicts would be the fifth.

### What it would cost to find out

| step | cost | what it settles |
|---|---|---|
| G3 — merge the adapter into `Qwen3.5-4B` and serve the merged weights | part of one session | whether the weights path works at all. **But a merged adapter is one model, not a pool** — it answers the diagnosis and discards the premise |
| read whether vLLM 0.29.0 forwards `lora_request` into the draft worker | a grep, but only where vLLM is installed — it is not on this machine, so it rides along with the next session rather than being free now | whether per-request adapter swapping in the speculative worker exists at all |
| the two-instance shortcut — drafter with multi-LoRA, target verifying over forced logprobs through our proxy | already how `alpha/` is built **[read]** | nothing about vLLM; it is the path that avoids the question |

The claim that this is closed by an upstream RFC, and the claim that SGLang's
multi-LoRA is less brittle on hybrid architectures, are **[unverified]** — neither
was checked from this machine, and neither should enter a plan until it is.

## 4. Why this is not the moment, and the reason is not difficulty

**Latency is not what this project buys from speculative decoding.** It buys
**acceptance as ranking** — α ordering experts the way verified quality orders them.
`composition-and-speculative.md` records why: EAGLE-3, Medusa and DFlash already win
the latency argument and are each bound to one target, so they cannot rank anything.

**And α has never been measured. Not once, on any target.** The instrument exists
(`alpha/`, `tokenizer_compat.py`, a compatible 32B chosen and hashed); the run has
not happened.

That reorders everything:

- A newer, slower target does not bring the ranking measurement closer. It makes an
  untaken measurement more expensive.
- `Qwen2.5-32B-Instruct` is sufficient to measure α, and is already settled **[ran]**.
- If α turns out not to rank, the migration would have bought a faster version of a
  mechanism that does not work.
- And `generated-code-ceiling.md` records the harder problem underneath: **ranking
  needs experts that differ in quality**, and this project does not have two. Every
  suite it has built either produces one expert at 1.000 or one expert that fails.

So the order is: experts that differ in quality → α ranks them, or does not → *then*
a target worth the migration. The migration is cheap and it is third.

## 5. What this analysis changes today

1. **Nothing is migrated.** `Qwen2.5-3B-Instruct` stays the base; `Qwen2.5-32B-Instruct`
   stays the declared speculative target.
2. **`Qwen3-32B` is recorded as an available target upgrade** with the four
   target-only ids and the thinking-channel caveat, for when α is run.
3. **`Qwen3.8-27B` is recorded as blocked on C18, not on tokenizers alone** — the
   tokenizer rules it out with a Qwen2.5 drafter, and C18 rules out the drafter that
   would fix the tokenizer.
4. **The mechanism of C18 stays unknown**, and is written down as unknown.
