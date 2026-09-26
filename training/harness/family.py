"""The model family, in one place — CLAUDE.md §0 and docs/ARCHITECTURE.md §6.

EVERY RELEASED MEMBER IS ON SMALL (2026-09-26): `email-full@v3` (M1b **[ran]**), `desk-commitment@v3` trained on both desk
bands (M1d **[ran]**), `distributor-wiki@v2` with comparisons (B5 **[ran]**). The service's entry point
(`serve_tunnel`) defaults to SMALL. PREVIOUS holds only the control arms; `pool_base` and `region_release` keep it as their
default because it reproduces the runs they recorded — the chain always passes BASE.

SMALL: Gemma 4 E4B, the user's decision of 2026-09-25 on B1 **[ran]** (a tie with Qwen3.5-4B on W9, 38 vs 35 and 35; the
development stack targets Gemma). LARGE: the large half of a pair, chosen to run on a Mac mini — one id space with SMALL
and a LoRA served applied (B2 **[ran]**); its LoRA raises acceptance of SMALL's drafts, α 0.871 → 0.898 (B4 **[ran]**);
it buys no accuracy once SMALL is taught the band (B3, B5 **[ran]**).
"""
SMALL = "google/gemma-4-E4B-it"
PREVIOUS = "Qwen/Qwen3.5-4B"
# The large half must run on a Mac mini after training (the user, 2026-09-26): 12B dense first — a LoRA on a dense
# model is the case this repository already serves — and 26B-A4B (MoE, 4B active, all 26B resident) second.
LARGE = "google/gemma-4-12B-it"
LARGE_ALTERNATIVE = "google/gemma-4-26B-A4B-it"
