# H1A — does the domain concentrate the routing of Gemma 4 26B-A4B? (flash line, Phase 1)

**Written 2026-10-04, after the instrument was frozen (code and tests) and before any trace exists.** Redesign counter: 0.

## What and why

The flash line asks whether a frozen MoE base can be read from slow storage with only part of its experts in RAM. The
Phase 0 analysis (`docs/flash-inference/00-analysis.md`) split the brief's H1 in two and put the cheap half first:
**H1a — on a domain's prompts the bare base uses a smaller, more stable set of experts than on general prompts, and a
cache preloaded per domain hits more** — nothing trained (§2); H1b (an adapter concentrates it further) only if H1a
passes. The review of two outside proposals (`docs/review/moe-distillation-and-spotlight.md`, §4 "The plan, in order", step 5)
puts this run on the list — the flash line's first step, and the data expert pruning by domain (§2.3) would need —
"only with the user's approval to resume the flash line". The user approved resuming it on 2026-10-04.

If the domain does not concentrate routing, all of H1 falls without anything trained (§2), and the line closes with its
document.

## Model and provider

- **`google/gemma-4-26B-A4B-it`**, bare, nothing trained: 30 layers, 128 experts per layer, top-8
  (`top_k_experts`) **[read]** spec §3. Thinking off, and the thought channel closed with an empty one
  (`<|channel>thought\n<channel|>`, the same prefill as `training/wiki/wiki_arm.py` `EMPTY_THOUGHT`: the larger Gemma 4
  models open it even with thinking off **[ran]** PAIR0 attempt 1). Greedy.
- **Hugging Face `transformers`**, not vLLM: a forward hook needs the graph in Python.
- **One Colab A100 (40 GB)** through `training/harness/chain_serve.sh`. The spec said "4-bit, ~15 GB, fits an L4 or an
  A100"; two facts read since then move it to the A100:
  - **bitsandbytes does not quantize Gemma 4's experts [read].** `BitsAndBytesConfig(load_in_4bit=True)` replaces
    `nn.Linear` modules only (`transformers/integrations/bitsandbytes.py`, `replace_with_bnb_linear`); Gemma 4 holds a
    layer's 128 experts as two 3-D `nn.Parameter`s (`Gemma4TextExperts.gate_up_proj [128, 1408, 2816]`,
    `down_proj [128, 2816, 704]`, `modeling_gemma4.py`), which stay bf16: $128 \times 30 \times 5.95\text{M} \times 2$ B
    ≈ 45.7 GB — no card on the account holds that. So `h1a.py` loads the model in bf16 **on the host** and quantizes each
    layer's experts itself, on the card: symmetric int4, one scale per group of 64 along the input dimension —
    $0.5 + 2/64 \approx 0.53$ bytes per parameter, the spec's "4 bits plus scales per group of 64" — dequantizing only the
    experts the router selected. Everything else stays bf16. On the card: ≈ 12 GB of experts + ≈ 6 GB of the rest.
  - **The host has to hold the bf16 load, ≈ 52 GB.** The A100 VM has ≈ 83 GB of RAM; the L4 VM ≈ 53 GB **[read]**
    Colab's machine shapes — too tight. Not a fallback here; an H100 would also do (refused on quota twice, PAIR1).
- **No `TRAINDEPS`**: nothing from bitsandbytes, peft or trl is imported. vLLM is installed by the chain's boot as always,
  and unused.

## Prompts — 150, frozen in `h1a.build_prompts` (tested: `tests/test_h1a.py`)

Thirty per domain, evenly spaced over each file (every family of a generated corpus, not its first block), served as
the member is served: every message before the first assistant turn (system + request + tool block).

| domain | source | prompts |
|---|---|--:|
| `wiki` | W9's distributor-wiki walks, `training/wiki/data/train.jsonl` (`distributor-wiki@v2`'s corpus) | 30 |
| `school` | the school's staff turns, `examples/school/data_turns/eval.jsonl` | 30 |
| `distributor` | the distributor's staff turns, `examples/distributor/data_turns/eval.jsonl` | 30 |
| `email` | email triage, `training/harness/data_ef/train.jsonl` (`email-full`'s corpus) | 30 |
| `general` | thirty requests written for this run (recipes, history, code, poems, travel, two in Spanish), no system prompt | 30 |

**Halves:** id `{domain}-{nn}`, even `nn` → half A (affinity is computed there), odd → half B (evaluated there):
15 + 15 per domain.

## What is traced

Prefill + **128 greedy decode steps** per prompt (`max_new_tokens = 129`: the last token generated is never fed back),
fewer when the model stops. A forward hook on every layer's **`Gemma4TextRouter`**
(`transformers.models.gemma4.modeling_gemma4`) records `top_k_index`, the third element of the router's own output —
its `torch.topk(router_probabilities, k=top_k_experts)` — not a re-derivation. The runner refuses to start unless it
hooked exactly `num_hidden_layers` routers, and a trace whose shape is not `[T, 30, 8]` is an error in the progress line.
Per prompt, as it lands: `h1a_traces/{domain}/{prompt_id}.npz` (`expert_ids` uint8 `[T, L, K]`, `token_idx`, `phase`
0 prefill / 1 decode), out of git; the results file after every prompt; the traces packed into `adapters_out.tgz` every
10 prompts, which the chain fetches while the session lives.

## Metrics — `experiments/flash_inference/h1a_metrics.py`, zero GPU

Per domain against general, on the decode phase (where flash is read), prefill beside:

- expert entropy per layer, $H_\ell = -\sum_e p_{\ell e}\log_2 p_{\ell e}$ (uniform: 7 bits);
- the fraction of a layer's experts covering 80 % of its activations;
- Jaccard between prompts, within the domain against between domains (general counts as another domain).
  **Weighted** (Ruzicka), $J_w(a,b) = \sum_k \min(a_k,b_k) / \sum_k \max(a_k,b_k)$ over (layer, expert) decode counts, is
  the one gated; plain set Jaccard is reported beside it. Why: 128 tokens choosing 8 of 128 leave an expert unused with
  probability $(1-8/128)^{128} = e^{-8.3} \approx 0.0003$ under uniform routing, so per-prompt expert *sets* are all
  ≈ everything and their Jaccard ≈ 1 for any pair — saturated by construction;
- consecutive-token reuse, $\frac1K|S_{t,\ell}\cap S_{t-1,\ell}|$;
- **a cache simulator** per half-B prompt, capacity $C = \lfloor G\cdot10^9 / 3.3\cdot10^6\rfloor$ experts (one expert
  ≈ 3.3 MB in 4 bits, spec §3): **4 GB → 1212, 8 GB → 2424, 12 GB → 3636** of 3840. Policies, fixed now:
  - **LRU** and **LFU** start empty; the request's prefill passes through the cache first, layer by layer, each expert
    its tokens touch once (LFU counts every token's use), *uncounted*; then every decode token's 8 × 30 experts, counted.
  - **affinity** (the gated one): the top-$C$ (layer, expert) pairs by decode count over the domain's half A, **pinned**;
    a miss is read from flash and not admitted. This is spec §4.3/§4.5's design — the gateway preloads the member's
    affinity before the prefill.
  - **affinity + LRU** (reported, not gated): the same preload, then managed as LRU through prefill and decode.
  - Hit rate, and bytes read per decode token $= \text{misses} \times 3.3\ \text{MB} / \text{tokens}$
    (none cached: $240 \times 3.3 \approx 0.8$ GB, spec §3).

## The gate — spec §5, verbatim, written before the run

> At 8 GB, on domain prompts:
> - the affinity-preloaded cache must hit **≥ 10 points more** than LRU without affinity;
> - the bytes read per token must fall **≥ 25 %**;
> - Jaccard within the domain must exceed Jaccard between domains.
>
> The comparison is prompt by prompt, with the repository's sign test. If it fails, **H1 is refuted** and the line
> closes with its document.

Operationally (`h1a_metrics.gate`): "domain prompts" = half B of `wiki`, `school`, `distributor`, `email`, pooled
(≈ 60); hit rates and bytes pooled over their decode tokens; the cache conditions also need affinity to beat LRU prompt
by prompt — exact two-sided sign test (`training/harness/bar.sign_test`), $p \le 0.05$, affinity ahead; the Jaccard
condition per domain prompt (all 120), $J_w$ within > between, same test.

| verdict | when |
|---|---|
| **PASSES** | all three conditions → H1b is next (spec §5) |
| **FALSIFIED** | any condition fails → H1 is refuted, the line closes with its document. If LRU already hits ≥ 90 %, the reading says *no headroom* — a cache needs no affinity |
| **VOID** | any domain with fewer than 10 evaluable half-B prompts (errors, no decode tokens); the hook not on 30 routers; a trace not `[T, 30, 8]` |

**Beside the gate, said now:** pinning can beat LRU on any stream, domain or not. General prompts get the same
treatment (affinity from general half A, evaluated on general half B). If the domains' affinity-minus-LRU gap is no
larger than general's, a PASS is read as the **policy's**, not the domain's (`gate.general_control.attributed_to`).

**Left out, said now:** an LRU warm from the previous request of the same domain (a server's steady state); a
cross-domain affinity (domain X's preload on domain Y's prompts); the real SSD's bandwidth (M3, the Mac mini). Prefill
reads are reported, not gated. A quantization-free reference trace (bf16 experts) is not bought: routing is read upstream
of the experts and a deployed flash base is 4-bit.

## Run

```bash
R=results/H1A-moe-routing-by-domain-20261004
# THE TRACES TRAVEL BETWEEN SESSIONS THROUGH THE CHAIN'S WEIGHTS CHANNEL, so SKIP_ADAPTERS is deliberately NOT set:
# the chain uploads $R/adapters.tgz (a symlink to the last adapters_out.tgz it fetched) and untars it on the VM, and the
# runner resumes every prompt whose record and trace are both there. Session 1 starts from an empty pack.
mkdir -p /tmp/h1a_empty/h1a_traces && tar czf $R/adapters_out.tgz -C /tmp/h1a_empty h1a_traces
ln -sf adapters_out.tgz $R/adapters.tgz
GPU=A100 BRANCH=h1a-20261004 RUN_DIR=$R MODULE=experiments.flash_inference.h1a \
  BASE=google/gemma-4-26B-A4B-it MARGS="--decode-tokens 128" RESULTS_NAME=h1a.json SESSIONS=2 \
  training/harness/chain_serve.sh
```

The code lives in `experiments/flash_inference/` (an underscore and an `__init__.py`: a hyphenated directory is not
importable as a module); `docs/flash-inference/` keeps the line's documents. The runner prints `[h1a] …` (in the chain's
peek, `tests/test_chain_scripts.py`), persists per prompt, resumes, and writes the gate and every metric into `h1a.json`
when all prompts are traced (`"finished"`). After: `tar xzf $R/adapters_out.tgz -C $R` and, to recompute zero-GPU,
`python -m experiments.flash_inference.h1a_metrics --traces $R/h1a_traces --records $R/h1a.json --out <file>`.

**Cost:** one A100 session, possibly two: the 52 GB download and load ≈ 10–15 min, the experts' quantization a few,
150 × (prefill + 128 steps) ≈ 25–35 min in eager `transformers` **[read]** estimate, not measured.

## Stopping condition

One run. The prompts, the halves, the policies and the gate do not change after the first trace exists. A VOID run is
repaired once (the instrument, never the gate) and rerun; a second VOID closes the run as not measurable on this stack.
**Abort early** if the first ten prompts show the hook on fewer than 30 routers, a prefill row count that differs from the
prompt's length (the runner raises it), or every decode step ending at once (a thought loop or an empty answer — read the
recorded `text`).

## Result *(written after the run)*
