# C1 — concurrency on the `server` profile: four members on one L4 under load (pre-registered 2026-09-29)

**Why.** Multi-user traffic was never measured, and it is the last thing missing before real traffic. E5 saw a hint: two
LoRAs in one burst of 16 kept 0.88 of one adapter's throughput. Before anyone counts on a single card serving a service
of several experts, this has to be a curve, not a burst.

**What.** `training/harness/load_test.py`. One vLLM 0.30 server on a Colab L4, `google/gemma-4-E4B-it` bf16 carrying
four members: `school-s0` (M8), `upper-s0` (E6), `staff-s0` (M9) and `out-s0` (M10).
- K concurrent sessions, each sending R = 4 requests in sequence.
- Each request is a member's own first-turn prompt as its gateway renders it, streamed, 64 tokens, temperature 0.
- With A adapters in play, session $j$ uses adapter $j \bmod A$.

| cells (K sessions × A adapters) |
|---|
| 1×1 · 8×1 · 8×4 · 16×1 · 16×2 · 16×4 · 32×1 · 32×4 |

Per cell: aggregate generated tokens/s, time to first token p50/p95, request latency p50/p95, and errors (counted, never
raised).

**Guards.** Every member answers one request before any cell runs, or the run stops: an adapter the server cannot serve
would otherwise read as load.

**Reading, written first (`load_test.reading`).**
- **Contention:** $r_A = \mathrm{tps}(16\times 4)/\mathrm{tps}(16\times 1)$. At or above 0.8, **NO MATERIAL CONTENTION**;
  below it, **CONTENTION**.
- **Capacity:** the largest K whose four-adapter p95 TTFT stays under 2 s, reported without a bar.

**Stopping condition.** One session. The cells are fixed here; none is added after the result.

**Not in this run.** More than four adapters; the gateway's own overhead; multi-turn sessions (MT0 runs them); llama.cpp
on the user's machine, which is one user by design.
