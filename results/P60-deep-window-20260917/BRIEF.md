# P60 — the generable window: a trained target on a deeper band (Phase 2 → 3 → 4, reopened)

**Pre-registered 2026-09-17, the review's step 3.** The closure of M2 rested on a wrong
argument (*a trained target leaves the ordering trivial*); what the runs prove is that
the window is absent **in two easy regions with an untrained target**. This buys the
arm that was skipped.

## Hypothesis, with the number that kills it

> There is a band of desk `commitment` deep enough that a **trained** 32B reaches
> $Q(T) \ge 0.90$ while the trained grades `g75 / g200 / g600` **do not saturate** —
> at least one adjacent pair resolved by the verifier, paired $p \le 0.05$.

Killed if either half fails: the grades all sit at 1.000 (no ordering), or the trained
target sits resolvably below the best grade (§7.2 fails under `≥`).

## 3a — the band, built (zero GPU) **[ran]** 2026-09-17

`commitment_deep`, opt-in (`generate(n, seed, regions=("commitment_deep",))`), its own
RNG, its own thread ids; **the shallow suite P51/P55b scored did not move a byte** —
pinned by hash in `tests/test_desk_deep.py`, regenerated and checked against P55b's
240 recorded truths: **0 mismatches**.

| depth | thread | last message | promises · distractors |
|---:|---|---|---|
| 1 | ask · my promise | mine | 1 · 0 |
| 2 | … · sender proposes a date | sender's | 1 · 1 |
| 3 | … · my revised promise · ack | sender's | 2 · 1 |
| 4 | … · sender proposes again · my final · ack | sender's | 3 · 2 |

The answer is **my latest promise**; from depth 2 on `message(id)` returns the
sender's text, so the chain must call the desk's `thread_history` (now carrying the
previews — the desk's surface only; the triage surface is untouched) and discriminate
my dates from the sender's. The verifier accepts **exactly one named date**: an answer
listing two has decided nothing.

The corpus (`training/harness/data_desk_deep/train.jsonl`, 600 rows, 150 per depth,
every evaluation prompt excluded by content) teaches the **oracle's** chain —
`thread_history` then the date — **not the target's**, on purpose: the review named
the confound (a corpus written by the target makes α measure the target's style).
Grades `g75 ⊂ g200 ⊂ g600`, every depth in each.

**An instrument fault found while building it:** #206's date verifier named its month
table `MONTHS`, shadowing the generator's, so every desk drawn since had silently
moved. Restored; the guard exists because of it.

## 3b — preflight: does vLLM apply a LoRA on the AWQ 32B? (10 min A100)

A toy adapter on `Qwen2.5-32B-Instruct-AWQ`, `verify_substrate` G1 with the empty-arm
rule. **If not applied, option A dies here, for the right reason, and the closure of
M2 is signed with that.**

## 3c — the trained target (≈ 1 h A100)

QLoRA on the 32B, the deep corpus, the documented recipe. Served on the AWQ base
(3b says whether that is sound). Measured on the 240 deep cases in corpus mode.

## 3d — the grades and the gates (1 session A100)

`g75 / g200 / g600` on the deep band, base as control, corpus mode; **M1** on adjacent
pairs; **M-target under §7.2's `≥`** — the trained 32B against `g600`. If both hold,
M2 runs in the same session (three α per case, verdict table unchanged). If not, the
closure is signed with the right arm run.

## What it cannot conclude

Nothing about a real-data suite; nothing about latency; nothing beyond `commitment`.
