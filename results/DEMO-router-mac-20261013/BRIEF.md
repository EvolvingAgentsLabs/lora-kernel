# DEMO-router-mac — the served tracker member answers locally and abstains to the frontier, on the user's Mac

**Written 2026-10-13, before anything runs.** The user approved running it on the Mac today. A demonstration for the
README and the site, not a measurement of the member: one session, on another runtime and quantisation than ROUTE1's
vLLM bf16 arm, said so.

## What and why

The site and the README describe the router — the role names the member, the member answers what its tools cover and
abstains (`OUT OF SCOPE`) on the rest, and the role's egress takes that — but nothing shows it running. This records one
developer session doing both, end to end on a 16 GB laptop, as a terminal recording (GIF) whose every line is the
gateway's own output.

## Setup (all local except the one forwarded turn)

    llama-server -m ~/lora-kernel-models/gguf/gemma-4-E4B-it-Q8_0.gguf \
        --lora ~/lora-kernel-models/gguf/lora-tracker-out-s0-f16.gguf --port 8792 -c 8192 -ngl 99
    python -m examples.school.gateway --org tracker --member tr-out-s0 --upstream http://127.0.0.1:8792 \
        --tokenizer google/gemma-4-E4B-it --memory --no-tool-block --max-calls 6 --port 8765 \
        --frontier-url https://api.anthropic.com/v1 --frontier-model claude-haiku-4-5 \
        --frontier-budget-usd 0.50 --frontier-rates 1,5 \
        --log results/DEMO-router-mac-20261013/events.jsonl
    python -m examples.tracker.demo_router --out results/DEMO-router-mac-20261013/demo.json

- **Member:** `tr-out-s0` (ROUTE1 **[ran]**: 27/30 out-of-scope abstained, no in-scope turn lost), Gemma 4 E4B Q8_0 +
  LoRA as GGUF f16, llama.cpp (Homebrew, Metal), the user's MacBook Air M4 16 GB.
- **Frontier:** Claude Haiku 4.5 through Anthropic's OpenAI-compatible endpoint, as in M10's live run; key read from
  `~/.config/lora-kernel/frontier.env` into the gateway process only; **cap US$0.50** for this run. The gateway's egress is
  closed to the llama.cpp host and the frontier host.

## The session (developer, harborworks)

1. "Details on HW-245?" — LIVE-tracker's wording; expected local, a read of the issue.
2. "Transition it to in review." — dependent turn; expected local, the transition on the issue stored in the memory.
3. "How do you say 'deadline' in French?" — a held-out ROUTE1 out-of-scope request `tr-out-s0` sent to the egress
   **[ran]**; expected `OUT OF SCOPE` → frontier → Haiku's reply.

## Bar (fixed here)

| | condition |
|---|---|
| **SHOWN** | turns 1–2 `route = local` with the right tool call and turn 3 `route = frontier` with a frontier reply |
| **NOT SHOWN** | anything else — reported as it happened, not re-rolled to look right |

Stopping condition: at most **two** attempts. A second attempt only for a transport failure (no gateway event); a
member error is the result and is published as such.

## Not in this run

Variance (one session), the QA role's egress to a person, OpenClaw (plain HTTP client here, so the recording shows the
gateway's fields: route and tool calls).

## Attempt 1 [ran] 2026-10-13 20:58 — NOT SHOWN: the member did not abstain mid-session

`attempt1_mid_session_not_shown.{demo.json,events.jsonl,gif}`, `attempt1.gateway.log`. Turns 1–2 as expected, local
(`issue_get HW-245`, then `get issue` → `issue_transition HW-245 in_review`; 7.3 s and 3.6 s wall). Turn 3 was **served
locally**: the member called `page_read definition#deadline` (no such page) and replied from the tracker — no
`OUT OF SCOPE`, the frontier never called (US$0 spent). Not a transport failure, so by the stopping condition not re-rolled.

**Read where it happens: the brief put the out-of-scope request where ROUTE1 never measured it.** ROUTE1's abstaining
turns, in training and in its held-out set, are each *the first turn of a fresh session* ("each a one-turn session under
the operational memory"); here it was turn 3, behind a context line holding `state: on_issue · keys: issue, component`.
One sample on another runtime: **the abstention `tr-out-s0` learned is not shown to hold mid-session** — an open question
for the corpus (abstaining turns after in-scope ones), not settled by one turn.

## Redesign 1 (of at most 1), written before attempt 2

The out-of-scope request is sent as **the first turn of its own session** (same developer, same token, new session id) —
the condition ROUTE1 measured. Turns 1–2 unchanged, on a restarted gateway (fresh store). Bar unchanged. If attempt 2 is
also NOT SHOWN, that is the result and the recording published is that one.

## Attempt 2 [ran] 2026-10-13 21:05 — transport failure: the member abstained, the gateway's egress guard refused the frontier

`attempt2_egress_bug.{events.jsonl,gateway.log,gif}`. Turns 1–2 local, as in attempt 1. Turn 3, in its own session,
**entered the frontier branch** (`gateway.py:176`, reached only when the member's reply contains `OUT OF SCOPE`) and the
forward failed: `egress to 160.79.104.10:443 is not in this gateway's allow-list`. No reply, no event logged for the turn,
US$0 spent.

**The bug, read where it happens:** `examples/common/egress.py` (since #310) allows the configured *names* at DNS, but
`connect` sees the resolved *address* and checked it against the names — so every remote host was refused after passing
DNS. Only loopback had ever been exercised; its test asked `_allowed` about names only. Fixed in the same PR: the
addresses an allowed name resolves to are allowed at `connect`, nothing else is
(`tests/test_persistence_egress.py::test_a_configured_remote_host_is_reachable_at_the_address_it_resolves_to`, which fails
on the old code). A transport failure, so by the stopping condition one more attempt, same design, nothing else changed.

## Result [ran] 2026-10-13 21:02 (attempt 3) — SHOWN

`demo.json`, `events.jsonl`, `gateway.log`, `llama-server.log`; the recording is `docs/img/demo-router.gif` (24 s, VHS,
`demo-router.tape` — the recording is the run, nothing re-enacted). The user's MacBook Air M4 16 GB, llama.cpp (Homebrew,
Metal), Gemma 4 E4B Q8_0 + `lora-tracker-out-s0-f16.gguf`.

| turn | session | route | calls | wall |
|---|---|---|---|--:|
| "Details on HW-245?" | 1 | **local** | `issue_get HW-245`, `put issue`, `put component` | 7.0 s |
| "Transition it to in review." | 1 | **local** | `get issue` → HW-245, `issue_transition HW-245 in_review` | 3.2 s |
| "How do you say 'deadline' in French?" | 2 (new) | **frontier** | none — `OUT OF SCOPE`, Haiku 4.5 answered (*délai* / *échéance*) | 2.6 s |

Frontier spend: 1 call, 18 + 69 tokens, **US$0.0004** of the US$0.50 cap. The first wall time includes llama.cpp's
first prompt on a cold cache.

**What this shows and what it does not.** One session, on the edge runtime: the member serves what its tools cover and
abstains on what they do not, and the role's egress takes it — on the condition ROUTE1 measured (abstention as a session's
first turn). It does **not** show abstention mid-session (attempt 1: not shown, one sample) and is not a rate.

**Three attempts, all kept:** 1 — member did not abstain mid-session (the brief's design, out of ROUTE1's measured
condition); 2 — redesign 1, member abstained, transport failed on the egress bug; 3 — the same design with the bug fixed.
