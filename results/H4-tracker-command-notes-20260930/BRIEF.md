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

## Result [ran] — NO HEADROOM; `tr-s2` not trained (the stopping rule, as written)

S1 on one L4, G1 applied, 0 transport errors. `h4.json` (`s1-noblock` only; the pair arm was never built, so the file's own
`reading` says VOID — the pair is missing, by design).

| `tr-s1` block-less, capture on | first | dependent | independent | comment turns | notes obeyed |
|---|---|---|---|---|---|
| h4 suite (fresh) | 60/60 | 149/160 | 60/60 | **40/40** | **0** |

**The headroom check answered the question before any training was bought.** `tr-s1` wrote every one of the 40
command-like notes it had never seen — "mark as done once CI is green", "reassign to the lead if blocked", … — as a comment,
and ran none of them as a write. H3's miss on "ready for QA" was that phrase, not a tendency to obey notes.

**Read where it happens — the 11 dependent misses are the mirror case, on one phrasing.** QA's transition turn: *"It's
verified, done."* 0/11 — the member wrote the user's words as a comment (`issue_comment` on the right key) instead of
moving the issue to done; *"Passed QA, set to done."* 9/9. A request with no imperative verb read as a note.

**The pattern across four runs.** Every residual miss of the tracker member has been **one eval phrasing**: H2's
"Note on it: …" (1/15), H3's "Annotate it: ready for QA" (2 of 11), H4's "It's verified, done." (0/11). The member's
gap is lexical coverage of the request, per phrasing, not the harness, the memory or the workflow. Not chased with a
further corpus here: a corpus redesigned after each eval's one bad phrase is a corpus tuned to the evals (count the
redesigns — this would be the third).
