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

## Result **[ran]** 2026-09-27 — the engine is not deterministic even in batch-invariant mode here; the test cannot be run on an L4 in FP8

One L4, `VLLM_BATCH_INVARIANT=1` in all three servers (it starts with FP8, the LoRA and the MTP drafter; G1 applied in all).

| set | **control** — plain vs plain | MTP vs plain | on the prompts stable in the control, MTP equal | MTP speed-up b1 | α |
|---|--:|--:|--:|--:|--:|
| base / domain | 9/16 | 12/16 | 9 of 9 | 2.40× | 0.780 |
| base / general | 1/8 | 0/8 | 0 of 1 | 2.32× | 0.551 |
| LoRA / domain | 3/16 | 3/16 | 2 of 3 | 1.73× | 0.332 |
| LoRA / general | 0/8 | 0/8 | — | 2.02× | 0.424 |

**By the table written first: the control differs, so the engine is not deterministic even in this mode on this hardware and
precision** (FP8 on an L4, across server restarts), and exact output identity **cannot be tested here**. What the run does
say: spec decode's disagreement with plain decoding is **the same size as plain decoding's disagreement with itself**
(12/16 vs 9/16, 3/16 vs 3/16), and where the control is stable MTP matches it 11 of 13 — F0's divergences read as ordinary
numeric drift, not a spec-decode fault, but that is a reading, not the proof. The proof needs bf16 on a GPU where
batch-invariant mode is built for (A100/H100 — refused over quota today). Speed-ups and acceptance reproduce F0's
(1.73× with the LoRA on its domain, α 0.33).
