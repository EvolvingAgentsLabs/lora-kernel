# Foundations — the mathematics under lora-kernel, tied to what ran

> *[Léeme en español](es/FOUNDATIONS.md)*

This document says, step by step and in mathematics, what the models are, why
generating with them is slow, what a LoRA is, what the engine does, what speculative
decoding computes, why acceptance can rank experts, what the tasks are as functions,
and why the Qwen 3 family and `Qwen3.8-27B` can be the large model. **Every formula
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

$$
p_\theta(x_t \mid x_{<t}) = \mathrm{softmax}\big(f_\theta(x_{<t})\big)_{x_t},
\qquad
p_\theta(x_{1:T}) = \prod_{t=1}^{T} p_\theta(x_t \mid x_{<t}).
$$

Generation is the recursion $x_{t} \sim p_\theta(\cdot \mid x_{<t})$, one id at a
time; **each step needs the whole prefix and cannot start before the previous id
exists.** That single fact — generation is sequential in $t$ — is what §2 prices and
what §6 exploits.

At temperature 0 the sampling collapses to $x_t = \arg\max_v f_\theta(x_{<t})_v$,
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

1. **Pre-norm.** $\tilde h = \mathrm{RMSNorm}(h) = h \oslash \sqrt{\tfrac{1}{d}\sum_j h_j^2 + \epsilon}\;\odot\; g$.

2. **Projections.** $Q = \tilde h W_q,\; K = \tilde h W_k,\; V = \tilde h W_v$ with
   $W_q \in \mathbb{R}^{d\times H d_h}$ and $W_k, W_v \in \mathbb{R}^{d \times H_{kv} d_h}$.
   With $H_{kv} < H$ each key/value head serves $H/H_{kv}$ query heads — *grouped-query
   attention*, which is what makes the KV cache in §2.2 smaller than it would be.

3. **Rotary position (RoPE).** Each pair of coordinates $(q_{2i}, q_{2i+1})$ at position
   $t$ is rotated by angle $t\,\omega_i$ with $\omega_i = \theta^{-2i/d_h}$; the same
   for $k$. Then $\langle q_t, k_s\rangle$ depends only on $t-s$ — position enters as a
   relative phase. Both families use $\theta = 10^6$ **[read]**.

4. **Causal attention**, per head:
   $$
   A = \mathrm{softmax}\!\Big(\frac{QK^\top}{\sqrt{d_h}} + M\Big)V,
   \qquad M_{ts} = \begin{cases}0 & s\le t\\ -\infty & s>t\end{cases}
   $$
   then $h \leftarrow h + A\,W_o$.

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
nothing, which `STACK.md` §1 records because a typed head once assumed otherwise.

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

$$
S_t = \alpha_t\,\big(I - \beta_t\, k_t k_t^\top\big)\, S_{t-1} \;+\; \beta_t\, k_t v_t^\top,
\qquad o_t = S_t^\top q_t,
$$

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

$$
\text{bytes}_{KV}(t) \;=\; 2 \cdot L \cdot H_{kv} \cdot d_h \cdot t \cdot b,
$$

with $b$ bytes per element. For `Qwen2.5-3B` in bf16: $2\cdot 36\cdot 2\cdot 128\cdot 2 = 36{,}864$ bytes
per token — **36 KB/token**, 147 MB at 4,096 tokens. For the 32B (bf16 cache on an
AWQ base): $2\cdot 64\cdot 8\cdot 128\cdot 2 = 262{,}144$ bytes — **256 KB/token**, 1 GB at
4,096. GQA is why these are $H_{kv}$ and not $H$. The linear-attention layers of §1.5
carry a fixed $d_k\times d_v$ state instead, which is the point of them.

### 2.3 Decode is bound by weight bytes

One decode step reads every weight once. With $B_W$ bytes of weights and memory
bandwidth $\mathcal{B}$, the floor is

$$
t_{\text{step}} \;\gtrsim\; \frac{B_W}{\mathcal{B}} \;+\; \frac{\text{bytes}_{KV}(t)}{\mathcal{B}}.
$$

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

$$
W' = W + \frac{\alpha}{r}\, A B, \qquad A \in \mathbb{R}^{d_{in}\times r},\; B\in\mathbb{R}^{r\times d_{out}},\; r \ll \min(d_{in}, d_{out}),
$$

trains only $A, B$, and at inference computes $xW' = xW + \tfrac{\alpha}{r}(xA)B$ —
two thin products beside the frozen one. Every adapter here uses $r=16$, $\alpha=32$,
dropout 0.05 on the seven projections of §1.2 **[ran]** `adapter_config.json`.

Because $W$ is never touched, **the base stays resident and the delta is the only
thing that changes between experts** — it can be swapped per request, batched across
requests (§5.2), versioned and discarded. That is the whole architectural premise:
*the system is a pool of deltas over one resident base.*

### 4.2 The count, reconciled with the artefact

Per block of `Qwen2.5-3B` ($d = 2048$, $H_{kv} d_h = 256$, $d_{ff} = 11008$), LoRA
parameters are $r\,(d_{in} + d_{out})$ per matrix:

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
the file on disk is **119,801,528 bytes** **[ran]** `STACK.md` §3 — the 67,256-byte
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

$$
\mathcal{L}(A,B) = -\sum_{t \in \text{assistant}} \log p_{\theta + \Delta}(x_t \mid x_{<t}),
$$

so the adapter learns $p(x_t \mid x_{<t})$ **for the prefixes the corpus contains**.
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

With adapters $\{(A_i, B_i)\}$ resident and a batch in which request $j$ names adapter
$i(j)$, the layer computes

$$
y_j = x_j W + s\,(x_j A_{i(j)}) B_{i(j)},
$$

as one shared GEMM for $xW$ plus a *batched, gathered* pair of thin GEMMs (the
`bgmv` / Punica kernels **[read]**, Chen et al. 2023; S-LoRA, Sheng et al. 2023). Flags
here: `--enable-lora --max-lora-rank 16 --max-loras k --lora-modules name=path`
**[ran]** `STACK.md` §5. The adapter is chosen by the request's `model` field, which is
how the pool is addressed with no router at all.

**C18 is a test of that equation.** An engine can load $(A_i, B_i)$, log
`Loaded new LoRA adapter`, and still return $y = xW$ — the delta term silently absent.
The identity gate serves the same prompt through base and adapter and requires the
texts to differ **[ran]** P33 (`Qwen2.5-3B`: differs; `Qwen3.5-4B`: identical) and
P55 A (`email-full`: 6 of 8 probes differ → `applied`).

### 5.3 Teacher forcing in one prefill: `prompt_logprobs`

Prefill (§2.1) computes $f_\theta(x_{<t})$ **for every $t \le P$ at once**. Asking
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

---

## 6. Speculative decoding

### 6.1 The algorithm

Given a target $p$ (large, slow) and a drafter $q$ (small, fast) over the same id
space (§3.2), one round at prefix $x$ **[read]** (Leviathan et al. 2023; Chen et al.
2023):

1. **Draft.** Sample $\tilde x_1 \sim q(\cdot\mid x)$, $\tilde x_2 \sim q(\cdot\mid x,\tilde x_1)$, …, $\tilde x_k$ — $k$ cheap decode steps.
2. **Verify.** One target pass over $x, \tilde x_1,\dots,\tilde x_k$ yields
   $p(\cdot\mid x,\tilde x_{<i})$ for all $i \le k+1$ at once (§5.3).
3. **Accept / reject**, left to right: accept $\tilde x_i$ with probability
   $$
   a_i = \min\!\Big(1, \frac{p(\tilde x_i \mid x, \tilde x_{<i})}{q(\tilde x_i \mid x, \tilde x_{<i})}\Big).
   $$
   At the first rejection, at position $i$, emit one token from the **residual**
   $$
   p'(v) \propto \max\big(0,\; p(v \mid \cdot) - q(v \mid \cdot)\big)
   $$
   and stop the round. If all $k$ are accepted, emit one extra token from
   $p(\cdot\mid x,\tilde x_{1:k})$ — the pass already computed it.

### 6.2 Exactness

For any $v$: $\Pr[\text{emit } v] = q(v)\min(1, p(v)/q(v)) + \big(1-\sum_u q(u)\min(1,p(u)/q(u))\big)\,p'(v) = \min(p(v),q(v)) + \max(0, p(v)-q(v)) = p(v)$.
**The output is distributed exactly as the target's**, whatever the drafter is. A bad
drafter costs speed, never correctness — which is why acceptance can be read as a
score *about the drafter* (§7).

### 6.3 Temperature 0

With $p$ one-hot at its argmax, $a_i = 1$ iff $\tilde x_i = \arg\max_v p(v\mid x,\tilde x_{<i})$
and $0$ otherwise. **Acceptance is argmax equality**, and the accepted prefix is the
longest prefix of the draft along which the target would have made the same choice.
This is the identity `alpha/` rested on from the start and `accept_rank.py` reads
token by token: *accepted iff rank = 1* **[ran]** P55 A preflight.

### 6.4 How much it buys, and why a slow target is where it pays

If each token is accepted independently with rate $\alpha$, the expected number of
tokens emitted per round with $k$ drafts is

$$
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha}.
$$

Let $c = t_{\text{draft}} / t_{\text{target}}$ be the cost of one drafter step relative
to one target step. A round costs $k\,c + 1$ target-steps and yields $\mathbb{E}[\tau]$
tokens, so

$$
\text{speed-up} \;=\; \frac{\mathbb{E}[\tau]}{k\,c + 1}
\;=\; \frac{1-\alpha^{k+1}}{(1-\alpha)(k c + 1)}.
$$

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
architecture keeps (`REPORT.md` §6), and it is what §7 formalises.

---

## 7. Acceptance as ranking — the thesis, formally

### 7.1 Definitions and the claim

A suite is a set of cases $\mathcal{C}$ with a mechanical verifier
$\mathrm{ok}(c, \text{answer}) \in \{0,1\}$. For an expert $E$ (base + one adapter)
its **verified quality** is $Q(E) = \tfrac{1}{|\mathcal C|}\sum_c \mathrm{ok}(c, E(c))$.
For a target $T$, its **acceptance** on case $c$ is

$$
\alpha_T(E, c) = \frac{1}{n_c}\sum_{i=1}^{n_c} \mathbf{1}\big[\tilde x_i^{E}(c) = \arg\max p_T(\cdot \mid \text{prefix}, \tilde x_{<i}^{E}(c))\big],
$$

the fraction of $E$'s $n_c$ *decision tokens* on that case that the target would have
written itself (§6.3), and $\alpha_T(E) = \tfrac1{|\mathcal C|}\sum_c \alpha_T(E,c)$.

**The claim (P55):** for experts $E_1,\dots,E_m$ on one suite,
$Q(E_a) > Q(E_b) \;\Rightarrow\; \alpha_T(E_a) > \alpha_T(E_b)$ — acceptance orders
experts the way verified quality orders them, with **no judge and no verifier at
serving time**. If it holds, a pool selects among close experts by letting the target
score their drafts; if it fails, the "free router" is gone and the architecture
survives without it.

### 7.2 The precondition, and P55 A as its instance

$\alpha_T(E)$ is agreement with $T$. If $T$ is wrong on a case, an expert that is
*right* is **rejected there**, and $\alpha$ rewards the expert that shares the target's
mistake. So the claim is only about quality when

$$
Q(T) \;\ge\; \max_a Q(E_a)
$$

— "it is only a distillation score when the target is stronger than every candidate"
(`alpha-surface` skill). P55's M-target gate is that inequality as a paired test, and
it fired: on 351 human triage cases the 32B was right where the expert was wrong on
**2** and wrong where the expert was right on **87**, $p = 0.0$;
$Q(T)=0.746 < Q(E) = 0.989$ **[ran]** P55 A. The untrained large model *gets every
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

### 7.4 The ordering test

For every pair $(E_a, E_b)$ the verifier resolves (§9.2), take the cases both were
scored on and count $u = \#\{c: \alpha(E_a,c) > \alpha(E_b,c)\}$,
$d = \#\{c: \alpha(E_a,c) < \alpha(E_b,c)\}$; ties are excluded; the exact two-sided
binomial on $(u,d)$ decides. Written before any run: **SUPPORTED** if every resolved
pair agrees; **FALSIFIED** if any pair is ordered the other way at $p\le0.05$;
**UNRESOLVED** if the verifier saw a difference and $\alpha$ did not — *a failure of
the claim as stated, not a tie* **[ran]** `results/P55-graded-ranking-20260916/BRIEF.md`.

---

## 8. The tasks, as functions

### 8.1 Triage, the chain, and the drift with numbers

A message $m$ carries facts $\phi(m) = (\text{automated}, w, a, s, f)$ — *I wrote in
the thread*, *addressed to me*, *asks something*, *frequent sender*. The label is

$$
y(m) = \neg\,\text{automated} \;\wedge\; \big[\,w + a + s + f \;\ge\; 2\,\big],
$$

`training/email/inbox.py::important`. **The listing shows none of $w, a, f$** — they
live behind three tools (`thread_history` → $w$, `sender_stats` → $f$, `message` → $a$
and the body for $s$), and `tests/test_email.py` asserts the best listing-only rule
scores exactly the majority class on human messages **[ran]**. So the expert's job
is a *chain*: decide which tools, call them with the right argument, read the
results, apply the rule.

The corpus-mode harness $\mathcal H$ is the recursion

$$
s_0 = \text{prompt},\qquad
\tilde s_{j} = E(s_{j-1}) \text{ up to } \texttt{</tag>},\qquad
s_j = s_{j-1} \,\|\, \tilde s_j \,\|\, \texttt{= } \mathrm{tool}(\tilde s_j)\texttt{\textbackslash n},
$$

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

---

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

$$
p = \min\Big(1,\; 2\,\Pr\big[\mathrm{Bin}(n_d,\tfrac12) \ge \max(u, n_d-u)\big]\Big),
$$

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

## 10. Why the Qwen 3 family, and `Qwen3.8-27B` as the large model

### 10.1 The target needs no LoRA

Speculative decoding has two models and two jobs. The **drafter** is the pool —
multi-LoRA is *its* requirement. The **target** verifies in one pass (§6.1 step 2)
and is one dense, unmodified model. C18 — *vLLM loads a LoRA on a 3.x base and
serves the base anyway* **[ran]** P33 — is a statement about serving a LoRA, so **it
constrains the drafter and says nothing about the target**. The 32B here is served
AWQ with no adapter (§4.3) and that is exactly the target's shape.

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

What is known: the adapter is real (G1: `lora_B` moved, output changed in process),
the engine says it loaded it, the served text equals the base's. **The failure is
measured; its mechanism is not**, and this project's rule after two withdrawn
diagnoses is to read the mechanism with the log in hand (D2), not to adopt one.

### 10.5 The route, as mechanisms

| # | mechanism | state |
|---|---|---|
| D0 | a 3.x drafter sharing an id space with 3.8-27B | **[ran]** ✓ |
| D1 | C18 under a newer vLLM | void — the chain installs the latest and it is **0.29.0**, P33's version **[ran]** |
| D2 | the C18 mechanism: G3 merge-and-serve; PEFT key ↔ vLLM module mapping, with the log | next |
| D3 | thinking off, verified by count | inside D4 |
| D4 | the P55 instrument, `--base Qwen/Qwen3.5-4B --target Qwen/Qwen3.8-27B`, graded pool retrained on 3.5-4B | blocked on D2 |

**Why the order.** Everything in §6–§7 is target-agnostic given §3.2; the instrument
built on Qwen 2.5 is the one D4 runs. If §7 fails on 2.5, D4 would buy a faster
version of a mechanism that does not rank. Nothing above depends on D; D4 depends on
all of it.

---

## 11. Map: section → run

| section | formula / claim | run that instantiates it |
|---|---|---|
| §1.3 | embedding width > vocabulary | `STACK.md` §1, P48 |
| §1.4–1.5 | dimensions, hybrid `layer_types` | `config.json` **[read]** 2026-09-17; P33 log |
| §2.4 | batching: 475 chains, 31 s / 230 s | P55 A `session_a.json` |
| §3.3 | id-map table | P48; P55 `D0-tokenizers.txt` |
| §4.2 | 29,933,568 params ↔ 119,801,528 bytes | `STACK.md` §3 |
| §4.4, §8.1 | drift: 0.741 → 0.989 | P43 `arm_email_475.json`; P55 A |
| §5.2 | C18 identity gate | P33 `lora_matrix.json`; P55 A `applied`; **Phase 0 P56: both members 3/3 `applied`, tools reachable, stop honoured** |
| §5.3 | `prompt_logprobs` shape | P55 A `preflight_target` |
| §5.4 | stop preflight; positional shim | P55 A attempts 1, 2 |
| §7.2 | $Q(T) < \max Q(E)$: 2 : 87, $p=0$ | P55 A `target_gate` |
| §8.2 | ceiling 0.989; commitment gradient | P55 A; P51 `desk_profile.json` |
| §9.3 | power at $n=351$ | `bar.resolvable` **[ran]** 2026-09-16 |
| §10.2 | 3.5 → 3.8 id space | P55 `D0-tokenizers.txt` |
| §10.5 D1 | vLLM resolves to 0.29.0 | P55 A boot log |
| §6.4 | **α, $\mathbb{E}[\tau]$, speed-up** | **not yet measured** |
| §7.4 | **the ordering verdict** | **not yet run** — blocked on a suite where §7.2 holds |
