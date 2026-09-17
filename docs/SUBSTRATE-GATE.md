# SUBSTRATE-GATE — Phase 0, specified

> *[Léeme en español](es/SUBSTRATE-GATE.md)*

Companion to `training/harness/verify_substrate.py`. The serving substrate — one
resident base, a pool of LoRAs that vLLM **actually applies**, tools reachable
through the proxy, stop strings honoured — is the layer everything in
[`EXPERIMENT_PLAN.md`](EXPERIMENT_PLAN.md) §0b stands on. It used to be checked by
ritual. This is the gate, and each row exists because a number already paid for it.

## The mathematics it guards

A member is a delta on the base's seven projections per block,
$y = xW + s\,(xA)B$ ([`FOUNDATIONS.md`](FOUNDATIONS.md) §4–§5). With $W$ frozen,
**a member whose served text never differs from the base's is serving $y = xW$** —
the delta term absent, whatever the engine logged. That is C18, and G1 is its test.

## Why each gate exists

| gate | validates | what it cost to learn |
|---|---|---|
| **P0** | `/v1/models` is the source of truth for members | four hand-kept lists have lagged the thing they tracked (`CLAUDE.md` §3) |
| **G1 (C18)** | the delta term is present: served text differs from the base on **≥ 2 of 3** probes | vLLM 0.29.0 loaded a LoRA on `Qwen3.5-4B`, logged it, served the base **[ran]** P33; the identity gate sees it in seconds |
| **G2** | the member reaches its tools **through the proxy** — no HTTP error, a tool call or an answer | P51's first arm: **240 of 240** requests HTTP 400 for missing parser flags, the progress line reading `correct 0 calls 0` — a broken run wearing a floor **[ran]** |
| **G3** | `stop` + `include_stop_str_in_output` honoured on a continuation the model cannot avoid | the corpus-mode loop (stop at `</tag>`, inject, continue) is impossible without it; the first preflight measured the model's phrasing instead **[ran]** P55 A attempt 1 |

## Design decisions

- **G1's threshold is 2 of 3, not 1 of 1.** At temperature 0 a short prompt can
  coincide across base and member without the delta being absent; a false NOT
  APPLIED costs a session. P55 A's gate saw **6 of 8** probes differ on a real
  adapter; 2 of 3 is the floor below which coincidence is no longer the explanation.
- **G2 is skipped with a notice when no `--proxy` is given.** It gates the *system*
  (server + proxy + tag ↔ `tool_calls` translation), not the server; running it
  against the upstream directly would prove nothing about the translation.
- **The verdict is read from the file, not the exit code.** Records are written
  before the summary and the summary is computed in a `try` (P47's rule); the exit
  code is for CI, `verdict.json` is for people.
- **It reuses what exists.** `serve_openai --gate-only` (P29) is the deeper identity
  comparison; `accept_rank.stop_check` is G3. This runner is the smoke version that
  runs every session and delegates the fine analysis to the existing gates when it
  fails.

## Where it runs

**Phase 0 is always GPU** — this laptop cannot serve vLLM (`CLAUDE.md` §0). It runs
on the card at the start of any session that serves the pool, through the chain:

    GPU=L4 RUN_DIR=results/P56-substrate-<date> MODULE=training.harness.verify_substrate \
      RESULTS_NAME=verdict.json MARGS="" SESSIONS=1 training/harness/chain_serve.sh

What runs on any machine, every time, is the static half: `tests/test_contract.py`
(the pool's declarations against its corpora) and `tests/test_verify_substrate.py`
(the verdict logic on every outcome a gate can have).

## First run — P56, 2026-09-17 **[ran]**

L4, both pool members carried in (P41's tarball), proxy started with `--prune`.
**`SUBSTRATE OK`**: P0 lists `email-full` and `fluids-full`; G1 **3/3** probes differ for each;
G2 `email-full` answers with **1 tool call**, `fluids-full` answers with none — the pruned
surface offers it no inbox tool, which is the right shape; G3 `stop_reason: '3'`.
`results/P56-substrate-20260917/verdict.json`.

## Its place in the plan

- **Phase 0 ✅ is the entry to every other phase.**
- **If vLLM or the base changes, Phase 0 re-runs before anything else** — the only
  permitted way to re-validate. If it breaks, the plan stops until it passes.
- **G1 is the same gate Phase 6 will run on `Qwen3.5-4B` (D2)** before D4 — the same
  script with another base and other members, not another script.
