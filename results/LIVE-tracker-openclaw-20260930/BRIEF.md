# LIVE-tracker — `tr-s1` block-less, through OpenClaw, on the user's Mac

**Written 2026-09-30, before anything runs.** The next step the user agreed to after H3 **[ran]**
(`results/H3-tracker-corpus-v2-20260929`: `tr-s1` 158/160 with the tool block, 156/160 without it).

## What and why

H3 measured the tracker member on vLLM bf16 through a scripted client. This run serves the same member the way the
product would on one machine — `edge`: llama.cpp on the user's Mac, the E4B as **Q8_0** GGUF, `tr-s1`'s LoRA converted to
GGUF (f16) — behind the gateway with the **operational memory on and the tool block off**, and drives it through
**OpenClaw**, a real agent runtime that keeps its own conversation (`--session-id`). It is a demonstration with a
pre-registered bar, not a measurement of the member: a different arm from H3's (another runtime, another quantisation),
said so.

## Setup (all local; no Colab)

    llama-server -m ~/lora-kernel-models/gguf/gemma-4-E4B-it-Q8_0.gguf \
        --lora ~/lora-kernel-models/gguf/lora-tracker-wf-s1-f16.gguf --port 8792 -c 8192 -ngl 99
    python -m examples.school.gateway --org tracker --member tr-s1 --upstream http://127.0.0.1:8792 \
        --tokenizer google/gemma-4-E4B-it --memory --no-tool-block --max-calls 6 --port 8765 \
        --log results/LIVE-tracker-openclaw-20260930/events.jsonl
    python -m examples.tracker.live_tracker --events results/LIVE-tracker-openclaw-20260930/events.jsonl \
        --out results/LIVE-tracker-openclaw-20260930/live.json

`lora-tracker-wf-s1-f16.gguf` was converted from `~/lora-kernel-adapters/H3-tracker-wf-s1/adapters.tgz` (adapter sha256
`33a8d32b…` in H3's `train_tr_s1.json`) with `convert_lora_to_gguf.py --outtype f16` on 2026-09-30.

## The sessions

Three, one per role, on the gateway's own store (`db.build()`, harborworks), H3's held-out wording, played in order
(`live_tracker.sessions`) — 14 turns, 8 of them dependent:

- **lead** — "Please report a bug — Invoice PDF shows the wrong total" → "Let Ana own it." → "Critical bugs — what's the
  policy?" → "How is the current sprint going?" → "Bring back the bug you just filed."
- **developer** — "Details on HW-245?" → "Transition it to in review." → "Track 3h against it." → "Its component — who owns
  it?" → "Annotate it: tested with a large account"
- **qa** — "What does HW-254 look like?" → "QA passed, it's done." → "Done criteria for tests?" → "Remark on it: tested with
  a large account"

The harness oracle solves all 14 on one store, block-less (`tests/test_tracker.py`): a miss is the runtime's or the
member's, never the script's.

## Verdict (scored per turn on the gateway's own event, by H3's `turn_right_h3`)

| | condition | reading |
|---|---|---|
| **PASSED** | every dependent turn right **and** ≥ 13/14 turns | the block-less member with memory survives the edge runtime and a real agent |
| **FAILED** | otherwise | read where it happens: runtime (no gateway event, OpenClaw's rewrite of the request), quantisation (Q8_0 vs bf16), or the member (H3's two open failures) |

A turn with no gateway event is a transport failure and is reported apart, never scored as the member's.

## Not in this run

A second pass for variance; the video (recorded on the same setup once PASSED); `tr-s0` on the edge.

## Result

*(written after the run)*
