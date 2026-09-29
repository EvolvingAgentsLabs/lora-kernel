# Guide — understanding lora-kernel from scratch

*For people, not for models.* This guide explains, in words and examples, every piece this repository uses: how a
language model generates text, what inference engines do (llama.cpp, vLLM, MLX), what quantization is, what a LoRA
is, how speculative decoding works (with a draft model, with MTP and with EAGLE), how many experts are served on a
single GPU, and how it all fits into what we are after. Then it tells, in order, what we have unlocked and what is
still missing.

The rigorous mathematics lives in [`FOUNDATIONS.md`](FOUNDATIONS.md); here is the intuition, with a link to the formal
section whenever it is needed. Measured results live in [`RECORD.md`](RECORD.md) and the live state in
[`PLAN.md`](PLAN.md).

**A convention you will see throughout the repository.** **[read]** marks something we know from reading (a paper,
documentation, someone else's code). **[ran]** marks something we observed by running it here, with the run's
directory. Anything without a marker is treated as [read]. The rule exists because an earlier project in this
organization reached 18,680 lines with three tests: reading is not measuring.

---

## 1. What we are after, in one page

An organization that runs on agents — one agent per role: customer service, purchasing, IT, teachers — sends every
task to a frontier model in the cloud (OpenAI, Anthropic, Google). Many of those tasks repeat: read a calendar, open a
ticket, answer from a list. This repository's thesis is that **that repetitive part can be done by a small, local,
specialized model**, and the frontier is kept for whatever falls in no measured territory.

The pieces, from the inside out:

- **A small base model, resident on a GPU** (today Gemma 4 E4B, and Gemma 4 12B as the large half).
- **One expert per task, as a LoRA** — a lightweight patch on top of the base model. Switching experts means switching
  patches, not models.
- **One memory per expert**: pages of short, verifiable statements. The LoRA does not memorize the facts; it learns to
  *walk* the memory and to cite the statement it relies on.
- **A gateway** in front: it verifies identity, decides the role, runs the tools with permissions the model cannot
  change, holds back what needs approval and anchors every answer in what the tools returned.
- **An exit to the frontier** for whatever no expert covers.
- **A speculative pair** (small + large) to gain speed without losing quality.

And one rule of method: **every claim is measured against our own previous version**, with the condition that would
falsify it written *before* running.

---

## 2. How a language model generates text

### 2.1 Tokens

A model does not see letters: it sees **tokens**, pieces of text drawn from a fixed vocabulary (in Gemma 4, 262,144
tokens). "refrigerator" may be one token or three. Text goes in as a list of numbers (ids) and comes out as another
list of numbers that are turned back into text. Details in [`FOUNDATIONS.md`](FOUNDATIONS.md) §3.

Why it matters here: **two models can only do speculative decoding together if they share the same vocabulary** — the
draft proposes ids that the large one has to be able to verify. Gemma 4 E4B and Gemma 4 12B have byte-for-byte
identical vocabularies **[ran]** B2.

### 2.2 One token at a time

Generating is a loop: the model looks at all the text so far, computes a **probability distribution** over the next
token (the *logits*, normalized), picks one, appends it and repeats. Always picking the most probable one is called
**greedy** or **temperature 0**: it is deterministic *in theory* — in practice, see §8.4.

### 2.3 Prefill and decode: two very different regimes

- **Prefill**: processing the whole prompt. It is a single pass over all positions at once — lots of arithmetic, well
  exploited by the GPU.
- **Decode**: generating each new token. Each step processes *one* position… but has to **read all of the model's
  weights from memory**. A 12B in bf16 is ~24 GB per step.

That is why generating is slow even when the GPU is fast: **the bottleneck is not multiplying, it is moving weights from
memory** (*memory-bound*). This single idea explains almost everything that follows: quantization (smaller weights →
fewer bytes per step), batching (several requests share one read) and speculative decoding (verifying several tokens
with a single read). See [`FOUNDATIONS.md`](FOUNDATIONS.md) §2.3.

### 2.4 The KV cache

To avoid recomputing everything at each step, the model keeps, for each layer, some intermediate matrices (the
attention keys and values) of the tokens already seen: the **KV cache**. It makes decode fast at the cost of memory,
which grows with the length of the text and with how many requests you serve at once. Managing it well is the central
problem of a server (§3.2).

---

## 3. Inference engines

A model is a file of weights. An **inference engine** is the program that loads it and generates text fast. Three
matter to us.

### 3.1 llama.cpp (and Ollama)

**[read]** llama.cpp is a C/C++ engine designed to run models on common hardware: CPU, Apple Silicon (Metal),
consumer GPUs. Its traits:

- **GGUF format**: a single file with weights and metadata, typically **quantized** (§4) with schemes such as `Q4_K_M`
  or `Q8_0`. It is what lets a 12B run on a laptop.
- **One request at a time, very well**: it is optimized for single-user latency; the server (`llama-server`) exposes
  an OpenAI-compatible API and supports several requests in parallel, but it is not designed for hundreds at once.
- **LoRA**: an adapter can be loaded at startup, and the server lets you adjust the scale of the loaded adapters at
  runtime — check with the version you use.
- **Speculative decoding with a draft model** (`--model-draft`).
- **Ollama** is built on llama.cpp (and, in recent versions, on MLX on Mac): it packages models (`gemma4:12b`,
  `gemma4:12b-mlx`) with a recipe (`Modelfile`) that can include a LoRA `ADAPTER` **fixed when the model is created**. It
  is not a per-request switch.

When it fits: one user, a local machine, little memory. Our 2026-09 analysis compared it with vLLM and vLLM was kept
for development for a concrete reason: **serving many LoRAs per request and measuring with the same tools across the
whole project**. Since 2026-09-28 llama.cpp is also, by the user's decision, the **edge serving runtime** — the
profile that puts a member in front of a live agent runtime on the user's own machine, once training and measurement
are done on the server profile (§3.5).

### 3.2 vLLM

**[read]** (Kwon et al. 2023) vLLM is a server engine, designed for **many concurrent requests** on GPU:

- **PagedAttention**: it stores the KV cache in fixed blocks with a page table per request, like an operating system's
  virtual memory. Requests of different lengths coexist without waste.
- **Continuous batching**: a new request joins the batch at any step, without waiting for the others to finish. It is
  what turns "several requests share one read of the weights" (§2.3) into real throughput.
- **OpenAI-compatible API** (`vllm serve`): any client that talks to OpenAI talks to vLLM.
- **Multi-LoRA**: many adapters resident at once, and **each request picks its own through the `model` field**; within
  one batch, each request uses its own LoRA (§5.4). Adapters can be **loaded and unloaded hot** with
  `VLLM_ALLOW_RUNTIME_LORA_UPDATING` and the `/v1/load_lora_adapter` endpoints — **0.23–0.28 s per adapter [ran] F0**.
- **Speculative decoding** with a draft model, n-grams, EAGLE/EAGLE-3 and MTP (§6), configured at startup with
  `--speculative-config`.

It is the engine of this whole repository: it runs on GPUs rented in Colab (L4, A100) through
`training/harness/chain_serve.sh`. Current version here: 0.30.0.

### 3.3 MLX (and mlx-lm, mlx-vlm)

**[read]** MLX is Apple's framework for its **unified memory**: on a Mac with Apple Silicon, CPU and GPU share the same
memory, so a model is not copied between them. `mlx-lm` generates and trains text; `mlx-vlm` adds multimodal models.

What we found reading its code (2026-09-27):

- Gemma 4's 12B is multimodal (`gemma4_unified`): **it is loaded by `mlx-vlm`, not `mlx-lm`**.
- The `mlx-lm` server accepts an adapter per request, but **switching it reloads the whole model** — it is not a hot
  switch.
- `mlx-vlm` ships **Gemma 4's MTP drafter** (`gemma4_unified_assistant`) and an EAGLE-3 one.

That is why this project's Mac track built its own hot switch: the base model is loaded once and each layer carries
the patches of every expert; switching experts is switching a pointer (§5.5). ~~MLX stays the `edge` engine~~ — as of
2026-09-28 that is superseded (§3.5): the verdict behind it was about speculative decoding only, and it still holds on
that narrow question. MLX remains the **research bench**: it is the one runtime with Python access to the graph
itself, which is what the hot-switch pointer trick needs.

### 3.4 Which to use, in one table

| | llama.cpp / Ollama | vLLM | MLX |
|---|---|---|---|
| hardware | CPU, Mac, consumer GPU | NVIDIA GPU (and others) | Apple Silicon |
| strong at | one user, little memory | many requests, many LoRAs | Mac, unified memory |
| LoRA per request | limited | **yes, native** | not native (we build it) |
| speculative | draft model | draft, EAGLE-3, MTP | draft, MTP (mlx-vlm) |
| here | **edge serving profile (2026-09-28)** | **server profile — training, measurement** | research bench (Python access to the graph) |

### 3.5 Two profiles, the user's decision (2026-09-28)

The project now names two runtime profiles instead of asking, case by case, which engine to use:

- **`server`** is vLLM on Colab: every training run and every measurement in this repository goes through it, for one
  reason that does not change with the hardware — **the same tool, the same numbers, across the whole project** (§8).
- **`edge`** is **llama.cpp on the user's own machine** (a MacBook Air M4, 16 GB): serving one member to a live agent
  runtime. **[ran] MAC2:** llama.cpp build 11146 loads the E4B, the 12B's LoRA acts once converted to GGUF (6/6), and
  `POST /lora-adapters` swaps it in **3 ms**, restoring the base exactly — the same swap-and-restore behaviour MLX
  showed in 2.9 µs, on a different engine. Serve the E4B as **Q8_0**, not Q4_0: Q4_0 flips the order id with
  llama.cpp's own prompt cache **[ran]** LIVE-distributor — a quantization choice that changes *which token* comes out,
  not just how fast.

This does not overturn MAC's finding about speculative decoding on the Mac: Gemma's MTP drafter still slows the 12B
there (0.52× with the expert's LoRA on its own domain, 0.66–0.87× otherwise, **[ran]** MAC2), and the E4B+12B pair
together still run out of Metal memory in 16 GB. What changed is narrower and cheaper to state: for *serving* one
member — no speculative pair, no second model resident — llama.cpp on the Mac is what the user runs, and MLX is kept
for the research that needs to reach inside the graph.

### 3.6 Prefix caching: what defeats it is order, not size

vLLM (and llama.cpp) can reuse the KV cache of a prompt's shared prefix across requests, so a tool block that every
request repeats should, in principle, be computed once. **[ran] E5:** it was not. OpenClaw's 54-tool block (7,205
Gemma tokens) served exactly as the member was trained — request first, tool block after, inside the same user turn —
made TTFT go from 0.10 s to 1.70 s (16.8×) and b8 throughput fall from 132 to 108 tok/s; accuracy fell with it, 70/70
to 39/70, because the member stopped calling its own tool in 28 of 31 failures. Put the very same block *before* the
request instead — the one change that lets a cache reuse it as a literal prefix — and it costs nothing: 0.09–0.11 s,
indistinguishable from the pruned baseline.

**Why [read]:** a prefix cache keys on the exact leading bytes of a prompt. Two requests that differ in their first
few hundred tokens never share a cache entry no matter how much of the rest is identical — so a block's *size* was
never the variable that mattered; its *position* was. This is also why pruning stays the default on both axes here:
the corpus was never trained with the block first, so moving it would be training a different member, not a format
change. **[ran] E5** also found that two LoRAs sharing one batch keep 0.88 of one adapter's throughput (contention at
the edge of one burst of 16) — small next to the caching effect, but real.

---

## 4. Quantization: smaller weights

Weights are stored as numbers. In **bf16/fp16** each takes 2 bytes: a 12B ≈ 24 GB. Quantizing is storing them with
fewer bits:

- **FP8** (1 byte): half. Recent GPUs (L4, H100) accelerate it in hardware. vLLM can quantize to FP8 at load time
  (`--quantization fp8`). **That is how we ran the 12B on a 24 GB L4 [ran] F0.**
- **INT4 / 4 bits** (½ byte): AWQ and GPTQ on GPU; `Q4_K_M` in GGUF; 4-bit "affine" in MLX. A 12B fits in ~7 GB — that
  is why it runs on your 16 GB Mac.

The cost is a small loss of numerical precision. Two practical consequences here:

1. **A LoRA trained on bf16 weights can be applied on quantized weights** (QLoRA does exactly that when training). We
   verified it: the 12B's LoRA, trained in bf16, is applied on the 12B in FP8 **[ran] F0** (G1, §8.2).
2. **Numbers are not compared across precisions as if they were the same**: a result in 4-bit MLX is not the same
   experiment as one in bf16 vLLM.

Details: [`FOUNDATIONS.md`](FOUNDATIONS.md) §4.3.

---

## 5. LoRA: an expert as a patch

### 5.1 The idea

Tuning a whole model (full *fine-tuning*) changes billions of weights and produces another model of the same size.
**LoRA** (Hu et al. 2021) **[read]** freezes the weights and learns, for some matrices, a **low-rank** correction:

```math
W' = W + \tfrac{\alpha}{r}\,A\,B
```

where $A$ and $B$ are two thin matrices (rank $r$, 16 here). Instead of changing $W$ (millions of numbers) you learn
$A$ and $B$ (thousands). A LoRA of the 12B weighs ~140 MB against the model's ~24 GB. See
[`FOUNDATIONS.md`](FOUNDATIONS.md) §4.1.

### 5.2 Why it is the central piece

Since $W$ is never touched, **the base model stays resident and the only thing that changes between experts is the
patch**. You can:

- switch it per request;
- mix requests for different experts in the same batch;
- version, publish and discard an expert without touching the base.

*The system is a set of patches on a resident base.*

### 5.3 How it is trained here

- With **PEFT** (Hugging Face), in Colab, on the seven attention and MLP projections of each layer, $r = 16$,
  $\alpha = 32$.
- In Gemma 4 the **vision and audio towers must be excluded**: their projections are of another type and PEFT does not
  accept them (that was block P29; `training/s4_train.py::towers_to_exclude`).
- The corpus is **exactly what the model will see when it is served**: the same system prompt, the same tool block,
  the same format. A corpus that teaches another prompt teaches something else (§8).

### 5.4 Serving many LoRAs at once

**[read]** (Punica, Chen et al. 2023; S-LoRA, Sheng et al. 2023) In a batch where each request uses a different
expert, the common part ($xW$) is computed once for all of them and each one's correction is computed with kernels that
"gather" the $A_i, B_i$ of each request. vLLM does it with `--enable-lora --lora-modules name=path`, and the request
picks its expert with the `model` field. See [`FOUNDATIONS.md`](FOUNDATIONS.md) §5.2.

**Does mixing experts in one server cost anything? [ran] C1** (`results/C1-concurrency-20260929`, one L4, vLLM 0.30,
four members mixed — `school-s0`, `upper-s0`, `staff-s0`, `out-s0`): no material contention. 16 sessions split across
the four adapters reach 278.6 tok/s against 269.7 tok/s for the same 16 sessions on one adapter alone (1.03×); 32
sessions across the four reach 504 tok/s, p95 time-to-first-token 0.24 s, 0 errors of 128 requests; throughput scales
near-linearly from 1 to 32 concurrent sessions (22.7 → 135 → 270 → 500 tok/s), and the ceiling still sits above 32.
This supersedes §3.6's E5 reading of 0.88 for two LoRAs sharing a batch — that number held at the edge of one burst of
16; C1 is the same question at the scale a live gateway would actually see.

### 5.5 Hot switching: what it really means

There are three different things called "switching LoRA":

| | how | cost |
|---|---|---|
| **reload** | unload the model and load it again with another adapter | seconds (what the `mlx-lm` server does) |
| **hot load** | add a new adapter to a running server | **0.23–0.28 s in vLLM [ran] F0** |
| **pick per request** | all adapters resident, each request uses its own | almost zero (vLLM; our Mac track) |

### 5.6 The trap of the adapter that is not applied

An engine can say "adapter loaded" and answer with the base model, with no error. It happened to us (C18: the tensor
names did not match the served model). That is why **every expert passes gate G1 before being measured**: the same
question to the base and to the expert has to give different texts (§8.2).

---

## 6. Speculative decoding

### 6.1 The idea

Generating with the large model is slow because each token is a full read of the weights (§2.3). But verifying **k
proposed tokens** costs almost the same as generating one: they are all processed in a single pass. So:

1. A fast **draft** proposes k tokens.
2. The large model **verifies them all in one pass**.
3. They are accepted left to right as long as they match what the large model would have chosen; at the first
   disagreement, the large model puts in its own token and the round ends.

**The output is exactly the large model's** — with any draft. A bad draft costs speed, never quality **[read]**
(Leviathan et al. 2023; Chen et al. 2023). At temperature 0 the rule is simple: a token is accepted if it is exactly
the one the large model would have chosen. Proof: [`FOUNDATIONS.md`](FOUNDATIONS.md) §6.1–6.3.

### 6.2 How much it yields: α and the accepted length

- **α (acceptance)**: the fraction of proposed tokens that are accepted.
- **Mean accepted length**: how many tokens are emitted per pass of the large model (including the one the large model
  puts in).

If each token is accepted with independent probability α and k are proposed:

```math
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha}
```

tokens per pass. The real speedup also depends on how much the draft costs ([`FOUNDATIONS.md`](FOUNDATIONS.md) §6.4).
With a large batch it yields less: the GPU is already busy with other requests and "verifying for free" stops being
free.

### 6.3 Three kinds of draft

| | what it is | sees the large model | here |
|---|---|---|---|
| **draft model** | a complete small model with the same vocabulary (E4B for the 12B) | no: it generates on its own | B4 measured its acceptance |
| **EAGLE / EAGLE-3** **[read]** | a small head that predicts from the large model's *hidden states* | yes | BCCard's public EAGLE-3, F0 |
| **MTP** (*multi-token prediction*) **[read]** | the draft Google published with Gemma 4 (`-assistant`): 4 layers that use the large model's activations and cache | yes | **the best performer, F0** |

The difference matters for experts: a draft that **sees the large model's activations** also "sees" the effect of the
active LoRA, so a single draft could serve every expert.

### 6.4 The LoRA problem: the draft was not trained with it

Gemma 4's MTP was trained looking at the 12B **without** a LoRA. With the LoRA active, the large model writes
differently — with the expert's style and format — and the draft guesses right less often. **We measured it [ran]
F0:** on the expert's own questions, acceptance at the first position falls from 0.98 to 0.58 and the speedup from
2.73× to 1.74×.

How that gap closes (the user's strategies document, 2026-09-27):

- **A. A shared draft**, trained on the answers of every expert.
- **B. A base draft + a draft LoRA per expert**, picked together with the large model's LoRA (vLLM does not support it
  yet; it is a proposal, RFC #52038).
- **C. A complete draft per expert**: the acceptance ceiling, expensive in GPU.
- **D. Retraining the native MTP per expert.**

---

### 6.5 Hot-swapping: the LoRA yes, the draft not yet

What we want is one server with **one base model**, **N experts** and, for each, **a draft tuned to that expert**, all
switchable per request. Those are two different things to hot-swap, and today they stand in very different places.

**The large model's LoRA — works today.**

| where | how | measured |
|---|---|---|
| vLLM | every LoRA resident; each request picks its own by the `model` field; added and removed with `/v1/load_lora_adapter` | hot load **0.23–0.28 s**, also with the draft running **[ran] F0** |
| Mac (MLX, our code) | each layer carries every expert's patch; one active; switching is moving a pointer | **2.9 µs**, and the base's text comes back exactly **[ran] MAC** |
| Mac (llama.cpp, `edge` profile) | the LoRA is converted to GGUF once; `POST /lora-adapters` swaps it on a running server | **3 ms**, base restored exactly, spec-decode output identical 20/20 **[ran] MAC2** |

**The draft (MTP, EAGLE, a small model) — one draft per server.**

- In vLLM the draft is fixed **at start-up** (`--speculative-config`) and is **one for the whole server**: there is no
  draft per request, and no way to change it without a restart **[read]** vLLM documentation.
- vLLM **applies no LoRA to a draft**: the proposal exists (RFC #52038, for DFlash drafts) but is not implemented **[read]**.
- Gemma 4's MTP draft **cannot be retrained with `speculators`**: its "MTP finetuning" covers the MTP heads that ship inside
  the checkpoint (Qwen3-Next, Qwen3.5), not Gemma 4's external `assistant` **[read]**.

**What happens today with one draft and several LoRAs.** It works, and the output is still the large model's (§6.1), but
the draft guesses worse on each expert's own ground: with the wiki LoRA, position-0 acceptance falls from 0.98 to 0.58
and the speed-up from 2.73× to 1.74× **[ran] F0**. On the Mac, with the LoRA, the draft does not speed things up **[ran]
MAC**; on llama.cpp it is worse than that — the MTP drafter *slows down* the 12B with the expert's LoRA on its own
domain (0.52×) and gives only a modest win otherwise (0.66–0.87×) **[ran] MAC2**. Restricting which layers carry the
LoRA does not rescue the drafter either — see §6.6.

**How to get "a draft tuned per expert", depending on what exists:**

| strategy | what changes per request | does it exist today? |
|---|---|---|
| **A. one shared draft**, trained on the answers of all experts | only the large model's LoRA | yes, with vLLM as is; it remains to be trained (EAGLE-3 with `speculators`) |
| **B. base draft + one draft LoRA per expert** | the large model's LoRA **and** the draft's | **not in vLLM** (it would take modifying the component that runs the draft). **Possible on our Mac track**: the same `HotLoRA` that wraps the large model's layers can wrap the draft's |
| **C. one full draft per expert** | the whole server (one instance per expert, or a restart) | yes, but it does not scale; it serves as the ceiling |
| **D. the native MTP retrained per expert** | same as C | no support in `speculators`; the training would have to be written |

**What we measured next:**
- ~~**F0b**: whether the output with the draft is identical to the plain one~~ — **[ran]**: not testable on an L4 in FP8; the differences read as drift (§8.4).
- **C0 [ran]:** on an A100 in bf16, Gemma's own MTP drafter with the domain's expert LoRA turned on gives 1.92× on the
  domain (α 0.34) and 2.40× general, against 2.80×/2.60× on the base — a real recovery from F0's 1.74×, but still below
  the base's speed. The other arm — the wiki E4B, already aligned to the same corpus (B4: the 12B accepted 90% of its
  drafts), merged and served as a full standalone draft (strategy C) — did not run: it OOMs beside the 12B on an L4;
  vLLM's online FP8 fails on that GPU's compute capability; bitsandbytes is not an accepted drafter quantization; an
  H100 was refused on quota. **This is still open** — a drafter aligned to the expert (strategy B or C, properly sized)
  is parked, not falsified, because MTP already pays for itself on an L4 and does not on the Mac (§6.5).
- **C0-upper [ran]:** does confining the LoRA to the upper half of the layers (§6.6) help the drafter, since MTP reads
  the large model's own upper-layer activations? No: α on the domain goes base 0.82 → full LoRA 0.44 → upper-half LoRA
  0.43 (ρ = −0.02). **Layer restriction does not help the drafter** — see §6.6 for why, and for what it *is* good for.

### 6.6 Restricting the LoRA to the upper layers: a KV-sharing lever, not a drafter fix

Everything in §6.4–§6.5 changes the expert's LoRA and asks what it does to the drafter. This section asks a different
question about the *same* lever — putting the LoRA only on the upper layers of the decoder — and gets a different
answer depending on which problem it is aimed at.

**As a way to share KV across experts — it works. [ran] E6:** the school member trained again with its LoRA reaching
only decoder layers 21–41 of 42 (the upper half; `--layers-from half`) scores exactly like the full member: 70/70
held-out, 15/15 demo, 0 lost. More to the point, **the KV cache of the 21 layers below is bit-identical to the base
model's** (a base-vs-base control came back identical too). The reason is mechanical, not a property of this expert in
particular: a layer the LoRA never touches computes the same keys and values for any expert, because nothing about the
weights that produced them changed. A server holding several experts could compute that lower KV once, from the base
model, and let every expert's requests share it — paying the LoRA's extra cost only from layer 21 up. **The caveat
[ran] E6:** the E4B already caches 24 of its 42 layers on its own (an architecture feature, unrelated to this LoRA), and
that boundary does not line up with the LoRA's: switching experts still recomputes layers 21–23. The suite also sits at
the full member's ceiling, and this ran on one seed.

**As a way to help the drafter — it does not. [ran] C0-upper:** the hope was that if MTP mainly reads hidden states
from the upper layers, an adapter confined to that same upper half would change less of what the drafter sees than a
full-depth adapter does, and so cost it less acceptance. It does not: α on the domain lands at 0.43 with the upper-half
adapter against 0.44 with the full one — no improvement (ρ = −0.02, read as none). **Why, [read]:** the upper-half
adapter still touches exactly the layers MTP reads from — confining the LoRA to the *upper* half leaves the top
untouched-by-restriction, so from the drafter's point of view almost nothing changed. On an L4 the E4B's own MTP still
pays with its LoRA on regardless (2.4× b1, 2.1× b8) — a result about that draft being cheap and aligned to begin with
(C0), not about which layers carry the adapter. **In vLLM, the upper-half adapter serves at exactly the full adapter's
speed** — half an adapter saves memory, not time, probably because the untouched lower layers are zero-filled rather
than skipped **[read]**.

**The two readings side by side, so as not to conflate them:** layer-restricted LoRA is a genuine lever for *serving
many experts cheaply* (shared lower KV, one control run to confirm it, §6.6 above) and a genuine dead end for *aligning
a drafter to an expert* (§6.4–§6.5) — the same knob, two different mechanisms, and only one of them moved.

## 7. From a model to a system

### 7.1 Memory: pages of atomic statements

A LoRA that memorizes facts is wrong when the facts change and cannot show where it got a piece of data. The user's
design (2026-09-24) separates the two:

- **The memory** is a wiki of pages; each page is a list of **one-sentence statements**, verifiable, with the links
  *inside* the statements ("The Lumo-410 film is stored in the Old Mill warehouse").
- **The LoRA learns the trajectory**: search, open a page, open the statement, follow the link, and **cite**
  `[id§anchor]` the statement it relies on. The "referee" verifies the citation mechanically.

**[ran]** W9: on a world the model never saw, the untrained model walks 19/40 multi-hop questions (Gemma); trained on
other worlds, 38/40. A skill the corpus did not show (comparing) is not learned (10/40); shown, it is (37/40) **[ran]**
B3, B5. Details: [`MEMORY.md`](MEMORY.md).

**Editing the library after training holds up — for the reason the design intends, not a stronger one. [ran] W7:** one
statement was patched in the markdown library, no retraining, on `distributor-wiki@v2`'s own worlds and questions: 37
of 38 control answers followed the new value, each one citing the patched line; 0 stale. That is the split working as
designed — the LoRA never held the fact, so there is nothing in the weights to contradict the page. Closed-book,
without the note in front of it, the weights still answer with the *old* value on 1 of 40 questions: not zero. **Why
[read]:** the member learned the *route* to the statement well enough that on rare occasions it can reproduce the
value it usually only reads — reading, not the library overruling memory, and a reminder that "the LoRA does not
memorize facts" is a matter of degree measured here, not an architectural guarantee.

### 7.2 The router and the frontier

Deciding *which expert* handles a request is a classifier that also has to be able to say "none". We tried an n-gram
model, embeddings (Qwen3-Embedding and EmbeddingGemma) and a small classifier: **none passed** — all of them lose
legitimate requests from senders they did not see **[ran]** M2, E1. In production, **the user's role (which comes in
their token) is the route**, and whatever the role does not cover goes to the frontier or to a person according to the
role's policy.

That leaves a second decision the router was never going to make for a single member anyway: once a request *is*
inside a role's corpus, when should that member itself say "not this"? **[ran]** M10 answers it by training the
abstention directly into the corpus rather than adding a classifier in front of it: `train_out` is the distributor
member's usual 700 turns, byte for byte, plus 70 `OUT OF SCOPE` turns drawn from the role's own egress policy. Compared
against the plain member (`staff-s0`), the abstaining one (`out-s0`) loses nothing it already had — 0 of 70 held-out
turns regress — and gains what it was trained for: 20 of 20 held-out out-of-scope requests abstained, against 0 of 20
for the member that never saw the pattern; the live demo went 6/6 against 5/6. **[read]** why this is cheaper than a
router: the member already reads the whole request to answer it, so asking it to also classify "is this mine" costs a
few training turns, not a second model in the path — at the price of doing it per member rather than once for all of
them.

### 7.3 Agents and the gateway

**OpenClaw** is an agent runtime: each agent talks to "a model" through an OpenAI-compatible API. This repository's
gateway sits in that place:

1. **Identity**: a signed token states user, role and school. The model cannot change it.
2. **Turn**: the role's prompt and tools, on the local expert.
3. **Permissions in the tools**: asking for another school's record is rejected by the tool, whatever the model
   writes.
4. **Holds**: a charge or a notice to every family waits for a principal's approval.
5. **Anchoring**: every line of the answer has to be in what the tools returned; if not, the tool's text is shown —
   and counted.
6. **Exit**: whatever the role does not cover goes to the frontier (Claude Haiku in the live run) or to a person.

**[ran]** the school from the reference diagram, 15/15 scripted scenes and 15/15 **through the real OpenClaw** with the
real model and Haiku as the frontier. What the first live turn taught: OpenClaw adds its own context as the last
message; the gateway has to read the real request inside that. See [`OPENCLAW.md`](OPENCLAW.md) §6, [`DEMO.md`](DEMO.md).

**The gateway does not care what serves the model underneath — proven by running it on the edge. [ran] LIVE-distributor:**
the distributor's member (E4B Q8_0 + its LoRA) served through llama.cpp on the user's own machine (§3.5), 5 of 5 turns
through the real OpenClaw 2026.9.4. The same identity/permission/hold/anchoring/exit machinery applied unchanged; what
running against a real client caught, and the server profile never would have: llama.cpp drops the stop string the
corpus-mode loop relies on to end a turn cleanly, and the distributor's own store was not thread-safe under OpenClaw's
concurrent calls (first attempt void; both fixed). **[ran] M10** then ran the abstaining member live the same way: 6 of
6 through OpenClaw, 5 answered locally and the sixth — a thank-you note to suppliers, correctly read as out of scope —
forwarded to **Claude Haiku 4.5** through the gateway's frontier exit: 10,198 + 195 tokens, $0.0112. That member is not
a formal release (no release file yet) — the live run is a demonstration of the egress path, not a claim that the
member has passed the gate.

### 7.4 Multi-turn and memory: why carrying the conversation is not the fix

A gateway that reads only the last request has no way to resolve "move it to dock 5" if "it" was named two turns
earlier — the reference has nothing to point at in that one message. The obvious repair is to hand the model the
whole conversation: `Gateway(history=True)`.

**Why that is still the naive baseline. [ran] MT0** (`results/MT0-multiturn-baseline-20260929`): on 60 held-out
distributor sessions (124 turns, 54 of them dependent on an earlier turn), a member with no conversation gets 4 of 54
dependent turns right — and even that is chance: the 4 all land in purchasing, whose 4/10 is no better than guessing,
while the other 44 dependent turns, outside purchasing, score 0. The same member given the conversation gets 43 of 54
(79.6%) — a real gain, and this is not a general fix for a broken member: independent first turns score 60 of 60 in
both arms. But look at *where* the 11 misses cluster: a reference copied straight into a tool argument is resolved
well (receiving 10/10, returns 10/10, purchasing 9/10, dispatch 12/14); a reference that only shows up in free text —
a customer-service reply that says "that order" without ever restating the order number — is filed wrong 8 of 10
times. **[read]**: the model can read the history; it does not reliably use it to restate a fact the reply needs but
the person did not repeat. And the fix does not stay cheap either way: tokens grow with the session even over two or
three turns (+24% by turn 2) — a shape that keeps getting worse as sessions get longer, which is exactly the case a
production gateway has to serve.

**What a KV operational memory is.** Instead of replaying the conversation, keep what a session has learned — an
order id, a dock number — in a small cache outside the prompt, addressed by name, the same way the library in §7.1 is
addressed by key: `<get>order</get>` returns a value, `<put>dock=5</put>` stores one. Each turn the model sees one
line instead of a transcript: `state: receiving/assigned · keys: order, dock` — the workflow's current state and the
*names* of the keys holding something, never the values. The state is not the model's to decide: it advances only
when the tool layer actually runs a call — the same discipline §7.3's gateway already applies to permissions and
grounding, now applied to what "the current step" means. **[ran] in tests, not yet trained on**
(`examples/common/opmemory.py`): a session cache scoped to (organisation, user, session) plus a per-organisation
global cache, served by the tool layer like any other tool and bounded by the same signed claim already described in
§7.3 — no key crosses a tenant or a user.

**How a LoRA could learn to operate it.** §7.1 showed a LoRA learning to *read* a library by key — search, open,
cite. The workflow harness under design asks for a second habit on the same footing: which workflow a session is in,
which tool its current state calls for, and which key holds the value that call needs — reading with `<get>`, and now
also writing with `<put>`. Nothing about *values* is trained in: the cache stays outside the weights and is written at
runtime, never memorised, exactly as the library is never memorised (§7.1). And it is trained *inside* the member,
next to its tools and its corpus, not as a second adapter stacked on top. **[read]**: that choice is not incidental —
a shared protocol adapter composed with a domain one is what `harness.lora` tried, and what got parked because the
composition could not be measured cleanly. Teaching the same habit inside each member's own corpus is a different bet
on the same idea, not a retry of the one that failed.

**What H1 will measure.** `results/H1-workflow-harness-20260929` (**pre-registered, running — no result yet**) trains
a member on MT0's corpus plus harness turns and compares three arms on MT0's own 60 sessions: `history` (the baseline
above), `harness` (the one-line context, tool block kept) and `harness-noblock` (the same, without restating the
tools in the prompt — testing whether the member knows them well enough not to need reminding). It passes only if the
harness loses no more than 3 of the 54 dependent turns `history` gets right, keeps prompt tokens flat as the session
grows (turn 3 no more than 1.1× turn 1, where `history` keeps climbing), holds first turns at 90% or better, and — the
check this design adds — every dependent turn answered right also fetched its value from the right key, not from a
lucky guess. Design and open decisions: [`review/harness-workflow-kv.md`](review/harness-workflow-kv.md). Until H1
lands, whether a LoRA can operate a workflow's keys the way it navigates a library is a claim under test, not a
result.

---

## 8. How we measure (and why this way)

### 8.1 Headroom first

Before building a treatment, you measure whether it **can** move anything: if the untrained model already scores
10/10, no treatment can improve and every arm ties — and a tie reads as success. Conversely, if everything is out of
reach, everything fails and it reads as "it does not work". A suite needs a difficulty axis.

### 8.2 G1: is the expert applied?

Three questions to the base and to the expert; if none changes, the adapter was not applied. A finding from this
month: in an expert trained only on tool turns, generic questions may change little (1 of 3) even though the adapter is
applied; that is why G1 now repeats with domain questions, under the same rule **[ran]** M9.

### 8.3 Comparing in pairs

Two variants on the same cases are compared **case by case**: only the cases where they differ count (one gets it
right and the other does not). With $b$ cases in favor of A and $c$ in favor of B, the exact sign test:

```math
p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}
```

So "53 to 0" is a real difference and "5 to 6" is a tie, even if the totals look different. See
[`FOUNDATIONS.md`](FOUNDATIONS.md) §9.2.

### 8.4 Temperature 0 does not guarantee the same output

In theory, greedy is deterministic. On a GPU, **the same question can give another text if the batch size changes**:
floating-point sums are done in another order, and in a near-exact tie between two tokens the other one wins. vLLM has
a batch-invariant mode (`VLLM_BATCH_INVARIANT=1`) for when exact texts need to be compared. **[ran] F0:** without that
mode, speculative decoding gave texts different from normal decoding in part of the cases — and so did the same LoRA
reloaded *without* a draft. Until it is repeated in invariant mode, "identical output" is not established. **[ran] F0b:** repeated in that mode, on an L4 in FP8, two plain runs already differed (9/16 identical on the domain), so the mode does not make this card deterministic; spec decode differed from plain about as much — which reads as drift, but proving it needs bf16 on an A100/H100.

### 8.5 Pre-registering

Every run has a `BRIEF.md` written **before**: what, why, with which model, what falsifies it and the verdict table.
Redesigns are counted: one is fine, two is suspicious, the third is already looking for the result.

### 8.6 Instruments lie in a few ways

A list paid for with time ([`CLAUDE.md`](../CLAUDE.md) §3, [`RECORD.md`](RECORD.md) §4): a suite at the ceiling; a
one-word check that measures phrasing; a corpus with a single difficulty that teaches a floor; knowledge fixed in the
corpus that gets memorized; a model without the prompt it was trained with; a key the chain reads as "finished" (it
happened to us last week).

---

## 9. What we have unlocked

| when | what was unlocked | how we know |
|---|---|---|
| 2026-09 | one expert per task on a small model, released through a gate | M1, M1b, M1d **[ran]** |
| 2026-09-15 | a real agent runtime (OpenClaw) using a local expert | P63, 40/40 **[ran]** |
| 2026-09-24 | memory as pages of atomic statements, with verifiable citations | W9, 35/40 → 38/40 on Gemma **[ran]** |
| 2026-09-25 | the whole family on Gemma 4 (the user's decision, on a measured tie) | B1 **[ran]** |
| 2026-09-26 | the E4B + 12B pair: they share a vocabulary, the large model's LoRA raises acceptance | B2, B4 **[ran]** |
| 2026-09-26 | the large model does not buy accuracy; the corpus does (comparisons 10 → 37/40) | B3, B5 **[ran]** |
| 2026-09-26 | the diagram's school complete, 15/15, and **live** with OpenClaw and Haiku | DEMO-school-diagram, LIVE **[ran]** |
| 2026-09-26 | the distributor with its own expert, 5/5 | M9 **[ran]** |
| 2026-09-27 | **speculative decoding with an expert LoRA on the 12B, in a server** | F0 **[ran]** |
| 2026-09-28 | the distributor served on the edge (llama.cpp, the user's own machine), abstaining correctly to the frontier, live through OpenClaw | LIVE-distributor, M10 **[ran]** |

---

## 10. What does not work yet, and the next step for each

| what | state | next step |
|---|---|---|
| identical output with speculative | **not testable on an L4 in FP8 [ran] F0b**: plain decoding twice already differs; spec decode differs about as much (reads as drift) | bf16 on an A100/H100, where batch-invariant mode is built for |
| a draft tuned per expert, hot-swapped | **[ran] C0**: the native MTP + expert LoRA recovers some of the speed (1.92× domain, 2.40× general, against 2.80×/2.60× on the base) but not all of it; the merged, fully-aligned E4B draft (strategy C) has not run — OOM beside the 12B on an L4, FP8/bitsandbytes/H100 all blocked this round. **[ran] C0-upper**: restricting the LoRA's layers does not help either (§6.6) | **still open, parked, not falsified**: strategy B (a draft LoRA) waits because MTP already pays for itself on an L4 and does not on the Mac — no reason yet to build the harder thing |
| the draft with the LoRA active | loses acceptance in the domain; aligning the large model's own MTP recovers part of it (1.74× → 1.92×, C0) but layer restriction does not add to that (C0-upper) | strategies A, C (properly sized) or D (§6.4), starting with the cheapest |
| the Mac track | **[ran]**: MLX hot swap in 2.9 µs (research bench, §3.5); **edge serving is now llama.cpp** — LoRA hot-swap in 3 ms, but MTP slows the 12B there too (0.52–0.87×, MAC2) and the E4B+12B pair does not fit in 16 GB | serve one member at a time on the edge, as LIVE-distributor does; a drafter aligned to the LoRA stays parked (above) |
| learned router | none passes; milestone 2's router loses real-looking requests | the role is the route; per-member abstention (M10) covers the "is this mine" half without one — left open only for cross-role routing |
| note search with embeddings | 0.63 against 0.80 | keyword search in use |
| real traffic | everything is synthetic | an anonymized sample from a system in use |
| the model still makes things up | 3 of 12 answers caught by the filter | a corpus that teaches it to repeat only what the tool says |
| the memory (library) inside a serving member | lives in `distributor-wiki@v2`, a separate member from the abstaining `out-s0` (M10) | merge them, or keep them apart by design — not yet decided |
| a vLLM bf16 live run of the distributor | not run — the only local arm measured is llama.cpp Q8_0 (LIVE-distributor) | run it once a same-precision comparison against the edge is needed |
| H1's result (the workflow harness) | **pre-registered, running** [ran] — no result yet | read the run before claiming the harness holds; release the member only if it passes |
| a router inside the gateway's own path | not built — the role is still the route (§7.2) | build only once cross-role routing, not per-member abstention, is the open half |
| the harness live through OpenClaw, multi-turn | not run — H1 first measures it on the server profile | repeat LIVE-distributor's pattern (§7.3) once H1 passes |
| sessions longer than 2–3 turns | not measured — MT0 and H1 both stop there | the proposed tracker domain (Jira/Confluence-like, longer workflows) would show it, if picked — not built |
| the global cache trained on | built and tested (`opmemory.py`), not yet inside a training corpus | fold into H1's corpus or the next domain's |
| real identity (Auth0), WhatsApp, installation | not built | after the above |

---

## 11. Glossary

- **Adapter / LoRA**: the low-rank patch that turns the base model into an expert (§5).
- **α (acceptance)**: fraction of the draft's tokens that the large model accepts (§6.2).
- **bf16, FP8, 4 bits**: weight precisions (§4).
- **Draft (drafter)**: the model or head that proposes tokens in speculative decoding (§6.3).
- **`edge` / `server`**: the two runtime profiles — `edge` is llama.cpp on the user's own machine, serving one member
  to a live agent runtime; `server` is vLLM on Colab, for training and measurement (§3.5).
- **KV cache**: what the model keeps from the tokens already seen so as not to recompute them (§2.4).
- **Continuous batching**: adding requests to a running batch (§3.2).
- **EAGLE-3**: a draft that predicts from the large model's hidden states (§6.3).
- **Frontier**: a large cloud model (Haiku, Gemini) for whatever no expert covers.
- **Prefix caching**: reusing the KV cache of a prompt's shared leading bytes across requests; defeated by moving the
  shared block later in the prompt, not by its size (§3.6).
- **G1**: the gate that verifies an adapter is applied (§8.2).
- **Gateway**: the server in front of the model that handles identity, permissions, holds and anchoring (§7.3).
- **GGUF**: llama.cpp's file format (§3.1).
- **MTP**: *multi-token prediction*; Gemma 4's native draft (§6.3).
- **OpenClaw**: the agent runtime the reference system uses (§7.3).
- **PagedAttention**: vLLM's paged management of the KV cache (§3.2).
- **Prefill / decode**: processing the prompt / generating each token (§2.3).
- **[read] / [ran]**: read / run here.

---

## 12. Sources

**Papers [read]:** Hu et al. 2021 (LoRA) · Kwon et al. 2023 (vLLM, PagedAttention) · Leviathan et al. 2023 and Chen et
al. 2023 (speculative decoding) · Chen et al. 2023 (Punica) · Sheng et al. 2023 (S-LoRA) · Gemma 4 Technical Report
(arXiv 2607.02770).

**Documentation and code [read], 2026-09-27:**
- [vLLM — Speculative Decoding](https://docs.vllm.ai/en/latest/features/speculative_decoding/) and
  [compatibility matrix](https://docs.vllm.ai/en/latest/features/)
- [vLLM PR #21068 — LoRA with speculative decoding (merged)](https://github.com/vllm-project/vllm/pull/21068) ·
  [PR #55628 (closed without merging)](https://github.com/vllm-project/vllm/pull/55628) ·
  [RFC #52038 — LoRA on drafts](https://github.com/vllm-project/vllm/issues/52038) ·
  [test_lora.py](https://github.com/vllm-project/vllm/blob/main/tests/v1/e2e/spec_decode/draft_model/test_lora.py)
- [Google — MTP for Gemma 4](https://ai.google.dev/gemma/docs/mtp/overview) ·
  [google/gemma-4-12B-it-assistant](https://huggingface.co/google/gemma-4-12B-it-assistant)
- [BCCard — EAGLE-3 for gemma-4-12B-it](https://huggingface.co/BCCard/MoAI-gemma-4-12B-it-speculator.eagle3)
- [mlx-lm — server](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/server.py) ·
  [mlx-vlm — Gemma 4 MTP drafter](https://github.com/Blaizzy/mlx-vlm/blob/main/mlx_vlm/speculative/drafters/gemma4_assistant/README.md) ·
  [mlx-optiq — Gemma 4 speculative decoding on Apple Silicon](https://mlx-optiq.com/blog/gemma-spec-decoding)

**Our runs [ran]:** [`RECORD.md`](RECORD.md) lists them all; the ones in this guide: W9, B1–B5, M8, M9,
DEMO-school-diagram, LIVE-school-openclaw, E1, F0, C0, C0-upper, E6, MAC2, W7, E5, LIVE-distributor, M10, MT0, C1 and
H1, each in `results/` with its `BRIEF.md`.
