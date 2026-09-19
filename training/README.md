# `training/` — experts, their corpora, and the gates they enter through

Everything here either **produces a weight delta**, **serves one**, or **decides whether a
number about one can be believed**. It lives in this repository and runs on Colab: this
machine is a 16 GB laptop and cannot hold vLLM, let alone a 27B.

## What is in the box

| path | what |
|---|---|
| `email/` | the two suites with a mechanical verifier: inbox triage (`inbox.py`, `tools.py`) and the desk's `commitment` region (`desk.py`, `desk_tools.py`) — shallow and deep bands |
| `mcp/inbox_server.py` | the inbox tools as an MCP server, so a real agent can use a member |
| `harness/data_ef/`, `harness/data_desk/`, `harness/data_desk_deep/` | the released corpora, hashed in `../releases/*.json`. **A corpus is the expert's definition and the router's training set** |
| `harness/generate_email_full.py`, `generate_desk.py`, `graded.py` | the generators — they *call* `render_tools`, so the corpus teaches the served prompt |
| `harness/train_pool.py`, `contract.py` | the pool registry: each member a record read off its corpus |
| `harness/openai_proxy.py`, `route.py`, `serve_tunnel.py` | the API: prune, member prompt, route per request; the tunnel for a live agent |
| `harness/release_gate.py`, `pool_second.py`, `verify_substrate.py`, `serve_openai.py` | the door a member enters through, and the identity gate |
| `harness/accept_rank.py`, `awq_lora_gate.py` | acceptance by teacher forcing; a LoRA over a large quantised model |
| `harness/pool_base.py`, `train_one.py` | milestone 1: every released member retrained on another base; `train_one` names the adapter for the class that will serve it |
| `harness/corpus_router.py`, `router_sets.py` | milestone 2's measured arm — an n-gram model of each corpus's frame — and the sets every router is scored on, including the three written after the freeze |
| `harness/lora_matrix.py`, `tiny_adapter.py`, `rekey.py`, `tokenizer_compat.py` | is this base — and this pair — usable at all |
| `harness/knowledge_arm.py`, `null_arm.py`, `ceiling.py`, `bar.py`, `suite_gates.py` | headroom, ceilings and the statistics, before and after |
| `harness/openclaw_live.py`, `openclaw_traffic.py`, `tunnel.sh` | the live OpenClaw turn, and shapes read from its own log |
| `harness/chain_serve.sh`, `chain_separate.sh` | the Colab chains |
| `physics/` | the fluids suite — an exact oracle and a handbook drawn per case — and `result_use.py`, which reads a failure where it happens. The region was marked *out* on a measurement of the serving path; served as taught it is 90/90 **[ran]** M7 arm 0b |

## Running on Colab, from a terminal

```bash
GPU=L4 BRANCH=<branch> MODULE=training.harness.<runner> \
  RESULTS_NAME=<file>.json MARGS="<runner flags>" \
  RUN_DIR=results/<run> training/harness/chain_serve.sh > results/<run>/chain.log 2>&1
```

- The brief goes in `results/<run>/BRIEF.md` **before** this line runs.
- `TRAINDEPS=1` when the runner trains; `SKIP_ADAPTERS=1` when no released adapter has to be
  carried in; `BASE=<model>` for a base other than the default.
- One chain at a time — they share `/tmp/_v*.py`. The chain streams position, fetches
  partial results, and stops its own session on exit.
- **The verdict is in the results file, never in the exit code.**
- Install order that works on a Colab runtime: vLLM first (it pins torch), then the training
  dependencies, `torchaudio` removed.

The rules that were paid for are in [`../CLAUDE.md`](../CLAUDE.md) §3; the milestones these
runners serve are in [`../docs/PLAN.md`](../docs/PLAN.md).
