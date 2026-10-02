# CITE0 — the runtime checks the citation before the answer leaves, on a fresh set

**Written 2026-10-02, after the check's design was frozen (code and tests) and before the question set is written or
anything runs.**

## What and why

The citation-corpus line stopped at REAL7 (two FALSIFIED redesigns). The losses that remain on real documents are
citations: on LIVE-library2's 52 walks **[ran]**, 15 misses, 7 of them *unverified* (the value right, the citation
not). Read offline over those walks — zero GPU, `memory.runtime.Conversation.check_final` replayed on each final line —
**9 of the 15 misses end on a line the referee can reject without knowing the answer** (no `[id§section]`, an id never
shown, a statement never opened, a number the cited statement does not hold), **and 0 of the 37 right answers do.**
That is the headroom, measured on a set the design was read against — so it is not the verdict.

## The treatment — `cite_check` (nothing else changes)

A final line that fails that check is answered **once** with `= ERROR: citation — <why>; end with one line: the answer
and [id§section] of a statement you opened that holds it — or Not in my library.` and the walk continues within the same
call budget; a second final line stands as it is. The check never sees the answer key: it reads the referee's own
record (ids shown, statements opened, the statement's text). It cannot catch a statement that holds the number but is not
the one asked about (REAL6/REAL7's failure) — that stays a loss.

$$\text{pass}(\ell) \iff \ell=\texttt{Not in my library.} \;\lor\; \bigl(\ell \text{ cites } [o\S a],\ o\in\text{shown},\ (\mathrm{id}(o),a)\in\text{opened},\ \mathrm{nums}(\ell)\subseteq\mathrm{nums}(\text{stmt})\bigr)$$

## The member, the runtime, the provider

`real-none-s0` (REAL4's accepted member), Gemma 4 E4B bf16 + LoRA, **vLLM on one Colab L4** through
`training/harness/chain_serve.sh`, `--max-model-len 16384`, REAL4's runtime (`+page`: full-text entry on every shelf,
fallback, pages with their statements; no page budget).

## The questions — fresh, written after the freeze

`questions.jsonl` (`make_questions.py`) on `knowledge/spcc-regs` (40 CFR 112, the third family): written from the pages
alone by an agent that read no model output; no supporting statement REAL5 used; target 14 one-hop, 26 two-hop,
4 three-hop, 8 the library cannot answer; strict citation (`cite = "support"`); oracle n/n at zero GPU before freezing.

### The set as frozen (2026-10-02, before any model sees it)

52 rows: 14 one-hop, 26 two-hop, 4 three-hop, 8 the library cannot answer (4 adjacent, 4 unrelated) — **headline 30**;
oracle 52/52, refused 0, floor headline 0/30 (`zero_gpu.json`). Written blind (library pages, REAL5's script as
template, the grader's source). **Limits, stated now:** four statements serve two rows each (a one-hop and a two-hop row
asking different numbers) — the library holds 40 usable numbered statements outside REAL5's; some values recur across
statements (August 30, 1994 four times, July 31, 2000 three, part 109 three) — exactly the case the check cannot catch;
three near-duplicate 112-12 statements were left out (a strict citation there would be a coin toss); one token is "1"
of "1 million gallons".

## Arms (one session, paired on the same rows)

| arm | what |
|---|---|
| `withlib-s0+page` | `real-none-s0`, the production runtime — the baseline, our previous version |
| `withlib-s0+page+check` | the same, with `cite_check` — the treatment |

## Verdict (fixed here)

The primary reading is **within the treatment's own walks** — the refused line and the line that replaced it, same walk,
graded by the same strict grader (`pre_check` in the record) — so vLLM's run-to-run spread cannot make or hide it.

- **CHECK WORKS** — on the rows where the check fired, *converted* (refused line not right → final right) beats *broken*
  (refused line right → final not right) at exact sign test $p \lt 0.05$, **and** the treatment arm is not below the
  baseline arm on all rows, paired (no paired loss at $p \lt 0.05$), **and** refusals do not drop by more than one.
- **CHECK HELPS** — converted > broken, $p \ge 0.05$.
- **FALSIFIED** — converted ≤ broken: being told why a citation fails does not make a 4B cite better.
- Beside it: fires (how many lines refused, by reason), the arm-vs-arm paired count and headline, refusals, one-hop.

## Stopping condition

One scoring session; the check, the set and the bars do not change after the set is frozen. If the check fires on fewer
than 5 rows the verdict cannot reach $p \lt 0.05$ and is reported as **NOT ENOUGH FIRES** — not rerun on a larger set
written to make it fire.

## Result [ran] — FALSIFIED: the check finds bad citations, and the member cannot repair them

One L4 session, 2026-10-02 07:52 → 08:16, G1 applied, 0 errors (`cite0.json`, `verdict.json` by `read.py`).

| arm | headline (30) | one-hop (14) | refusals (8) | all (52) |
|---|---|---|---|---|
| `withlib-s0+page` (baseline) | 18 | 8 | 6 | 32 |
| `withlib-s0+page+check` | 19 | 8 | 6 | 33 |

- **Verdict: FALSIFIED** — the check fired on **6** rows (≥ 5, so the verdict is readable); **converted 0, broken 0**. The
  arm pair is 1 : 0 ($p = 1.0$), and the one row that differs is a context overflow in the baseline, not a fired row.
- **Read where it happens — what the member did after `= ERROR: citation`:** on 3 of 6 it did the right thing first —
  opened the page the error named — and then still ended without a verified line; once it retreated to
  `Not in my library.`; once it repeated the refused line word for word (`[zkh§112.9(c)(2)]` — a section number written
  as an anchor); once it wrote two `= …` results itself, an invented error and an invented answer (P43's stray results).
  The member was never shown a refused citation in its corpus; a 4B does not follow what it merely reads (P61).
- **What the check is, measured: a detector with no false alarm.** Every one of the 6 refused lines was already not
  right (6/6), as offline on LIVE-library2's walks (9/9 misses, 0 of 37 right). Across both sets: **15 fires, 0 on a right
  answer.** It catches 6 of the baseline's 20 misses here; the largest remaining class (7) is the one it cannot see — a
  statement that holds the value but is not the one asked about.
- **Not rerun** (stopping condition). The next use of the check is the one this run measured it fit for: **a gate, not
  a hint** — a line that fails it is not delivered as an answer (the runtime says the library could not verify one, or
  forwards to the frontier), which on these two sets would have removed 15 wrong answers and 0 right ones.
