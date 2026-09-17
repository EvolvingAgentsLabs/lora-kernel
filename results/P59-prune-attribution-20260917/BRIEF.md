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

---

## Result — attempt 2, 2026-09-17 **[ran]** `attribution.json`, A100, 0 errors in either arm

| arm | 475 | human 351 | calls | refused | what it writes |
|---|---:|---:|---:|---:|---|
| `--prune off` — 54 tools, room for the block | 357 | **0.664** | 227 | **225** | `IMPORTANT` 344 times, `NOT IMPORTANT` 131 — answers from the listing at the majority bar (0.655) |
| `--prune on` — the member's three | 380 | **0.729** | 1160 | 8 | uses its tools; P43's 0.744 within noise |

**Paired over 475: 87 : 64, $p = 0.073$ — a tie by the pre-registered $p \le 0.05$.**
Power at this $n$ for a +0.05 effect is 0.81 and `n_for` says 466, so the run was sized
at the edge on purpose and the edge is where it landed: the pruned arm wins more cases
than it loses, and not resolvably.

**The behaviour is not a tie.** Unpruned, the expert **copies tags off the block**: it
calls `agents_list`, `agents_wait`, `apply_patch`, `ask_user`, `browser`, `canvas` —
the first entries of the 54-line listing, six cases each — **225 of 227 calls refused,
2 answered**. That is P25's measured failure (an unknown surface: knows a step needs a
tool, gets the name wrong) inside the product path, and it did not reproduce P43's
*zero* calls because `agent_sim` is not OpenClaw: OpenClaw would have **executed**
those calls. **Unpruned, an expert inside an agent runtime reaches for `apply_patch`
and `browser`.** Pruning is not an optimisation; it is the boundary.

And the prefill: **~7,956 tokens** of tool block per turn unpruned against **~77**
pruned, measured before any model was served.

**Reading for Phase 5:** `--prune` becomes the default the docs recommend, on the
behaviour evidence; the accuracy delta is real in direction and unresolved at this
$n$, and is not the reason.
