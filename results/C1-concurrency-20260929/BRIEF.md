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

## Result **[ran]** 2026-09-29 — **NO MATERIAL CONTENTION** (four adapters 1.03× one at K = 16); one L4 carries 32 sessions of four members at p95 TTFT 0.24 s, 0 errors

One L4 session, vLLM 0.30, E4B bf16 with four members. All four were reachable before any cell ran. `c1.json`,
`chain.log`.

| K sessions × A adapters | tok/s | TTFT p50 / p95 | latency p95 | errors |
|---|--:|--:|--:|--:|
| 1 × 1 | 22.7 | 0.10 / 0.11 s | 2.62 s | 0/4 |
| 8 × 1 | 135.1 | 0.17 / 0.19 s | 2.99 s | 0/32 |
| 8 × 4 | 139.4 | 0.17 / 0.21 s | 3.16 s | 0/32 |
| 16 × 1 | 269.7 | 0.15 / 0.16 s | 3.00 s | 0/64 |
| 16 × 2 | 263.2 | 0.16 / 0.21 s | 3.11 s | 0/64 |
| **16 × 4** | **278.6** | 0.16 / 0.17 s | 3.17 s | 0/64 |
| 32 × 1 | 490.8 | 0.17 / 0.27 s | 3.43 s | 0/128 |
| **32 × 4** | **504.3** | 0.18 / 0.24 s | 3.52 s | 0/128 |

**By the table written first:**
- **NO MATERIAL CONTENTION**: $r_A = 278.6/269.7 = 1.03$, against a bar of 0.8.
- **Capacity**: the largest K tested, 32, with p95 TTFT at 0.24 s, an eighth of the 2 s budget. The ceiling is above 32 and
  was not reached.

**Reading.**
1. On this server, mixing four members in one batch costs no throughput within the noise: 8×4, 16×4 and 32×4 are each at or
   above their one-adapter cell. E5's 0.88 came from one burst of 16 and sits inside the spread of a single measurement;
   it is superseded by these steady-load cells.
2. Throughput scales almost linearly with sessions: 22.7 → 135 → 270 → 500 tok/s for 1 → 8 → 16 → 32. At 32 sessions each
   request still starts in under a quarter of a second.
3. **Not measured:** more than four adapters; K beyond 32 (the ceiling); the gateway's own overhead; longer generations.
