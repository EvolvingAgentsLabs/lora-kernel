# LIVE-library — the real-document member, through OpenClaw, on the user's Mac

**Written 2026-10-01, before anything runs.** The member the user accepted after REAL4 (`real-none-s0`: walks over real
documents of another family, span-masked loss, unanswerable walks) served the way the product would on one machine:
llama.cpp (E4B **Q8_0** + the LoRA as GGUF f16, context 16,384) behind `examples/library/serve.py` — an
OpenAI-compatible endpoint running REAL4's runtime (the question's full-text entry on every shelf, fallback, pages opened
with their statements), egress closed to llama.cpp — and driven by **OpenClaw** (`openclaw agent --local`, one fresh
session per question).

**The questions: REAL4's 52** (REAL3's fresh 40 + 12 unanswerable, 6 adjacent), graded by REAL4's grader on the endpoint's
own walk record — value and strict citation, or `Not in my library.`

**A different arm from REAL4's** (another runtime, another quantisation, OpenClaw in the loop), said so. REAL4 on vLLM bf16
**[ran]**: `real-none-s0` 38/52 — headline 16/23, refusals 15/16.

## Verdict (fixed here)

- **PASSED** — ≥ 34/52 (REAL4's 38 less vLLM's observed spread on this set) **and** refusals ≥ 13/16 **and** headline ≥ 14/23.
- **FAILED** — otherwise; read where it happens: transport (no walk recorded), quantisation, OpenClaw's rewrite of the
  question, or the member.

## Run log

- **Smoke test (3 questions) [ran]:** llama.cpp returned `<search shelf=wiki>…` without its closing tag — it drops the
  stop string, and `close_open_tag` only rebuilt bare tags, so no search ran. The rebuild now accepts a tag with
  attributes (`training/harness/accept_rank.py`, test `test_a_dropped_stop_string_is_put_back_on_a_tag_with_attributes`).
  A fix to the transport, before any scored row.
- **Attempt 1 — out of memory, nothing scored** (`llama-server_attempt1_oom.log`): context 16,384 on the 16 GB Mac while
  another session's llama-server held ~8 GB. Not killed; waited until it was gone.
- **Attempt 2 — the run** (`attempt2_llama-server.log`, then `llama-server.log`): context **12,288**, `-b 512 -ub 512` —
  a change of the edge configuration from this brief's 16,384, said so; the questions, grader and bars did not move.

## Result [ran] — PASSED

52 questions through **OpenClaw 2026.9.4** (`openclaw agent --local`, a fresh session each), 2026-10-01 21:32 → 21:54
(22.5 minutes), on the user's MacBook Air. `live.json`, `walks.jsonl`, `run.log`.

| arm | headline (23) | refusals (16) | one-hop (13) | all (52) |
|---|---|---|---|---|
| **`real-none-s0`, llama.cpp Q8_0, through OpenClaw (this run)** | **16** | **15** | 5 | **36** |
| `real-none-s0`, vLLM bf16, the harness (REAL4) | 16 | 15 | 7 | 38 |

- **Verdict: PASSED** — 36 ≥ 34, refusals 15 ≥ 13, headline 16 ≥ 14. On the headline and the refusals the member served
  on the Mac matches the measured one exactly; the two rows lost are one-hop.
- **Latency:** the endpoint's walk median **13.0 s** (max 43 s); a question through OpenClaw median 16.3 s (max 119 s).
- **Read where it happens — every loss beside the member is the edge's, not the member's:**
  - **Context:** 4 walks overflowed 12,288 tokens (requests of ~15,250) after opening `1910.178` — the powered-industrial-
    trucks page, ~7k tokens read whole — and ended with no line. At vLLM's 16,384 they fit.
  - **OpenClaw:** one question took 119 s and no walk was recorded (`no-walk`); on 3 slow forklift questions OpenClaw
    re-sent the question wrapped in its own envelope (`[Queued user message from a previous active turn …] … Continue the
    current task …`), and the runtime's first full-text search ran on the wrapper.
  - **What the user saw:** the endpoint showed a walk with no final line as `Not in my library.` — 6 of 51 walks looked
    like refusals and were failures. The grade read the final line, so they counted as wrong, never as refusals; the reply
    now says the walk ended without an answer (`serve.NO_ANSWER`, test `test_a_walk_with_no_answer_is_not_shown_as_a_refusal`).
- **Owed, not done:** strip OpenClaw's queued-message envelope before the runtime reads the question; a page budget (open
  a long page by its matched statements, not whole) so a 7k-token page fits a 12k context.
