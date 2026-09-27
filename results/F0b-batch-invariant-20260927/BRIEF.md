# F0b — is speculative decoding's output identical, once the engine is deterministic? (pre-registered 2026-09-27)

**Why.** F0 **[ran]**: at temperature 0 the text with the MTP drafter equalled plain decoding's in only part of the cases
(8/16, 0/8, 4/16, 1/8), diverging at near-ties — and the same LoRA reloaded *without* a drafter also drifted. vLLM is not
deterministic across batch shapes unless its batch-invariant mode is on, so F0 could not tell a spec-decode fault from
numeric drift. vLLM's own LoRA × spec-decode test runs under `VLLM_BATCH_INVARIANT=1` for exactly this reason **[read]**.

**What.** `spec_lora_spike --batch-invariant --equality-only`, the same 12B FP8 + `wiki12b` on one L4, the same prompts,
batch 1, three servers in turn: `nospec`, **`nospec2` (the control — plain decoding again)**, `mtp`.

**Readings, written first.**

| control `nospec2` vs `nospec` | `mtp` vs `nospec` | reading |
|---|---|---|
| identical | identical | **spec decode with a LoRA preserves the output** — the brief's mandatory test passes |
| identical | differs | **a real spec-decode difference** — read where it diverges; not shippable as exact |
| differs | — | the engine is not deterministic even in this mode on this hardware/precision — the test cannot be run here |
| the server does not start | — | batch-invariant mode is not available for this GPU / FP8 / LoRA / drafter; recorded with its error |

Speed is not read in this run: batch-invariant kernels are slower by design. One L4 session.
