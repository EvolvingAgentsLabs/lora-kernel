# The stack, exactly

Every model id, every adapter hyperparameter, every vLLM flag, with the run that
established it. **This page is an inventory, not an explanation** — the mechanisms
live in [`ARCHITECTURE.md`](ARCHITECTURE.md),
[`TECHNICAL-REFERENCE.md`](TECHNICAL-REFERENCE.md) and [`SERVING.md`](SERVING.md).

Values are read off the code and the artefacts, not remembered. Where a number is a
measurement it is **[ran]** with its run directory.

---

## 1. The base

| | |
|---|---|
| **model** | `Qwen/Qwen2.5-3B-Instruct` |
| vocabulary | **151,643** tokens + 22 added = 151,665 ids |
| embedding columns | 151,936 — **wider than the vocabulary**, so a mask over the extra columns is masking nothing |
| dtype served | `bfloat16` |
| dtype trained | `bfloat16` on Ampere or newer; `float16` on Turing |

**It is settled by measurement, not preference.** P33 read it against a control:
vLLM 0.29.0 loads a LoRA on `Qwen3.5-4B`, logs `Loaded new LoRA adapter`, and
**serves the base anyway** **[ran]** — the C18 identity gate. Gemma 4 is not a peft
base at all (`Gemma4ClippableLinear` is not `nn.Linear`). Run
`serve_openai --gate-only` against any candidate before proposing it.

**bf16 is checked, not assumed.** `torch.cuda.is_bf16_supported()` returns `True` on
a T4 because it counts *emulation*, and emulated bf16 has no kernel — every
generation dies. The check is compute capability ≥ 8.0 **[ran]** 2026-09-08.

## 2. The two targets, which are different jobs

| job | model | why this one |
|---|---|---|
| **fallback** — answers what the pool is measured to fail | `google/gemini-3.8-flash` | **66/90** on the fluids suite through the same client the local expert uses **[ran]** P41 |
| **speculative target** — verifies drafted tokens | `Qwen/Qwen2.5-32B-Instruct` | **byte-identical `tokenizer.json`** to the base, `c0382117ea329cdf…` **[ran]** P48 |

### Tokenizer compatibility, measured **[ran]** `results/P48-tokenizer-compat-20260916/`

| candidate target | vocab | ids match | usable as a speculative target |
|---|---:|---|---|
| `Qwen2.5-7B / 14B / 32B / 72B-Instruct` | 151,643 | yes | **yes — byte-identical file** |
| `Qwen3-14B`, `Qwen3-32B` | 151,643 | yes | yes, with 4 target-only ids (151665-151668: `<tool_response>`, `</tool_response>`, `<think>`, `</think>`) — **an available upgrade, not adopted**; see [`analysis/qwen3-migration.md`](analysis/qwen3-migration.md) |
| `Qwen3.5-27B`, `Qwen3.6-27B`, `Qwen3.8-27B` **with the Qwen 2.5 drafter** | **248,044** | **no** | **no — a different vocabulary; the 2.5 drafters cannot reach them** |
| **`Qwen3.8-27B` with a `Qwen3.5-2B / 4B` drafter — the goal** | 248,044 | yes | **yes** — identical map, 7 target-only audio/TTS ids, `<think>` shared **[ran]** `results/P55-graded-ranking-20260916/D0-tokenizers.txt` |

A frontier API can never be a speculative target: it returns no logprobs for a
**forced** continuation (C2) and does not share the tokenizer (C3). Check any new
pair with `training/harness/tokenizer_compat.py` before serving it.

## 3. The adapters

All of them are **LoRA on the same base**, identical hyperparameters, differing only
in corpus. Each is **119,801,528 bytes** of `adapter_model.safetensors` — about
114 MiB, against ~6 GB of base weights.

| adapter | corpus | rows | band | surface | what it scores |
|---|---|---:|---|---|---|
| `email-full` | `training/harness/data_ef/train.jsonl` | 598 | 0-3 steps | `thread_history`, `sender_stats`, `message` | **384/475 = 0.808**; on human messages **260/351 = 0.741** against a 0.655 bar, exact p **0.00036** **[ran]** P43 |
| `fluids-full` | `training/physics/data_ff/train.jsonl` | 600 | 6-9 steps | `calc`, `lookup`, `convert` | **11/90 = 0.122** against the frontier's 0.733 **[ran]** P41; below its band it over-solves **18 of 18** **[ran]** P45 |
| `kernel-mt` | `training/harness/data_mt/train.jsonl` | 600 | 2-4 steps | `calc`, `convert`, `lookup` | the protocol without the domain |
| `kernel-email` | `training/harness/data_ep/train.jsonl` | 600 | 1-1 steps | `thread_history`, `sender_stats`, `message` | the same protocol in the email vocabulary |
| `domain-mt` | `training/physics/data_mt/train.jsonl` | 600 | **0-0 steps** | **none** — calls nothing | the physics with the protocol removed — calls nothing, by design |

**Bands and surfaces are read off the corpora, not declared** — `tests/test_contract.py`
and `tests/test_prune.py` re-read every one, and doing that caught three of five bands
wrong on the first pass **[ran]**, then the surface *order* wrong on every corpus that
teaches one **[ran]** 2026-09-16. Declared in `POOL` via `training/harness/contract.py`.

**The order of a surface is part of it, where a corpus teaches one.** The three
corpora that carry an offered block list it in a fixed order in every prompt, and none
of those orders is alphabetical; rendering a pruned surface sorted would show the
adapter a listing it never read. The two `-mt` corpora carry no block, so their tags
are written alphabetically to say that no order was taught.

### LoRA hyperparameters — identical for every adapter

| | value | note |
|---|---|---|
| `r` | **16** | and `--max-lora-rank 16` at serve time must cover it |
| `lora_alpha` | **32** | |
| `lora_dropout` | 0.05 | |
| `bias` | `none` | |
| `task_type` | `CAUSAL_LM` | |
| `target_modules` | `q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj` | **all seven projections** |
| `modules_to_save` | `null` | **no embedding resize** — which is what makes a typed head's single-token values possible |
| peft | 0.20.0 | recorded in every `adapter_config.json` |

### Training run

| | value |
|---|---|
| trainer | `trl.SFTTrainer` / `SFTConfig` |
| epochs | 3 |
| learning rate | 2e-4 |
| batch × accumulation | 2 × 8 = effective 16 |
| max sequence length | 1536, **`packing=False`** — packing refills every sequence to the maximum and puts the token budget straight back |
| gradient checkpointing | on during training, **off before generation** — it disables the KV cache |
| seed | 0 |
| 4-bit | optional `--four-bit`: nf4, double quant, compute dtype = the bf16/fp16 decision above |

## 4. vLLM

**Version 0.29.0** **[ran]** — recorded in every run's `vllm.log`.

```
vllm serve Qwen/Qwen2.5-3B-Instruct \
    --dtype bfloat16 \
    --enable-lora \
    --max-lora-rank 16 \
    --max-loras <N> \
    --lora-modules name=path [name=path ...]
```

| flag | why |
|---|---|
| `--dtype bfloat16` | the fp16 path produced every false zero in S4 |
| `--max-lora-rank 16` | must be ≥ the largest `r` served, including a third party's |
| `--max-loras N` | how many may be **active concurrently** |
| `--lora-modules name=path` | the name is what an HTTP request's `model` field selects |

vLLM listens on **:8000**; `training/harness/openai_proxy.py` sits on **:8001** and
is what every client talks to — it appends the tool surface, serialises tag ↔
`tool_calls`, and announces routes as **shapes only, never content**.

> **`--max-loras` has only ever been 1 or 2 in this repository.** The largest pool
> served is `['email-full', 'fluids-full']` **[ran]** P41. S-LoRA reports thousands
> on one machine **[read]**; ours is untested above two, and it is the first real
> risk in any design that needs many.

### Hardware

| card | what it holds | used for |
|---|---|---|
| **L4** (24 GB) | the 3B plus one or two rank-16 adapters | every serving run so far |
| **A100** (40 GB) | the same, with room for a large target beside it | P3, P33, and what P4 will need |
| this laptop | **nothing** — arm64, 16 GB, vLLM does not run (C4) | writing and analysis only |

## 5. What is refused, and by what

| refusal | where | why |
|---|---|---|
| a `.bin` adapter | `third_party.py` | it is a pickle — code executes on load |
| a base mismatch | `third_party.py` | an adapter for another base is not a pool member |
| an adapter that loads without applying | the **C18 gate** in every runner | vLLM logs success and serves the base |
| a pool whose members do not differ from each other | `pool_run.py` | two names over one adapter is one expert |
| a typed member without verified single-token ids | `contract.py` | a typed contract whose values are not one token is a text contract wearing a label |
| a member with no declared band | `contract.py` | P45: an adapter served outside its band over-solves and nothing in the output says so |
| a credential on a command line | `tests/` | it lands in `ps` and in shell history |

## 6. Where each number came from

| claim | run |
|---|---|
| the base is the one vLLM applies adapters to | `results/P33-…` |
| a pool serves, members distinct, a stranger's adapter joins | `results/P40-…`, `results/P42-third-party-20260915/` |
| `email-full` clears its bar | `results/P43-openclaw-e2e-20260915/` |
| region routing 0.546 → 0.775 | `results/P41-routing-20260915/` |
| the depth floor a corpus teaches | `results/P45-ladder-sweep-20260915/` |
| the ranking ceiling | `results/P46-ranking-ceiling-20260916/` |
| tokenizer compatibility | `results/P48-tokenizer-compat-20260916/` |
