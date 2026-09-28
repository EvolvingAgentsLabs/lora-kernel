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

**Attempt 1 [ran] 2026-09-28: stopped at G1, before any number.** `staff-s0` did not show on the generic probes
(`e5_attempt1_g1.json`). This is M9's known behaviour: a LoRA trained only on tool turns barely moves off-domain text.
The runner now checks that member by the rule it was released under (`staff_arm.g1`: the generic probes, then three of its
own domain requests under the same test). That is M9's redesign 1, applied here. E5's measurement is unchanged, and no
reading was seen.

## Result **[ran]** 2026-09-28 — Q1 **COSTS** (16.8×), Q2 **NOT FREE** as registered (but free wherever the whole prefix recurs), Q3 **CONTENTION** at the edge (0.88)

One L4 session (attempt 2), vLLM 0.30, E4B bf16. G1: `school-s0` applied on the generic probes, `staff-s0` on its domain
probes (M9's rule). `e5.json`, `chain.log`.

| variant | prompt tokens | TTFT b1 (median) | tok/s b1 | tok/s b8 | prefix hit $h$ |
|---|--:|--:|--:|--:|--:|
| `pruned` | 216 | **0.10 s** | 23.1 | 131.8 | 0.59 |
| `full` (54 tools after the request) | 7,395 | **1.70 s** | 12.4 | 107.9 | 0.51 |
| `full_first` (54 tools before the request) | 7,395 | **1.69 s** | 15.4 | 118.2 | 0.72 |

$h$ includes the batch-8 phase, which re-sends the same 16 prompts. The batch-1 TTFT counts each prompt once.

**By the table written first:**
- **Q1 = COSTS**: $r_1 = 16.8$.
- **Q2 = NOT FREE**: $r_2 = 16.7$.
- **Q3 = CONTENTION**: two adapters keep 0.88 of one adapter's throughput (196.9 vs 223.6 tok/s), just under 0.9. One burst
  of 16, so this sits near the noise; the median TTFT was *lower* with two adapters (0.41 vs 0.48 s).

**Accuracy, 70 held-out turns:** `pruned` **70/70**, `full` **39/70**. All 31 failures miss the check that the member made
its tool call. In 28 the member made **no call at all** and wrote a reply (often inventing the tool's result, e.g. an
`ERROR: permission denied` it never received). Only 1 of 31 called OpenClaw's tools, so this member does not copy tags off
the block as P59's did. It stops calling its own.

**Q2, read where it happens.** Per request in `full_first`:
- the first request of each role pays **1.7 s**;
- each request whose role already appeared (6 of 16: `it`, `cfo`, `dev`) has **0.09–0.11 s, equal to `pruned`**.

My variant put the block after the role's system prompt and the role's own tools, so the shared prefix was per role, and
the 16 turns mix roles. **The 7,205-token block is free once it sits inside a recurring prefix**; the registered median
cannot show it, because most requests were a role's first. Said as measured: the verdict stands as registered, and the
per-request data carry the finding.

**What it means for the claims.**
1. P59's "~7,956 vs ~77 tokens" is not only an accuracy point. **As served today, the unpruned block costs 17× the time
   to first token with prefix caching on**, because the member's corpus puts it after the request. The review's premise
   (a static block is free with a prefix cache) does not hold for this format. The docs citing the number now say so
   (OPENCLAW, FOUNDATIONS §4.4).
2. **Pruning stays the default for two independent reasons:** accuracy (70 → 39) and latency (0.10 → 1.70 s).
3. **A format lever exists**: tools before everything that varies, including the role's system prompt. The per-request data
   show that prefix is then free. It needs a corpus rendered that way and a retrained member; the pruned prompt is already
   cheap, so there is no reason to buy it now.
4. **Multi-LoRA:** 12 % of throughput at two adapters in one burst of 16. The reviewer's concern is real but small; a
   longer run at more adapters would size it.
