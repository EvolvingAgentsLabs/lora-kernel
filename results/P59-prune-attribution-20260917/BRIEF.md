# P59 — does pruning the tool surface turn zero calls into calls? (Phase 5, first buy)

**Pre-registered 2026-09-17.** Runner `training/harness/prune_attribution.py`; verdict
logic in `tests/test_prune_attribution.py`.

## The number this buys

P43 ran the pool inside OpenClaw and the agent turn made **no tool calls at all**: the
runtime offered **54 tools** to an expert trained on three, and the three it knew
arrived as `lora-inbox__…` **[ran]**. `openai_proxy --prune` (#190) exists to fix
exactly that and has never been measured against the surface that caused it.

## The surface, recorded rather than assumed

One local OpenClaw turn against a recording stub — shapes only, the prompt is not
written anywhere — captured the real request: **54 tools, streaming**, including the
three inbox tools under `lora-inbox__` **and OpenClaw's own `message`** (`action`,
`channel`, `target`, …). `openclaw_tools.json`.

Rendered as the block an adapter reads (`tools_to_instruction`, arity on):

| surface | chars | ≈ tokens |
|---|---:|---:|
| the 54, unpruned | **31,825** | **~7,956** |
| pruned to the member's three | **310** | **~77** |

**[ran]** 2026-09-17 — a ~100× smaller prefill per turn, before any model is served.

## Arms, in the order that kills first

1. **`--prune off`** — must reproduce P43's zero-call turn, or the replay is not the
   surface that caused it.
2. **`--prune on`** — the same expert, cases and client.

Same 475 cases (`generate(475, 717171)`), `email-full@v1`, through the proxy and
`tool_calls` (the product path, where P43's 0.741 was taken), `agent_sim --tools-json`
replaying the recorded surface. **Compared on the same cases by the exact two-sided
sign test on discordant pairs** (FOUNDATIONS §9.2).

## Gate

**PRUNING PAYS** if the on-arm wins resolvably ($p \le 0.05$, more discordant cases its
way); **HURTS** if it loses; **a tie** otherwise. **VOID if either arm has a transport
error** — the count is reported and nothing is compared.

## What voids it — and attempt 1 did

**Attempt 1 [ran]:** every `--prune off` request failed with *"maximum context length
is 4096"* — the ~8k-token block does not fit — and the first `compare` counted the
errors as wrong answers: **PRUNING PAYS 385 : 0** over an arm that never reached the
model. A broken run wearing a floor, the failure `CLAUDE.md` §3 names. Fixed: errors
void the verdict; the runner serves at 16,384; errors are in the progress line. The
on-arm of attempt 1 stands on its own: **385/475, human 261/351 = 0.744**, 1169 calls
— P43's 384/475, 260/351 within one case.

## What it cannot conclude

Nothing about a live OpenClaw turn (the client here is `agent_sim`, not OpenClaw);
nothing about the ordering test (closed); nothing about latency.
