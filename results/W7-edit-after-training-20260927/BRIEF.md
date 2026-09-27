# W7 — edit one statement after training; the answer must follow the library (pre-registered 2026-09-27)

**Why.** The project's thesis: *the LoRA is the specialist who knows how to use the library; the weights hold the
navigation, the base holds the content.* If that holds, changing a fact is a commit to a Markdown line, not a retraining.
`docs/MEMORY.md` §W7 has asked this since 2026-09-19 and it was never run. The user took it, 2026-09-27, as the one piece
of an external review worth measuring: its "atomic edits on Git" step, measured instead of built.

**Where it can fail.** Not in the evaluation world: the member never saw those values, and following them is what W9
already measured. **It can fail in the member's own training worlds, on its own training questions**, where 600 walks may
have written the values into its weights. That is where the library has to win.

**What.** `training/wiki/w7_edit.py`.
- 40 rows of `distributor-wiki@v2`'s own corpus (`train_cmp.jsonl`), across 15 families. Each answer is numbers or times
  only (extensions, hours, cut-offs, lead times, packs…); comparisons and refusals are excluded.
- Per fixture, the row's world is written to Markdown. **One line of one page is patched**: the supporting statement's
  value is replaced by a new one of the same shape that appears nowhere else on the page. Then the library is reloaded
  from disk. Example:

  `- §extension Wanda Penhale can be reached on extension 5090.` → `+ … extension 3458.`

**Arms.** Each is the member `distributor-wiki@v2` (E4B + `wiki-cmp-walks-s1`), served by vLLM 0.30:

| arm | library | right means |
|---|---|---|
| control | unedited | the old value, cited to its statement (the member answers its own training questions) |
| **edited** | patched | **the new value**, cited to the patched statement, and the old value nowhere in the line (`never`) |
| closedbook | none | reported only: how often the weights still write the old value |

**Instrument, checked at zero GPU [ran].** 40 patches built, each changing one statement line; **the oracle walks every
patched library to the new value 40/40** (`--zero-gpu`). The first version gave 0/40 because the edited row kept the old
answer string; it was fixed before any GPU ran.

**Model and provider.** `google/gemma-4-E4B-it` bf16 + the released adapter (sha `d4d91ea4…`), one Colab L4 session, no
training.

**Verdict, written first (`w7_edit.verdict`).**

| outcome | reading |
|---|---|
| G1 not applied | **VOID** |
| control right on fewer than 32 of 40 | **VOID**: the member cannot answer its own training questions, so there is nothing to follow from |
| edited right on ≥ 90 % of the fixtures the control gets right **and** the old value in ≤ 2 edited lines | **PASSED**: the answer follows the library |
| otherwise | **FALSIFIED**: the weights overrule the library, or the reading breaks |

**Beside the verdict: `memory`**, the closed-book arm writing the old value. If it is ≤ 4 of 40, the weights held little
to overrule, and a pass reads as *reading*, not as *the library winning over memory*. Said either way.

**Stopping condition.** One session, one reading; no redesign after the result.

**Not in this run.**
- Comparisons, where an edit flips which of two items is chosen: the next W7 row if this passes.
- Structural edits: a link moved to another page, a statement deleted.
- Edits on the evaluation world.

## Result **[ran]** 2026-09-27 — **PASSED: 37 of 38 follow the edit, 0 stale**; the weights held the old value on 1 of 40, so this measures reading, not overruling

One L4 session, vLLM 0.30, `distributor-wiki@v2`. G1: applied, 3/3. `w7.json`.

| arm | right | detail |
|---|--:|---|
| control (unedited library) | **38/40** | the member answers its own training questions |
| **edited** (one statement patched) | **37/40**; **37 of the 38** the control gets right | **0 stale**: the old value appears in no edited line |
| closedbook (no library) | 0/40 | **memory 1/40**: the old value, from the weights, once (`14:00`, a product cut-off); otherwise invented numbers or "not in my library" |

**By the table written first: PASSED.** The pre-registered qualifier applies: memory is 1 ≤ 4.

**The three misses, read where they happen.**
- `w1009-train-depot-hours-0`: the walk opened the **patched** statement ("open from 11:00 to 17:00") and answered only
  `17:00`. It wrote half the answer; it did not use the old value (08:00 to 15:00). A reading slip, not memory.
- `w1006-` and `w1025-train-invoice-ext-0`: wrong **identically in the control and in the edited arm**; the cited
  statement does not hold the value. The member's walk fails there with or without the edit.

**What it means.**
- **A fact changed by a one-line Markdown patch changes the expert's answer, cited to the new line, with no retraining.**
  The change never surfaces as the old value: 0 of 40.
- **What it does not show:** the library winning *against* memory. After 600 walks over 32 worlds, the member's weights
  hold almost none of those worlds' values (1/40). It learned the route, not the facts, which is the thesis's other half,
  measured here for the first time. There was nothing in the weights for the library to overrule. A test of overruling
  needs a fact the weights do hold; with this corpus design (values drawn per world) there is none. Said as designed.
