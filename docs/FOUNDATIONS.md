# Foundations — the mathematics under lora-kernel, tied to what ran

> *[Léeme en español](es/FOUNDATIONS.md)*

This document says, step by step and in mathematics, what the models are, why
generating with them is slow, what a LoRA is, what the engine does, what speculative
decoding computes, what acceptance measures between a small expert and the large model of
its subdomain, what the tasks and the router are as functions, and why the Qwen 3 family
supplies both halves of a pair. **Every formula
that has a number under it names the run that produced the number.**

## 0. How to read this, and the standing rule

| mark | meaning |
|---|---|
| **[read]** | from a paper, a `config.json`, or source, and cited |
| **[ran]** | observed by executing something in this repository, with the run named |
| **[unverified]** | asserted somewhere, not checked from here; never load-bearing |

**The standing rule (2026-09-17).** Every Colab run updates this document: the number
lands in the section whose formula it instantiates, and §11's map gains a row. A
formula with no run under it is a claim; a run with no formula over it is a number.
Neither is knowledge on its own.

Model dimensions below were read from each model's `config.json` on the Hub on
2026-09-17 **[read]**; sizes on disk and every accuracy are **[ran]**.

---

## 1. The language model as a function

### 1.1 Tokens and the autoregressive factorization

A tokenizer maps text to a sequence of integer ids $x_1, \dots, x_T$ over a
vocabulary $V$. A causal language model is a function $f_\theta$ from a prefix to a
distribution over the next id:

```math
p_\theta(x_t \mid x_{<t}) = \mathrm{softmax}\big(f_\theta(x_{<t})\big)_{x_t},
\qquad
p_\theta(x_{1:T}) = \prod_{t=1}^{T} p_\theta(x_t \mid x_{<t}).
```

Generation is the recursion $x_{t} \sim p_\theta(\cdot \mid x_{\lt t})$, one id at a
time; **each step needs the whole prefix and cannot start before the previous id
exists.** That single fact — generation is sequential in $t$ — is what §2 prices and
what §6 exploits.

At temperature 0 the sampling collapses to $x_t = \arg\max_v f_\theta(x_{\lt t})_v$,
and the whole generation becomes a deterministic function of the prompt. Every
measurement in this repository is taken at temperature 0 — with the caveat that vLLM
at temperature 0 is not bit-reproducible across sessions (84, 81, 82 on identical
cases **[ran]** P36/P38/P40), so paired tests are used throughout (§9).

### 1.2 One decoder block, step by step

Both families are decoder-only transformers **[read]** (Vaswani et al. 2017; the
Qwen2 variant with RMSNorm, RoPE, grouped-query attention and a SwiGLU MLP). With
hidden width $d$, $H$ query heads, $H_{kv}$ key/value heads, head width $d_h$ and MLP
width $d_{ff}$, the $\ell$-th block maps $h^{(\ell)} \in \mathbb{R}^{T\times d}$ to
$h^{(\ell+1)}$:

1. **Pre-norm.** $\tilde h = \mathrm{RMSNorm}(h) = h \oslash \sqrt{\tfrac{1}{d}\sum_j h_j^2 + \epsilon}\ \odot\  g$.

2. **Projections.** $Q = \tilde h W_q,\  K = \tilde h W_k,\  V = \tilde h W_v$ with
   $W_q \in \mathbb{R}^{d\times H d_h}$ and $W_k, W_v \in \mathbb{R}^{d \times H_{kv} d_h}$.
   With $H_{kv} \lt  H$ each key/value head serves $H/H_{kv}$ query heads — *grouped-query
   attention*, which is what makes the KV cache in §2.2 smaller than it would be.

3. **Rotary position (RoPE).** Each pair of coordinates $(q_{2i}, q_{2i+1})$ at position
   $t$ is rotated by angle $t\ \omega_i$ with $\omega_i = \theta^{-2i/d_h}$; the same
   for $k$. Then $\langle q_t, k_s\rangle$ depends only on $t-s$ — position enters as a
   relative phase. Both families use $\theta = 10^6$ **[read]**.

4. **Causal attention**, per head:

```math
A = \mathrm{softmax}\!\Big(\frac{QK^\top}{\sqrt{d_h}} + M\Big)V,
\qquad M_{ts} = \begin{cases}0 & s\le t\\ -\infty & s>t\end{cases}
```

   then $h \leftarrow h + A\ W_o$.

5. **MLP (SwiGLU).** $h \leftarrow h + \big(\sigma(\tilde h W_{gate}) \odot \tilde h W_{up}\big) W_{down}$,
   with $\sigma$ the SiLU, $W_{gate}, W_{up} \in \mathbb{R}^{d\times d_{ff}}$,
   $W_{down} \in \mathbb{R}^{d_{ff}\times d}$.

The seven matrices $W_q, W_k, W_v, W_o, W_{gate}, W_{up}, W_{down}$ of every block are
exactly the `target_modules` every adapter here patches (§4) **[ran]**
`adapters/email-full/adapter_config.json`.

### 1.3 The unembedding

After $L$ blocks and a final RMSNorm, logits are $z = h_T W_{out}$ with
$W_{out} \in \mathbb{R}^{d\times |V_{emb}|}$. In `Qwen2.5-3B` the unembedding is tied
to the input embedding (`tie_word_embeddings: true`) and has $|V_{emb}| = 151{,}936$
columns — **wider than the 151,643-entry tokenizer plus its 22 added tokens = 151,665
ids** **[read]**/**[ran]** P48. The extra columns are padding; a mask over them masks
nothing, which `STACK.md` §1 (the tag `v0.1-foundations`) records because a typed head once assumed otherwise.

### 1.4 The two families we serve

| | `Qwen2.5-3B-Instruct` | `Qwen2.5-32B-Instruct-AWQ` | `Qwen3.5-4B` | `Qwen3.8-27B` |
|---|---:|---:|---:|---:|
| class | `Qwen2ForCausalLM` | `Qwen2ForCausalLM` | `Qwen3_5ForConditionalGeneration` | `Qwen3_5ForConditionalGeneration` |
| $d$ | 2,048 | 5,120 | 2,560 | 5,120 |
| $d_{ff}$ | 11,008 | 27,648 | 9,216 | 17,408 |
| $L$ | 36 | 64 | 32 = 24 linear + 8 full | 64 = 48 linear + 16 full |
| $H$ / $H_{kv}$ / $d_h$ | 16 / 2 / 128 | 40 / 8 / 128 | 16 / 4 / 256 | 24 / 4 / 256 |
| tokenizer ids | 151,643 | 151,643 | 248,044 | 248,044 |
| weights on disk | ~6 GB bf16 | **19.3 GB** AWQ int4 g128 | — | — |
| role here | **the resident base; every adapter sits on it** | **the speculative target** | candidate 3.x drafter (D0) | the large model the route aims at |

All dimensions **[read]** `config.json`, 2026-09-17; disk sizes **[ran]** P48/P49.

### 1.5 The hybrid layers of Qwen 3.5 / 3.8: Gated DeltaNet

The 3.x line is **not** a stack of identical attention blocks. Its `layer_types`
alternate: three *linear-attention* layers, then one *full-attention* layer
(`full_attention_interval: 4`) **[read]**. P33's serving log names the kernel:
`qwen_gdn_linear_attn.py … GDN decode kernel: cuda` **[ran]**.

A linear-attention layer replaces the $T\times T$ softmax with a **recurrent state**
$S_t \in \mathbb{R}^{d_k\times d_v}$ updated once per token. Gated DeltaNet's rule
**[read]** (Yang et al., *Gated Delta Networks*, 2024) is

```math
S_t = \alpha_t\,\big(I - \beta_t\, k_t k_t^\top\big)\, S_{t-1} \;+\; \beta_t\, k_t v_t^\top,
\qquad o_t = S_t^\top q_t,
```

with data-dependent gates $\alpha_t \in (0,1]$ (decay) and $\beta_t \in (0,1]$
(write strength). The first term *forgets* along $k_t$, the second *writes* $v_t$ at
$k_t$ — a delta rule. Two consequences matter here:

- **Per-token cost is $O(d_k d_v)$ and independent of $T$**, and the "cache" is one
  matrix per layer rather than $T$ vectors — so the 3.x models are cheap at long
  context, which is why they are attractive as the large model.
- **The projections that produce $q_t, k_t, v_t$ and the gates are still ordinary
  linear maps** $\tilde h W$ — the shape LoRA patches. Nothing in the recurrence
  forbids a delta on $W$. Whether a *serving engine* applies it is a different
  question, and it is C18 (§10.4).

The `ForConditionalGeneration` wrapper adds a vision tower (`visual.*` modules) in
front of the text model; the text model's own class is `qwen3_5_text` **[read]**.

---

## 2. Why generating is slow: recursion, the KV cache and bandwidth

### 2.1 Prefill and decode are different regimes

Given a prompt of $P$ tokens, **prefill** runs one forward pass over all $P$ positions
at once — a matrix–matrix workload, compute-bound. **Decode** then produces each new
token with a forward pass over *one* position — a matrix–vector workload, bound by
how fast the weights can be read from memory.

### 2.2 The KV cache

Attention at step $t$ needs $K_{1:t}, V_{1:t}$ of every layer. Recomputing them is
$O(t)$ per step; caching them makes decode $O(1)$ in recompute at the price of memory:

```math
\text{bytes}_{KV}(t) \;=\; 2 \cdot L \cdot H_{kv} \cdot d_h \cdot t \cdot b,
```

with $b$ bytes per element. For `Qwen2.5-3B` in bf16: $2\cdot 36\cdot 2\cdot 128\cdot 2 = 36{,}864$ bytes
per token — **36 KB/token**, 147 MB at 4,096 tokens. For the 32B (bf16 cache on an
AWQ base): $2\cdot 64\cdot 8\cdot 128\cdot 2 = 262{,}144$ bytes — **256 KB/token**, 1 GB at
4,096. GQA is why these are $H_{kv}$ and not $H$. The linear-attention layers of §1.5
carry a fixed $d_k\times d_v$ state instead, which is the point of them.

### 2.3 Decode is bound by weight bytes

One decode step reads every weight once. With $B_W$ bytes of weights and memory
bandwidth $\mathcal{B}$, the floor is

```math
t_{\text{step}} \;\gtrsim\; \frac{B_W}{\mathcal{B}} \;+\; \frac{\text{bytes}_{KV}(t)}{\mathcal{B}}.
```

On an A100-40GB ($\mathcal{B}\approx 1.5$ TB/s **[read]**): the 3B (~6.2 GB) floors
at **~4 ms/token**; the 32B-AWQ (19.3 GB) at **~13 ms/token**. The arithmetic is
tiny by comparison — $2\cdot\text{params}$ FLOPs per token against $3\times 10^{14}$
FLOP/s — which is what *memory-bound* means: **the GPU spends its time moving weights,
not multiplying them.** Quantisation to 4 bits (AWQ, §4.3) helps decode exactly by
shrinking $B_W$.

### 2.4 Batching amortises the weight read

$n$ concurrent sequences share one weight read per step, so throughput scales almost
linearly in $n$ until the KV cache or compute saturates. That is why P55 ran cases at
concurrency 8: **475 corpus-mode chains through the 3B in 31 s, and through the 32B
in 230 s** **[ran]** `results/P55-graded-ranking-20260916/session_a.json` — a 7.4×
wall ratio for a 3.1× ratio of weight bytes, the remainder being the 32B's longer
chains (2.6 calls/case against 2.2) and its int4 dequantisation.

**This is the whole reason speculative decoding exists** (§6): the target's decode
step costs a full weight read *whether it verifies one token or five*, because the
$k+1$ positions are scored in one prefill-shaped pass.

### 2.5 KV identity below an untouched depth, and switching mid-generation (E6)

The recursion of §1.2 makes block $\ell$'s output depend only on the blocks *below* it:
$h^{(\ell)}$ is a function of $\theta_0,\dots,\theta_{\ell-1}$ and the input, never of
$\theta_\ell,\dots,\theta_{L-1}$. So if a LoRA leaves every block below some depth $k$
untouched ($\theta_\ell = \theta_\ell^{\text{base}}$ for $\ell \lt  k$),

```math
h^{(\ell)}_{\text{expert}} = h^{(\ell)}_{\text{base}}, \qquad K_\ell = K_\ell^{\text{base}}, \qquad V_\ell = V_\ell^{\text{base}}, \qquad \text{for every } \ell < k \text{ and every prefix.}
```

This is a mechanical identity, not a statistical one — it holds bit for bit or the
derivation is wrong — and it is the condition under which a request can switch which
expert answers *mid-generation* without invalidating the KV already computed for the
layers below $k$.

**Measured [ran] `results/E6-upper-layers-20260927`.** The school member retrained
with its LoRA on layers 21–41 of 42 only: **70/70 held-out, 15/15 demo**, exactly the
full member's score (0 lost against it), and a base-vs-base control over the 21 layers
below the adapted range came back bit-identical, confirming the identity above rather
than just assuming it. Two caveats travel with the result. The E4B shares KV across
groups of layers (24 of 42 are cache-sharing groups **[ran]**), so a switch still
recomputes layers 21–23 even though *their own* weights sit below $k$ — sharing, not
the LoRA, is what reaches into the adapted range. And the suite sits at the full
member's ceiling with one seed (§9.4), so this is a mechanism check, not yet a quality
comparison.

---

## 3. Text as ids: BPE, id maps and merges

### 3.1 Byte-pair encoding in three lines

Start from bytes. Repeatedly merge the most frequent adjacent pair into a new
symbol; each merge is a rule $(a, b) \to ab$ and the rules, in order, are the
`merges` list. The `vocab` maps each symbol to an id. Encoding text applies the
merges; **after that, everything the model does is in id space.**

### 3.2 What speculative decoding needs: the same id map

Rejection sampling (§6.1) compares $p_{\text{target}}(v)$ and $q_{\text{draft}}(v)$
**at the same $v$**. So a drafted id must name the same string to both models:
$\text{vocab}_D(v) = \text{vocab}_T(v)$ for every $v$ the drafter can emit, and no id
may mean two things. **The `merges` may differ** — they only decide how *text* becomes
ids, which happens once, for the prompt; a target that segments the prompt
differently from the drafter is handed the drafter's ids and scores those.
`tokenizer_compat.py` checks the id map and reports the merges separately for this
reason **[ran]** P48.

### 3.3 Measured

| drafter → target | vocab | id map | target-only ids | usable |
|---|---:|---|---:|---|
| Qwen2.5-3B → Qwen2.5-32B | 151,643 | byte-identical file, `c0382117…` | 0 | **yes** |
| Qwen2.5-3B → Qwen3-32B | 151,643 | identical map, different merges | 4 (`<think>`, `</think>`, `<tool_response>`, `</tool_response>`) | yes |
| Qwen2.5-3B → Qwen3.5/3.6/3.8-27B | 151,643 vs **248,044** | **different** | — | **no** |
| Qwen3.5-2B / 4B → Qwen3.8-27B | 248,044 | identical map | 7, all audio/TTS specials | **yes** |

Rows 1–3 **[ran]** `results/P48-tokenizer-compat-20260916/`; row 4 **[ran]**
`results/P55-graded-ranking-20260916/D0-tokenizers.txt`.

A **target-only id** is one the target can emit and the drafter cannot propose: at any
position where the target's argmax is such an id, acceptance is **0 by construction**
— a systematic, not random, rejection. For Qwen3-32B those are the thinking tags,
handled by serving with thinking off; for Qwen3.8-27B they are modality specials the
text task never reaches. In the 3.5 → 3.8 pair `<think>` is *shared*, so the thinking
channel is a serving flag, not an id problem.

---

## 4. LoRA: the patch, as linear algebra

### 4.1 The delta

LoRA **[read]** (Hu et al. 2021) replaces a frozen weight $W \in \mathbb{R}^{d_{in}\times d_{out}}$
by

```math
W' = W + \frac{\alpha}{r}\, A B, \qquad A \in \mathbb{R}^{d_{in}\times r},\; B\in\mathbb{R}^{r\times d_{out}},\; r \ll \min(d_{in}, d_{out}),
```

trains only $A, B$, and at inference computes $xW' = xW + \tfrac{\alpha}{r}(xA)B$ —
two thin products beside the frozen one. Every adapter here uses $r=16$, $\alpha=32$,
dropout 0.05 on the seven projections of §1.2 **[ran]** `adapter_config.json`.

Because $W$ is never touched, **the base stays resident and the delta is the only
thing that changes between experts** — it can be swapped per request, batched across
requests (§5.2), versioned and discarded. That is the whole architectural premise:
*the system is a pool of deltas over one resident base.*

### 4.2 The count, reconciled with the artefact

Per block of `Qwen2.5-3B` ($d = 2048$, $H_{kv} d_h = 256$, $d_{ff} = 11008$), LoRA
parameters are $r\ (d_{in} + d_{out})$ per matrix:

| matrix | $d_{in}\to d_{out}$ | params |
|---|---|---:|
| $W_q$ | 2048 → 2048 | 65,536 |
| $W_k$ | 2048 → 256 | 36,864 |
| $W_v$ | 2048 → 256 | 36,864 |
| $W_o$ | 2048 → 2048 | 65,536 |
| $W_{gate}$ | 2048 → 11008 | 208,896 |
| $W_{up}$ | 2048 → 11008 | 208,896 |
| $W_{down}$ | 11008 → 2048 | 208,896 |
| per block | | **831,488** |
| × 36 blocks | | **29,933,568** |

At 4 bytes (fp32, PEFT's default for saved adapters) that is **119,734,272 bytes**;
the file on disk is **119,801,528 bytes** **[ran]** `STACK.md` §3 (the tag `v0.1-foundations`) — the 67,256-byte
difference is the safetensors header. **The derivation and the artefact agree**, and
the adapter is ~1% of the base's 3.09 B parameters.

### 4.3 QLoRA and AWQ: two different 4-bit stories

**Training** (QLoRA **[read]**, Dettmers et al. 2023): the frozen base is stored in
4-bit NF4 and dequantised on the fly inside each matmul; gradients flow only into the
bf16 $A, B$. Here the base is trained in bf16 on Ampere and float16 on Turing
**[ran]** P2 — bf16 is checked by compute capability, because
`torch.cuda.is_bf16_supported()` counts emulation and emulated bf16 has no kernel.

**Serving** (AWQ **[read]**, Lin et al. 2023): the *target's* weights are
quantised once to int4 with per-group scales chosen to protect activation-salient
channels; it is a smaller $B_W$ in §2.3 and nothing else. The 32B is served AWQ
(`bits: 4, group_size: 128` **[read]**) and **holds no adapter** — which is the
observation §10.1 rests on.

### 4.4 Training objective, and why the corpus is the served prompt

SFT minimises the next-token cross-entropy over the assistant span only:

```math
\mathcal{L}(A,B) = -\sum_{t \in \text{assistant}} \log p_{\theta + \Delta}(x_t \mid x_{<t}),
```

so the adapter learns $p(x_t \mid x_{\lt t})$ **for the prefixes the corpus contains**.
Serve it a prefix from a different distribution and it is extrapolating. The
email-full corpus renders a whole chain in one assistant turn,
`<tag>…</tag>= {result}\n…\nIMPORTANT`, so the learned conditional is
$p(\text{next tag or verdict} \mid \text{real results so far})$. Served through
`tool_calls`, the model cannot receive a result mid-generation and writes
$p(\cdot \mid \hat h)$ where $\hat h$ is a result **it invented**; every later decision
conditions on $\hat h \ne h$. Measured: the same adapter scores **0.808** served that
way (P43) and **0.992** served as the corpus teaches (P55 A) **[ran]** — §8.1.

---

## 5. The engine: vLLM

### 5.1 PagedAttention and continuous batching

vLLM **[read]** (Kwon et al. 2023) stores the KV cache of §2.2 in fixed-size blocks
addressed through a per-sequence page table, so sequences of different lengths share
one GPU without fragmentation and a new request can join a running batch at any step
(*continuous batching*). That is what turns §2.4's "batching amortises the weight
read" into throughput a client sees. Every server here is `vllm serve` 0.29.0
**[ran]** P3…P55.

### 5.2 Multi-LoRA serving

With adapters $\lbrace (A_i, B_i)\rbrace$ resident and a batch in which request $j$ names adapter
$i(j)$, the layer computes

```math
y_j = x_j W + s\,(x_j A_{i(j)}) B_{i(j)},
```

as one shared GEMM for $xW$ plus a *batched, gathered* pair of thin GEMMs (the
`bgmv` / Punica kernels **[read]**, Chen et al. 2023; S-LoRA, Sheng et al. 2023). Flags
here: `--enable-lora --max-lora-rank 16 --max-loras k --lora-modules name=path`
**[ran]** `STACK.md` §5 (the tag `v0.1-foundations`). The adapter is chosen by the request's `model` field, which is
how the pool is addressed with no router at all.

**C18 is a test of that equation.** An engine can load $(A_i, B_i)$, log
`Loaded new LoRA adapter`, and still return $y = xW$ — the delta term silently absent.
The identity gate serves the same prompt through base and adapter and requires the
texts to differ **[ran]** P33 (`Qwen2.5-3B`: differs; `Qwen3.5-4B`: identical) and
P55 A (`email-full`: 6 of 8 probes differ → `applied`).

### 5.3 Teacher forcing in one prefill: `prompt_logprobs`

Prefill (§2.1) computes $f_\theta(x_{\lt t})$ **for every $t \le P$ at once**. Asking
the server for `prompt_logprobs` returns, at each position, the target's top-$k$ ids
with log-probabilities *and the rank of the actual token* — i.e. the full teacher-forced
distribution along a given text, in one pass, generating nothing. That is the
operation §6.5 uses to verify a draft: hand the target `prefix + draft`, read whether
each draft token was the target's rank-1 choice. Preflight measured the shape: one
entry per prompt token, first `None`, each with `rank` **[ran]** P55 A.

### 5.4 Stop strings and the corpus-mode harness

`stop=[…]` ends a generation the moment a listed string is produced;
`include_stop_str_in_output` returns it. The corpus-mode loop (§8.1) is exactly:
generate until `</tag>`, answer the tag with a real tool, append `= {result}\n`,
continue. Two preflights guard it — the server honours the stop on a continuation the
model cannot avoid (counting, stopped at `3`), and a positional tag body is keyed by
parameter count before the tool sees it — both added after an attempt each
**[ran]** P55 A attempts 1 and 2.

### 5.5 Prefix caching is keyed by position, not by content (E5)

vLLM's prefix cache (§5.1) hashes a sequence's blocks **in order from position 0**:
block $j$'s hash chains from block $j-1$'s, so a cache hit at block $j$ requires every
earlier block to match too. With $\text{hit}(x)$ the number of tokens $x$ shares, from
position 0, with some previously served sequence,

```math
\text{TTFT}(x) \;\approx\; t_{\text{prefill}}(|x| - \text{hit}(x)),
```

with $t_{\text{prefill}}$ the compute-bound cost of §2.1. **A block's own content being
static does not make it cacheable** — only its *position* being a shared prefix does. A
tool-call block served, as trained, after the user's request sits behind that
request's tokens, which differ per call; $\text{hit}(x)$ collapses to whatever the
system prompt shares, and the whole block is recomputed every time despite being
byte-identical across requests.

**Measured [ran] `results/E5-engine-baseline-20260928`.** OpenClaw's 54-tool block
(7,205 Gemma tokens) served after the request: TTFT **0.10 → 1.70 s (16.8×)** with
prefix caching on; batch-8 throughput **132 → 108 tok/s**; accuracy **70/70 → 39/70**
(the member stops calling its own tool in 28 of 31 failures — an instance of §4.4's
drift, not of the engine). The same block costs **nothing** (0.09–0.11 s) in the one
case where the whole prefix, block included, recurred from position 0 — **the order,
not the size, defeats the cache.** Two LoRAs served in one batch (§5.2) keep **0.88**
of one adapter's solo throughput (contention at the edge, measured over one burst of
16); pruning the tool block to the member's own stays the default on both accuracy and
latency.

### 5.6 Multi-adapter throughput under load, steady rather than a burst (C1)

§5.2's cost model says a request under adapter $i$ costs one shared $xW$ plus a thin, batched pair of
rank-$r$ terms — cheap beside the shared weight read (§2.3–2.4). If that holds under real load, and
not only in the single-burst reading of §5.5's own contention line, mixing $A$ different adapters in one
batch should cost close to nothing against serving the same $K$ sessions on one adapter alone. Define
the ratio at a fixed session count $K$:

```math
r_A(K) = \frac{\mathrm{tps}(K\ \text{sessions},\ A\ \text{adapters mixed})}{\mathrm{tps}(K\ \text{sessions},\ 1\ \text{adapter})},
```

with $\mathrm{tps}$ the server's aggregate generated tokens/s. **NO MATERIAL CONTENTION** iff $r_A \ge 0.8$
— the bar fixed in the brief before the run, the same bar §5.5's own single burst was read against.

**Measured [ran] `results/C1-concurrency-20260929`.** Four members (`school-s0`, `upper-s0`, `staff-s0`,
`out-s0`) on one L4, `google/gemma-4-E4B-it` bf16, $K \in \lbrace 1, 8, 16, 32\rbrace$ sessions, each session round-robin
across the adapters in play: $r_4(16) = 278.6 / 269.7 = 1.03$ — **above the 0.8 bar, and above 1**, so mixing
four adapters costs nothing measurable against one at this load. §2.4's near-linear scaling in the number of
concurrent sequences holds across the whole run and is not an artefact of a single adapter: total throughput
goes **22.7 → 135.1 → 278.6 → 504.3 tok/s** for $K = 1, 8, 16, 32$ (four-adapter cells), each within noise of
its one-adapter counterpart (269.7, 490.8 at $K=16, 32$). TTFT stays low throughout (p95 **0.24 s** at $K=32$,
an eighth of the 2 s budget fixed in the brief), 0 errors of 128 requests, and the ceiling is above 32 —
not reached. **This supersedes E5's 0.88** ([`RECORD.md`](RECORD.md) §2): that number came from one burst of
16 requests, inside the spread of a single measurement, not from a curve — the failure §9.4 and §1.1 both
warn against, reading one draw as the rate.

---

## 6. Speculative decoding

### 6.1 The algorithm

Given a target $p$ (large, slow) and a drafter $q$ (small, fast) over the same id
space (§3.2), one round at prefix $x$ **[read]** (Leviathan et al. 2023; Chen et al.
2023):

1. **Draft.** Sample $\tilde x_1 \sim q(\cdot\mid x)$, $\tilde x_2 \sim q(\cdot\mid x,\tilde x_1)$, …, $\tilde x_k$ — $k$ cheap decode steps.
2. **Verify.** One target pass over $x, \tilde x_1,\dots,\tilde x_k$ yields
   $p(\cdot\mid x,\tilde x_{\lt i})$ for all $i \le k+1$ at once (§5.3).
3. **Accept / reject**, left to right: accept $\tilde x_i$ with probability

```math
a_i = \min\!\Big(1, \frac{p(\tilde x_i \mid x, \tilde x_{<i})}{q(\tilde x_i \mid x, \tilde x_{<i})}\Big).
```

   At the first rejection, at position $i$, emit one token from the **residual**

```math
p'(v) \propto \max\big(0,\; p(v \mid \cdot) - q(v \mid \cdot)\big)
```

   and stop the round. If all $k$ are accepted, emit one extra token from
   $p(\cdot\mid x,\tilde x_{1:k})$ — the pass already computed it.

### 6.2 Exactness

For any $v$: $\Pr[\text{emit } v] = q(v)\min(1, p(v)/q(v)) + \big(1-\sum_u q(u)\min(1,p(u)/q(u))\big)\ p'(v) = \min(p(v),q(v)) + \max(0, p(v)-q(v)) = p(v)$.
**The output is distributed exactly as the target's**, whatever the drafter is. A bad
drafter costs speed, never correctness — which is why acceptance can be read as a
score *about the drafter* (§7).

### 6.3 Temperature 0

With $p$ one-hot at its argmax, $a_i = 1$ iff $\tilde x_i = \arg\max_v p(v\mid x,\tilde x_{\lt i})$
and $0$ otherwise. **Acceptance is argmax equality**, and the accepted prefix is the
longest prefix of the draft along which the target would have made the same choice.
This is the identity `alpha/` rested on from the start and `accept_rank.py` reads
token by token: *accepted iff rank = 1* **[ran]** P55 A preflight.

### 6.4 How much it buys, and why a slow target is where it pays

If each token is accepted independently with rate $\alpha$, the expected number of
tokens emitted per round with $k$ drafts is

```math
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha}.
```

Let $c = t_{\text{draft}} / t_{\text{target}}$ be the cost of one drafter step relative
to one target step. A round costs $k\ c + 1$ target-steps and yields $\mathbb{E}[\tau]$
tokens, so

```math
\text{speed-up} \;=\; \frac{\mathbb{E}[\tau]}{k\,c + 1}
\;=\; \frac{1-\alpha^{k+1}}{(1-\alpha)(k c + 1)}.
```

Two readings. **The target's verify pass costs one weight read for $k+1$ positions**
(§2.3–2.4): that is where the tokens come from. And **the gain grows as $c \to 0$** —
a 3B drafting for a 32B has $c \approx 0.3$ by weight bytes; a 2B drafting for a 27B
*with 48 linear-attention layers whose per-token cost does not grow with context*
(§1.5) has a target that is slow per token for a different reason and a drafter that
is not — the user's observation that the big model *"es lento y justifica muy bien"*
is this ratio. With $\alpha = 0.8$ and $k=4$: $\mathbb{E}[\tau] = 3.36$, and at
$c=0.3$ the speed-up is $1.5\times$; at $c = 0.1$, $2.4\times$. **No acceptance rate
has been measured yet** — §11.

### 6.5 The two-instance shortcut used here

vLLM's native speculative worker binds *one* drafter at start-up and does not swap
its adapter per request (the state of `lora_request` forwarding into that worker is
**[unverified]** from here). This repository does not need it to *measure*: the
drafter server (3B, multi-LoRA) produces the whole draft in corpus mode; the target
server scores it by `prompt_logprobs` (§5.3). Under §6.3, **the per-token verdicts are
identical to what the fused loop would compute** — one prefill per span instead of
one per round, which is more expensive per token and exactly as informative. What it
does not give is wall-clock speed-up, which §6.6 says this project is not buying.

### 6.6 Latency is EAGLE's; ranking is ours

EAGLE-3 / Medusa / DFlash **[read]** attach a small head to the *target's* hidden
states and draft from them; they are trained per target and reach acceptance a
separate small model cannot. A community `Qwen2.5-32B-Instruct_EAGLE3` exists
**[read]**. So **speculative decoding as a latency device is settled, and not by us.**
What a single bound head cannot do is compare $k$ *different* drafters — there is one
of it. **Acceptance as a judge-free ordering over $k$ experts** is the claim this
architecture keeps ([`RECORD.md`](RECORD.md) §5), and it is what §7 formalises.

### 6.7 MTP acceptance under a domain LoRA, and layer restriction (C0, C0-upper)

Gemma's own multi-token-prediction (MTP) head drafts from the target's own final
hidden states — a bound head in the sense of §6.6, so §6.4's speed-up formula applies
with $c$ the MTP head's cost relative to one full decode step. **A domain LoRA on the
target moves the hidden states the head reads from, and acceptance falls with them.**

**Measured [ran] `results/C0-aligned-draft-20260927`** (A100, bf16, `gemma-4-12B-it`'s
native MTP, $k=4$): with no adapter the speed-up is **2.80×** on the domain and
**2.60×** general; with the expert LoRA on, domain acceptance falls and the speed-up
with it — **1.92× on the domain ($\alpha$ 0.34, against $\alpha \approx 0.79$ with no
adapter)**, **2.40× general** (the LoRA barely touches general-text hidden states).
**The LoRA costs the drafter, not the target** — §6.4's $c$ is unchanged; what moved is
$\alpha$.

**Does restricting the LoRA to the upper layers recover it? [ran]
`results/C0-upper-e4b-20260927`.** The natural hope from §2.5's identity — if the
lower layers are untouched, maybe the head's *input* is untouched too — has to be
checked, because the head reads the *last* layer's state, which a LoRA confined to the
upper half still moves. Normalise the upper-restricted adapter's acceptance between the
untouched base and the fully-adapted model:

```math
\rho = \frac{\alpha_{\text{upper}} - \alpha_{\text{full}}}{\alpha_{\text{base}} - \alpha_{\text{full}}},
```

so $\rho = 1$ says layer restriction recovers all the acceptance the full LoRA lost,
$\rho = 0$ says it is exactly as damaging as the full LoRA. On the E4B and its own MTP
drafter, domain: $\alpha_{\text{base}} = 0.82$, $\alpha_{\text{full}} = 0.44$,
$\alpha_{\text{upper}} = 0.43$, so

```math
\rho = \frac{0.43 - 0.44}{0.82 - 0.44} = -0.02.
```

**NONE: layer restriction does not help the drafter** — $\rho$ sits at (within noise
of) zero, not toward 1. Restricting the adapter to layers close to the head still moves
exactly the states the head reads. On an L4 the E4B's own MTP still pays with the LoRA
on (2.4× batch 1, 2.1× batch 8); served in vLLM, the upper-half adapter runs at exactly
the full adapter's *speed* — layer restriction saves memory, not decode time
(**[read]**, probably zero-filled layers rather than skipped ones).

**A different regime, where $c$ moves instead of $\alpha$ [ran]
`results/MAC2-llamacpp-20260927`.** On llama.cpp/Metal (the Air), Gemma's MTP *slows*
the 12B rather than speeding it up — **0.52×** with the LoRA on its domain, **0.66–
0.87×** otherwise. Speculative decoding output is identical either way (20/20), so
this is not an $\alpha$ effect: §6.4's $c$, the drafter's cost relative to the target's,
is high enough on this engine that $kc+1$ exceeds $\mathbb{E}[\tau]$ even at the same
acceptance a GPU would pay for gladly — the same formula, a different hardware term.

---

## 7. Acceptance — between a small expert and the large model of its subdomain

### 7.1 Definitions and the claim

A suite is a set of cases $\mathcal{C}$ with a mechanical verifier
$\mathrm{ok}(c, \text{answer}) \in \lbrace 0,1\rbrace$. For an expert $E$ (base + one adapter)
its **verified quality** is $Q(E) = \tfrac{1}{|\mathcal C|}\sum_c \mathrm{ok}(c, E(c))$.
For a target $T$, its **acceptance** on case $c$ is

```math
\alpha_T(E, c) = \frac{1}{n_c}\sum_{i=1}^{n_c} \mathbf{1}\big[\tilde x_i^{E}(c) = \arg\max p_T(\cdot \mid \text{prefix}, \tilde x_{<i}^{E}(c))\big],
```

the fraction of $E$'s $n_c$ *decision tokens* on that case that the target would have
written itself (§6.3), and $\alpha_T(E) = \tfrac1{|\mathcal C|}\sum_c \alpha_T(E,c)$.

**The claim this project first made (P55), and what became of it.** *Acceptance orders
experts the way verified quality orders them* — $Q(E_a) > Q(E_b) \Rightarrow
\alpha_T(E_a) > \alpha_T(E_b)$, a free router. Its precondition (§7.2) failed twice for an
untrained target and the question was closed without a verdict ([`RECORD.md`](RECORD.md) §2).

**The claim now (2026-09-19, [`PLAN.md`](PLAN.md) milestone 4).** Let $S_\theta$ be the
small model with the LoRA of one subdomain, $T$ the bare large model and $T_\phi$ the large
model with a LoRA trained on the *same corpus*. The pair is speculative iff

```math
\alpha_{T_\phi}(S_\theta) > \alpha_{T}(S_\theta),
```

paired over cases — training the large half on the subdomain makes it agree with the small
expert's correct drafts more than the generalist does. It is read beside
$Q(T_\phi) \gt  Q(S_\theta)$ (milestone 3): a verifier that is not better than its drafter
has nothing to verify. **Not yet measured.**

### 7.2 The precondition, and P55 A as its instance

$\alpha_T(E)$ is agreement with $T$. If $T$ is wrong on a case, an expert that is
*right* is **rejected there**, and $\alpha$ rewards the expert that shares the target's
mistake. So the claim is only about quality when

```math
Q(T) \;\ge\; \max_a Q(E_a)
```

— "it is only a distillation score when the target is stronger than every candidate"
(`alpha-surface` skill). P55's M-target gate is that inequality as a paired test, and
it fired: on 351 human triage cases the 32B was right where the expert was wrong on
**2** and wrong where the expert was right on **87**, $p = 0.0$;
$Q(T)=0.746 \lt  Q(E) = 0.989$ **[ran]** P55 A. The untrained large model *gets every
fact and misapplies the rule*; an ordering measured against it would have been an
ordering by agreement with its errors. **The instrument was ready and correctly not
run.**

### 7.3 Three α per case, because a chain is not one token

A triage chain is ~40 decision tokens of which the verdict is one or two. Acceptance
weights every token equally, so two experts that differ only in verdicts differ in
$\alpha$ by a few percent. So the instrument reports, per case,

| | over | reads |
|---|---|---|
| $\alpha$ | all decision tokens | the claim as stated |
| $\alpha_{\text{tags}}$ | the tool-call spans | protocol agreement |
| $\alpha_{\text{verdict}}$ | the final span | the 1–2 tokens the verifier scores |
| $\alpha_{\text{lcp}}$ | accepted prefix per span ÷ tokens | what one speculative round would keep |

and **the harness-supplied `= {result}` lines are in the target's prefix and in no
span** — scoring them would score the tool. A result of "α does not rank" then says
*where* agreement lived rather than only that it failed.

### 7.4 The test, for an ordering and for a pair

**As written for the ordering claim (P55).** For every pair $(E_a, E_b)$ the verifier
resolves (§9.2), take the cases both were scored on and count
$u = \lvert\lbrace c: \alpha(E_a,c) \gt  \alpha(E_b,c)\rbrace\rvert$, $d = \lvert\lbrace c: \alpha(E_a,c) \lt  \alpha(E_b,c)\rbrace\rvert$;
ties are excluded; the exact two-sided binomial on $(u,d)$ decides. **SUPPORTED** if every
resolved pair agrees; **FALSIFIED** if any pair is ordered the other way at $p\le0.05$;
**UNRESOLVED** if the verifier saw a difference and $\alpha$ did not **[ran]**
`results/P55-graded-ranking-20260916/BRIEF.md`.

**For a pair (milestone 4)** the same count is taken over *targets* instead of experts:
$u = \lvert\lbrace c: \alpha_{T_\phi}(S_\theta,c) \gt  \alpha_{T}(S_\theta,c)\rbrace\rvert$ and $d$ its mirror, same
binomial. The draft is the same text under both targets, so the comparison is paired by
construction and costs one extra prefill per case (§5.3).

---

## 8. The tasks, as functions

### 8.1 Triage, the chain, and the drift with numbers

A message $m$ carries facts $\phi(m) = (\text{automated}, w, a, s, f)$ — *I wrote in
the thread*, *addressed to me*, *asks something*, *frequent sender*. The label is

```math
y(m) = \neg\,\text{automated} \;\wedge\; \big[\,w + a + s + f \;\ge\; 2\,\big],
```

`training/email/inbox.py::important`. **The listing shows none of $w, a, f$** — they
live behind three tools (`thread_history` → $w$, `sender_stats` → $f$, `message` → $a$
and the body for $s$), and `tests/test_email.py` asserts the best listing-only rule
scores exactly the majority class on human messages **[ran]**. So the expert's job
is a *chain*: decide which tools, call them with the right argument, read the
results, apply the rule.

The corpus-mode harness $\mathcal H$ is the recursion

```math
s_0 = \text{prompt},\qquad
\tilde s_{j} = E(s_{j-1}) \text{ up to } \texttt{</tag>},\qquad
s_j = s_{j-1} \,\|\, \tilde s_j \,\|\, \texttt{= } \mathrm{tool}(\tilde s_j)\texttt{\textbackslash n},
```

until a span carries no tag, whose text is parsed as the verdict. The *spans*
$\tilde s_j$ are the expert's decisions and the only thing the target scores (§7.3).

| serving | conditions each decision on | human accuracy |
|---|---|---:|
| `tool_calls` (P43) | $\hat h$ — a result the expert **invented** because it could not receive one mid-turn | **0.741** |
| corpus mode (P55 A) | $h$ — the real result, injected at `</tag>` | **0.989** |
| bare base, either | nothing — 0 calls | 0.345 |

**[ran]** — the same 598-example adapter, the same 351 human cases. The 25-point
difference is the drift of §4.4 made visible: nothing in the weights changed.

### 8.2 The ceiling, and where a gradient exists

Two things must hold for §7 to be measurable: $Q(T) \ge \max Q(E)$ **and** headroom
above the best expert. On triage neither holds — $Q(E) = 0.989$ leaves at most four
human cases for a target to win (a 4 : 0 pair gives $p = 0.0625$, below resolution),
and $Q(T)=0.746$. The desk suite (`training/email/desk.py`) varies depth by *how much
is handed over* independently of the question; on its `commitment` region P51 measured
the 32B at **1.000 at every depth** and the base falling **1.000 → 0.800 → 0.133 →
0.000** **[ran]** `results/P51-desk-profile-20260916/` — a target stronger by
construction and a gradient no expert will sit on top of. That is the redesign left
for a decision.

### 8.3 Graded experts

Nested subsets of one corpus: one seeded shuffle, and each grade is a prefix of it,
$\mathcal D_{75} \subset \mathcal D_{200} \subset \mathcal D_{598}$
(`training/harness/graded.py`, balance 43 % / 49 % important **[ran]**). Nesting is
what makes *how much* the only variable: a grade that saw different examples rather
than fewer would confound amount with content. Same base, same $r, \alpha$, same
epochs — so if $Q$ orders them, there is, for the first time, an ordering for
$\alpha$ to agree or disagree with.

### 8.5 The router: a classifier over corpus distributions, with abstention

Each released member $m$ has a corpus $K_m$; its user turns are samples of the distribution
$P_m$ the member was trained under. A router is a function
$r(x) \in \lbrace m_1,\dots,m_M,\ \mathrm{out}\rbrace$ built from a score $s_m(x)$ per member and a
threshold:

```math
r(x) = \begin{cases} \arg\max_m s_m(x) & \text{if } \max_m s_m(x) \ge \tau \ \text{and the margin to the runner-up} \ge \delta,\\ \mathrm{out} & \text{otherwise.}\end{cases}
```

The dictionary of P62 is the special case $s_m(x) = \lvert\lbrace \text{keys of } m \text{ in } x\rbrace\rvert$,
$\tau = 1$, $\delta = 1$. In §8.4's sum the only term a router can change is the third —
a request sent to a member whose corpus it does not belong to counts as wrong — so a router
is scored on **misrouted-to-local** and on the out share, not on accuracy, and $\tau$ is
set on out-of-distribution text before anything else is measured: a model asked to choose
always chooses. **[ran]** for the dictionary: P62, P64. The learned $s_m$ is
[`PLAN.md`](PLAN.md) milestone 2.

### 8.6 A knowledge base, and a trajectory through it

A subdomain's base is a set of notes $\mathcal N = \mathcal N_{\text{enc}} \cup \mathcal N_{\text{op}}$
— encyclopedic and operational — with links $\mathcal L \subseteq \mathcal N \times \mathcal N$
and an embedding $e:\text{text}\to\mathbb R^d$. A **trajectory** on case $x$ is the sequence of
notes the expert opens, $\pi(x) = (n_1,\dots,n_T)$, each chosen from what the last step exposed:

```math
n_{t+1} \in \underbrace{\mathrm{top\text{-}}k_{\,n \in \mathcal N}\ \langle e(q_t), e(n)\rangle}_{\text{a query the expert wrote}} \ \cup\ \underbrace{\{n : (n_t, n) \in \mathcal L\}}_{\text{a link the last note offered}} .
```

The adapter's parameters are the **policy** — which $q_t$ to write, which candidate to open, when
to stop; the base is the **content**. Two conditions make that split measurable rather than
nominal. *Unmemorisable content:* what a note says is drawn per case, $n = n(x)$, so
$I(\text{answer}; \text{weights} \mid \text{policy}) = 0$ for the looked-up part — P21's handbook,
extended to procedures. *A needed channel:* no looked-up value occurs in the statement.

With $\pi^{\star}(x)$ the oracle's trajectory and $Q_{\pi}(F)$ verified quality on family $F$ under
trajectory $\pi$, milestone 7 reads three differences, in this order:

```math
\underbrace{Q_{\pi^{\star}}(F') - Q_{\varnothing}(F')}_{\text{what reading can buy on a sibling family } F'} \qquad
\underbrace{Q_{\pi^{\star}}(F') - Q_{\hat\pi}(F')}_{\text{what navigation loses}} \qquad
\underbrace{Q_{\hat\pi}^{\text{op}} \ \text{vs}\ Q_{\hat\pi}^{\text{enc}}}_{\text{which kind of knowledge carries it}}
```

each paired (§9.2). $Q_{\varnothing}(F') \approx 1/20$ is measured **[ran]** P14; the rest is
**not yet measured** — [`PLAN.md`](PLAN.md) milestone 7. Navigation is scored where it happens —
retrieved, opened, followed — not only at the answer: a reader that got lucky over an empty note
is a case the final score cannot see.

### 8.7 Abstention inside a member, beside the router's (M10)

§8.5's $r(x)$ abstains *before* a request reaches a member. A member can abstain a
second time, *inside* its own region, once its corpus teaches an `OUT OF SCOPE`
verdict — the generation-level analogue of $r(x) = \mathrm{out}$, scored the same way:
a **lost** rate over what the member already answered, and a **caught** rate over what
it now correctly refuses.

```math
\ell = \frac{|\{x \in D_{\text{prior}} : \text{answered before, wrong or silent now}\}|}{|D_{\text{prior}}|}, \qquad
\text{caught} = \frac{|\{x \in D_{\text{oos}} : \text{abstained}\}|}{|D_{\text{oos}}|}.
```

**Measured [ran] `results/M10-distributor-abstain-20260928`.** `train_out` adds 70
`OUT OF SCOPE` turns, by the role's own egress, to M9's 700 turns **byte for byte**.
Against the prior member (`staff-s0`): **$\ell = 0$ of 70** — nothing the member already
did is lost by teaching it to refuse — and **caught = 20/20** held-out out-of-scope
cases (`staff-s0` itself: 0/20, since it was never taught the verdict); demo 6/6
against `staff-s0`'s 5/6. Live on the Air, the sixth scene (a thank-you note to
suppliers) is exactly the case that abstains and is forwarded — 10,198 + 195 tokens
through **Claude Haiku 4.5**, $0.0112 — the frontier component of `CLAUDE.md` reached
by a member's own abstention, not the router's.

### 8.8 Editing the library after training (W7)

§8.6's unmemorisable-content condition, $I(\text{answer}; \text{weights} \mid
\text{policy}) = 0$, makes a prediction: if the policy really carries no fact, patching
one statement in the library after training should change every answer that cites it,
with nothing in the weights to disagree. Two rates read the walks against the edit —
**follow**, over the control's answers that touch the patched statement, and **stale**,
over the same set, mutually exclusive by definition
($\text{follow} + \text{stale} \le 1$, the remainder being answers that do not reach
the statement at all):

```math
\text{follow} = \frac{|\{x : \text{answer}(x) = \text{new value, cited to the patched line}\}|}{|\{x : \text{control answers, touches the statement}\}|}, \qquad
\text{stale} = \frac{|\{x : \text{answer}(x) = \text{old value}\}|}{|\{x : \text{control answers, touches the statement}\}|}.
```

**Measured [ran] `results/W7-edit-after-training-20260927`**, one statement patched on
`distributor-wiki@v2`'s own training worlds and questions: **follow = 37/38**, cited to
the patched line; **stale = 0**. Closed-book — the same questions with no library open
— the weights still write the old value on **1 of 40**: the member learned *the route
to the statement*, not the statement itself, and that one case is reading a route
memorised well enough to answer without opening the page, not the library being
overruled. This is the mechanism [`MEMORY.md`](MEMORY.md) §7 lists as "a value … no
retrain", now measured rather than only claimed.

---

### 8.4 Delivered accuracy under a routing policy

A policy $r$ sends case $x$ to a local member $m$ or out to the frontier. With
$L_m(x) \in \lbrace 0,1\rbrace$ whether member $m$ answers $x$ right, $F(x)$ whether the
frontier does, and $m^\ast (x)$ the member of $x$'s region,

```math
\mathrm{delivered}(r) = \frac{1}{n}\sum_x \Big( [r(x) = (\mathrm{local}, m^*(x))]\,L_{m^*}(x) + [r(x) = \mathrm{out}]\,F(x) + [r(x) = (\mathrm{local}, m \ne m^*(x))]\cdot 0 \Big)
```

A case handed to the wrong member counts as wrong by construction — the conservative
reading. The by-region policy (P41) is $r(x) = \mathrm{region}(x)$ read off a label;
routing per request replaces the label by a classifier and can lose only by its
misroutes, so the two are compared on the same cases and the gate is a tie with zero
misroutes. **[ran]** P62: by region 0.775, by request 0.775, misroutes 0 (§11).

### 8.9 Multi-turn dependent accuracy, and the flat-context condition (MT0, H1)

A conversation is a sequence of turns $x_1,\dots,x_n$; turn $i$ is **dependent** when the right call's
argument is a value the user named, or a tool returned, on an earlier turn $j\lt i$ and $x_i$ itself does
not contain it. For a set $D$ of dependent turns and an arm $a$ (what the gateway renders on a turn),

```math
A_{\text{dep}}(a) = \frac{1}{|D|}\sum_{x\in D} \mathbf 1[\,\text{answer}_a(x)\text{ correct}\,].
```

**Measured [ran] `results/MT0-multiturn-baseline-20260929`**, $|D| = 54$: reading only the last
request, $A_{\text{dep}}(\text{last}) = 4/54$ — without the conversation the referent does not exist,
and the 4 are chance on a three-item choice. Carrying every earlier turn in the prompt,
$A_{\text{dep}}(\text{history}) = 43/54$ (79.6%): it resolves a reference it only has to **copy** into
an argument (32/34) but not one it must **write into free text** — a claim about "that order" filed
with no order number, 8 of 10 times. That split — copied into a call versus composed into prose — is
what the workflow harness's `get`/`put` targets: the value is fetched by key into the call, not left to
the model's own reading of the history.

**Prompt length by turn position, and why one arm is flat by construction.** Let $\bar p_i^a$ be the mean
rendered prompt length at turn $i$, over sessions that reach it. Under `history`, turn $i$'s prompt
carries every earlier turn's request and reply, so

```math
\bar p_i^{\text{history}} \;\approx\; \bar p_1 + \sum_{j=1}^{i-1} \ell_j = O(i),
```

with $\ell_j$ the rendered length of turn $j$ — genuinely growing in the number of turns, whatever their
content. The workflow harness instead renders one line, `state: <workflow>/<state> · keys: <names>`,
whose length is bounded by the number of keys and the state's own name — properties of the **domain's**
workflow, fixed once the TOML is written, not of **how many turns** the conversation has had:

```math
\bar p_i^{\text{harness}} \;\approx\; \bar p_1 + O(1) \quad\text{in } i,
```

the same order as `last` (the arm above that fails on accuracy), but without losing the referent, because the
value itself lives in the operational-memory cache and is fetched by key rather than carried in the
prompt. **H1's flatness condition** operationalises the contrast: with $\bar p_1,\bar p_2,\bar p_3$ the
mean prompt tokens at the first three turn positions,

```math
\bar p_3 \;\le\; 1.1\ \bar p_1
```

is the bar a harness arm must clear — at most 10 % growth by the third turn, distinguishing genuine
$O(1)$ behaviour (a small change from state-name length) from an implementation that quietly re-injects
growing content. **Measured [ran] MT0**, the two arms this bar is set against: $\bar p_1,\bar p_2,\bar
p_3 = 345, 376, 303$ for `last` and $345, 428, 394$ for `history` — the growth `history` shows even in a
two-to-three-turn suite (+24 % at turn 2, $\bar p_2/\bar p_1 = 1.24$) is exactly the term §2.4's batching
argument does not touch: a longer prompt is a longer prefill (§2.1) on every turn, for every session,
whether or not the GPU is otherwise idle.

**Measured [ran] H1** (`results/H1-workflow-harness-20260929`): a member (`wf-s0`) trained to read the
harness's one-line context instead of `history`'s growing one, on MT0's own 60 sessions.
$A_{\text{dep}}(\text{harness}) = 53/54$ against $A_{\text{dep}}(\text{history}) = 43/54$ — one turn lost,
eleven gained, a discordant pair count of $11 : 1$ favouring `harness` ($n_d = 12$, $p \approx 0.006$ by
§9.2's exact sign test) — and every one of the 53 right dependent turns fetched its value from the store
by key, not from the model's own reading of the transcript. The flatness bar holds by construction:
$\bar p_1,\bar p_2,\bar p_3 = 745, 726, 710$, so $\bar p_3/\bar p_1 = 0.953 \le 1.1$, flat rather than
merely bounded — the context line's length tracks the workflow's own state and key names, not the turn
count. These $\bar p$ values are **higher than either MT0 arm's** (745 against `history`'s 345 at turn 1)
because the harness spends more **generation steps** per turn — a `<get>` and its result, the tool call,
a `<put>` and its confirmation, then the answer — where `last`/`history` write the answer directly; §2.1's
prefill cost is paid once per step, so more steps at a flat per-turn floor is a real cost this measurement
states rather than hides. What it does not state: how much of that repeated get/call/put scaffold a
prefix cache (§3.6) would absorb across turns — not measured here, and the reason the harness's *token*
case is for sessions longer than MT0's two or three turns, even though its *accuracy* case already holds
at that length. A fourth arm, `harness-noblock` (the same corpus, tool block withheld at serving time
although always present in training), scores $A_{\text{dep}} = 0/60$: an unfamiliar prompt, not a harder
one (§8.1, §8.6). **The run's own stopping rule — first-turn accuracy $\ge 0.90$ in *every* arm or the run
is VOID — was written to guard the whole comparison and instead let one arm's failure void the other
two's real result; read per arm rather than as written, `harness` passes this section's bars and
`harness-noblock` does not.** The user's decision (2026-09-29): the per-arm reading stands for the release
gate — `harness` PASSED, `harness-noblock` FALSIFIED — and the as-written VOID is kept as the record of
that instrument error.

**Measured [ran] H2** (`results/H2-tracker-harness-20260929`), the same harness on a second domain built
for it (a Jira + Confluence-like team tracker), 60 held-out long sessions, $|D| = 160$ dependent turns,
60 first turns, 60 independent turns. Sessions here run five turns rather than two or three, so the
flatness condition is stated over five: with $\bar p_1,\dots,\bar p_5$ the mean prompt tokens at the first
five turn positions,

```math
\bar p_5 \;\le\; 1.1\ \bar p_1
```

is the bar this run is read against. $A_{\text{dep}}(\text{harness}) = 146/160$ (91.3%), against a 90%
bar, with $\bar p_1,\dots,\bar p_5 = 1613, 1223, 1011, 1149, 1274$ — $\bar p_5/\bar p_1 = 0.790 \le 1.1$,
flat (in fact falling, as the get/put scaffold amortises once the workflow's own state settles). The
untrained baseline `base-history` (bare Gemma 4 E4B, the conversation in the prompt) scores
$A_{\text{dep}} = 4/160$ and its own first turns 44/60 fall under the 90% bar; applying the per-arm VOID
rule H1 established makes the pre-registered "`harness` beats `base-history`" comparison unreadable, so
**H2 reads FALSIFIED as written, not VOID** — voiding an untrained baseline whose low first-turn score
*is* the headroom being measured is a narrower instrument error than H1's, recorded rather than patched.
Descriptively, on the same 160 dependent turns: **142 : 0** favouring `harness`, $p\lt 10^{-40}$ by §9.2's
exact sign test — stated because it costs nothing to state, not offered as a substitute for the
pre-registered verdict its void arm makes unreadable. Decision pending for the user, as for H1: accept the
readable conditions as H2's verdict, or rerun with the per-arm rule restricted to trained members.

## 9. Statistics used, and only these

### 9.1 The majority bar

Answering the majority class to every case scores $\max(\pi, 1-\pi)$; a system below
it has learned nothing. On the 351 human triage cases it is **0.655** **[ran]**; on
the full 475 it is easier, because `noreply@` is free, which is why human messages are
the reported subset.

### 9.2 The exact two-sided sign test on discordant pairs

Two arms scored on the same cases disagree on $n_d$ of them; $u$ of those favour
$A$. Under $H_0$ each discordant case favours either arm with probability $\tfrac12$,
so $u \sim \mathrm{Bin}(n_d, \tfrac12)$ and

```math
p = \min\Big(1,\; 2\,\Pr\big[\mathrm{Bin}(n_d,\tfrac12) \ge \max(u, n_d-u)\big]\Big),
```

`training/harness/bar.py::sign_test`. Ties carry no information and are excluded —
that is what makes it the paired test rather than a comparison of two proportions.
**Totals are never compared**: 84, 81, 82 correct on identical cases were three ties
by this test, and reading them as movement was the mistake P43's power check ended.

### 9.3 Power and the size that resolves an effect

For a bar $\pi_0$ and $n$ cases, the pass threshold is the smallest $t$ with
$\Pr[\mathrm{Bin}(n,\pi_0)\ge t] \le 0.05$, and the **power** to see a true rate
$\pi_0+\delta$ is $\Pr[\mathrm{Bin}(n,\pi_0+\delta) \ge t]$. `bar.resolvable` and
`bar.n_for` are those two functions. At $n=351$ over $0.741$: $\delta=0.07$ is seen
**93 %** of the time, $\delta=0.05$ only **71 %** **[ran]** — which is why P55's
grades were placed at 75 / 200 / 598 rather than closer.

### 9.4 What headroom means

A treatment cannot move a baseline that sits at the ceiling; the arm must be checked
for room *before* it is bought (P42's ARC adapter, 0.825 over a base at 0.815, was
unresolvable at $n=200$ **[ran]**). §8.2 is the same rule applied to the target.

---

## 10. The Qwen 3 family: small and large of one id space

### 10.1 Both halves carry a LoRA

Speculative decoding has two models and two jobs. The **drafter** is the pool — multi-LoRA
is *its* requirement. The **target** verifies in one pass (§6.1 step 2).

~~The target is one dense, unmodified model and needs no LoRA.~~ **Restated 2026-09-19.**
An unmodified large model scored *below* the small expert in both regions tried —
$Q(T) \lt  \max Q(E)$, 0.746 < 0.989 and 0.967 < 1.000 **[ran]** P55, P55b (§7.2) — so the
target of a pair is $T_\phi$: the large model with a LoRA of the same subdomain. That makes
serving a LoRA a requirement of **both** halves, and both are measured: over a 4-bit large
model the adapter is applied, mean $|\Delta\ell|$ 0.22–0.49 nats against a base-vs-base
0.000 **[ran]** P60 §3b (§4.3); over the 3.x small model it is applied once its tensors are
named for the class vLLM serves **[ran]** D2 (§10.4).

### 10.2 The id space

From §3.3: a Qwen 2.5 drafter can be verified by `Qwen3-32B` today (identical map,
four thinking ids to keep off); it **cannot** be verified by `Qwen3.8-27B`
(248,044 ≠ 151,643). But `Qwen3.5-2B` and `Qwen3.5-4B` **can** — identical map, seven
audio/TTS specials the text task never reaches, `<think>` shared **[ran]** D0. So the
pair *3.5-drafter → 3.8-27B-target* is sound in id space, and the 3B experts of today
are not the drafters of that pair.

### 10.3 The thinking channel

A thinking target opens `<think>` before its answer; the drafter writes the answer.
At every such position acceptance is 0 (§3.3). The target is served with thinking
disabled and the count of `<think>` ids in its greedy output on the suite must be
**0** — D3, a gate inside D4.

### 10.4 The hybrid architecture and C18: what the evidence shows

| assertion in the outside analysis | what the P33 log **[ran]** shows | status |
|---|---|---|
| the class is a multimodal wrapper | `Resolved architecture: Qwen3_5ForConditionalGeneration` | **confirmed** |
| linear attention / Gated DeltaNet is real | `qwen_gdn_linear_attn.py … GDN decode kernel: cuda`; `layer_types` 24 linear + 8 full **[read]** | **confirmed** |
| vLLM's LoRA kernels do not dispatch on the language layers | every `no matching PunicaWrapper … will be ignored` line names a **`visual.`** module; `_lora_expand_kernel` JIT-compiled **during inference** | **contradicted** |
| restrict `target_modules` to the MLP to unblock it | "the adapter touched only MLPs" was a diagnosis P33 **withdrew** — the loaded tree carries `q_proj` | **no support** |
| an RFC closes per-request LoRA in the speculative worker; SGLang handles hybrids | not checked from here | **[unverified]** |

What was known on 2026-09-17: the adapter is real (G1: `lora_B` moved, output changed in
process), the engine says it loaded it, the served text equals the base's.

**The mechanism, read and then run — D2 [ran] 2026-09-19.** With $K$ the adapter's tensor
names, $m$ vLLM's name mapper for the served class and $M$ the served model's modules,

```math
\text{applied}(K) = \{\,k \in K : m(k) \in M\,\}.
```

Trained through `AutoModelForCausalLM`, PEFT names tensors `model.layers.N…`; vLLM serves
`Qwen3_5ForConditionalGeneration` and activates by `language_model.model.layers.N…`.
Loading validates only the last component of each name and logs *Loaded*; activation looks
up the full name and resets the slot. As trained $|\text{applied}(K)| = 0$ of 496 and the
real activation sets 0 of 178 modules; renamed by `training/harness/rekey.py`, 496 of 496
and 152 of 178, and the identity gate turns from `not applied` to `applied`. The 26 modules
left empty are `lm_head`, `embed_tokens` and 24 `conv1d`, none targeted; the
linear-attention projections are among the 152.

### 10.5 The route, as mechanisms

| # | mechanism | state |
|---|---|---|
| D0 | a 3.x small model sharing an id space with 3.8-27B | **[ran]** ✓ |
| D1 | C18 under a newer vLLM | void — the chain installs the latest and it is **0.29.0**, P33's version **[ran]** |
| D2 | the C18 mechanism: PEFT key ↔ vLLM module mapping, with the log | **[ran]** ✓ 2026-09-19 — a naming mismatch (§10.4) |
| D3 | thinking off, verified by count | inside milestones 3–4 |
| ~~D4~~ | ~~the ranking instrument pointed at 3.5-4B → 3.8-27B~~ | retired with the ranking claim; replaced by [`PLAN.md`](PLAN.md) milestones 1, 3 and 4 |

**Why the order.** Everything in §6–§7 is target-agnostic given §3.2. Milestone 1 moves the
released members to the 3.x small model with their Qwen 2.5 releases as the control;
milestone 3 trains the large half; milestone 4 measures §7.1's inequality.

---

## 11. Map: section → run

**Runs named here that have no directory on `main` live at the tag `v0.1-foundations`.**

| section | formula / claim | run that instantiates it |
|---|---|---|
| §1.3 | embedding width > vocabulary | `STACK.md` §1 (the tag `v0.1-foundations`), P48 |
| §1.4–1.5 | dimensions, hybrid `layer_types` | `config.json` **[read]** 2026-09-17; P33 log |
| §2.4 | batching: 475 chains, 31 s / 230 s | P55 A `session_a.json` |
| §3.3 | id-map table | P48; P55 `D0-tokenizers.txt` |
| §4.2 | 29,933,568 params ↔ 119,801,528 bytes | `STACK.md` §3 (the tag `v0.1-foundations`) |
| §4.4, §8.1 | drift: 0.741 → 0.989 | P43 `arm_email_475.json`; P55 A |
| §4.4, §9.2 | **a release reproduces**: re-served 0 : 0 against its record; re-trained 1 : 0 — training variance one case in 475 | P57 `release.json`, `releases/email-full@v1.json` |
| §5.2 | C18 identity gate | P33 `lora_matrix.json`; P55 A `applied`; **Phase 0 P56: both members 3/3 `applied`, tools reachable, stop honoured** |
| §5.3 | `prompt_logprobs` shape | P55 A `preflight_target` |
| §5.4 | stop preflight; positional shim | P55 A attempts 1, 2 |
| §7.2 | $Q(T) \lt  \max Q(E)$: 2 : 87, $p=0$ | P55 A `target_gate` |
| §8.2 | ceiling 0.989; commitment gradient | P55 A; P51 `desk_profile.json` |
| §8.3 | the smallest grade is not saturated: $Q(g25) = 0.000$, base 0.171 — it fabricates the tool's answer | P58 `g25.json` |
| §8.3 | **no intermediate grade**: `g75` ≡ `g600` = 1.000 on a one-call protocol; M1 passes on one bit | P55b `p55b.json` |
| §8.2 | **a deeper band exists by construction**: `commitment_deep`, the latest of 1–3 promises among the sender's proposals, last message the sender's from depth 2; the shallow suite pinned by hash after #206 had silently moved it (0 mismatches vs P55b) | P60 §3a, `tests/test_desk_deep.py` |
| §7.2 | **$Q(T) \lt  \max Q(E)$ a second time**: 32B 0.967 (date-normalised) vs `g600` 1.000, 0 : 8, $p = 0.008$ | P55b `target_gate` |
| §9.3 | power at $n=351$ | `bar.resolvable` **[ran]** 2026-09-16 |
| §10.2 | 3.5 → 3.8 id space | P55 `D0-tokenizers.txt` |
| §10.5 D1 | vLLM resolves to 0.29.0 | P55 A boot log |
| §4.4 | **an unknown surface is extrapolation**: unpruned (54 tools) the expert copies tags off the block, 225 of 227 calls refused; pruned, 8 of 1160; the block is ~7,956 vs ~77 tokens — and served after the request, as trained, it costs TTFT 0.10 → 1.70 s with prefix caching on | P59 `attribution.json`; E5 `e5.json` |
| §6.4 | **α, $\mathbb{E}[\tau]$, speed-up** | token-level α (rank-1 acceptance) **[ran]** B4: 0.871 bare 12B, 0.898 12B + LoRA over 107 E4B draft records; $\mathbb{E}[\tau]$ at $k=4$ under §6.4's independence, 3.87 → 4.08 — derived, not measured; **wall-clock [ran] F0** (12B FP8 + LoRA, the native MTP drafter, k = 4): the base 2.73× at batch 1 with mean accepted length 4.16, the LoRA expert 1.74× on its domain (4.16 → 2.25) — the LoRA costs the drafter, measured; output identity at temperature 0 not yet established |
| §7.4 | **the ordering verdict** | **closed without a verdict 2026-09-19**: §7.2 fails for an *untrained* target in two easy regions (P55 A, P55b). What survived it is the trained target — now the large half of a pair (§7.1, §10.1) |
| §10.5 D2 / §3.4 | **a LoRA applies over the AWQ 32B**: mean $\vert \Delta\ell\vert$ 0.22–0.49 nats vs base-vs-base 0.000, 3/3; text gate 2/3 | P60 §3b `awq_gate.json` |
| §10.5 D2 | **C18 is a naming mismatch**: $\text{applied}(K)=\lbrace k\in K: m(k)\in M\rbrace$ — as trained 0 of 496 tensors land on the served text stack and the real activation sets 0 of 178 modules (`not applied`); renamed, 496 of 496 and 152 of 178 (`applied`); control `applied` | D2 `lora_matrix.json`, `vllm.log` |
| §7.1, §7.4 | **the pair inequality** $\alpha_{T_\phi}(S_\theta) \gt  \alpha_T(S_\theta)$ | **holds [ran] B4**: 76 : 18 records, $p \lt  10^{-4}$ — on the corpus's own distribution (0.855 → 0.914), not on a band neither half trained on (0.885 → 0.881); [`PLAN.md`](PLAN.md) milestone 4 |
| §8.5 | **the router as a classifier with abstention**; the dictionary is its special case | dictionary: P62, P64. **An n-gram model of each corpus's frame [ran] M2**: foreign text 0/128 served locally against the dictionary's 59/128; legitimate requests from unseen senders 120/120 lost against 0/120 — does not pass; the embedding arm: **not yet measured** |
| §8.6 | **a trajectory through a subdomain's knowledge base**; the policy in the weights, the content outside | $Q_\varnothing(F') \approx 1/20$: P14. Two- and three-hop walks over pages of atomic statements, cited and checked: 0/40 untrained → 35/40, 38/40 on Gemma **[ran]** W9, B1; a skill the corpus never showed is not learnt (comparisons 10/40), shown it is (37/40) **[ran]** B3, B5; on the nursing library the central claim is not passed **[ran]** W5, W5c |
| §7.3, §8.2 | **weights or harness — weights**: base 0.345, base + 914-token procedure 0.601 (both 0 tool calls, under the 0.655 majority bar), expert 0.989; expert vs base+kb **137 : 1**; the sign test alone read the flipped default as paying (164 : 74) — the majority bar guards it | P61 `session.json` |
| §8.4 | **routing per request ties by region**: 0.775 = 0.775, 0 misroutes, 37.5 % out on P41's 240 cases | P62 `replay.json` (zero GPU) |
| §4.4, §8.1 | **the live turn is corpus mode or it is nothing**: under the runtime's prompt 2/32 human turns call a tool (0.281); under the member's released prompt with `</tag>` stops, the round-trip cap and 256 tokens/step, 19/32 call and 0.688 vs bar 0.655 ($p=0.43$), 40/40 local | P63 `live.json`, attempts 4 and 7 |
| §9.2, §8.4 | **a second member through Phase 1's door**: `desk-commitment` ties its recorded run 240/240 (0 discordant, $p=1$) and beats the base 202 : 0 ($p = 2\cdot2^{-202}$); co-resident with `email-full`, `auto` routes each by its question | P64 `pool_second.json` |
| §2.5 | **KV below an untouched depth is bit-identical**: LoRA on layers 21–41 of 42 only, 70/70 held-out = the full member (0 lost), base-vs-base control over layers 0–20 identical bit for bit; caveat: 24 of 42 layers are KV-shared, so 21–23 still recompute | E6 `results/E6-upper-layers-20260927/BRIEF.md` |
| §5.5 | **prefix caching is keyed by position, not content**: TTFT 0.10 → 1.70 s (16.8×), b8 throughput 132 → 108 tok/s, accuracy 70/70 → 39/70; 0.09–0.11 s where the whole prefix recurred; two LoRAs in one batch keep 0.88× | E5 `results/E5-engine-baseline-20260928/BRIEF.md` |
| §6.7 | **MTP speed-up under a domain LoRA**: base 2.80×/2.60× (domain/general), LoRA on 1.92× ($\alpha$ 0.34) / 2.40× | C0 `results/C0-aligned-draft-20260927/BRIEF.md` |
| §6.7 | **layer restriction does not help the drafter**: $\rho = -0.02$ (E4B's own MTP, base 0.82, full 0.44, upper 0.43) — NONE | C0-upper `results/C0-upper-e4b-20260927/BRIEF.md` |
| §6.7 | **on llama.cpp/Metal the drafter is not cheap**: Gemma's MTP *slows* the 12B, 0.52× with the LoRA on its domain, 0.66–0.87× otherwise — §6.4's $c$, not $\alpha$, is what moved | MAC2 `results/MAC2-llamacpp-20260927/BRIEF.md` |
| §8.7 | **abstention inside a member**: $\ell = 0$ of 70, caught 20/20 against `staff-s0`'s 0/20, demo 6/6; live, the abstained turn reaches Claude Haiku 4.5, $0.0112 | M10 `results/M10-distributor-abstain-20260928/BRIEF.md` |
| §8.8 | **editing the library after training**: follow 37/38, stale 0, closed-book 1/40 | W7 `results/W7-edit-after-training-20260927/BRIEF.md` |
| §8.9 | **dependent-turn accuracy without and with history**: $A_{\text{dep}}$(last) 4/54, $A_{\text{dep}}$(history) 43/54; prompt tokens $\bar p_1,\bar p_2,\bar p_3$ = 345/376/303 (last), 345/428/394 (history) | MT0 `results/MT0-multiturn-baseline-20260929/BRIEF.md` |
| §5.6 | **multi-adapter throughput ratio**: $r_4(16) = 278.6/269.7 = 1.03$, NO MATERIAL CONTENTION; near-linear 22.7 → 135.1 → 278.6 → 504.3 tok/s for K = 1, 8, 16, 32; p95 TTFT 0.24 s at K = 32, 0 errors of 128 | C1 `results/C1-concurrency-20260929/BRIEF.md` |
| §8.9 | **the workflow harness against MT0's history arm and the flatness bar $\bar p_3 \le 1.1\ \bar p_1$**: $A_{\text{dep}}$(harness) 53/54 vs 43/54, 11 : 1 paired ($p\approx0.006$); $\bar p_1,\bar p_2,\bar p_3$ = 745/726/710, flat; `harness-noblock` 0/60. As written VOID (the first-turns rule voids across arms); read per arm, `harness` PASSED and `harness-noblock` FALSIFIED — the user's decision (2026-09-29): per arm stands, the as-written VOID kept as the instrument-error record | H1 `results/H1-workflow-harness-20260929/BRIEF.md` |
| §8.9 | **the same harness on a five-turn tracker domain, the flatness bar $\bar p_5 \le 1.1\ \bar p_1$**: $A_{\text{dep}}$(harness) 146/160 (91.3%) against a 90% bar; $\bar p_1,\dots,\bar p_5$ = 1613/1223/1011/1149/1274, flat; `base-history` 4/160, its own first turns 44/60 void it under H1's per-arm rule, making the pre-registered comparison unreadable — reads FALSIFIED as written, not VOID; descriptive paired 142 : 0, $p\lt 10^{-40}$ (arm void, not a substitute verdict); decision pending the user | H2 `results/H2-tracker-harness-20260929/BRIEF.md` |
