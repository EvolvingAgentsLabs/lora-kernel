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

---

# Result — 2026-09-18 **[ran]** · LIVE, on the seventh attempt

**Identity through the tunnel:** 3/3 probes differ, applied (`identity_through_tunnel.json`).

| attempt | what it measured | what it found |
|---|---|---|
| 1 | first turn | the router read OpenClaw's 37 KB system prompt (channels, gates, tanks…) and sent triage out as fluids — 503, never a wrong member |
| 2 | first turn | OpenClaw's internal-context envelope arrives as a second `user` message: "no region" |
| 1' | 40 turns | the expert answered, then echoed the tool block; its `<tag>...</tag>` placeholders became executed calls — 7 calls, no verdict |
| 2' | 40 turns | after a tool result the trailing user message is only the envelope; and the finalisation request carries OpenClaw's instruction as the user turn — "no region" both ways |
| 3 | 7 turns (runtime prompt) | 0 tool calls on 7/7; a killed turn left the profile's gateway lock, turns 9–22 died in a second each |
| **4** | **40 turns, runtime prompt** | **NOT LIVE: 40/40 local, 0 invented, 2/32 human turns called a tool, human 0.281** — under the runtime's prompt the expert answers from the listing, as the bare base does (P43's finding, now with tools in reach) |
| 5 | member prompt, uncapped | the expert writes a malformed call after its verdict, gets an error, writes it again: 30 round-trips, 71 messages, until killed |
| 6 | member prompt, capped | three-minute turns: nothing bounded a step's tokens |
| **7** | **40 turns, member prompt, cap 6, 256 tokens/step** | **LIVE: 40/40 local, 0 invented, 19/32 human turns called a tool, human 22/32 = 0.688 vs bar 0.655** ($p = 0.43$, exact — above the bar, not clearing the gate at $n = 32$, as pre-registered: descriptive); 59 requests, 19 calls, 3.5 s per turn |

**What it decides.** Milestone 3 passes its three pre-registered gates with the member
served under its released prompt. The attribution is the pair 4 → 7 on the same 40
messages: same proxy, same tunnel, same tools; the prompt is the only treatment
(plus the two bounds, which are the corpus loop's). **A member is what its corpus
taught — the block, and the prompt.** `--prune` and `--member-prompt` are the
proxy's recommended defaults for a member.

**What it does not claim.** Accuracy at $n = 32$ human turns is not a gate result;
P43's 0.741 (475 cases, `agent_sim`) and P59's 0.729 remain the numbers. Latency is
recorded, not gated. One region live; real mail is a different program.
