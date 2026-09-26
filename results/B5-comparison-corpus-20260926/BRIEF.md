# B5 — milestone 3, second and last look: does a corpus that SHOWS comparisons teach them, and then does the 12B beat the E4B? (pre-registered 2026-09-26)

**Why.** B3 **[ran]**: on the comparison band both trained halves walk, cite, and fail the comparison itself (E4B + LoRA
10/40, 12B + LoRA 9/40, a tie) — and W9's corpus never showed one comparison. *A corpus with one difficulty teaches a
floor* (CLAUDE.md §3). Milestone 3 cannot be read until both halves are taught the band they are measured on.

**The corpus [ran, zero GPU] — `training/wiki/data/train_cmp.jsonl`.** W9's 600 rows **byte for byte** (sha `562786…`,
reproduced) plus **128 comparison walks** — `compare-lead` and `compare-pack`, two each per training world (32 worlds, not
the evaluation world), *train* wording disjoint from the band's. One unknown: the comparisons. Gate `gate_cmp.json`
PASSED against `eval.jsonl` **and** `eval_hard.jsonl`: G1–G5 all 0, the oracle's 128 walks verified. G4 on a choice reads
what decides it — the deciding statement's numbers, the offered names struck — because a choice offers both names by
design (`corpus.asked`; the leak still fails, `tests/test_wiki.py`).

**Recipe and seeds.** As W9 (`release_gate.RECIPE`); E4B seed 1 (the released member's seed, so the pair against it shares
everything but the corpus), 12B seed 0 (B3's). One seed each, said as such.

**Sessions, in order (queue `~/lora-kernel-queue/queue4_cmp.sh`), each stops the queue if it fails:**

| # | what | session |
|---|---|---|
| T1 | E4B trained on `train_cmp` → `adapters/wiki-cmp-walks-s1` | A100 |
| S1 | E4B + cmp-LoRA on the hard band (40) | L4 |
| G1 | E4B + cmp-LoRA on W9's set (67) — the guard | L4 |
| — | **stop here if E4B + cmp-LoRA ≥ 36/40** (no room left for the large) | — |
| T2 | 12B trained on `train_cmp` → `adapters/wiki12b-cmp-walks-s0` | A100 |
| S2 | 12B + cmp-LoRA on the hard band | A100 |

**Verdict — written first.** Credit as W9 (value right and citation verified); exact two-sided sign test on discordant pairs.

| check | required | reading if not |
|---|---|---|
| E4B cmp vs E4B released (`withlib-s1`, B3: 10/40) on the hard band | improvement | tie → **showing comparisons does not teach them at this size**; the 12B still runs (size may be what is missing) |
| guard: E4B cmp on W9's headline (released: 39/40) | not a regression | regression → the comparisons cost the trained skill; the corpus is not releasable |
| E4B cmp on the hard band | < 36/40 | **NO ROOM**: the small half does comparisons once taught — milestone 3 closes *the large buys no accuracy here*; T2/S2 not bought |
| **`12B cmp vs E4B cmp` on the hard band** | **improvement** | tie → **milestone 3 closes negative on this family**: the large half is a verifier (B4), not a more accurate member; regression → it loses |

**Stopping condition.** This is the band's second corpus. Whatever S2 says closes milestone 3 on Gemma E4B/12B: no third
corpus, no other band, no seed shopping. Beside: by family; the misses read as B3's were (cited-and-wrong vs uncited).
**Ceiling:** 2 A100 training + 1 A100 scoring + 2 L4.

## Result **[ran]** 2026-09-26 · NO ROOM — the small half compares once shown comparisons; milestone 3 closes: on this band the large buys no accuracy

T1 (A100): `wiki-cmp-walks-s1`, corpus `train_cmp.jsonl` sha `7b307d53…` (reproduced locally, byte for byte), adapter
`d4d91ea4…`. S1 and G1 (L4): G1 identity gate applied on both.

| E4B + LoRA | hard band (40) | compare-lead | compare-pack | W9 headline (40) | W9 all (67) |
|---|--:|--:|--:|--:|--:|
| released, W9's corpus (B3, B1) | 10 | 6 | 4 | 39 | 63 |
| **comparison corpus** | **37** | 17 | **20** | **39** | **63** |

- **E4B cmp vs released on the hard band: 28 : 1, $p = 1.1\times10^{-7}$ — improvement.** Showing comparisons teaches them.
- **Guard: 0 : 0 on W9's set** — the same 4 misses on both (`terms-1`, `order-approver-0/1`, `invoice-ext-2`). The
  comparisons cost nothing.
- **37 ≥ 36: NO ROOM** — as written, T2/S2 were not bought. The 3 misses are all `compare-lead`: a supplier named and the
  lead-time statement of another cited (`the cited statement does not hold the value`).

**Reading.** B3's tie was the corpus: both halves failed a skill neither was shown. Taught it, the E4B does 37/40, so on
this band a 12B has at most 3 cases to win — milestone 3 closes *the large half buys no accuracy here*; on this family its
job is the verifier of the pair (B4). One seed, said as such. **What follows:** `distributor-wiki@v2` — the same member
plus comparisons, through the gate on both sets (`releases/distributor-wiki@v2.json`). Not measured: B4's acceptance with
this member's drafts, which would need a 12B trained on `train_cmp`.
