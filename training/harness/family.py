"""The model family, in one place — CLAUDE.md §0 and docs/ARCHITECTURE.md §6.

SMALL is the base every NEW member is trained on: Gemma 4 E4B, the user's decision of 2026-09-25 on B1 **[ran]**
(a tie with Qwen3.5-4B on W9, 38 vs 35 and 35; the development stack targets Gemma). PREVIOUS is the base the
released members were trained on (`releases/*@v2.json`); the serving pool keeps it until each member is re-released
on SMALL through the release gate, which is why `pool_base` and `region_release` do not read SMALL. LARGE is the
named large half of a pair on the same family — NOT measured: no LoRA has been trained or served on it here.
"""
SMALL = "google/gemma-4-E4B-it"
PREVIOUS = "Qwen/Qwen3.5-4B"
LARGE = "google/gemma-4-31B-it"
