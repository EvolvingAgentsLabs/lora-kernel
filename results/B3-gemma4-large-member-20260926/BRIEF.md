# B3 — milestone 3: does the large half (Gemma 4 12B + LoRA) beat the small (E4B + LoRA) where the small misses? (pre-registered 2026-09-26)

**Why.** B2 **[ran]**: E4B and 12B share one id space and the 12B serves a LoRA applied. Milestone 3's gate: *large + LoRA
beats small + LoRA on the band that decides, paired*. On W9's own set the small member is already at 39/40 — no room — so
the band is built first.

**The band [ran, zero GPU] — `training/wiki/data/eval_hard.jsonl`.** 40 comparison questions on the evaluation world,
evaluation wording: `compare-lead` (20: two products → their suppliers → both lead times → name the faster supplier, 4
statements) and `compare-pack` (20: two products' packs → name the bigger). The answer is a name cited on the statement
that decides it; a reply that names the loser too is wrong (`check.never`). Oracle 40/40 verified through the real loop.
**The training corpus is W9's, unchanged** (reproduced byte for byte; comparisons are evaluation only), so both halves are
trained on the same corpus, as the design says, and measured on a band neither saw.

**Sessions, in order (queue `~/lora-kernel-queue/queue3_pair.sh`):**

| # | what | session |
|---|---|---|
| H | **headroom**: E4B bare walk and E4B + `wiki-walks-s1` (the released member) on the hard band; the member's walks on W9's set too, with spans, as B4's drafts | two runs, L4 |
| T | the wiki member trained on `gemma-4-12B-it` — W9's corpus and recipe, seed 0, `adapters/wiki12b-walks-s0` | A100 |
| S | 12B bare walk and 12B + LoRA on the hard band | A100 |

**Verdict — written first.** Credit as W9 (value right and citation verified), exact two-sided sign test on discordant pairs:

| check | required | reading if not |
|---|---|---|
| headroom — E4B + LoRA on the hard band | < 36/40 | **NO ROOM**: the small member already does comparisons; the large is not needed for accuracy here — B4 (latency) still runs |
| `12B+LoRA vs E4B+LoRA` on the hard band | improvement | tie → the large buys no accuracy on this band; regression → it loses |

Beside: 12B bare vs E4B bare (what size alone buys); by family. One seed each, said as such. **Ceiling:** 2 L4 + 2 A100.
