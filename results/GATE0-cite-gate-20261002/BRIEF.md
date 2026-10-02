# GATE0 — the citation check as a gate: an answer the referee cannot verify is not delivered

**Written 2026-10-02, before the gate is replayed on any record.**

## What and why

CITE0 **[ran]**: told why its citation fails, `real-none-s0` repairs nothing (0 converted of 6) — FALSIFIED as a hint.
What survived is the check as a **detector**: every line it refused was already not right — 6/6 on CITE0, 9/9 offline
on LIVE-library2's walks, **15 fires, 0 on a right answer**. Both sets are now read; neither is the verdict.

**The gate:** the same check (`memory.runtime.citation_problem`) on the walk's final line; a line that fails it is not
delivered — the reply says the library could not verify an answer (`examples/library/serve.py --cite-gate`), where a
frontier is configured that is where it goes. The walk is unchanged; only what leaves changes.

**One fix to the check, declared here:** a statement's numbers are read with the opaque ids of its links removed (an id
like `5sf` is random per conversation and its digit would count as the statement's). This is the check's first change;
it can only make the check fire *more* on a number the statement does not print.

## The instrument — exact, zero GPU

Because the gate does not change the walk, replaying it on recorded walks **is** the gated run, not an estimate of it.
**Records (held out — none was read to design the check):** every `+page` arm on vLLM in REAL3, REAL4, REAL5, REAL6 and
REAL7's result files (members `real-spans-s0/s1`, `real-none-s0/s1`, `real-cite-s0/s1`, `real-link-s0/s1`, and the
untrained base), two libraries (`logistics-regs`, `spcc-regs`): ~600 walks. REAL3's attempt-1 member (whole-text loss, a
discarded recipe) is reported beside, not counted. Per walk: the final line, the referee's resolved citation, the
statements opened.

## Verdict (fixed here), over all counted records

- **GATE WORKS** — it blocks **≤ 1 %** of the right answers **and** **≥ 15 %** of the answerable rows that were not right.
  Delivered answers then hold fewer wrong ones at almost no cost in right ones.
- **GATE COSTS** — it blocks more than 1 % of the right answers: an honest answer withheld is a real loss; read them.
- **GATE IDLE** — ≤ 1 % of the right but < 15 % of the not-right: harmless and nearly useless.
- Beside it: per member and per library, the reasons it fires, refusals (untouched by construction), and the delivered
  precision $\text{right} / (\text{right}+\text{delivered not right})$ before and after.

## Stopping condition

One replay; the check, the thresholds and the record list do not change after it runs.

## Result [ran] — GATE WORKS as written, with a cost the brief did not name

`replay.py` → `gate0.json`: 14 arms, 532 walks with a final line over two libraries (85 more ended with no line and
already reach the user as "no answer"; refusal rows apart).

| | before the gate | after |
|---|---|---|
| right answers delivered | 275 | **275** (0 blocked, 0 %) |
| not-right answers delivered (answerable rows) | 165 | **79** (86 blocked, 52.1 %) |
| answers to unanswerable questions delivered | 11 | **0** (11 blocked) |
| precision of what is delivered, $\text{right}/(\text{right}+\text{not right})$ | 0.625 | **0.777** |

- **Verdict as written: GATE WORKS** — 0 % of the right answers blocked (≤ 1 %), 52 % of the not-right (≥ 15 %).
  Every arm agrees: no arm loses a right answer, every arm loses not-right ones (2–13 each). It fires because the line
  cites no `[id§section]` (63), a number the statement does not print (25), a statement not opened (7), an id never shown (2).
- **What "0 right blocked" is worth — said plainly.** The grader's `right` already requires a cited statement that was
  shown, opened and holds the value; the gate's first three reasons are the same conditions, so a right answer could only
  be blocked by the numbers rule. The 0 % is mostly the grader's definition, not luck. The measured part is how much of
  the not-right the gate catches without the key — **52 %** — and what it withholds.
- **The cost the brief did not name:** of the 86 blocked, **43 had the wrong value** (removed: 43 of 93 wrong values,
  46 %) and **43 had the right value under a citation that fails** (`unverified`: 43 of 72). Counted by value, the gate
  withholds **43 of 347 correct values (12.4 %)** and delivers values right $304/354 = 85.9\%$ of the time instead of
  $347/440 = 78.9\%$. By this project's rule — credit is `right` only; a value the walk cannot show it read is not
  verifiable memory — that is the gate working. Whether a person would rather have an uncheckable right number than
  "could not verify" is a product decision, and it is the user's: the gate ships off by default
  (`examples/library/serve.py --cite-gate`).
- **Beside (not counted):** REAL3's attempt-1 member (whole-text loss) — 0 of 10 right blocked, 41 of 48 not-right.
