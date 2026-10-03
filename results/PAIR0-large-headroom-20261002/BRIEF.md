# PAIR0 — does the large half buy anything on real documents? Headroom before any pair is trained

**Written 2026-10-02, before anything runs.**

## What and why

The speculative pair works as a mechanism — the large LoRA accepts more of the small LoRA's drafts (B4 **[ran]**, α
0.871 → 0.898) and speculative decoding with a LoRA runs 1.7–2.1× in vLLM (F0, C0 **[ran]**). But on Gemma the large half
**bought no accuracy** in any region measured (B3 **[ran]**: 12B + LoRA 9/40 against E4B + LoRA 10/40; B5: the E4B alone
does 37/40 once taught). A pair accelerates a large model nobody has shown is needed. The real-document line is the
hardest region the project now has — the member's remaining misses are choosing a statement among many — and it has
never been run on the 12B. **Before training a 12B member, one control: the two bases, untrained, under the served
runtime.**

## Arms (no training)

| arm | model | provider |
|---|---|---|
| `base-walks+page+top8` | `google/gemma-4-E4B-it`, bf16 | vLLM, one Colab L4 |
| `base-walks+page+top8` | `google/gemma-4-12B-it`, bf16 | vLLM, one Colab A100 |

PAGE0's 52 rows on `knowledge/hazwaste-regs` (40 CFR 262), the served runtime: full-text entry on every shelf, fallback,
pages with their statements, `page_top = 8`; `--max-model-len 16384`; the strict grader. Beside, for scale, `real-none-s0`
(E4B + LoRA) under the same runtime **[ran]** PAGE0/FMT0: 33–34/44 answerable.

## Verdict (fixed here), 12B against E4B, paired on the answerable rows

- **LARGE HAS HEADROOM** — the 12B beats the E4B at exact sign test $p \lt 0.05$: size reads real documents better
  untrained, so a 12B member (the large half) is worth training next, against `real-none-s0`.
- **LARGE TIES** — no significant difference: on this region, as on B3's, size is not the lever; no 12B member is trained
  for it, and the pair stays a speed result without a region that needs the large half.
- Beside: refusals, multi-hop and one-hop apart, value-right, both against `real-none-s0`.

## Stopping condition

Two scoring sessions (one per base); the set, runtime and bars do not change after the first walk.

## Run log

- **E4B [ran]:** 29/52 (`pair0_e4b.json`), 0 errors.
- **12B attempt 1 — VOID, an instrument failure** (`attempt1_pair0_12b.json`): 8/52, and read where it happens the bare
  12B wrote its thought channel (`<|channel>thought…`, printed as `thought` lines) with thinking off — `enable_thinking=False`
  only omits the `<|think|>` token — and on many rows looped on it until the call budget ran out (34 of 43 misses: no
  citation). CLAUDE.md §3: a bare base that thinks its tokens away scores as a floor. **Fix, the instrument's first
  change:** `wiki_arm --empty-thought` prefills an empty channel (`<|channel>thought\n<channel|>`) for the 12B; the E4B
  arm, which never opened the channel, stands as run. The set, runtime and bars do not move.

## Result

*(written after the run)*
