# E5 — the harness baseline with the engine counted (pre-registered 2026-09-28)

**Why.** The thesis review's H-C (approved as Phase 1): comparing tool-schema tokens against an uncached prompt inflates
what pruning saves, because with **prefix caching** a static block costs KV memory and a first-time TTFT, not compute per
request. Our claim to correct is P59's: the runtime's 54 tools pruned to the member's own, a block of "~7,956 tokens"
against "~77". The same review, and an external one, raise a second question: several LoRAs in one vLLM batch.

**What the design found before any GPU ran [ran, tokenizer only].** In the prompt our members are trained on, the gateway
renders **the request first and the tool block after it**, inside the user turn (`render_tools`). No two requests share the
block as a prefix, so prefix caching cannot reuse it as served today. With Gemma's tokenizer, the school member's pruned
first-turn prompt is **215 tokens**; OpenClaw's 54-tool block is **7,205 tokens**.

**What.** `training/harness/e5_baseline.py`, one vLLM 0.30 server on a Colab L4: `google/gemma-4-E4B-it` bf16 +
`school-s0` (M8) + `distributor-staff-s0` (M9), `--max-model-len 16384`, prefix caching on (vLLM's default).

| variant | the school member's first-turn prompt |
|---|---|
| `pruned` | the gateway's own: the request, then the role's tools. Production |
| `full` | the same, with OpenClaw's 54 tools (P59's recorded surface) rendered after the request, as trained |
| `full_first` | the same block **before** the request, where a prefix cache can reuse it. Latency only: the member never trained on that order |

**Per variant.** 16 distinct held-out turns, streamed, 64 tokens:
- median TTFT at batch 1 (the first request, which warms the shared system prompt, is excluded);
- tokens/s at batch 1, and throughput with 8 in flight;
- the server's own prefix-cache hit rate over the variant, $h = \mathrm{hits}/\mathrm{queries}$.

**Q3.** The 16 `pruned` prompts in flight at once, all on `school-s0`, then split half and half with `staff-s0`.

**Accuracy beside it.** The 70 held-out turns through the gateway, `pruned` against `full`. This is P59 reproduced on
today's member.

**Readings, written first (`e5_baseline.reading`).**

| question | measure | reading |
|---|---|---|
| **Q1** — does the 7,205-token block cost latency *as served*? | r₁ = TTFT(full) / TTFT(pruned) | r₁ ≥ 2 **COSTS**: pruning saves latency, not only accuracy · r₁ ≤ 1.2 **ABSORBED**: the savings are accuracy only · between: **PARTIAL** |
| **Q2** — would it be free as a prefix? | r₂ = TTFT(full_first) / TTFT(pruned) and $h$ | r₂ ≤ 1.2 with h ≥ 0.8 **FREE AS A PREFIX**: a format lever, which needs a corpus that puts tools first · else **NOT FREE** |
| **Q3** — do two LoRAs in one batch cost throughput? | tps(two) / tps(one) | ≥ 0.9 **NO MATERIAL CONTENTION** · else **CONTENTION** |

Whichever way Q1 falls, the docs that cite "~7,956 vs ~77 tokens" (OPENCLAW, FOUNDATIONS §4.4, FRAMEWORK) get the reading
beside the number.

**Instrument checks [ran, zero GPU].**
- The three surfaces are built from the same rows and share the system prompt.
- The block sits after the request in `pruned` and `full`, and before it in `full_first`.
- The prefix-cache counters are parsed across vLLM's metric names.
- If G1 fails for either member, the run stops before any number.

**Stopping condition.** One session, resumable across sessions (latency first, then Q3, then accuracy). No redesign after
the result. A cache-off server is the attribution arm, bought only if Q1 or Q2 needs it.

**Not in this run.** More than two adapters; batch sizes other than 1, 8 and 16; the 12B; the distributor member's accuracy.
