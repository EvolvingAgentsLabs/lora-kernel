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

## Result

*(written after the run)*
