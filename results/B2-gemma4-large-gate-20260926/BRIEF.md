# B2 — the large half of the pair on Gemma 4, sized for a Mac mini (pre-registered 2026-09-26)

**Why.** Milestones 3–4: per subdomain, a LoRA on a small model drafts and a LoRA on a large one verifies. The user,
2026-09-26: the large half must be **Gemma 4 12B or 26B** so the pair can later run on a Mac mini (Gemma 4 E4B + 12B in
4-bit is ~3 + ~7 GB). **12B dense first**: a LoRA on a dense model is what this repository already serves; the 26B-A4B is
a mixture of experts (4B active, all 26B resident) and whether vLLM applies a LoRA to its experts is a second unknown —
it is the alternative, bought only if 12B fails a gate. `training/harness/family.py`: LARGE = `gemma-4-12B-it`.

**Two preconditions, one A100 session, cheapest first (`training.harness.large_gate`):**

| gate | what | stops the pair if |
|---|---|---|
| **ids** | `tokenizer_compat` on E4B's and 12B's `tokenizer.json` | an id means two different things, or the base maps disagree → **NO PAIR on this family**; ids only the large can emit are reported as guaranteed rejections, not failures |
| **LoRA** | `lora_matrix`, control `Qwen2.5-3B-Instruct` (applied without rekey), subject `gemma-4-12B-it`: G1 in process, G2 served by vLLM | control invalid → **VOID**; G2 not applied → **NO LORA ON THE LARGE** (try 26B-A4B) |

**Not measured here, and next only if both pass:** milestone 3 proper — the wiki member trained on 12B from W9's corpus,
and whether large + LoRA beats small + LoRA on a band with room (W9's 3-hop band, or a deeper one; the small already
reaches 38/40 on the headline, so the headroom check comes first); then milestone 4 — the small's drafts accepted under
the large's verification, with and without the large's LoRA. A Mac runtime (vllm-metal, llama.cpp) is its own
substrate gate, after a pair exists on Colab. **Redesign counter: 0.**
