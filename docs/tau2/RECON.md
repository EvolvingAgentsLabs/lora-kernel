# τ²-bench reconnaissance (T0 steps 2–4)

**Written 2026-10-05** for `results/TAU2-T0-recon-20261005/BRIEF.md`. Every claim is **[read]** from
`sierra-research/tau2-bench` at the pinned commit unless marked **[ran]**; paths below are relative to
that checkout (`~/evolvingagents/tau2-bench`). No member was scored and no model ran locally.

| | |
|---|---|
| commit | `5bfa7e37b36656b37dc6d022156be6563c1007f3` (2026-09-28, `git describe` v1.0.1-47) |
| package | `tau2` 1.0.1 (`pyproject.toml`), Python 3.12.13, litellm 1.81.11, gymnasium 1.2.2 |
| full record | `results/TAU2-T0-recon-20261005/MANIFEST` |

**Status, 2026-10-05, after the user's decisions (`results/TAU2-T0-recon-20261005/BRIEF.md`).** T0 **passes by option (b)**:
no published score was reproduced; instead `tau2 evaluate-trajs` re-graded the four airline trajectory files shipped with
τ² and **800 of 800 simulations get the recorded reward** [ran], so the local grader is τ²'s grader. The teacher and the
user simulator are **Gemma 4 31B, self-hosted** (`docs/tau2/TEACHER-TERMS.md`). The sections below were written before
those decisions and are kept as written; where one says "the user decides" or "was not run", that is the state of the
reconnaissance, not of the plan.

## 0. Install and mock run [ran]

- The README asks for `uv sync` and Python `>=3.12,<3.14` (`README.md:37`, `:58–73`). Installed into its own
  `.venv` (python3.12) with `uv sync --extra gym --extra dev`, which follows `uv.lock`.
- **The core install does not import.** `tau2` fails with `ModuleNotFoundError: websockets`: the import chain
  `data_model/simulation.py:62` → `voice/audio_native/openai/provider.py:12` needs `websockets`, which only
  the `voice` extra installs. Fixed by `uv pip install websockets` (recorded in the MANIFEST). On Colab, do the
  same or install `--extra voice`.
- **Mock, haiku 4.5 as agent and as user simulator, 3 tasks × 1 trial:** `create_task_1` 1.0,
  `update_task_1` 1.0, `impossible_task_1` 0.0 → **pass^1 = 0.667**. Command in the MANIFEST, results in
  `results/TAU2-T0-recon-20261005/mock_results.json`. The harness runs from start to finish.
- **The one failure was the simulator's, and it is what costs money.** In `impossible_task_1` the agent
  correctly called `transfer_to_human_agents`; the haiku *user* never sent `###TRANSFER###`
  (`data/tau2/user_simulator/simulation_guidelines.md:15`) and the two models thanked each other for 200
  messages until `max_steps`. Any termination other than agent/user stop scores 0
  (`src/tau2/evaluator/evaluator.py:115–127`). That one conversation cost **0.96 USD of the run's 0.97**.
  Lesson for T1: a weak user simulator's failure looks like an agent failure and is paid for by the step. Cap
  `--max-steps` (or `--timeout`) on any haiku-simulated run, and say in the report that you did.

## 1. Domains

Registered (`src/tau2/registry.py`; printed by `tau2 run --help`): **`mock`, `airline`, `retail`, `telecom`,
`telecom-workflow`, `banking_knowledge`**. Task sets: `mock`, `airline`, `retail`, `telecom_full`,
`telecom_small`, `telecom`, `telecom-workflow`, `banking_knowledge`.

| domain | tasks (`tasks.json`) | splits (`split_tasks.json`) |
|---|---|---|
| mock | 10 | base 10 |
| airline | **50** | **train 30 / test 20 / base 50** |
| retail | 114 | train 74 / test 40 / base 114 |
| telecom | `tasks.json` 2285 | small 20 / train 74 / test 40 / full 2285 / base 114 |
| banking_knowledge | 97 (+698 documents) | no split file |

**`banking_knowledge` exists.** It is a retrieval domain that needs `--extra knowledge` and a
`--retrieval-config` (`README.md:28`, `:70`; `src/tau2/knowledge/README.md`). Its grading changed in v1.0.1, and
results from before that version are not comparable (`README.md:24`).

## 2. Airline

### Policy
`data/tau2/domains/airline/policy.md`, 1,313 words. Sections: Domain Basic (User / Flight / Reservation), Book
flight, Modify flight, Cancel flight, Refunds and Compensation (`grep '^#'`). Fixed clock: "The current time is
2024-05-15 15:00:00 EST" (`policy.md:3`; also `AirlineTools._get_datetime`, `src/tau2/domains/airline/tools.py:100–102`).
Rules that touch the format gap: get an explicit "yes" before any write (`policy.md:7`), and "only make one tool
call at a time … not respond to the user simultaneously" (`policy.md:11`). The rule is not enforced unless
`--enforce-communication-protocol` is passed.

### Tools (14) — `src/tau2/domains/airline/tools.py`, type from `@is_tool(ToolType.…)`

| tool | type | args (JSON-schema type) | line |
|---|---|---|---|
| `book_reservation` | WRITE | user_id, origin, destination, flight_type, cabin (str); **flights, passengers, payment_methods (array of objects)**; **total_baggages, nonfree_baggages (int)**; insurance (str) | 186 |
| `calculate` | GENERIC | expression | 321 |
| `cancel_reservation` | WRITE | reservation_id | 339 |
| `get_reservation_details` | READ | reservation_id | 371 |
| `get_user_details` | READ | user_id | 387 |
| `list_all_airports` | READ | — | 403 |
| `search_direct_flight` | READ | origin, destination, date | 432 |
| `search_onestop_flight` | READ | origin, destination, date | 451 |
| `send_certificate` | WRITE | user_id, **amount (int)** | 488 |
| `transfer_to_human_agents` | GENERIC | summary | 532 |
| `update_reservation_baggages` | WRITE | reservation_id, **total_baggages, nonfree_baggages (int)**, payment_id | 547 |
| `update_reservation_flights` | WRITE | reservation_id, cabin, **flights (array of objects)**, payment_id | 591 |
| `update_reservation_passengers` | WRITE | reservation_id, **passengers (array of objects)** | 692 |
| `get_flight_status` | READ | flight_number, date | 720 |

The tools' OpenAI schema takes 11,148 characters as JSON **[ran]**. **τ² does not validate argument types at
call time:** `ToolKitBase.use_tool` calls the Python function with `**kwargs` directly
(`src/tau2/environment/toolkit.py:138–142`). A string `"50"` where the schema says `integer` goes into the
database as a string, and the DB comparison then fails.

### Database
`data/tau2/domains/airline/db.json`, 7.0 MB: **300 flights, 500 users, 2,000 reservations** [ran]. Models are in
`src/tau2/domains/airline/data_model.py` (`User` :203, `Reservation` :222, `Flight` :162, payment-method union
credit card / gift card / certificate :53–73, flight-date status union :94–141).

### Reward
- **Every airline task has `reward_basis = [DB, COMMUNICATE]`** (50/50 [ran]). 43 of 50 tasks have gold
  `actions` (mean 2.84, max 19). All 50 have `nl_assertions` and 6 have `communicate_info`. No task has an `initial_state`.
- Final reward = **product** of the components in the basis (`evaluator.py:241–256`). ACTION and NL_ASSERTION
  are not in the airline basis, so matching tool calls and the LLM judge (default gpt-4.1, `config.py:24`)
  **do not count**. Airline grading needs no judge model.
- **DB:** replay the task's gold actions on a fresh environment, replay the agent's trajectory on another, and
  compare the SHA-256 of `json.dumps(db.model_dump(), sort_keys=True)` for both the agent DB and the user DB
  (`evaluator_env.py:104–131`, `utils/utils.py:39–45`). The match is all-or-nothing.
- **COMMUNICATE:** each `communicate_info` string must appear as a case-insensitive substring of some assistant
  text message, with commas removed (`evaluator_communicate.py:60–70`). If the list is empty, the score is 1.
- A run that hits max_steps, too many errors or a timeout scores 0 before any of these checks (`evaluator.py:115–127`).
- Success = reward within 1e-6 of 1 (`metrics/agent_metrics.py:12–14`).

### pass^k
`pass_hat_k(n, c, k) = C(c, k) / C(n, k)` per task (`agent_metrics.py:113–126`, citing arXiv 2406.12045),
averaged over tasks (`:169–180`, `:238–244`). With 1 trial, pass^1 is the mean success rate.

### Splits — and the rule "nothing tuned on test"
- τ² ships an official split: **airline train 30 / test 20, disjoint** [ran], `base` = all 50
  (`data/tau2/domains/airline/split_tasks.json`; loaded by `src/tau2/domains/airline/environment.py:35–53`;
  added in 0.2.1 "Train/test task splits for all domains", `CHANGELOG.md:244`). Select one with `--task-split-name`.
- **The default split and the leaderboard both use `base`, which includes the 20 test tasks**
  (`README.md:35`, `docs/leaderboard-submission.md:25`). So a published airline number is over train+test.
  For this project: tune and distil on `train` only, report the member on `test`, and treat a `base`
  comparison to the leaderboard as context only. 20 test tasks is a small denominator: one task is 5 points,
  and the binomial SE at p≈0.7 is about 10 pp per trial.

### User simulator
- Default model `gpt-4.1-2025-04-14`, temperature 0.0 (`src/tau2/config.py:18–22`). Override with
  `--user-llm` / `--user-llm-args`.
- System prompt = global guidelines (`data/tau2/user_simulator/simulation_guidelines.md`, or `_tools.md` when the
  user has tools) + persona + `<scenario>{instructions}</scenario>` (`src/tau2/user/user_simulator.py:33–37`, `:86–92`).
  The conversation ends on the tokens `###STOP###`, `###TRANSFER###` and `###OUT-OF-SCOPE###` (`simulation_guidelines.md:14–16`).
- The published v1.0.1 leaderboard runs use **gpt-5.2 (reasoning_effort low)** as the user simulator, 4 trials,
  seed 300 (e.g. `web/leaderboard/public/submissions/claude-sonnet-4-5_sierra_2026-02-26/submission.json`, methodology.notes).

### How the agent model is configured
- `--agent-llm <litellm model string>`, default `gpt-4.1-2025-04-14`, temperature 0.0 (`config.py:17–21`).
  `--agent-llm-args '<json>'` is passed through as `**kwargs` to `litellm.completion`
  (`src/tau2/utils/llm_utils.py:409–415`).
- **OpenAI-compatible endpoint (vLLM or the shim):** `--agent-llm openai/<served-name> --agent-llm-args
  '{"temperature":0,"api_base":"http://HOST:PORT/v1","api_key":"x"}'`. That `api_base` goes through is
  [read] from the kwargs pass-through and litellm's provider convention. τ²'s docs never mention it.
  `OPENAI_API_BASE` in the environment is litellm's alternative. Cost for an unpriced model: `completion_cost`
  raises, and τ² logs the error and records **0.0** (`llm_utils.py:119–131`).
- System prompt: `<instructions>` (reply or call a tool, never both; "generate valid JSON only") +
  `<policy>{policy.md}</policy>` (`src/tau2/agent/llm_agent.py:24–41`).
- **The tool format is native function calling via litellm.** Every call sends `tools=[t.openai_schema …]` with
  `tool_choice="auto"` (`llm_utils.py:388–391`). History goes back as OpenAI messages: an assistant turn carries
  `tool_calls[{id, type:"function", function:{name, arguments: json.dumps(args)}}]` and each result is a
  `{"role":"tool","content":…,"tool_call_id":…}` (`llm_utils.py:168–209`). Results are JSON strings of the pydantic
  return value (`environment/environment.py:413+`). Several calls in one assistant message are accepted:
  in the shipped gpt-4.1-mini airline trajectories, 221 assistant messages carry more than one call and 185
  carry text plus a call [ran], despite `policy.md:11`.

### Gymnasium / RL interface
`src/tau2/gym/gym_agent.py` (`--extra gym`; `src/tau2/gym/README.md`). `register_gym_agent()` registers
`AgentGymEnv` (`TAU_BENCH_ENV_ID`, :45, class :549), where you play the agent against the user simulator, and
`UserGymEnv` (:1091), where you play the user. `reset()` → (observation, info with `tools`, `policy`).
`step(action: str)` (:747) takes **one string**: a JSON `ToolCall`, a **functional call
`name(arg=value, …)`**, or plain text to the user, parsed by `tau2.utils.tools.parse_action_string`. The
orchestrator runs in a thread. The reward is `evaluate_simulation(..., EvaluationType.ALL)` on the run so far
(:832–857), so it is sparse and terminal, 0 until the conversation ends normally. `truncated` is always False.
`tau2 play` is the interactive version.

### Reference scores and cost [read]
Published airline pass^1 (text, `web/leaderboard/public/submissions/*/submission.json`):

| model | pass^1 | user sim | τ² ver | agent $/conv |
|---|---|---|---|---|
| Claude Sonnet 4.5 (thinking) | 72.0 | gpt-5.2 | 1.0.1 | 0.296 |
| Claude Opus 4.5 | 84.0 | gpt-5.2 | 1.0.1 | 0.399 |
| GPT-5.2 (reasoning none) | 52.5 | gpt-5.2 | 1.0.1 | 0.054 |
| GPT-5.2 | 83.0 | gpt-5.2 | 1.0.1 | 0.114 |
| GPT-4.1-mini | 48.7 | gpt-4.1 | 0.1.3 | — |
| Claude 3.7 Sonnet | 64.2 | gpt-4.1 | 0.1.3 | — |

- **There is no published entry for claude-haiku-4-5**, and no published text entry uses a Claude user
  simulator. Every v1.0.1 entry uses gpt-5.2 as the simulator.
- **With only the Anthropic key, no published score can be reproduced.** Each published configuration needs an
  OpenAI key for the simulator. Under the brief's gate this is the case "reported as not reproduced, the user
  decides". The options are: (a) an OpenAI key and Sonnet 4.5 + gpt-5.2 (≈ 50 × (0.30 + sim) ≈ 17–20 USD at k=1,
  over half of T0+T1); (b) GPT-5.2-none + gpt-5.2 (cheapest published, a few USD, OpenAI only); (c) haiku 4.5
  for both, which is unanchored and serves only as the internal baseline.
- **Shipped trajectories disagree with the leaderboard.** `data/tau2/results/final/` ships airline 4-trial files.
  The gpt-4.1-mini file's mean reward is 0.505 against a listed 48.7, and the claude-3-7-sonnet file's is
  **0.50 against a listed 64.2** [ran]. Both files predate the v1.0 task fixes (commits `ade3949`, `c30d59a`).
  Cite neither as a reproduction target without that caveat.
- **A free check worth running first:** `tau2 evaluate-trajs` re-grades shipped trajectories with no model
  calls. That shows the local grader agrees, separately from whether a model reproduces.
- **Cost estimate, haiku 4.5 agent + simulator, airline, k=1.** Tokens from the shipped claude-3-7 airline file
  (Claude tokenizer, 200 sims) [ran]: agent ≈ 107k in / 1.8k out per conversation, user ≈ 6.1k in / 0.24k out,
  29 messages. At list price 1 / 5 USD per MTok (litellm `model_cost`) [read], that is ≈ 0.116 + 0.007 ≈
  **0.12 USD per conversation → ≈ 6.2 USD for base (50) and ≈ 2.5 USD for test (20)**, with no prompt caching.
  On top of that is the tail risk measured in the mock run, ≈ 1 USD per run-away conversation at max_steps=200.
  This does not fit this task's 3 USD cap, so it was not run.

## 3. The format gap

### The two sides
- **τ²** sends `tools=[…]` (OpenAI schema) plus `tool_choice:"auto"`, reads `tool_calls` back, executes them
  itself, and returns each result as a `role:"tool"` message with a `tool_call_id` (§2).
- **Members** write inline tags and read results inline. The tag is `<name>k=v; k=v</name>`, or `<name>value</name>`
  for a tool with one argument. The result follows as `= value` in the same running transcript, and generation
  stops at the closing tag (`training/harness/tool_calls.py`, `training/harness/accept_rank.run_chain`,
  `examples/common/agent_loop.py`). Served the other way, they break (11/90 against 90/90, CLAUDE.md).

### What already exists in this repo
`training/harness/openai_proxy.py` **already is this shim** for OpenAI agent runtimes, and almost all of it carries over:

- `render_tools` + `tool_calls.tools_to_instruction`: renders `tools=[…]` as the tag block, using the arity convention.
- `rebuild_transcript`: folds `tool_calls` + `role:"tool"` history back into tags plus `= value`. It is
  marked *unmeasured* in its docstring.
- `tool_calls.to_tool_calls`, `strip_calls`, `keep_offered` and `stop_for`: turn tags back into `tool_calls`
  and stop at `</tag>` with `include_stop_str_in_output`.
- `enable_thinking: False` for members. Buffered SSE (τ² does not stream; irrelevant here).
- `examples/school/gateway.py` is the other pattern: **the gateway executes the tools itself** (`run_chain` over
  a `ToolSuite`). τ² must execute every call itself for the DB replay to grade it, so the gateway pattern is
  **not** reusable here. Only the proxy pattern is.

### What breaks if the proxy is pointed at τ² airline unchanged [ran on shipped data, no model]
I replayed all 1,587 tool calls of the shipped gpt-4.1-mini airline trajectories through
`from_tool_call` → `to_tool_calls`:

- **Exact round trip: 1,345 / 1,587.** Every loss falls on the calls that matter for the DB: **220 of 320 write
  calls are lost**, which is every `book_reservation`, `update_reservation_flights`, `update_reservation_baggages`,
  `update_reservation_passengers` and `send_certificate`. Only `cancel_reservation`, which has one string
  argument, survives. Causes: nested arrays of objects come back as a truncated string; integers come back as
  strings, and since τ² does no type coercion (`toolkit.py:138–142`) the DB hash fails; `PAIR` stops a value at
  `,`, which truncated 19/40 `transfer_to_human_agents` summaries; and a call with no arguments
  (`list_all_airports`, 3/3) is dropped because an empty body counts as a placeholder.
- `MAX_ROUNDTRIPS = 6` counts every `role:"tool"` message in the conversation. Airline averages 7.9 calls per
  conversation (max 36), and **106 of 200 conversations exceed 6** [ran]. Past that point the shim would turn
  every later call into text.
- `under_member_prompt` (`--member-prompt`) **replaces** the system messages, which would delete the airline
  policy. For τ² it must not be used as-is.

### Adapter spec (not built)
An OpenAI-compatible HTTP shim between τ² and vLLM, `openai_proxy` with a τ² profile:

1. **Wire it in.** `--agent-llm openai/<member> --agent-llm-args '{"temperature":0,"api_base":"http://shim:8001/v1","api_key":…}'`.
   The shim forwards to vLLM's `/v1/chat/completions` with `tools`/`tool_choice` popped. The user simulator never
   goes through the shim.
2. **Inbound (τ² → member).** Keep τ²'s system prompt (instructions + policy). A member prompt, if any, is
   *prepended*, never substituted. Render `tools` with `tools_to_instruction`. Fold history with
   `rebuild_transcript`, so each `tool_calls` turn becomes its tags and each `role:"tool"` becomes `= <json string>`
   matched by `tool_call_id`.
3. **Argument encoding (the one real change).** The tag body is `k=v; k=v` only when every value is a string
   with no `; , < = newline` and no surrounding whitespace. Otherwise the body is the **JSON object of the
   arguments**: `<book_reservation>{"user_id": …, "flights": [{…}], "total_baggages": 1}</book_reservation>`.
   The CALL regex `[^<]*` already admits JSON with no `<`. Decoding: a body starting with `{` goes through
   `json.loads`, anything else through the existing `k=v` path. **Then coerce scalars by the schema's declared
   JSON type** (`integer`, `number`, `boolean`). This is driven by τ²'s own schema, so it stays a serializer and
   names no domain. An empty body on a tool whose schema has no properties is a call with `{}`, not a placeholder.
   Candidate measured on the same 1,587 calls: **1,587/1,587 exact** [ran]; 242 of them need the JSON body.
   An alternative already inside τ² is the gym's functional syntax `name(k='v', n=1, flights=[…])`
   (`to_functional_format` / `parse_action_string`), which also round-trips **1,587/1,587** [ran]. It is not
   the members' trained surface, though, so the JSON-body tag stays closer to the corpus.
4. **Outbound (member → τ²).** Stop at `</tag>`, include it, and emit **one** `tool_calls` entry with a
   conversation-unique id (not `call_0` reused each turn). Content is `None` when a call is present, which
   matches `policy.md:11`. Cut text after the closing tag. A tag whose name was not offered is returned as text
   and counted.
5. **Caps.** No `MAX_ROUNDTRIPS` for τ². τ²'s own `--max-steps` / `--max-errors` govern, and any shim cap is
   per assistant turn, never per conversation. `MEMBER_MAX_TOKENS` must fit a JSON `book_reservation`, so raise
   it to at least 512.
6. **Log.** One line per request with shapes only (offered tools, calls out, dropped, JSON-body vs k=v), as `_record` does.

### The no-loss check (T0's Colab step, before any member is scored)
- **G-shim-1, offline, $0, runnable on the Mac (no model):** replay every τ² trajectory available (shipped
  airline files plus the mock results) through inbound render → outbound parse. Assert **identity** of
  `(name, arguments)` for every tool call, with types, and identity of every tool result string recovered from
  the rendered transcript. Pass = 100%, no tolerance.
- **G-shim-2, Colab:** τ² `mock` (`create_task_1`, `update_task_1`) with the agent served **through the shim**
  by a model whose native tool calling also works (the base Gemma 4 on vLLM). Run it twice, once natively
  (`openai/<base>` straight at vLLM with its tool parser) and once through the shim, and check that both runs
  complete normally. The shim's request log must show that what τ² received equals what the model wrote. This
  is the path check. It is not a score.
- **G-shim-3, leak check:** confirm the shim sees only the agent's messages and τ²'s tools. Nothing from the
  task's `evaluation_criteria` or gold actions may reach it (it cannot, by construction, but assert it in the log).

## 4. Spend
Mock run: 207 model calls, **0.970 USD** (τ²/litellm per-message `cost`), logged per call in
`results/TAU2-T0-recon-20261005/spend.jsonl`. Everything else in this document was read or computed offline.
