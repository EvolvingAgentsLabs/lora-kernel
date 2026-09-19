# M5 headroom — does a small base already know a nursing procedure, and can it read one? (pre-registered 2026-09-19)

**Question.** Before anything is trained for the first real region ([`PLAN.md`](../../docs/PLAN.md)
milestone 5): on questions a program can check, is the bare `qwen3.5:4b` **below the ceiling
closed-book**, and does **the note in its context** lift it? The clinical suite of S1 died here —
no model was ahead of a free local 12B — so headroom is bought first.

**Source.** Three IV-therapy checklists from *Nursing Skills* (Open RN, CC BY 4.0), 32 + 24 + 14
top-level steps — text nobody in this repository generated (`training/nursing/source.py`).

**Model, provider, cost.** `Qwen/Qwen3.5-4B` in bf16, served by **vLLM on a Colab L4** through
`training/harness/chain_serve.sh`, thinking off, temperature 0 — the base milestone 1 is moving the
pool to, as the pool serves it. No API, no training; about ten minutes of an L4, most of it boot.

*Corrected before any number was used, 2026-09-19.* This brief first named a local Ollama build on
the user's laptop. The user's instruction is that **no model runs on local resources — Colab for
everything**; the local run was stopped at 70 of 72 closed-book answers and its file discarded. It
would not have been comparable anyway: a quantised local build is not the model vLLM serves.

**72 questions, four kinds, fixed seed** (`training/nursing/questions.py`):

| kind | n | what it asks | verified by |
|---|--:|---|---|
| `order` | 24 | which of two non-adjacent steps comes first | the letter |
| `next` | 24 | having just done step *k*, which of four comes next | the letter |
| `rate` | 12 | gtt/min by gravity, or mL/hr on a pump | the computed number, ±1 |
| `site` | 12 | a quantity **this unit's protocol changed** (cleanse 8 s, not the textbook's 5) | the site's number, exactly |

**Two arms, in order.** 1. **Closed book** — the question alone: the headroom arm. 2. **Open book**
— the same question with the one relevant note above it (the checklist; the rate formula; the
site's protocol line). Arm 2 shares arm 1's session — the boot is the cost, the second pass is minutes — so it is bought even if arm 1 is surprising; it is
**not** a trained expert and says nothing about one.

**Verdict, written first.**

| outcome | reading |
|---|---|
| closed-book ≥ 0.90 on `order` + `next` | **no headroom**: the base already knows the procedure; a knowledge base of textbook procedures buys nothing here — only `site` remains |
| closed-book well below, open-book near the ceiling | **the region has headroom and reading closes it**: for *answering about* a procedure, retrieval alone may do, before any LoRA — and that has to be the baseline any trained trajectory beats |
| closed-book well below, open-book also low | reading does not close it at 4B: this is P61's wall on real text, and milestone 7's trained navigation is what is left |
| `site` closed-book ≈ 0 and open-book high | the unmemorisable base works as designed on real content |
| `site` open-book low | the model answers its prior over the note in front of it — the failure milestone 7's arm 5 exists to detect |

`rate` is read apart: it is arithmetic, and the record says arithmetic belongs to a calculator
(P5–P7); a low number there is a reason to keep the tool, not a finding about knowledge.

**Known limits, before the run.** 72 questions by the person who wrote the runner; the checklists'
wording is as returned by a summarising fetch, not byte-checked; option order is seeded, letters
are near-balanced (`order` 13 A / 11 B); one model, one run, temperature 0.
Training material only — nothing here advises a patient.

**Redesign counter: 0.**
