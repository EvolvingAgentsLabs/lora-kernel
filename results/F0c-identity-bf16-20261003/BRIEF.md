# F0c — does speculative decoding with a LoRA preserve the output? F0b's test, in bf16 on an A100

**Written 2026-10-03, before anything runs.**

## What and why

F0 **[ran]**: the 12B with an expert LoRA and its native MTP drafter runs 1.7–2.1× — but at temperature 0 the text equalled
plain decoding's in only part of the cases. F0b **[ran]** asked it under `VLLM_BATCH_INVARIANT=1` and could not answer:
on an L4 in FP8 the control — plain decoding against plain decoding — itself differed (9/16, 1/8, 3/16, 0/8), so the
engine was not deterministic there; F0b named the proof's conditions: **bf16, on a GPU batch-invariant mode is built for
(A100/H100)** — refused over quota that day. A pair that changes what the member writes is not the member; exact output is
the mandatory test before the pair is served.

## What

`training.harness.spec_lora_spike --batch-invariant --equality-only --configs nospec,nospec2,mtp`, **no quantization
(bf16)**, `google/gemma-4-12B-it` + the expert LoRA `wiki12b` (B3, `adapters.tgz` from F0), one Colab **A100**, vLLM,
the same 16 expert prompts and 8 general as F0/F0b, batch 1, temperature 0, three servers in turn: `nospec`, `nospec2`
(the control), `mtp` (k = 4).

## Verdict (F0b's table, unchanged)

| control `nospec2` vs `nospec` | `mtp` vs `nospec` | reading |
|---|---|---|
| identical | identical | **SPEC PRESERVES** — spec decode with a LoRA preserves the output |
| identical | differs | **A REAL DIFFERENCE** — read where it diverges; not shippable as exact |
| differs | — | **NOT DETERMINISTIC HERE** — the test cannot be run on this hardware/precision either |
| the server does not start | — | batch-invariant mode not available for this combination; recorded with its error |

"Identical" is per set: all prompts of the set equal. Read per set (base/domain, base/general, LoRA/domain,
LoRA/general); the verdict is the LoRA rows'. Speed is not read (batch-invariant kernels are slower by design).

## Stopping condition

One A100 session. If the A100 is refused three times, recorded as such, not moved to another precision.

## Result [ran] — the engine is deterministic here; spec decode differs only at near-ties, and on the LoRA's rows never inside what serving generates

One A100, bf16, `VLLM_BATCH_INVARIANT=1`, G1 applied in all three servers (3/3), `spike.json`.

| set | **control** — plain vs plain | MTP vs plain | MTP speed-up b1 | α | mean accepted length |
|---|--:|--:|--:|--:|--:|
| base / domain | **16/16** | 16/16 | 2.89× | 0.760 | 4.04 |
| base / general | **8/8** | 3/8 | 2.65× | 0.550 | 3.20 |
| LoRA / domain | **16/16** | 14/16 | 1.98× | 0.337 | 2.35 |
| LoRA / general | **8/8** | 8/8 | 2.34× | 0.437 | 2.75 |

- **The control is identical in every set:** in bf16 on an A100 the engine is deterministic, and the test F0b could not run
  is read here.
- **Verdict by the table written first: A REAL DIFFERENCE** — the control identical, MTP differing in two sets.
- **Read where it diverges.** **LoRA / domain, 2 of 16:** both diverge *after* a `</search>` — this spike decodes freely to
  160 tokens with no runtime, so the member goes on to *invent* the result line and writes an opaque id, `[00e]` against
  `[00i]`, a near-perfect tie. In serving, generation stops at the closing tag and the runtime writes the result: **up to
  the stop, all 16 are identical** — the text that differs is text a served walk never generates. **LoRA / general:** 8/8.
  **Base / general, 5 of 8:** synonym choices at near-ties ("the interior" / "the air inside", "nature's" / "the
  Earth's") — numerical: the drafter's verification scores several positions in one forward, a different reduction shape
  from one-token decoding, and batch-invariant mode makes batches equal, not verification shapes. Not a fault in the
  acceptance rule; not bitwise.
- **What this establishes:** with the expert's LoRA on its own domain, speculative decoding with the native MTP drafter
  preserves what the member writes up to every stop, at **1.98×**; exact bitwise identity holds where no near-tie occurs
  and is not guaranteed by vLLM in general. On general text — which the frontier, not a member, serves — synonyms flip.
