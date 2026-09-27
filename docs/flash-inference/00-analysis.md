# Inference from flash — Phase 0: analysis and proposed spec changes

*The user's brief of 2026-09-27, "frozen base in flash/ROM + adapters in RAM". This document is the Phase 0 that brief asks
for: it answers its questions, corrects the hypothesis where needed, proposes spec changes **without implementing them** and
stops here for review. None of it touches lora-kernel's runtime.*

---

## 1. The brief's three questions

**What base does lora-kernel run on today? Dense or MoE?** Dense. Every released member is on `google/gemma-4-E4B-it` and
the large half of the pair is `gemma-4-12B-it`, also dense **[ran]** B1, B2, M1b, M1d, B5. The MoE variant,
`gemma-4-26B-A4B-it`, is named as the large half's alternative (`training/harness/family.py`, `LARGE_ALTERNATIVE`) and has
never been used.

One nuance matters for this brief: **the E4B is already partly "base in flash"**. Of its ~8 billion parameters, ~2.8 billion
are per-layer embedding tables (42 layers × 256 × 262,144 rows, `hidden_size_per_layer_input: 256` **[read]** config.json).
Per token **one row** of each table is read, so those tables can live in slow storage almost for free. Gemma 3n/4 designed
them for that **[read]**. They are also the tables that today keep the E4B from fitting as a drafter beside the 12B on an L4
**[ran]** C0.

**Which modules do the adapters patch?** The seven projections of every text layer: `q, k, v, o` (attention) and
`gate, up, down` (MLP), with $r = 16$, $\alpha = 32$. The vision and audio towers are excluded **[ran]** `adapter_config.json`.
On an MoE base that would mean patching the experts too: see §3.

**Does the kernel know the active adapter before generating?** Yes, and before the first token:
- the gateway resolves the role from the signed token, and with it the expert (`examples/school/gateway.py`);
- in vLLM the request names the adapter by the `model` field;
- on the Mac track the expert is switched by a pointer before `generate` **[ran]** LIVE, F0, MAC.

**There is a prefetch window between the request's arrival and the first decode token**: it lasts the whole prefill.

---

## 2. The hypothesis, corrected

**The brief's H1:** a domain adapter concentrates expert routing relative to the base without the adapter.

**The control problem.** An MoE already concentrates its routing by the **topic** of the text, with no LoRA at all. Compare
"base on general prompts" against "base + adapter on domain prompts", and the concentration the domain put there is credited
to the adapter. The right control is **the base without the adapter on the same domain prompts**. H1 splits in two:

| | hypothesis | what it needs | cost |
|---|---|---|---|
| **H1a** | **the domain concentrates routing**: on a domain's prompts the base uses a smaller, more stable set of experts than on general prompts, and a cache preloaded per domain hits more | the MoE base and traces; **nothing trained** | hours of GPU |
| **H1b** | **the adapter concentrates it further**: on the *same* domain prompts, base + adapter concentrates more than the base alone | a LoRA on the MoE base, which **does not exist** | one QLoRA session on an A100 + traces |

**Order:** H1a first. If the domain does not concentrate routing, all of H1 falls without anything trained — the repository's
rule: first the cheap test that can falsify.

---

## 3. The MoE base: what exists and what it costs to read

**Bases verified today [read]** (Hugging Face, 2026-09-27):

| | layers | experts / layer | active per token | size of one expert | in MLX |
|---|--:|--:|--:|---|---|
| `google/gemma-4-26B-A4B-it` | 30 | 128 | 8 (`top_k_experts`) | $3 \times 2816 \times 704 \approx 5.95$ M parameters | `mlx-community/gemma-4-26b-a4b-it-4bit`, **15.37 GB** |
| `Qwen/Qwen3-30B-A3B` | — | — | — | — | `mlx-community/Qwen3-30B-A3B-4bit` (config not verified) |

**The arithmetic for Gemma 4 26B-A4B in 4 bits (derived, not measured):**
- one expert ≈ 5.95 M × ~0.56 bytes (4 bits plus scales per group of 64) ≈ **3.3 MB**;
- all experts: 128 × 30 × 3.3 MB ≈ **12.9 GB**; the rest (attention, dense MLP, embeddings) ≈ **2.5 GB**, always in RAM;
- per token 8 × 30 = **240 experts ≈ 0.8 GB are read if none is cached**.

With a hit rate $h$ in the expert cache and a storage read bandwidth $\mathcal B$, the I/O ceiling on decode is

```math
\text{tok/s} \;\lesssim\; \frac{\mathcal B}{(1-h)\cdot 0.8\ \text{GB}}
```

At 3 GB/s: with $h = 0.8$ the ceiling is ~19 tok/s; with $h = 0.5$, ~7.5 tok/s. **The SSD's real bandwidth is measured,
not assumed.** On a 16 GB Mac, less the system (~4 GB), the dense part (2.5 GB) and the KV cache (~1 GB), about 8 GB remain for
experts: ~60 % of them. **The whole question is which 60 %.**

---

## 4. Proposed spec changes (not implemented)

1. **Where the LoRA goes on an MoE base.** Patch only **attention** (and the router, if trainable), leaving the experts
   untouched. That way the experts, 84 % of the bytes, stay frozen and fit for flash/ROM, and the deltas fit in RAM.
   Whether an attention-only LoRA keeps the expert's quality has to be measured — an experiment of its own, not an
   assumption.
2. **The member's manifest** (`releases/*.json`) gains `base_kind: dense | moe` and `lora_scope: attention | attention+router | all`.
3. **An `expert_affinity` per member**: the most-used experts per layer with their frequency, computed offline on a set of the
   domain's prompts **different** from the evaluated one, and hashed as the corpus is hashed today.
4. **Unmerged adapters**, applied as a delta at runtime. That is what we already do (vLLM per request; the Mac track by
   pointer, 2.9 µs **[ran]** MAC); merging stays only for when an engine accepts no delta, as with C0's drafter.
5. **Prefetch in the gateway**: once the role is resolved, before the prefill, ask for the member's affinity experts to be
   preloaded.

---

## 5. Plan: H1a in the cloud, with a gate

**Where:** Colab, by the user's decision (2026-09-27): the Gemma 4 MoE runs go to the cloud, not the Mac. With `transformers`,
the model in 4 bits (bitsandbytes, ~15 GB) fits an L4 or an A100. A *forward hook* on each layer's router records the 8 experts
chosen per token.

**What:**
- **Prompts** from the domains we already have, ~30 per domain: the distributor wiki, the school turns, the distributor staff
  turns and email. On top of that, ~30 general prompts.
- **Traces** of the prefill and of 128 greedy decode tokens. Decode is what matters, because that is where flash is read.
- **Format:** `traces/{domain}/{prompt_id}.parquet` with `token_idx, layer, expert_ids[8]`, out of git like every heavy artefact.
- **Metrics per domain against general:**
  - expert entropy per layer;
  - the fraction of experts covering 80 % of activations;
  - Jaccard between prompts of the same domain against Jaccard between prompts of different domains;
  - reuse between consecutive tokens.
- **A cache simulator** at 4, 8 and 12 GB with the policies LRU, LFU and "preloaded by domain affinity". The affinity is
  computed on half of the prompts and evaluated on the other half.

**H1a's gate, written before the run.** At 8 GB, on domain prompts:
- the affinity-preloaded cache must hit **≥ 10 points more** than LRU without affinity;
- the bytes read per token must fall **≥ 25 %**;
- Jaccard within the domain must exceed Jaccard between domains.

The comparison is prompt by prompt, with the repository's sign test. If it fails, **H1 is refuted** and the line closes with
its document.

**If H1a passes → H1b:**
- an **attention-only** LoRA on the MoE base, for the wiki domain, trained with QLoRA on an A100;
- the same traces with the base and with base + LoRA, **on the same prompts**;
- the same gate, now of the adapter against the base.

**Then M3 and M4 as the brief asks.** M3 is the real streaming run (mmap) on the Mac mini: flush the page cache
(`sudo purge`) between runs, measure the bytes read from disk and separate prefill from decode. M4 is the hardware draft.

---

## 6. Risks and open decisions

- **Scope**: this is a sibling line of `CLAUDE.md`'s objective, not the objective. It stays timeboxed and under
  `experiments/flash-inference/` and `docs/flash-inference/`, without touching the runtime.
- **Measuring on the Mac**: the user's exception covers it, but the user prefers the cloud for the MoE. Only M3 (the real
  streaming) needs the Mac mini, because it measures its SSD.
- **ROM**: freezing the base in silicon makes it impossible to update; LoRAs remain the only way to change it.
- **Prefill**: with the base in flash, the prefill (which reads every expert the prompt touches) can be slow; it is measured
  separately.

**Paused for review.** No code until you approve this Phase 0: the H1a/H1b split, the gate and where the LoRA goes.
