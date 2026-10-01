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

## Result

*(written after S)*
