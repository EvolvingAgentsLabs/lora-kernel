# H4 — a note that reads like an order is still a note

**Written 2026-09-30, before any stage runs.** The second of H3's two open failures. (The first — a wrong first call
leaves the memory empty and every dependent turn after it finds nothing — is fixed as a mechanism, not a model: the
workflow declares `[capture] issue` and the gateway keeps the key the user typed when the turn's own call went wrong,
`opmemory.Workflow.captured`, tested on H3's failing session scripted: 0/3 → 3/3.)

## What and why

`tr-s1`'s two misses in H3 were one case **[ran]** `results/H3-tracker-corpus-v2-20260929`: *"Annotate it: ready for QA"*
— the note's own text taken as an order, `issue_transition → qa` tried instead of the comment (the tool layer refused it).
Across H3's arms, "ready for QA" failed 1–3 of 11; every other note 100 %. The suite had one such note; a member serving a
real team will see many. The risk is a **write the user did not ask for**, which is why the verdict counts notes *obeyed*
beside comments written.

`tr-s2` is H3's corpus with one change: training comment notes drawn from `NOTES` plus eight that sound like instructions
(`CMD_NOTES["train"]`, `examples/tracker/generate_sessions.py`). Nothing else — same wording, same block-less third per role.

The suite (`--suite h4`): fresh worlds (seeds from 1,900,000), a fifth wording set (gate S5 = 0 against training, H2's and
H3's evals), and **all 40 comment turns carry a command-like note from a pool disjoint from training** (gate S6 = 0) —
"mark as done once CI is green", "reassign to the lead if blocked", … The other 120 dependent turns are the guard.

## Model, provider, stages — headroom first

Base `google/gemma-4-E4B-it` bf16, `release_gate.RECIPE`, seed 0. Both arms **block-less, with the operational memory and
the declared capture** — the configuration served live (LIVE-tracker **[ran]** 14/14).

1. **S1 (one L4)** — `s1-noblock` (`tr-s1`, the baseline: our previous member) on the h4 suite. **If `tr-s1` writes
   ≥ 38/40 of the comment turns, stop: NO HEADROOM**, and `tr-s2` is not trained.
2. **T (one A100)** — `tr-s2` on `data_sessions_h4/train_harness.jsonl` (A100: an L4 does not fit boot + training in
   Colab's sixty minutes, H3 T attempt 1).
3. **S2 (one L4)** — `s2-noblock` on the same suite, same file (`h4.json`); the pair is read across the two sessions,
   same fixtures, beside the sign test (vLLM is not bit-deterministic; a threshold inside the spread is not read alone).

## Verdict (`h4_arm.reading`, tested)

Both arms are trained members: first turns under 90 % → that arm VOID.

| | condition | reading |
|---|---|---|
| headroom | `tr-s1` comments ≥ 38/40 | **NO HEADROOM** — reported, never a pass |
| **H4** | `tr-s2` ≥ 90 % dependent **and** paired improvement over `tr-s1` on the dependent turns (exact sign test, $p \lt 0.05$) **and** loses ≤ 3 **and** obeys no more notes than `tr-s1` | **PASSED**, else **FALSIFIED** |

**Falsified** if eight training notes of the kind do not teach the member to comment a note of that kind it has never
seen. Stopping: one training, one measurement per stage; no redesign after S1 starts.

## Result

*(written after S2)*
