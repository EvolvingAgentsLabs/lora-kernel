# H1 — the workflow harness: a member that operates the session's memory by key (pre-registered 2026-09-29)

**Why.** The user's design (docs/review/harness-workflow-kv.md; approved 2026-09-29, all four decisions as proposed). The
member knows the domain's workflow, its tools and the keys of a short-term operational memory
(`examples/common/opmemory.py`). Each turn it reads one context line (the workflow's state and the key names, never the
values) and fetches or stores values with `get` / `put`, instead of carrying the conversation. MT0 **[ran]** sets the bar:
- with the conversation in the prompt, `out-s0` resolves 43/54 dependent turns;
- it loses free-text references: a claim about "that order" is filed without the order number, 8 of 10 times.

**What changes: one unknown.**
- `data_turns/train_harness.jsonl` is M10's `train_out.jsonl` **byte for byte** plus every turn of MT0's 300 training
  sessions, as the harness serves them: 627 rows (277 with `get`, 250 with `put`).
- Each row is written by an oracle through the real gateway with the memory and the role's workflow (TOML). A first turn
  makes its call and `put`s what later steps need; a dependent turn `get`s it and makes its call. A claim names the order
  fetched by key **and** what went wrong.
- Gate at zero GPU (`gate_harness.json`): the oracle gets every training and evaluation session right through the memory.
  MT0's suite gate (wording split, worlds apart, no self-contained dependent turn) still holds.
- The recipe is unchanged. The member is `wf-s0` (`staff_arm --train-seed 0 --corpus train_harness`, one L4).

**Arms**, on MT0's 60 held-out sessions (54 dependent turns), one L4, vLLM 0.30, both members served:

| arm | member | what the model reads on a turn |
|---|---|---|
| `history` | `out-s0` | MT0's naive baseline, rerun in the same session for a clean pair |
| `harness` | `wf-s0` | the context line + the request + the tool block (with `get` / `put`) |
| `harness-noblock` | `wf-s0` | the context line + the request: **no tool block**, the member trusted to know its tools |

**Verdict, written first (`session_arm.h1_reading`).**

| condition | bar |
|---|---|
| first turns right, every arm | ≥ 90 %, else **VOID** |
| dependent turns `history` gets right and `harness` wrong | $\ell \le 3$ |
| `harness` prompt tokens on turn 3 against turn 1 | $\bar p_3 \le 1.1\ \bar p_1$ |
| every dependent turn `harness` gets right | fetched its value by key: a `get` with a result |

All four → **PASSED**. `harness-noblock` passes if it loses no more than 3 dependent turns to `harness`. Beside the verdict:
customer service's claims, MT0's failure (2/10 with history), and whether the claim names the order.

**Stopping condition.** One seed, one scoring session. There is no redesign after the result. A FALSIFIED is recorded,
and the fallback in the design (the gateway writes the cache, §6.1) would be a new brief.

**Not in this run.** Sessions longer than three turns (the tracker domain, if the user approves it); the global cache
across sessions (built and tested at zero GPU, not trained on); OpenClaw live.

## Result **[ran]** 2026-09-29 — as written **VOID**; read per arm, **`harness` PASSED** (53/54 against 43/54) and **`harness-noblock` FALSIFIED** (0/60)

T (L4): `wf-s0` trained on `train_harness.jsonl`, 1,397 rows. A first attempt was paused at the user's request mid-training
(`T_attempt1_paused_by_user.log`) and relaunched from scratch. S (L4, vLLM 0.30): G1 applied for `out-s0` and `wf-s0`.
`h1.json`.

| | `history` (`out-s0`) | **`harness`** (`wf-s0`) | `harness-noblock` (`wf-s0`) |
|---|--:|--:|--:|
| first turns | 60/60 | 60/60 | **0/60** |
| dependent turns | 43/54 (MT0's number, reproduced) | **53/54** | 0/54 |
| — customer service ("a claim about that order") | 2/10 | **10/10** | 0/10 |
| — dispatch | 12/14 | **14/14** | — |
| — receiving / returns / purchasing | 10/10 · 10/10 · 9/10 | 10/10 · 10/10 · 9/10 | — |
| independent control | 10/10 | 10/10 | 0/10 |
| right dependent turns that fetched their value by key | — | **53/53** | — |
| prompt tokens by turn position, $\bar p_1, \bar p_2, \bar p_3$ | 345, 428, 394 | 745, 726, 710 | 251, 119, 82 |

**The verdict as written is VOID.** The BRIEF's first condition, "first turns ≥ 90 % in every arm, else VOID", is applied by
`h1_reading` across all three arms, and `harness-noblock`'s 0/60 voids the whole run. **That was a design error in the
instrument:** `harness-noblock` had its own pass condition, and a VOID was meant per arm. The error is recorded here and the
code is not changed after the result.

**Read per arm**, with `h1_reading` on `history` and `harness` alone (the same code, the no-block arm left out):
- **`harness` PASSED**: $\ell = 1 \le 3$ lost against `history`, 11 gained; $\bar p_3 = 710 \le 1.1\ \bar p_1$ (flat); every
  right dependent turn fetched its value by key (53/53).
- **`harness-noblock` FALSIFIED**: 0/60, and 0/54 lost against `harness` would have needed ≤ 3.

**Read where it happens.**
1. **The failure MT0 found is gone.** The claims now carry the order the member fetched by key and what went wrong
   (`order 58: The seal on that order was broken`): 10/10, where history got 2/10.
2. **The one `harness` miss** (purchasing): the member `get`s `lowest_item` and reorders `bottled water`, not the lowest
   item. The value it had stored in turn 1 was wrong; the fetch itself worked.
3. **Without the tool block the member calls no tool at all and states data it never read** ("According to the system:
   order 12 — picking, dock 3"). Trained only on prompts that carry the block, it does not know its tools without them.
   That half of the idea needs a corpus that drops the block. Production keeps the block, and the grounding filter would
   replace such a reply.
4. **Tokens.** The harness's per-turn prompt is flat and `history`'s grows: +24 % at turn 2, and it would keep growing.
   **In absolute terms the harness reads about twice as many prompt tokens per turn in these short sessions**, because a
   turn takes more generation steps (`get` → call → `put` → answer) and this counter re-adds the prompt at each step. In
   serving, the prefix cache reuses that shared prompt across a turn's steps; that was not measured here. The token
   advantage belongs to longer sessions, which this suite does not have (the tracker domain's would).

**Decision for the user:** whether to accept the per-arm reading as H1's verdict, with the instrument error recorded, or
keep the VOID and rerun `history` against `harness` alone under the same code (one L4 session).

## The user's decision (2026-09-29): **the per-arm reading stands — `harness` PASSED, `harness-noblock` FALSIFIED**

Offered both readings, the user chose the per-arm one. The as-written VOID is kept above as the record of an instrument
error: a first-turns rule meant to guard a comparison was applied across arms, so one failing arm voided two passing
ones. From H2 on, a VOID is per arm (`examples/tracker/session_arm.reading`).
