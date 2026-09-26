# LIVE-school-openclaw — the school demo through a real agent runtime (pre-registered 2026-09-26)

**Why.** The school demo's 15/15 (`results/DEMO-school-diagram-20260926`) was driven by scripted HTTP requests. The
reference system runs **OpenClaw instances, one per role**, against a model API; "part of that traffic on a local model"
means OpenClaw itself, unmodified, pointed at the gateway. OpenClaw had run live only against the email expert (P63, 40/40).

**What was built.** `examples/school/gateway.py` serves a live runtime: buffered SSE for `stream: true` (OpenClaw streams
by default), `GET /v1/models`, the user turn as a list of parts, and **the person's request read out of what OpenClaw
actually sends** (`runtime_request`): OpenClaw appends a user message of its own internal context *after* the request,
stamps the request `[Sat 2026-09-26 20:41 GMT-3] …` and adds a `Runtime: agent=…` footer — the first live turn read the
context and routed the question to a person. `python -m examples.school.gateway --upstream … --member school-s0` writes
one OpenClaw config patch per user, each carrying that user's signed token as the provider key; `--frontier-url /
--frontier-model / --frontier-key-env` make the frontier egress real (the key from the environment). `examples/school/
live_openclaw.py` plays `demo_run.SCENES` through `openclaw agent --local`, one profile per user, and scores each turn
with the scripted demo's own `check` on OpenClaw's printed reply and the gateway's event for the turn.

## Wiring run **[ran]** 2026-09-26 — the real runtime, a stand-in model: 15/15

OpenClaw 2026.9.4 (3a9d69d), the real binary, one profile per user; the model a scripted stand-in (`fake_vllm`,
tests' `scripted`) because Colab granted no GPU. **15 of 15 scenes pass** (`wiring_stand_in_model.json`): the read, another
school's student refused by the tool, the enrolment, the $45 charge held, the planted instruction, the all-families
announcement held, frontier and person egress, and the seven boxes. **What this proves:** the transport — token → role,
SSE, OpenClaw's message shape, tools, holds, the event log — end to end with the unmodified runtime. **What it does not:**
anything about the model; the replies are the stand-in's.

## The run that counts — pending a GPU

`serve_tunnel` on a Colab L4 serving `gemma-4-E4B-it` + `school-s0`, the gateway here with `--upstream <tunnel URL>`, and
`live_openclaw`. **Verdict, written first:** the scripted run's 15/15 is the bar — every scene that passed there must pass
through OpenClaw; a scene lost is a difference the runtime makes (its system prompt, its history, its wrapping) and is
read where it happens. The frontier egress runs real when a key is configured (`--frontier-*`), else says it is not.
