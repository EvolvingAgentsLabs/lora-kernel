# LIVE-library 2 — the edge's two losses repaired: OpenClaw's envelope stripped, a long page opened within a budget

**Written 2026-10-02, before anything runs.**

## What and why

LIVE-library **[ran]** (2026-10-01) passed at 36/52 — headline 16/23, refusals 15/16, one-hop 5/13 — against the same
member on vLLM at 38/52 (REAL4). Read where it happened, the losses beside the member were the edge's:

1. **Context:** 4 walks overflowed the Mac's 12,288-token context (requests of ~15,250) after opening 29 CFR 1910.178,
   7,389 Gemma tokens read whole.
2. **OpenClaw's envelope:** on 3 slow questions OpenClaw re-sent the request wrapped in `[Queued user message from a
   previous active turn …] … Continue the current task …`, and the runtime's first full-text search ran on the wrapper.

## The change (the treatment), nothing else

- `examples/school/gateway.runtime_request` strips the envelope (test `test_openclaw_queued_envelope_is_stripped`).
- `memory.runtime.Conversation.page_budget` (served at **2,500** tokens by `examples/library/serve.py`): a page whose text
  exceeds it opens with its statements in BM25 order against the question until the budget, shown in document order,
  then the anchors left out, each openable as `id§anchor`; only the shown statements count as read. On this library
  only 1910.178 exceeds it (2,452–2,558 Gemma tokens after, from 7,389). **Offline [ran]:** the 8 statements REAL4's
  oracle walks need on that page are kept 8/8 at any budget from 1,500 to 3,500 — the budget was fixed at 2,500 from
  that check, before any walk.

Same everything else as LIVE-library: `real-none-s0`, llama.cpp E4B Q8_0 + LoRA GGUF f16, `-c 12288 -b 512 -ub 512`,
OpenClaw 2026.9.4, REAL4's 52 questions and grader, the user's MacBook Air.

**Two changes in one run, said so:** they repair disjoint failures, and each is read where it happens — overflows from
llama-server's log, envelopes from the walk record. The page budget also changes every walk that opens 1910.178 (a
risk to rows that were right), which the paired test below would show.

## Baseline: our previous version — LIVE-library, 36/52, on the same 52 rows

## Verdict (fixed here)

- **REPAIRED** — 0 context overflows **and** ≥ 38/52 (REAL4's vLLM number) **and** refusals ≥ 13/16 **and** headline ≥ 14/23.
- **NO CHANGE** — 0 overflows but below 38: the edge's losses are gone and the score did not follow; read the rows.
- **REGRESSED** — headline below 14, or refusals below 13, or a paired loss against LIVE-library on the same rows
  (exact sign test, $p \lt 0.05$) — the budget cost more than it saved.
- Beside it: the paired count against LIVE-library, rows touching 1910.178 apart, envelopes seen and stripped.

## Stopping condition

One run. The budget, the questions and the bars do not move after the first walk. A transport failure that records no
walk on more than 3 rows voids the run (not the treatment) and is reported as such.

## Run log

- **Part 1 [ran]** (07:02 → 07:21, `run_part1.log`): 31 rows recorded, then the driver stopped on row 32
  (`real3-duty-agreement-31`): the endpoint answered in 25 s (`walks.jsonl`), and OpenClaw held the turn until the
  driver's 600 s timeout, which the driver did not catch. Not a walk lost: a transport fault in the driver.
- **Driver fix, before resuming:** a timed-out OpenClaw turn is graded on the endpoint's walk like every row and flagged
  `openclaw_timeout`; `--resume` keeps the recorded rows. **Part 2** reruns from row 32 (a fresh OpenClaw session; the
  first walk for that row stays in `walks.jsonl` and is not graded). The questions, budget and bars did not move.

## Result [ran] — NO CHANGE: both edge losses gone, the score did not follow

52 rows, 2026-10-02 07:02 → 07:37 in two parts (`live.json`, `walks.jsonl`, `run_part1.log`, `run.log`).

| arm | headline (23) | refusals (16) | one-hop (13) | all (52) | context overflows | envelopes |
|---|---|---|---|---|---|---|
| **this run — envelope stripped, page budget 2,500** | **16** | 14 | **7** | **37** | **0** | **0** |
| LIVE-library (our previous version) | 16 | 15 | 5 | 36 | 4 | 3 |
| REAL4, vLLM bf16 | 16 | 15 | 7 | 38 | — | — |

- **Verdict as written: NO CHANGE** — 0 overflows, but 37 < 38. Not REGRESSED: headline 16 ≥ 14, refusals 14 ≥ 13, and
  paired against LIVE-library **3 : 2** (exact sign test $p = 1.0$).
- **Each repair, read where it happens:** llama-server logged **0** context overflows (4 before); **0** walks carried
  OpenClaw's envelope (3 before). The three wins are exactly the rows the edge had cost: `one-hop-04` and `-06`
  overflowed on 1910.178 yesterday, `-07` recorded no walk. One-hop now equals vLLM's 7/13.
- **The two losses:** `one-hop-03` (cited an id without a section); and **`none-9`** — *"What placard must a truck carrying
  flammable liquids display?"* — refused yesterday, answered today with NFPA 30 from 1910.178: the budget put the
  question's best-matching statement in view of a question the library cannot answer. One row; a cost of selecting by
  the question's words, recorded as such.
- **What remains is the member's, not the edge's:** 2 walks ended after opening a section number as an id (`<open>20</open>`,
  `<open>402</open>`) — the same two as yesterday; 7 unverified citations and the rest of the misses match REAL4's on vLLM.
- **OpenClaw held a turn after the endpoint had answered** on 3 rows (600 s once, which stopped part 1; 300 s twice,
  graded on the walk, both right). The endpoint's walks took median 12.0 s (max 46 s).

**What it means:** on the Mac the member now does what it does on vLLM — 37 against 38, the edge's own losses repaired
and measured at zero. The score's ceiling here is the member's citations, which is the next step (a runtime citation
check on a fresh set), not more edge work. **Owed:** why OpenClaw holds a finished turn.
