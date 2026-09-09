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
