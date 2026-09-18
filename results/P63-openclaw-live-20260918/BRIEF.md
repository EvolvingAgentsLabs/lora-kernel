# P63 — milestone 3: the live OpenClaw turn with `--prune` and `--auto` (2026-09-18)

**Question (one unknown).** With the inbox tools handed to OpenClaw over MCP, the proxy
pruning the surface to the member's three tags and routing `auto` by text, does the
live agent turn call the tools and stay local?

**Why.** P43 ran the transport end to end and the turn made **0 tool calls** (OpenClaw
sends its own tools). P59 measured, in simulation on the recorded 54-tool surface,
unpruned 225/227 calls refused vs pruned 8/1160. Nothing has measured the live path
with both fixes.

**Set-up.** Pool on Colab L4 (`serve_tunnel`, `email-full@v1`), cloudflared → this Mac;
local proxy `--upstream <tunnel> --prune --auto auto --log traffic.jsonl` (no fallback:
an `out` decision is a 503, never a silent local answer); OpenClaw 2026.9.4, profile
`lorakernel` (isolated), provider `lorapool` with model `auto`, MCP `lora-inbox`
serving the synthetic inbox (seed 717171, n 150). Turns: `openclaw agent --local
--model lorapool/auto -m "<listing>"`, the first 40 messages of that inbox.

**Preflight.** The identity gate through the tunnel (base vs `email-full`, 3 probes) —
the run is void if the tunnel changes what the model sees (P43's rule).

**Pre-registered (before the run), `openclaw_live.verdict`:**

- `routed_local == n` — every turn stays local via `auto`; any `[route] OUT` fails.
- `invented == 0` — no call to a tool the agent was not offered (pruning reaches the
  live path).
- `call_share ≥ 0.5` — at least half the human turns call an inbox tool (P43: 0).
- Human accuracy against the 0.655 majority bar (exact binomial, §9.1), beside P43's
  0.741 and P59's simulated 0.729 — descriptive at n≈30 human turns.

**Failure written first.** `invented > 0`: pruning does not reach OpenClaw's path.
`call_share < 0.5`: the live agent still answers from the listing — milestone 3 stays
open and the next step is reading OpenClaw's tool-call round-trip, not another turn.

**Not measured:** latency per turn (recorded, not gated); a second region live; real mail.
