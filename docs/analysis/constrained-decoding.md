# Constrained decoding: what to keep, and why it is not what we need

**Analysis, 2026-09-16.** Prompted by
[harshatheg/Qwen-2.5-1B-RLCD](https://huggingface.co/harshatheg/Qwen-2.5-1B-RLCD).
Read from the source, not the card. **Nothing implemented** — the reason is §4.

## 1. The model is not a model

The repository contains **no weights**: no `.safetensors`, no `config.json`, no
tokenizer. It is 642 lines of inference engine (MLX and torch), a web UI and four
preset JSON schemas, published under a model name. The `base_model:finetune:` tag is
author metadata; nothing was fine-tuned because there is nothing to fine-tune with.
`downloads: 0` **[read]** 2026-09-16.

Even with weights it would be **Qwen2.5-1.5B full**, not a LoRA on our 3B base, so it
could not be a pool member. That question is closed and cost five minutes.

## 2. What the engine actually does

Per schema field: build a prompt suffix, run **one batched forward pass** sharing the
prefix KV cache across fields, take the logits at the decision position, **slice them
to that field's candidate token ids**, softmax over just those, return the argmax as
the value and its mass as the confidence.

    field_logits = suffix_out[i, decision_idx, :]
    scores  = [field_logits[tid] for tid in cand_tokens]
    probs   = softmax(scores / temperature)

That is a restricted softmax over verified candidate tokens, plus a shared-prefix KV
cache, plus field batching.

## 3. It fixes a problem we do not have

**Restricting the softmax removes invalid answers. It adds no information.** The
relative mass between two candidates is identical before and after discarding the
rest of the vocabulary — so schema validity improves and *ranking* does not.

And schema validity is not our problem:

| | n | unparseable answers |
|---|---:|---:|
| `email-full` | 475 | **0** |
| base | 475 | **0** |

**[ran]** P44. Our refusals are tool-call arity, never an out-of-enum value.

**What we do have** is P46: the confidence does not order the errors, and on the full
inbox both arms are already at the information ceiling — room 0.030 and 0.007
**[ran]**. A narrower softmax cannot move a number that is bounded by what the input
contains.

### And "calibrated" is a name here, not a measurement

The engine returns `mode: "parallel_constrained_calibrated"` and
`has_calibrated_probabilities: True`. **There is no calibration in the code**: no
temperature fitting, no reliability curve, no validation set, and ECE is never
computed. `temperature` is a free parameter defaulting to 1.0.

This is the pattern already documented in [`typed-adapters.md`](typed-adapters.md) —
a confidence asserted rather than measured — and P44 falsified exactly that on our own
model: **0.999 mean confidence at 0.345 accuracy** **[ran]**.

The benchmark is arithmetic rather than a finding: `speedup = sequential / parallel`
against a baseline that generates field by field. Parallelising 28 independent fields
over a shared prefix is ~7× because there are 28 fields. Real as engineering, silent
about quality.

## 4. What is worth keeping

**One pattern, recorded for when there is a router to put it in.** Not built now,
because there is no consumer and new surface area is the expensive kind of progress.

> **k typed questions about one context cost one prefill, not k.** Prefill the shared
> context once, repeat the KV cache across k branches, run one batched forward, and
> slice each branch's logits to its own candidate ids.

The routing questions this project already has are exactly that shape and share a
context: *which expert?*, *which tools of the 54?*, *is this important?* When the
router exists, this is how it asks all of them at once — and it is the same economy
the cross-model KV-cache reuse work reports at 58× for multi-adapter pipelines
([`composition-and-speculative.md`](composition-and-speculative.md)).

**And one confirmation.** The engine cannot run without candidate **token ids** per
field, which is independent evidence that `value_tokens` belongs in the contract we
merged rather than being a convenience. `training/harness/contract.py` already
refuses a typed member without them.

## 5. The warning from our own history

This organisation has built constrained decoding twice, and neither run confirmed the
thesis:

- **`llm_os` IR v0.2 — falsified.** Prose beat the assembler under the same oracle;
  the surviving finding was that verifier severity is a dial nobody chooses and it
  moves every number.
- **`capability-kernel` — the mask did not make injection harmless.** An injection
  produced a wrong write anyway.

So *"constrained decoding helps"* is not an open question here. It is one this
workspace has tested twice and not confirmed, which is a reason to keep the pattern
and refuse the thesis.

## 6. Verdict

**Do not download it, do not use it.** Keep the shared-prefill pattern for the router,
keep the confirmation about `value_tokens`, and carry the "calibrated without
calibration" example into the file that already tracks that failure mode.
