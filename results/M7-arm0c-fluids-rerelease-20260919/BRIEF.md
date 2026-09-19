# M7 arm 0c — `fluids-full` back through the gate, on the base the pool runs on (pre-registered 2026-09-19)

**Question (one unknown: the base).** `fluids-full` is `serve: out` in `route.REGIONS` on 11/90
**[ran]** P41, and that number was the serving path: inline, as its corpus taught, the same adapter is
**90/90** **[ran]** M7 arm 0b — on `Qwen2.5-3B-Instruct`. The pool has run on `Qwen3.5-4B` since
**[ran]** M1. **Retrained on the 4B from the same corpus with the same recipe, served in corpus mode
on the same 90 cases: does the member hold its recorded run, beat its bare base, and not lose to the
frontier?**

**Falsification.** Any of: G1 not applied (VOID); the member loses to its own 3B run (REGRESSION,
paired); the member only *ties* the bare 4B — the corpus bought nothing on this base, which is also
what a base at the ceiling looks like, so the base arm is scored first and read first; the member
loses to the frontier's recorded 66/90. The region then stays `out` and the 3B adapter stays the only
fluids member, in the `@v1` control pool.

**Arms, in the order bought.** (1) bare `Qwen3.5-4B`, corpus mode — the headroom check, bought first
because a base near 90 voids the rest; (2) `fluids-full-q35`. Recorded, zero GPU: the 3B member's
90/90 (`results/M7-arm0b-corpus-mode-20260919/corpus_mode.json`) and the frontier's 66/90
(`results/P41-routing-20260915/frontier_fluids.json`), both rescored under this suite's rule — the
test asserts they reproduce 90 and 66. **Not bought:** the proxy path, the `@v1` re-train on the 3B,
any knowledge base.

**Suite.** `suites.load("fluids")` — `multitool.generate(90, 616161)`, four families, 6–9-step
chains, handbook values drawn per case; paired by case id with both recorded arms. The test asserts
no evaluated statement occurs in the corpus. All 90 oracle chains pass this loop **[ran]** arm 0b.

**Models.** Base `Qwen/Qwen3.5-4B` (Hugging Face weights, bf16), served by **vLLM on Colab** — no API
provider is called in this run. Adapter: QLoRA, recipe `release_gate.RECIPE`, corpus
`training/physics/data_ff/train.jsonl` restored byte-for-byte from the tag `v0.1-foundations`
(600 rows, sha256 `a16883e0…`), trained by `training.harness.train_one`, which renames the tensors
for serving (D2). Thinking off in every render.

**Parameters.** Temperature 0, 200 tokens a step, up to 12 calls a chain, concurrency 8, results
written inline as `:.6g`. Verdict: three exact two-sided sign tests on discordant pairs,
$p = 2\sum_{k\le\min(b,c)}\binom{b+c}{k}2^{-(b+c)}$, different at $p<0.05$. Against 90/90 a tie means
at most five lost cases (0:5, $p=0.0625$); 0:6 is a regression — that is the absolute floor, 85/90.

**Cost.** Two Colab sessions, no dollars to a provider. Session A (A100, else L4): train only,
`--stop-after-training`, adapter fetched while the session lives (~45 min on an L4 by M1's clock).
Session B (L4): serve, G1, two arms × 90 chains (~15 min). Ceiling: **four sessions**.

**Abort rule.** Session A is killed if no `loss` line appears within 15 minutes of training start.
Session B is stopped after the base arm if the bare 4B scores ≥ 85/90: there is no headroom, the
member cannot *beat* it under this rule, and the right reading is "the base already does this", not
a failed member. vLLM is not deterministic at temperature 0: a verdict is read beside its pair, never
off a total.

**Redesign count: 0.** Stopping condition: a second reshaping of the verdict after the base arm is seen
ends the step as *not released*.

**What follows a RELEASED verdict (not in this run):** `releases/fluids-full@v2.json`; the member
back in `train_pool.POOL` with its contract; the proxy's per-member call cap read from the contract
(a fluids chain is 6–9 calls, the cap is 6); the region marked `local`; then the routing replay.
