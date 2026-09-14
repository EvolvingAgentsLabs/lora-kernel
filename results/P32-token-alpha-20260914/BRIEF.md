# P32 — α at token level, and the gate that decides which base it runs on

**Pre-registered 2026-09-14.**

## The debt this pays

`CLAUDE.md` §3 has required "α with its `k`, beside the verified score of the same
run" since the project's first day, and **α at token level has never been computed**.
Constraint C3 says why: a frontier target does not share the base model's tokenizer,
so α had to be measured in characters — *"sound as a distillation score, unsound as a
speedup claim"*. §11 then replaced character α with semantic answer agreement after
measuring character α scoring 1/5 against one target and 4/5 against another **on the
same candidates**.

**A target from the same family shares the tokenizer, and the metric becomes
available.** It does not need speculative decoding to be supported: C1 records that at
T = 0 the accepted prefix **is** the longest common prefix with the target's greedy
continuation. Two models served, greedy, and α is a computation.

## Two candidate pairs, and the tokenizer was measured rather than assumed

| pair | tokenizer | ids identical on a probe | weights |
|---|--:|---|--:|
| `Qwen2.5-3B-Instruct` → `Qwen2.5-32B-Instruct-AWQ` | **151 665** | **yes** | 19.3 GB |
| `Qwen3.5-4B` → `Qwen3.6-27B` | **248 077** | **yes** | 55.6 GB (FP8: 30.9) |

`Qwen2.5-32B-Instruct` in bf16 is 65.5 GB and does not fit a 40 GB card; the AWQ
build does, beside a 3B draft. **α against a quantised target is α against that
target** — which is what production would speculate against — and the report will say
so rather than implying a bf16 number.

Two corrections came out of measuring instead of asserting: **"Qwen 2.6" does not
exist** (the newer family is 3.6), and `config.json`'s `vocab_size` is the *padded
embedding width* — 151936 against 152064 for two models whose tokenizers are
byte-identical. Comparing that field would have given the wrong answer twice.

## Why the second pair is not ruled out, and why I said it was

I wrote that the 3.5/3.6 family "is not servable with LoRA today". **That claim was
not supported.** It generalised P3's silent failure — vLLM **0.28.0**, `Qwen3.5-2B` —
into a property of a family. Reading vLLM **0.29.0** says otherwise:

    Qwen3_5ForCausalLMBase            ✅ SupportsLoRA   (declared)
    Qwen3_5ForConditionalGeneration   inherits Qwen3VLForConditionalGeneration
    Qwen3VLForConditionalGeneration   ✅ SupportsLoRA

and 0.29.0 has a **text-only** `Qwen3_5ForCausalLM` that 0.28.0 did not, which is the
class P3 tried to force and could not load.

**A declaration is necessary and not sufficient.** C18 is precisely the case where
vLLM accepted a `LoRARequest`, applied nothing, and said nothing. So this is settled
by the gate, not by reading code.

## The order

    1. the identity gate on `Qwen3.5-4B`      ~20 min, nothing trained
    2. P32 on whichever base passes            the α run
    3. P31's triage headroom                   unchanged, re-queued

**The gate runs first because it decides the base**, and training two adapters on
Qwen2.5 to discover afterwards that the stronger family served fine is the mistake
this project keeps paying for in the other direction.

## Falsification for the α run

- **α is measurable** if both models serve and the draft's greedy prefix can be
  compared to the target's on the same tokens.
- **The pair is void** if the two tokenizers disagree on any probe — checked offline
  and passed for both pairs, and re-checked in the run against what the servers
  actually emit.
- **The number means nothing without its `k`** and without the verified score of the
  same run beside it. That is §3 and it is the reason this step exists.
