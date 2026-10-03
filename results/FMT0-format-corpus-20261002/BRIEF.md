# FMT0 — a corpus for the served page form, and recovery after an error

**Written 2026-10-02, before the member trains or anything is scored.**

## What and why

Of `real-none-s0`'s 42 misses over three sets **[ran]**, 21 cite the wrong statement on the right page (PAGE0's target),
9 are format failures, and the rest scattered. Reading the "no answer line after an ERROR" walks where they happen
**[ran]**: the member opened a section number as an id (`<open>20</open>`), and the guard, in `strict` mode, **ended the
walk** — it never had the chance to recover. The guard's `recover` mode (`docs/MEMORY.md` §5.3: the violation written
inline, the walk goes on) exists and was never measured: *"whether small experts do recover is an arm, not an
assumption."* Separately, the served page form is now `page_top = 8` (PAGE0 HELPS, the user's decision): the member was
trained on whole pages and never opened a single section (0 of 315 walks) — a needed statement the page hides is, for it,
absent.

## The member — `real-fmt-s0`

Gemma 4 E4B + LoRA, `release_gate.RECIPE`, seed 0, span-masked loss (only the model's spans), window 4,096, A100, on
`training/wiki/data/train_real_fmt.jsonl` (`real_corpus.py --walks --with-none --with-format`): **REAL4's questions,
walked under the served form** — 320 rows (114 two-hop, refusals as REAL4), gate passed (`gate_real_fmt.json`):
- every walk rendered with `page_top = 8`; a needed statement the page hides — the link a two-hop walk follows or the one
  it cites — is opened as `id§section` (25 walks);
- **one walk in three (96) first opens the page's own section number as an id**, reads the ERROR under the `recover`
  guard, and goes on; that open is kept out of the loss (the recovery is taught, not the mistake).
**One unknown at the corpus level, said so:** the page form and the recovery change together — both are what serving now
is; attribution only if there is an effect.

## Arms (one L4 session, vLLM, `--max-model-len 16384`), on PAGE0's set (`knowledge/hazwaste-regs`, 52 rows)

PAGE0's set is fresh to this corpus: its library is not in it (G1), its questions were never read to design it.

| arm | what |
|---|---|
| `withlib-s0+page+top8` | `real-none-s0`, the served form, `strict` guard — **the baseline** (our previous version) |
| `withlib-s0+page+top8+recover` | `real-none-s0` with the `recover` guard — the runtime alone (attribution, cheap) |
| `withlib-s1+page+top8+recover` | `real-fmt-s0` with the `recover` guard — **the treatment** |

## Verdict (fixed here), treatment against the baseline on all answerable rows

- **FMT WORKS** — paired, exact sign test $p \lt 0.05$, **and** refusals do not drop by more than one.
- **FMT HELPS** — more paired wins than losses, $p \ge 0.05$.
- **FALSIFIED** — wins ≤ losses.
- Beside: the runtime alone (`real-none-s0` + `recover` vs the baseline); the treatment's format failures (no line,
  `[id]` without `§section`), walks that opened `id§section`, walks that recovered after an ERROR, one-hop and multi-hop.

## Stopping condition

One training (A100, one session), one scoring (L4). No change to the corpus, the arms or the bars after training starts.

## Result [ran] — FALSIFIED: no headroom on the set, and the check that would have said so was on disk

`real-fmt-s0` trained on an A100 (320 rows, span-masked); one L4 session, G1 applied to both members, 0 errors (`fmt0.json`).

| arm | answerable (44) | multi-hop (30) | one-hop (14) | refusals (8) | no line | `[id]` without `§` | walks with an ERROR |
|---|---|---|---|---|---|---|---|
| `real-none-s0`, top-8, strict (baseline) | 33 | 23 | 10 | 7 | 1 | 0 | 2 |
| `real-none-s0`, top-8, recover | 33 | 23 | 10 | 7 | 0 | 1 | 1 |
| `real-fmt-s0`, top-8, recover (treatment) | 33 | 23 | 10 | 7 | 0 | 3 | 1 |

- **Verdict as written: FALSIFIED** — treatment against baseline **1 : 1**, $p = 1.0$; the runtime alone 0 : 0. All three
  arms score the same rows, the same counts in every slice.
- **Read where it happens: there was nothing on this set for the treatment to repair.** Under the served top-8 form the
  baseline's 11 misses hold **one** missing line and no malformed citation; a mistaken open happened in 2 walks of 52.
  The recovery the corpus taught had, in effect, no occasion. The trained member did not regress (refusals, multi-hop,
  one-hop unchanged), and wrote `[id]` without `§section` 3 times against the baseline's 0 — a small cost, no gain.
- **The instrument error, owned:** the headroom check for *this* set was available before training — PAGE0's own top-8
  arm, already on disk, had **1 format failure in 10 misses**. The headroom measured instead was over the three read sets
  (9 of 42, whole pages, `strict`), where the format failures largely came from the guard ending walks and from pages read
  whole — two things the served form (top-8) and the `recover` mode had already changed. The rule "check headroom before
  building the treatment" was applied to the wrong baseline. It cost one A100 and one L4 session.
- **What stays true:** the `recover` guard is harmless on this member (0 : 0) and the top-8 corpus does not hurt it — but
  neither is a measured gain. **The format-corpus line stops here**: on the served form the failure it targets is ~1 row
  in 44.
