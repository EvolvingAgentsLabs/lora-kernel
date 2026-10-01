# H5 — does training only what the model writes cost anything where results are short?

**Written 2026-10-01, before training.** REAL3 **[ran]** found that `training/s4_train.py` had always put the loss on the
whole text — system, request and every tool result — and that on real pages read whole this taught a LoRA to write the
pages (1/23) where the span-masked loss gave 18/23. Every member before REAL3 was trained the whole-text way. Their tool
results are short lines, so it never visibly failed — but whether it cost them anything, and whether the span-masked loss
can be the **default recipe**, is unmeasured.

**Headroom, checked first:** the tracker member is near the ceiling (`tr-s1` 156/160 on H3's suite, 149/160 on H4's, its
11 misses one phrasing). **H5 cannot show a gain worth the name; it is an equivalence test**, and that is the decision it
serves: adopt the span-masked loss for every member, or keep the whole-text loss where results are short.

## The arms (one A100 to train, one L4 to score)

- `tr-s3` — **`tr-s1`'s corpus byte for byte** (`data_sessions_h3/train_harness_spans.jsonl`: the same messages, a test
  holds it, plus the model's spans), the same recipe and seed, **loss on the model's spans only**.
- `tr-s1` — H3's member, whole-text loss. The baseline is our own previous version.
- Both block-less, with the operational memory and key capture, on **H4's fresh suite** (60 sessions, 160 dependent turns).

## Verdict (`h5_arm.reading`, tested)

- **EQUIVALENT** — no paired difference and totals within 3 dependent turns → the span-masked loss becomes the default
  recipe for every new member.
- **BETTER** — an improvement ($p \lt 0.05$) → default, and the earlier members are owed a retrain.
- **WORSE** — a regression → the whole-text loss stays for short-result members; the span-masked loss only where results
  are long.

## Result [ran] — VOID as written: `tr-s3`'s first turns 50/60 (bar 90 %)

T on an A100 (attempt 1 stopped by the user's pause, attempt 2 trained); S: two failed uploads (48 MB chunks timed out on a
0.2 MB/s uplink — the chain now sends 16 MB chunks with retries), then two L4 sessions (the first ended at Colab's cap after
`s1-noblock`; the second scored `s3-noblock`), G1 applied for both, 0 errors. `h5.json`.

| arm (block-less, memory + capture, H4's suite) | first | dependent | independent |
|---|---|---|---|
| `tr-s1` (whole-text loss) | 60/60 | 149/160 | 60/60 — H4's numbers again |
| `tr-s3` (span-masked loss) | **50/60** | 140/160 | 60/60 |

**Read where it happens — one phrasing, one cause.** All 10 first-turn misses are the lead's *"New defect — …"*: `tr-s3`
calls `issue_create` with `type=defect` (the tool refuses: story or bug), then `put`s an invented key, and both dependent
turns of those 10 sessions fail after it (`issue_assign` 10, `issue_get` 10) — the whole of the gap. `tr-s1` writes
`type=bug`.

**The mechanism, as a hypothesis to test (not a result):** the whole-text loss also trained on the **tool block** the corpus
rendered in two thirds of its rows — including that `type` is `story` or `bug`. A member served **without** the block
recalls it from there. The span-masked loss conditions on the block but never learns it, so block-less it does not know the
enum. If so, block-less serving rests on the tool block being *learned*, and the recipe is: mask the tools' results, keep
the loss on the tool descriptions.

**The attribution arm, bought because there is an effect:** `tr-s3` **with** the tool block (`s3-harness`) against
`tr-s1` with it (`s1-harness`), same suite, no training — if `tr-s3` recovers the lead's turns with the block in front of
it, the hypothesis holds. Queued after REAL5.
