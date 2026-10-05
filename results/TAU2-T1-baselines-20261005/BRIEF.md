# TAU2-T1 — is there a gap worth distilling? Gemma 4 31B against Gemma 4 E4B as τ²-bench airline agents

**Written 2026-10-05, after the instrument was frozen (`examples/tau2/t1_run.py`, `tests/test_tau2_t1.py`) and before
any simulation exists.** Redesign counter: 0. Phase T1 of the user's τ²-bench brief; T0 passed
(`results/TAU2-T0-recon-20261005/BRIEF.md`).

## What and why

The plan distils a teacher's τ² trajectories into an E4B member. Distillation transfers what the teacher does and the
student does not; **if the untrained E4B already does what the 31B does on airline, there is nothing to transfer** and the
domain leaves the plan before a trajectory is generated. This is the headroom check, bought before any treatment
(CLAUDE.md §3): one teacher arm, one base arm, the same simulator, the same tasks.

The card's own figure says a gap may exist — "Tau2 (average over 3)" 76.9 % for the 31B against 42.2 % for the E4B
**[read]** `google/gemma-4-31B-it-qat-w4a16-ct` README — self-reported, over three domains, a different simulator, no
split stated. Context only; never the baseline (workspace rule: compare against ourselves).

## Arms

| arm | agent | simulator | path |
|---|---|---|---|
| **teacher** | `google/gemma-4-31B-it-qat-w4a16-ct` @ `52f3f65` | the same 31B server | native tool calls, vLLM `--tool-call-parser gemma4` |
| **base** | `google/gemma-4-E4B-it` @ `ee0ef60` (bf16 — the base members are trained on) | the 31B | native tool calls, vLLM `--tool-call-parser gemma4` |

- **The 31B checkpoint: Google's official QAT release in compressed-tensors W4A16** (int4 weights, group 32, symmetric,
  bf16 activations; `quantization_config` in its `config.json`, one 23.3 GB `model.safetensors`) **[read]**
  huggingface.co/google/gemma-4-31B-it-qat-w4a16-ct. The card: "QAT checkpoints serialized in the compressed-tensors format
  for native, optimized inference with vLLM", and QAT "preserving similar quality to bfloat16" **[read]**. Apache 2.0, not
  gated. Why not the alternatives:
  - **bf16** (`google/gemma-4-31B-it`, 62.5 GB of weights **[read]** HF API) does not fit a 40 GB A100 at all, and beside
    the E4B leaves ~13 GiB of a 96 GB G4 for two KV caches — possible, not chosen; it is the user's call below.
  - **FP8** — vLLM's W8A8 FP8 kernel does not run on the A100 (sm80): `cutlass_scaled_mm_sm80_epilogue` **[ran]** TEACH0
    attempt 2.
  - W4A16 runs where FP8 does not: vLLM 0.30's `CompressedTensorsWNA16.get_min_capability()` is 75 (Turing and up), and
    its CUDA arch list includes 8.0 (A100) and 12.0 (RTX PRO 6000 Blackwell, the G4) **[read]** vLLM `v0.30.0` source.
    **Never run on this account** — the preflight is the check.
  - The QAT teacher is the teacher: if T1 passes, T2's trajectories come from this same checkpoint, so the teacher
    measured is the teacher distilled.
- **Native tool calling on Gemma 4 in vLLM 0.30:** `--enable-auto-tool-choice --tool-call-parser gemma4`
  (`gemma4_engine_tool_parser.Gemma4EngineToolParser`, registered as `gemma4` in `vllm/tool_parsers/__init__.py`) and
  `--reasoning-parser gemma4` **[read]** vLLM `v0.30.0`; vLLM's docs page lists only `functiongemma` **[read]** — the
  source is what was checked. Thinking off (`chat_template_kwargs.enable_thinking=false`, passed by τ² through litellm's
  `extra_body`); the reasoning parser takes the empty thought channel the larger Gemma 4 models still open (card: "for
  all models except E2B and E4B … the model will still generate the tags but with an empty thought block" **[read]**).
- **`--language-model-only`** on both servers (vLLM 0.30 arg **[read]**): no vision or audio tower on the card.
- **Both arms see the same degraded nested schema [ran, offline]:** Gemma 4's chat template renders τ²'s array-of-object
  arguments (`flights`, `passengers`, `payment_methods`) as `items:{anyOf:[{$ref:#/$defs/FlightInfo}, …]}` and never
  renders `$defs` — rendered with the E4B's own `chat_template.jinja` and τ²'s 14 airline schemas. The 31B's template is
  byte-identical between its bf16 and QAT repos (md5 `f016bd4b…`) and has the same macros **[read]**. Equal for both
  arms, so the gap is fair; it lowers both absolute levels on the write tools. Not patched: patching the template
  would make it a third arm.

## Provider and card

- **Colab, one session at a time, through `training/harness/chain_serve.sh`; API spend 0 USD** (the T0+T1 cap is 50 USD,
  0.97 spent in T0 — T1 adds nothing; "$/task" is reported as Colab session time).
- **Card: G4 — NVIDIA RTX PRO 6000 Blackwell, 96 GB** (Colab's `G4` option **[read]** `colab new --help`; 96 GB GDDR7
  **[read]** cloud.google.com G4 announcement). **Both models resident on one card:** the 31B at
  `--gpu-memory-utilization 0.45` (~43 GiB: ~22 GiB weights, the rest KV) and the E4B at `0.40` (~38 GiB: 15.2 GiB
  weights **[ran]** B1, the rest KV), `--max-model-len 32768` for both.
- **Why not the A100:** Colab's A100 has 39.49 GiB **[ran]** (vLLM logs, C0); the 31B W4A16 (~22 GiB) and the E4B bf16
  (15.2 GiB) leave no KV cache on it. **The teacher arm alone fits the A100** (0.90 utilisation) and the runner will run it
  there and say the base arm needs a bigger card. **The H100 (80 GB)** holds both too and is the fallback — Colab refused it
  on quota twice (PAIR1).
- **G4 has never run on this account.** If vLLM does not start there (a recorded error in `vllm.log`), the one change
  allowed is the card: H100; else the teacher arm on an A100 and the base arm waits, reported to the user.

## Simulator, tasks, trials

- **Simulator:** the 31B (the user's decision, T0 BRIEF), served once and shared by both arms, temperature 0, thinking off.
- **Split:** airline `test`, **20 tasks** (`--task-split-name test`; train 30 / test 20, disjoint **[ran]** T0). Nothing is
  tuned on these; T2 trains on `train` only.
- **k = 4 trials** (`--num-trials 4`, τ²'s seed 300), **`--max-steps 150`** (the longest shipped airline conversation is 104
  messages **[ran]**, T0's runaway simulator ran to 200), `--timeout 1200` s per simulation, `--max-concurrency 8`,
  `--max-errors` τ²'s default (10). Agent `max_tokens` 2048, simulator 1024.
- **At temperature 0 the four trials differ only through vLLM's batch nondeterminism and the simulator's replies**
  (CLAUDE.md §3: 84, 81, 82 on one adapter). pass^4 therefore measures consistency under that noise, not sampling — the
  same convention as τ²'s published runs (temperature 0, 4 trials).

## Metrics (per arm, in `t1.json`)

$$\text{pass}^k = \frac{1}{|T|}\sum_{t\in T}\frac{\binom{c_t}{k}}{\binom{n_t}{k}}$$

τ²'s definition (`agent_metrics.py:113–126`), re-stated in `t1_run.pass_hat_k` and checked against τ²'s own
`compute_metrics` on its four shipped airline files — identical to 1e-4 on pass^1…pass^4 **[ran]** `tests/test_tau2_t1.py`.

- **pass^1 and pass^4 with 95 % bootstrap CIs** over tasks (B = 10 000, seed 0; the task is the unit — trials of one task
  are not independent).
- **Tool calls per task** (per simulation), **tool errors** (τ² `error: true` results), **malformed calls** (parser markup —
  `<|tool_call>`, `<|"|>`, `call:name{` — left in an assistant message's text: a call the parser did not extract).
- **Tokens:** agent prompt and completion tokens per simulation (vLLM's `usage`), simulator tokens.
- **Latency:** agent generation seconds per call (τ²'s `generation_time_seconds`), simulation duration.
- **Terminations** by reason (`user_stop`, `agent_stop`, `max_steps`, `too_many_errors`, `agent_error`, …).
- **Cost:** 0 USD of API; Colab session seconds per session (`sessions[]`), wall seconds per arm.

## Gate T1 (fixed here)

$$\Delta = \text{pass}^1_{\text{teacher}} - \text{pass}^1_{\text{base}}, \quad \text{paired over the 20 tasks}$$

- **DISTIL HERE** — $\Delta \ge$ **15 pp** **and** the 95 % paired bootstrap CI of $\Delta$ over tasks excludes 0 → T2 is
  planned (trajectory generation on `train`), **after the pause below**.
- **NO NEED TO DISTIL HERE** — anything else → airline leaves the plan (the user's brief).

**Why 15 pp.** The unit is the task: one task is 5 pp of pass^1 (a task's own pass^1 moves in steps of 1.25 pp across 4
trials, but trials are not independent). 15 pp is three tasks' worth — the smallest gap that pays for a corpus, a
training and a member through the gate. **In practice the CI binds first:** with per-task differences of SD ≈ 0.5 the
standard error over 20 tasks is ≈ 0.11, so the CI excludes 0 only from a gap of roughly 20–25 pp up; a true gap of 15–20 pp
will read NO NEED. That is the instrument's resolution at 20 tasks, said here so it is not discovered later (test:
`test_the_gate_refuses_a_gap_under_the_threshold_or_inside_the_noise`, 15 pp carried by 7 : 4 tasks → NO NEED).

**Read beside, not gating:** pass^4 gap with its CI; tasks the teacher wins / the base wins; the teacher's own level (a
teacher under 50 % pass^1 is a low ceiling for anything distilled from it); malformed calls and tool errors of the base
(the shape of its headroom).

**VOID, per arm, read before the gap** (an arm that never reached its tools must not look like a floor; a rule that
voids across arms already cost H1 and H2 their verdicts):
- the arm's preflight failed (below);
- more than 5 % of its simulations ended `infrastructure_error` / `unexpected_error` (the wire, not the model);
- more than 5 % ended `user_error` (the shared simulator broke).
A base that fails by its own errors (`too_many_errors`, `agent_error`, malformed calls) is headroom, not VOID
(`test_void_and_incomplete_are_per_arm_and_read_first`). Before a VOID or a floor is written, the failures are read where
they happen (the trajectories are in `t1.json`, packed).

**INCOMPLETE** — an arm short of 20 tasks × 4 trials: no verdict.

## Preflight (per arm, before it scores)

1. Three tool-call probes against the agent's server with τ²'s own system prompt and 14 tool schemas (captured from τ²'s
   `LLMAgent`, `examples/tau2/fixtures/tau2_requests.json`): **STOPPED if parser markup appears in `content`**; the teacher
   must call a tool on at least one probe (the base is not held to it — a base that answers in text is headroom).
2. A simulator probe: plain text back, no markup.
3. **τ²'s own path:** one `litellm.completion("openai/<name>", api_base=…, extra_body=…)` in τ²'s venv, the call τ² makes.

## Stopping condition

- **Sessions:** at most **3** G4 sessions (`SESSIONS=3`); the runner resumes from τ²'s own checkpoint (`--auto-resume`),
  carried between sessions inside `t1.json`. Estimate **[inferred]**: ~20 min of each session goes to installing vLLM and
  τ², downloading 23 + 16 GB and starting two servers; 80 simulations per arm at concurrency 8 — the teacher arm ~25–40 min,
  the base arm less — so 2 sessions expected. Not finished after 3: stop and report the position; no fourth session
  without the user.
- **The card:** as above — one change allowed (G4 → H100), nothing else.
- **Nothing in the arms, tasks, trials, simulator, thresholds or gate moves after this brief.** A change is a redesign,
  counted here.

## The pause

**After T1, the user is reported to before anything of T2 or T3 is spent** — whatever the verdict. T1's report carries the
gate, the numbers above, and the failures read.

## Chain commands

The branch must be on GitHub for the VM to clone it (the chain clones `BRANCH`); this branch is committed locally, not
pushed. vLLM comes from the chain's boot (`pip install 'vllm>=0.28'`; the version is recorded per session). **τ² is installed
by the runner itself, not by the chain** — `chain_serve.sh` has no extra-deps hook beyond `TRAINDEPS` (peft/trl), and τ²
belongs in its own venv beside vLLM's: `git clone` at `5bfa7e37…`, `uv sync --frozen --python 3.12` (τ²'s lock), `uv pip
install websockets` (the T0 gap). Nothing gated, so no `HF_AUTH`; nothing carried in, so `SKIP_ADAPTERS=1`.

```bash
R=results/TAU2-T1-baselines-20261005
GPU=G4 BRANCH=tau2-t0-20261005 RUN_DIR=$R MODULE=examples.tau2.t1_run \
  BASE=google/gemma-4-E4B-it MARGS="--teacher google/gemma-4-31B-it-qat-w4a16-ct --arms teacher,base" \
  RESULTS_NAME=t1.json SESSIONS=3 SKIP_ADAPTERS=1 \
  training/harness/chain_serve.sh 2>&1 | tee $R/S_chain.log
```

Fallback (the card change allowed): the same with `GPU=H100`. Split across cards, if the user prefers (teacher on an A100
now, base later on a big card):

```bash
GPU=A100 … MARGS="--teacher google/gemma-4-31B-it-qat-w4a16-ct --arms teacher" … training/harness/chain_serve.sh
# the runner writes "stopped_at_gate" when the arms it was asked for are done; drop it from the local copy before the next chain:
python3 -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d.pop("stopped_at_gate",None); json.dump(d,open(p,"w"),indent=1)' $R/t1.json
GPU=G4 … MARGS="--teacher google/gemma-4-31B-it-qat-w4a16-ct --arms teacher,base" … training/harness/chain_serve.sh
```

(Splitting puts the teacher arm's simulator at 0.90 utilisation and the base arm's at 0.45 on another card type — a
difference in batch shape and numerics, named; the single-G4 run has none.)

The runner prints `[tau2] …` (in the chain's peek, `tests/test_tau2_t1.py`), one line per finished simulation, persists
after each, and writes `"decision"` and `"finished"` into `t1.json` when both arms are complete.

## Decisions owed to the user

1. **The card:** G4 (never run here) for both arms in one card, H100 as fallback — or the split above.
2. **The teacher's precision:** QAT W4A16 (this brief) or bf16 on the G4 (fits beside the E4B with ~13 GiB of KV for
   both; slower, tighter).
3. **The resolution:** 20 test tasks resolve gaps of ~20–25 pp. The `base` split (50 tasks, train included) would resolve
   ~13–16 pp for 2.5× the Colab time — but T2 would then train on tasks T1 measured. This brief keeps `test`.

## Result

*(written after the run)*

## Result [ran] 2026-10-05 — VOID as written; DISTIL HERE under both readings of the failures

One G4 session, both arms complete (80/80 simulations each), API spend 0 USD.

| arm | pass^1 (τ²) | pass^4 | calls/sim | malformed | terminations |
|---|---|---|---|---|---|
| teacher — Gemma 4 31B (QAT w4a16) | **0.5375** [0.35, 0.725] | 0.40 | 7.22 | 0 | `user_stop` 80 |
| base — Gemma 4 E4B | 0.2125 [0.0625, 0.3875] | 0.118 | 4.81 | 0 | `user_stop` 71 · `infrastructure_error` 9 |

**As written: VOID** — the base arm has 9 of 80 simulations (11 %) ended `infrastructure_error`, over the 5 % clause
(`t1.json` → `gate.decision`).

**The failures, read where they happen** (τ²'s raw record, packed in `t1.json`): all nine are on three tasks (2: 3 of 4
trials, 13: 3 of 4, 45: 3 of 4), each with **zero messages and zero duration** — τ² raised
`ValueError: AssistantMessage must have either content or tool_calls` on the agent's **first reply**: the base answered
with neither text nor a tool call. That is the agent's own output, not the wire (the server answered; the simulator was
not involved); whether the empty reply was the E4B emitting nothing or vLLM's tool parser swallowing malformed markup is
**not recordable from this run** — the runner keeps τ²'s messages, not the raw completion. τ² labels it
`infrastructure_error`; the brief's clause keyed on the label, and the brief's own rule says a base failing by its own
output is headroom.

**The gap under both readings** (paired over tasks, per-task pass^1, bootstrap 10,000, seed 0 — computed here, not by the
runner's gate):

| reading | Δ pass^1 | 95 % CI | tasks teacher : base | gate clause |
|---|---|---|---|---|
| the nine empty first replies are the base's failures (reward 0), 20 tasks | **+36.3 pp** | [20.0, 53.7] | 11 : 0 | DISTIL HERE |
| the three tasks dropped, 17 tasks | **+30.9 pp** | [13.2, 48.5] | 8 : 0 | DISTIL HERE |

The teacher wins the three dropped tasks too (0.25, 1.0, 1.0 against the base's 0.0, 0.25, 0.0). Beside, not gating: the
teacher sits just above the brief's 50 % level for a teacher; the base calls tools ~5 times a simulation with no malformed
call, so its headroom is in what it calls, not in the format.

**The decision between the readings is the user's** (the H1/H2 precedent): reading 1, the failures are the base's own
output and the gate reads DISTIL HERE; or VOID as written stands and T1 is rerun with the raw completion recorded. No T2
or T3 spend before that decision (the pause above).
