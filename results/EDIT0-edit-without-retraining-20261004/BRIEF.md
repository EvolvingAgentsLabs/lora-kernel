# EDIT0 — edit without retraining: a changed statement must change the answer (Spotlight's overwrite property, on our memory)

**Written 2026-10-04, after the edited library and rows are built and checked at zero GPU, and before any model sees them.**

## What and why

The thesis is that *the weights hold the navigation and the library holds the content*. If the knowledge lives in the
library, editing a statement must change the answer with no retraining. PLAN milestone 7's arm 5, *edit without
retraining*, has never run. Percepta's Spotlight Memory ([read] percepta.ai/blog/spotlight-memory) reports the property
for a learned memory: a rewritten key returns its latest value, stale-value rate 0. The review
`docs/review/moe-distillation-and-spotlight.md` §3 maps it here, as the one idea of that architecture this project can
test without pretraining.

## The instrument

- **The edit** (`make_edit.py`): `knowledge-edit/hazwaste-regs` is `knowledge/hazwaste-regs` with **one number changed in
  each of 17 supporting statements** — 20 numbers in total, nothing else touched (`edits.json`). Each new value is +30 %,
  rounded, and printed nowhere else on its page or in its question.
- **The rows** (`questions_edit.jsonl`): PAGE0's 17 rows whose supporting statement was edited — the same questions, the
  new value as the check token, the old one kept as `stale`. **Chosen before any edit run, by a rule:** the member was
  right on each in **both** top-8 records (PAGE0, FMT0), and every answer is a plain quantity — no year, ZIP code, form
  number, page number, or number also spelled in words.
- **The oracle** walks all 17 on the edited library: 17/17 verified, 0 refused (`zero_gpu.json`).
- **Beside it, zero GPU:** an operational-memory `put` on an existing key replaces its value
  (`tests/test_opmemory_overwrite.py`, passing).

## The arm

`real-none-s0` + `+page+top8`, on `knowledge-edit/hazwaste-regs`. Gemma 4 E4B + LoRA, vLLM, one Colab L4, the served
runtime, the strict grader. The member was trained on another document family and has never seen this library, edited or
not, so there is nothing for it to have memorised.

## Verdict (fixed here)

- **EDITS HOLD** — ≥ 16 of 17 rows right with the **new** value, cited to the edited statement, **and** at most 1 row whose
  final line carries an old value (stale).
- **STALE** — 2 or more rows answer an old value: something other than the library supplied it.
- **NEITHER** — fewer than 16 right, and at most 1 stale: the edit broke the walk, not the content. Read where it happens.

## Stopping condition

One L4 session. The edit, the rows and the bars do not change after the first walk.

## Result [ran] — EDITS HOLD: 17 of 17 answer the edited value, 0 stale

One L4, G1 applied, 0 errors (`edit0.json`, `verdict.json` by `read.py`).

- **Verdict: EDITS HOLD** — **17/17** right with the **new** value, each cited to the edited statement (the strict grader),
  and **0** final lines carrying an old value. Changing one number in a statement changed the answer, with no retraining:
  the content the member delivers comes from the library, not from its weights. Milestone 7's arm 5, *edit without
  retraining*, open since 2026-09-19, passes.
- **The operational memory's half [ran]:** a `put` on an existing key replaces its value, session and organisation keys
  alike, never a stale duplicate (`tests/test_opmemory_overwrite.py`).
- **What this does not show:** the rows were chosen where the member was right twice before the edit, so this measures
  whether an edit is *followed*, not whether the member is right more often; and a member trained on this very library
  (none is) would be the harder case — a value it could have memorised.
