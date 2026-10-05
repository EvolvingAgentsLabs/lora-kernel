# TAU2-T0 — reconnaissance of τ²-bench airline, before any model is scored

**Written 2026-10-05, before anything runs.** Phase T0 of the user's τ²-bench brief (2026-10-05): one domain (**airline**),
an API spend cap of **50 USD for T0 + T1 together**, and the teacher chosen by the user only after a table of terms of use.

## Why τ²-bench

Its reward is computed from the database's final state by code nobody here wrote — the external verifier milestone 5
asks for, which this project has never had. Its tasks are multi-turn, tool-using and policy-bound: the work the gateway
and the members are built for. The comparison stays internal (CLAUDE.md, workspace rules): teacher against member on the
same tasks and simulator; published leaderboard numbers are context **[read]**, never the baseline.

## What T0 does (no member is scored)

1. **Terms of use** for candidate teachers (frontier APIs and large open models): may their outputs train a model that is
   published? `docs/tau2/TEACHER-TERMS.md` **[read]**, for the user's decision.
2. **Install** `sierra-research/tau2-bench` outside the repository at a pinned commit, recorded in `MANIFEST`; run the
   `mock` domain end to end.
3. **`docs/tau2/RECON.md` [read]:** each domain's policy, tools and database; how the reward is computed; train/test
   splits and sizes (airline); the user simulator's configuration; the Gymnasium/RL interface; whether `banking_knowledge`
   exists.
4. **The format gap, named before anything is built:** τ² hands the agent tools as native tool calls and executes them
   itself; this project's members are trained on inline tags and break when served otherwise (11/90 against 90/90,
   CLAUDE.md §3). T0 specifies the adapter between the two and its no-loss check; serving Gemma 4 through vLLM to τ² is
   checked in T0's Colab step.

## Spend

Every API call is logged to `spend.jsonl` (model, tokens, USD) as it happens. T0's own cap is 10 USD of the 50. Above
it, stop and ask.

## Gate T0 (fixed here)

- **PASS** — the mock domain runs end to end; and on airline, a reference model's pass^1 reproduces a published score
  within its stated noise (or, if no published score fits the cap, the run is reported as not reproduced and the user
  decides).
- **FAIL** — the harness does not run, or the reference does not reproduce: the configuration is wrong; nothing is scored.

## Result

*(written after the run)*
