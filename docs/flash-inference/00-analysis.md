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
- on the Mac track the expert is switched by a pointer before `generate` **[ran]** LIVE, F0, MAC. **Superseded
  2026-09-28:** edge *serving* now runs on llama.cpp, not MLX (`CLAUDE.md` §0); MLX stays this document's research
  bench, where the pointer-switch numbers above still apply.

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

---

## 7. H1a result — resumed 2026-10-04, FALSIFIED as written; the substance holds

**Resumed by the user's decision, 2026-10-04**, after the pause above (also recorded in
[`docs/review/moe-distillation-and-spotlight.md`](../review/moe-distillation-and-spotlight.md) §4). H1a ran on one
A100, `gemma-4-26B-A4B-it` with its experts quantised to int4 on the card (bitsandbytes does not quantize a 3-D expert
parameter — read in the run — so the model loads in bf16 on the host, ≈ 52 GB, and is quantized layer by layer on the
GPU), 150 prompts traced (30 per domain × 5 domains: wiki, school, distributor, email, general), 0 errors.
**[ran]** `results/H1A-moe-routing-by-domain-20261004/BRIEF.md`.

| §5's gate, at 8 GB, domain prompts | bar | measured |
|---|---|---|
| affinity-preloaded cache hits more than LRU | ≥ 10 points | **+7.4** (LRU 92.1 %, affinity 99.5 %) — **fails** |
| bytes read per decode token fall | ≥ 25 % | **−93 %** (62.4 → 4.1 MB/token), affinity ahead on 60/60 prompts |
| Jaccard within the domain exceeds Jaccard between domains | — | **0.49 vs 0.26**, 120 : 0 |

**Verdict as written: FALSIFIED** — the one failing clause is the absolute 10-point margin, and it had no headroom: LRU
alone already hits 92.1 % at 8 GB after the prefill warms it, so no routing behaviour could add 10 more points. The
run's own instrument flagged `no_headroom`. Read past that one clause, the domain concentrates the 26B's routing
strongly: 80 % of a domain's decode activations sit in 17–21 % of the experts (40 % on general text, entropy 5.0–5.3
against 6.2 bits), and a cache pinned to a domain's top experts from half its prompts reads 93 % fewer bytes per token
on the other half at 8 GB, winning on every prompt. The general-text control runs the other way (affinity −6 points
against LRU), so the gain is the domain's, not the pinning policy's — the attribution §2's split asked for.

Beside the gate: at 4 GB the affinity margin over LRU is +15.5 points (77.9 % → 93.4 %), where the gate's own 8 GB
choice has already cost the 10-point clause its room; at 12 GB both policies are near-saturated (98.8 % → 100 %).

**For this line:** H1a's substance is what §2.3 of the review doc needed — the data REAP's pruning idea starts from.
H1b (does an attention-only adapter trained on the MoE base concentrate routing further than the base alone) and M3
(real streaming from the Mac mini's SSD) are the next steps, both the user's call, not yet taken.

---

## 8. Is the line worth it? Better results, does it work, at what speed (evaluation, 2026-10-04)

The user asked three questions of the flash line. Each is answered from H1a's record (`h1a.json`: aggregate per-domain
routing and cache metrics) and from runs already on disk. **The per-prompt traces were deleted when worktrees were
cleaned** (they were kept out of git by design), so a per-prompt prefill simulation would need H1a rerun (one A100).

**1. Better results? Unknown, and the evidence so far says no.** A smaller memory footprint for the 26B is worth only as
much as the 26B beats what is served now. In this project's regions no larger model has beaten the E4B member: a trained
12B ties it (B3, PAIR1 **[ran]**), an untrained 12B loses (PAIR0 **[ran]**). The 26B's own headroom run (TEACH0) is
**closed by the user's decision of 2026-10-05, blocked by the serving engine, no result [ran]**: vLLM 0.30's FP8 does not
run on the A100 and it has no `bitsandbytes` method for the L4 retry
(`results/TEACH0-26b-headroom-20261004/BRIEF.md`). Beside it, Google's own model card **[read]** reports τ² (average over 3)
at 68.2 % for the 26B-A4B against 69.0 % for the 12B and 76.9 % for the 31B
(`docs/tau2/TEACHER-TERMS.md` §2.1; self-reported): on that harness the 26B is not ahead of the 12B, which PAIR0/PAIR1
already showed buys no accuracy here. **The line's payoff depended on a larger model beating the member, and none has: the
line buys speed or footprint for a model with no measured quality gain. It rests until a larger model shows value** — the
question moves to τ² T1 (Gemma 4 31B against the E4B base on an external verifier, `docs/tau2/RECON.md`).

**2. Does it work? The routing half, yes [ran].** On a domain's decode tokens, 80 % of the activations sit in 17–21 % of
the experts (general text: 40 %). A cache pinned to the domain's top experts reads 93 % fewer bytes per decode token at 8 GB
(62 → 4.1 MB) and 70 % fewer at 4 GB (175 → 52 MB). **Prefill is broader:** 80 % of prefill activations sit in about 25 % of
the experts (general: 31 %), and a prefill over a few hundred tokens touches most experts of most layers.

**3. At what speed, on a 16 GB machine? Decode plausibly yes; prefill and memory are the risks (derived, not measured).**
The bound is the formula of §3, with the read bandwidth $\mathcal B$ an assumed 3 GB/s, still unmeasured:

$$\text{tok/s}_{\text{decode}} \;\lesssim\; \frac{\mathcal B}{\text{MB read per token}}$$

| | expert cache | MB read per decode token [ran] | I/O ceiling at 3 GB/s |
|---|---|---|---|
| affinity-pinned | 8 GB | 4.1 | ~730 tok/s — I/O stops mattering; compute bounds it (~4B active per token, near the E4B's) |
| affinity-pinned | 4 GB | 52 | ~58 tok/s |
| LRU | 4 GB | 175 | ~17 tok/s |

- **Memory.** 16 GB less the system (~4 GB) and the dense part (2.5 GB) leaves ~9.5 GB for experts *and* the KV cache. This
  project's walks run to 12k tokens: on this Mac, the E4B ran out of memory at a 16,384-token context (LIVE-library
  **[ran]**). An 8 GB expert cache leaves ~1.5 GB for KV, which is too little for these walks. A 4–6 GB cache is the
  realistic one.
- **Prefill.** Each tool turn re-prefills its new tokens, and they touch most experts. With the cache pinned, the experts
  outside it are read from storage once per prefill. That is up to (1 − cache share) × 12.9 GB: about 9 GB at a 4 GB cache,
  roughly 3 s per prefill at 3 GB/s. A walk makes 3–5 calls, so that is **+9–15 s per walk** in the worst case, against the
  E4B's whole walk of 13 s (median, LIVE-library **[ran]**). The real figure is lower, because not every expert is touched,
  but it is unmeasured.

**Verdict of this evaluation:** the mechanism works for decode, and decode speed on a 16 GB machine is plausible at a 4–6 GB
cache. Prefill, on this project's tool-heavy walks, and the memory left for the KV cache are the open risks. The line's
payoff depends entirely on a quality result it does not have. **Order:**
1. ~~TEACH0 (tomorrow, on Colab).~~ **Ran 2026-10-04, blocked; closed 2026-10-05 by the user's decision, no result**: FP8
   failed twice (inductor compile, then vLLM's FP8 kernel does not run on the A100's sm80); the A100 was refused three
   times; the one bitsandbytes retry the brief allows (an L4) met a vLLM 0.30 with no such method. ~~The retry runs when A100
   quota returns.~~ No retry: the 26B line is closed, and PAIR0/PAIR1 plus Google's card **[read]** (26B 68.2 vs 12B 69.0 on τ²)
   are why. The line **rests until a larger model shows value**; τ² T1 asks it of the 31B.
2. ~~Only if the 26B beats the E4B member: M3, the real streaming test of §5, on the user's machine. It needs the user's
   approval: about 45–60 minutes of the machine, which covers downloading a ~15 GB 4-bit GGUF, timing decode and prefill
   on our walk prompts, and measuring the SSD's actual bandwidth.~~ Not reached, and not requested: its condition never
   held. M3 would come back only if a larger model first shows value.
3. ~~H1b (attention-only adapter) only after M3, because it adds nothing if the base cannot be served fast enough.~~ Same:
   behind M3, so it rests too.
