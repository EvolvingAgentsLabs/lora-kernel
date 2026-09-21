# M6 — pricing the P41/P62 replay both ways, zero GPU (2026-09-21)

**Question.** Milestone 6's gate (`docs/PLAN.md` §1): "the local share saves more than it costs, on
real traffic." No real traffic exists; the closest thing on disk is the 240-case P41/P62 replay
(150 email-full cases, 90 fluids cases), already scored, already routed — nothing here retrains or
re-serves anything. **Money was never measured before this** (`docs/FRAMEWORK.md` §5 row M: "nothing").

**What is priced, from records already on disk, not re-run:**
- `results/P41-routing-20260915/pool_results.json` — 150 email-full transcripts, served locally.
- `results/P41-routing-20260915/frontier_fluids.json` — 90 fluids cases, actually served by
  `google/gemini-3.8-flash` (confirmed in the file's own `model` field).
- `results/P62-route-per-request-20260918/replay.json` — confirms the split: under the by-request
  policy, out = 90 = exactly the 90 fluids cases; the 150 email cases are exactly the local share.
  (`out_share` 0.375 = 90/240.)

**Rates, sourced today, dated, [read]:**
- `gemini-3.8-flash`, paid tier: **$0.75 / 1M input tokens, $3.75 / 1M output tokens**, promotional
  through 2026-12-31 (then $1.50 / $7.50) — `https://ai.google.dev/gemini-api/docs/pricing`, fetched
  2026-09-21.
- The Colab GPU rental rate ($/compute-unit or $/GPU-hour) could **not** be fetched live — the
  pricing page (`colab.research.google.com/signup`) renders its price table client-side; two attempts
  (the signup page, a support.google.com answer page) both returned no usable numbers. **Not
  fabricated.** The local share's token volume and turn count are computed below so a real rate is a
  one-number substitution away, and the user rents this card and knows the real number better than a
  scrape would.

**Tokenizer.** `tiktoken` `cl100k_base` — not the pool's own tokenizer (Qwen) nor Gemini's, an
approximation stated as one. It is the same approximation for both arms, so the *comparison* is not
biased by the choice; the absolute numbers carry that caveat.

**Method — email (exact, no approximation beyond the tokenizer):** each transcript is a list of
turns; for every assistant turn, cost is billed the way a chat API bills it — input = every token in
every turn *before* it (the conversation resent), output = that turn's own tokens. Summed over all
assistant turns in all 150 conversations.

**Method — fluids (a stated approximation, biased toward overstating the frontier's real cost, i.e.
conservative in the direction that makes the local share look *better*):** the `chain` field
interleaves model-generated tool calls and tool-returned results as one string; splitting them needs
re-deriving the turn boundary from `accept_rank.py`'s own loop, not done here. Instead: `statement`
is priced as input once; `chain` is priced entirely at the **output** rate (the higher of the two),
which overstates the true frontier cost of the 90 fluids cases actually sent out.

**What this run answers, and what it does not.** It answers: what does the design's current 37.5 %
frontier share actually cost, in dollars, against the ceiling of sending everything there — a real
number, sourced, computed from real records. It does **not** answer whether the local 62.5 % costs
more or less than what it saves, because that needs the GPU rate. **Falsifier for the part that can
run:** none — this is an arithmetic pass over existing records, not an experiment with a stop
condition; the number is reported whichever way it comes out, same as every other result here.
