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
