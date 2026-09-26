"""The model family, in one place — CLAUDE.md §0 and docs/ARCHITECTURE.md §6.

M1b **[ran]** 2026-09-25: `email-full` is released on SMALL (`releases/email-full@v3.json`); `desk-commitment@v3` too, trained on
both desk bands (M1d **[ran]**); `distributor-wiki@v1` on SMALL. PREVIOUS now holds only the control arms.

SMALL is the base every NEW member is trained on: Gemma 4 E4B, the user's decision of 2026-09-25 on B1 **[ran]**
(a tie with Qwen3.5-4B on W9, 38 vs 35 and 35; the development stack targets Gemma). PREVIOUS is the base the
released members were trained on (`releases/*@v2.json`); the serving pool keeps it until each member is re-released
on SMALL through the release gate, which is why `pool_base` and `region_release` do not read SMALL. LARGE is the
large half of a pair on the same family, chosen to run on a Mac mini — NOT measured yet (B2 is its gate).
"""
SMALL = "google/gemma-4-E4B-it"
PREVIOUS = "Qwen/Qwen3.5-4B"
# The large half must run on a Mac mini after training (the user, 2026-09-26): 12B dense first — a LoRA on a dense
# model is the case this repository already serves — and 26B-A4B (MoE, 4B active, all 26B resident) second.
LARGE = "google/gemma-4-12B-it"
LARGE_ALTERNATIVE = "google/gemma-4-26B-A4B-it"
