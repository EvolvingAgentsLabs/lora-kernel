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

## The user's decisions (2026-10-05, on the terms table and the recon)

1. **Teacher and user simulator: Gemma 4 31B, self-hosted** (Apache 2.0 from teacher to base to adapter; the simulator's
   turns end up in the trajectories too, so it must be as clean as the teacher — `docs/tau2/TEACHER-TERMS.md`).
2. **Gate T0, option (b):** no published score is reproduced (every published airline run used a GPT user simulator; this
   project holds only an Anthropic key, and comparisons stay internal by the workspace's rule); instead the local grader
   is checked against the published trajectories, at no cost.
3. **The 26B line closes** (TEACH0 blocked by the serving engine; PAIR0, PAIR1 and Google's own card put the large half
   level with or behind the small one).

## Result [ran] — T0 PASSES (option b)

- **Install:** `tau2-bench` at commit `5bfa7e3` (v1.0.1-47), Python 3.12, `uv sync` (+ `websockets`, an upstream gap) —
  `MANIFEST`.
- **Mock, end to end:** pass^1 0.667 on 3 tasks (haiku 4.5 as agent and simulator); the one 0 was the simulator looping
  200 messages instead of ending the transfer — every later run carries a `--max-steps` cap. **Spend: 0.97 USD.**
- **The grader, checked [ran]:** `tau2 evaluate-trajs` re-graded the four airline trajectory files shipped with τ²
  (claude-3-7-sonnet, gpt-4.1, gpt-4.1-mini, o4-mini; 4 trials × 50 tasks each) — **800 of 800 simulations get the same
  reward** as recorded (means 0.500, 0.560, 0.505, 0.590, unchanged). The local reward is τ²'s reward.
- **Recon [read]:** `docs/tau2/RECON.md` — airline: 50 tasks, an official split of **30 train / 20 test**, 14 tools (6
  writes), reward = DB-state hash × communicated-info check (no judge model), any early stop scores 0; native function
  calling through litellm; a vLLM endpoint plugs in as `openai/<name>` with `api_base`.
- **The format gap, measured offline [ran]:** the repo's tag serializer round-trips only 1,345 of 1,587 shipped airline
  tool calls, and loses **220 of 320 writes** (nested arrays, integers as strings, values cut at commas, empty-argument
  calls); a JSON-body tag round-trips **1,587 / 1,587**. The shim is specified in RECON.md; it is built and checked (no
  loss, both ways) before any member is scored.

## The shim, built and checked offline (2026-10-05) [ran]

- **Built:** `examples/tau2/shim.py`, RECON §3's spec: τ²'s system prompt kept (a member prompt prepended), the repo's tag
  block (arity on) plus one domain-free sentence on JSON bodies, history folded inline (`<tag>…</tag>= result`, the open
  turn continued as corpus mode does), `k=v` only for plain strings, positional for one required argument, JSON otherwise,
  strings coerced to the schema's types, one call per turn with a conversation-unique id, no round-trip cap, ≥ 512 tokens,
  upstream vLLM `/v1/completions` with `accept_rank`'s stop handling. `openai_proxy.py` untouched.
- **G-shim-1 PASS** (`g_shim_1.json`, `examples/tau2/check_shim.py`, 0 model calls): all four shipped airline files,
  800 conversations — **5,829 / 5,829 tool calls** identical in name, arguments and argument types, both ways (1,008 writes;
  703 need the JSON body); the repo's `k=v` serializer on the same calls, as the control that must fail, keeps 4,960 /
  5,829; **800 / 800 conversations** fold and unfold to the same calls, results (byte-identical) and user turns (assistant
  text up to surrounding whitespace, the one normalisation), plus 647 mid-turn cuts; 40 / 40 folded prompts survive
  Gemma 4 E4B's own chat template verbatim; τ²'s own `generate` → the shim over HTTP → a scripted member → the airline
  environment executes 4 / 4 calls with the schema's types (`amount=50` arrives as the integer 50).
- **G-shim-3 PASS** (`tests/test_tau2_shim.py`): six requests recorded from τ²'s own `LLMAgent` through litellm
  (`examples/tau2/capture_request.py`, a local recorder, 0 model calls) carry exactly `model, messages, tools,
  tool_choice, temperature`; no `nl_assertion`, scenario instruction or gold action list reaches the shim's request or
  the prompt it forwards, and a gold value appears only where the conversation itself said it; a planted leak is caught;
  the forwarded prompt is a function of `messages` and `tools` alone; `shim.py` imports nothing from τ² and names none of
  the grading fields (read from its AST).
- **Still owed before a member is scored:** G-shim-2, the same path against a served model on Colab (RECON §3).
