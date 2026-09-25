# M8 — a school-staff trajectory LoRA, for the demo that has to work (pre-registered 2026-09-25)

**Why.** The school demo's first live run **[ran]** (`results/DEMO-school-20260925/`): every part of the system
behaved — identity, tenant boundary, held writes, a director's approval, egress, the log — and the bare
`Qwen3.5-4B` passed 3 of 8 scenes: it invented an answer after a correct call, retried a denied call, looped
after a write, skipped calls. W9 **[ran]** took the same missing habit from 0/40 to 35/40 with a corpus of walks.
**One unknown here: does a corpus of full gateway turns give the school's roles that habit?**

**The corpus [ran, zero GPU]** — `examples/school/generate_turns.py`: 700 turns played through the gateway's own
loop with a scripted oracle as the model, so the system and user turns are byte for byte what the gateway serves
and the assistant turn is the real chain — the call, the real tool result, an answer built from it. Kinds: read 307,
write 151, held 75, denied 93, out of scope 74. Each case on its own synthetic school (a new seed, a second tenant
for denials). Gate PASSED: no demo request and no held-out request in the corpus, no shared world, every walk the
kind it was meant to be. **Held-out: 70 turns**, their own worlds, the evaluation wording.

**Arms.** T0, T1: `school_arm --train-seed 0|1`, one A100 each, W9's recipe (`release_gate.RECIPE`). S: one L4,
`--arms base,school-s0,school-s1` — every arm on the 70 held-out turns and on the demo's scripted day.

**Verdict — written first (`school_arm.analyse`).** Credit per turn = `demo_run.check` passed: the intended call (or
none), the denial or the hold where one is due, the route, a clean reply, no loop, a grounded answer. On the 70,
paired, exact sign test on discordant pairs: `school-s<k> vs base` an improvement for **every** seed → **PASSED**;
for some → **DRAW-DEPENDENT**; none → **FALSIFIED**. The demo day (8 scenes, the fixed demo school) is reported
beside — a demonstration, not a sample. G1 not applied → VOID.

**Model, provider.** `Qwen/Qwen3.5-4B`, bf16, vLLM 0.30 on Colab; no API provider. Thinking off. **Ceiling:** 2 A100
+ 1 L4. Every piece was first run end to end against `training/harness/fake_vllm.py` (`tests/test_school_demo.py`).
**Not measured:** WhatsApp (the user's call: not yet), a real identity provider (the token is HS256 with a demo
secret), Postgres (sqlite), a real payment provider (a mock ledger).

## Amended before any arm ran, 2026-09-25 — the base is Gemma 4 E4B, and its headroom is bought first

B1 **[ran]** chose Gemma 4 E4B for new members (a tie on W9, the user's rule). And its bare base leaves less headroom
than Qwen's did (it walks W9 untrained 19/40 where Qwen walked 0/40), so the order changes: **H — one L4, the bare
Gemma on the 70 held-out turns and the demo day** (`school_arm --arms base --base google/gemma-4-E4B-it`). If the bare
base already passes ≥ 90 % of the held-out turns, no adapter is trained and the demo runs on the bare base; otherwise
T0/T1 train on Gemma and S scores `base, school-s0, school-s1`, the verdict as written above. The corpus is unchanged.

## H — the bare Gemma's headroom **[ran]** 2026-09-25 · 27/70, demo day 3/8 — the adapter is bought

One L4, `school_headroom.json`. Held-out 27/70 (39 %): out-of-scope 12/12, denied 4/4, read 11/30, write 0/19, held 0/5.
Failed checks: the intended call not made 27 (Gemma writes the arguments as XML attributes —
`<billing_charge amount_cents=4500; membership_id=1>` — a form the loop does not parse), a raw tag as the reply 18, an
answer not grounded in the tool's result 16. Demo day 3/8 (an invented agenda again: "Math test: Chapter 3 review").
Under 90 %: T0/T1 train on Gemma, as amended.
