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

## Result

*(written after the run)*
