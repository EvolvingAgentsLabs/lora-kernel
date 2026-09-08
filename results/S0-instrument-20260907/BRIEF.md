# S0 — does the instrument measure what it says, on models we already have

**Question.** Does `alpha/` produce an acceptance surface and a verified score
from the same run, end to end, with a local stand-in for the frontier target —
and do the two numbers move independently?

**Falsification.** Any of these kills the instrument rather than the hypothesis:
the target's answer channel comes back empty; α is identical across candidates
(nothing to route on); α is 1.0 for every candidate (the metric is degenerate);
the verified score cannot be computed from the same run.

**Arms.** One. This buys nothing about the thesis — it buys the right to believe
the next number. The frontier arm is deliberately not bought yet: it needs a key
this machine does not have, and a flat instrument would make it wasted money.

**Suite.** `clinical_learning` held-out, first 4 cases, exact verifier, borrowed
from `../verified-runtime` rather than rebuilt.

**Models.** Target `ollama:gemma4:12b-mlx` — the strongest local model, standing
in for the frontier so the mechanism can be exercised at zero cost. Drafters
`ollama:qwen3.5:4b` and `ollama:qwen3.5:9b`. Provider is ollama on this machine;
no API is involved and no key is required.

**Parameters.** temperature 0, top_k 1, seed 0, window 24 chars, positions 1
(position 0 only — no prefill, because ollama's chat renderer was measured
ignoring it), max_tokens 700.

**Cost.** Zero dollars. Wall clock is the only budget; three models totalling
~22 GB on a 16 GB machine will swap on every switch.

**Abort rule.** Kill it if a single case takes more than 5 minutes, and report
the swap cost as the finding.

**Redesign count.** 1. The instrument was reshaped once, before any run, when the
local models turned out to be thinking models and ollama turned out not to honour
an assistant prefill. Two more and the stopping condition fires.
