# PAGE0 — a page opens with the question's best statements: choosing the paragraph on the right page

**Written 2026-10-02, after the treatment was frozen (code and tests) and before the question set is written or
anything runs.**

## What and why

Of `real-none-s0`'s 42 misses on vLLM over REAL4's, REAL5's and CITE0's sets **[ran]** (zero GPU over their records),
**21 reached the supporting page and cited another statement on it** — pages of 12 to 162 statements read whole; 9 are
format failures (a citation without `§section`, no line after an error), the rest scattered. Ranked by BM25 against the
question, the supporting statement is in its page's **top 3 in all 21**, and the statement the member wrongly cited falls
outside the top 8 in 8 of them; on the 73 rows the member got right, the supporting statement is in the top 5 in 72.
**Caveat, named now:** those questions were written from their supporting statement and share its words, which favours
a lexical ranking; the fresh set below is written the same way, so the effect on a person's own wording may be smaller.

## The treatment — `page_top = 8` (`memory.runtime.Conversation.page_top`, arm flag `+top8`)

A page with more than 8 statements opens with the 8 the question ranks best (BM25 over the statements' text,
$k_1 = 1.2$, $b = 0.75$, ties in document order), shown in document order, then the anchors left out, each openable as
`id§section`; only the shown statements count as read. **8 was fixed from the zero-GPU check, before any walk:** with 8,
every statement the oracle's walk needs is shown in 113 of 115 walks over the three read sets (with 5: 108).
**Risk, named now:** the member never opened a single section in its corpus (0 of 315 walks), so a needed statement
left out is, for it, absent.

## Member, provider, the fresh set

`real-none-s0`, Gemma 4 E4B bf16 + LoRA, vLLM on one Colab L4, `--max-model-len 16384`, REAL4's runtime (`+page`).
**A fourth family, never seen by any member or set:** `knowledge/hazwaste-regs` — 40 CFR Part 262 (EPA, standards for
generators of hazardous waste), ingested verbatim from the eCFR (`sources/40-part_262.xml`): 69 pages, 1,103
statements, 162 links; pages up to 134 statements. Questions written blind after this brief (`questions.jsonl`,
`make_questions.py`), oracle n/n at zero GPU before freezing.

### The set as frozen (2026-10-02, before any model sees it)

52 rows on `hazwaste-regs`: 14 one-hop, 26 two-hop, 4 three-hop, 8 the library cannot answer (4 adjacent, 4 unrelated)
— **headline 30**; oracle 52/52, refused 0, floors 0 (`zero_gpu.json`). Written blind (library pages, the CITE0/REAL5
scripts as template). No supporting statement repeats; 10 of 14 one-hop supports sit on pages of 40+ statements, 11 of
26 two-hop. **Limits, stated now:** two values recur in a second statement (a phone number, "12 months") — a twin
citation fails the strict check; a few single-digit tokens ("2", "4", "1"); a few two-hop links are thin in meaning.

## Arms (one session, paired on the same rows)

| arm | what |
|---|---|
| `withlib-s0+page` | the served runtime — the baseline, our previous version |
| `withlib-s0+page+top8` | the same, a page opening with the question's best 8 |

## Verdict (fixed here)

- **PAGE TOP WORKS** — the treatment beats the baseline on all answerable rows, paired, exact sign test $p \lt 0.05$,
  **and** refusals do not drop by more than one.
- **PAGE TOP HELPS** — more paired wins than losses, $p \ge 0.05$.
- **FALSIFIED** — wins ≤ losses: showing the question's best statements does not help a member trained on whole pages
  choose among them.
- Beside: the same-page-wrong-statement count in each arm (the failure this is for), rows whose needed statement the
  treatment hid, multi-hop and one-hop apart, the oracle with `+top8` (the ceiling it leaves).

## Stopping condition

One scoring session; N, the set and the bars do not change after the set is frozen.

## Result

*(written after the run)*
