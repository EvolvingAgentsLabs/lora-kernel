# P10 — what the crippling prompt cost every baseline in P5–P8

**The doubt, stated plainly.** Every baseline in P5–P8 was measured under a system
prompt that told the model *"show no working: reply with one JSON object only"*,
while every treatment was trained to show working. In P9 an unmodified
`Qwen2.5-3B-Instruct` scored **4/30** under the neutral contract on the same suite
**[ran]**. So the frontier gap of **+0.975** and the 0/40 attribution arms are
comparisons between a model that was allowed to think and a model that was told
not to.

**Three arms on the same 30 cases, P9's eval seed, so every number is comparable.**

| # | arm | cost | what it answers |
|---|---|---|---|
| 1 | `qwen3.5:4b` · **legacy** contract | free | reproduces P5's conditions |
| 2 | `qwen3.5:4b` · **shared** contract | free | **arm 2 minus arm 1 is the price of the prompt** |
| 3 | `gemini-3.8-flash` · shared contract | ~$0.10 | the frontier, measured the same way |

**Falsification, written before the run.** If arm 2 is far above arm 1, the
headroom P5 reported was manufactured by its own prompt and every number derived
from it — the +0.975, the withdrawal gap's baseline, the attribution arms — has to
carry that correction. If arm 2 ties arm 1, the prompt cost nothing and P5 stands.

**The honest frontier gap is arm 3 minus arm 2**, and it replaces +0.975 wherever
that figure is cited.

**Why this is bought at all.** It is the cheapest arm in the project — two local
runs and one API call — and it decides whether four published numbers survive.

---

## Outcome (2026-09-09)

| arm | accuracy |
|---|---|
| `qwen3.5:4b` · legacy prompt | **0/30 — 0.000** |
| `qwen3.5:4b` · shared contract | **14/30 — 0.467** |
| `gemini-3.8-flash` · shared contract | **30/30 — 1.000** |
| **honest gap** | **+0.533** |

**The falsification fired.** Arm 2 is far above arm 1, so the headroom P5 reported
was in part manufactured by its own prompt: **0.467 of the claimed 0.975**. The
corrected figure is +0.533 and it replaces +0.975 wherever that was cited.

**A second instrument fault was found on the way, and it cut the other way.** At
2000 tokens the frontier scored 17/30 — truncated mid-derivation, with
`parse_answer` falling back to an intermediate number. Publishing +0.167 from that
run would have been the mirror image of P5's error. At 6000 tokens neither arm has
a single response missing the agreed JSON.

**The headroom survives, halved, and P7 is sharper for it.** +0.533 is a gap a
withdrawal can fall from, where the clinical suite offered +0.05. And the adapter
with a calculator scores 1.000 against a *fair* baseline of 0.467 — a real +0.533
closed, not a manufactured +0.975.

**Redesign count: 0.** Two faults found, both published, neither tuned.
