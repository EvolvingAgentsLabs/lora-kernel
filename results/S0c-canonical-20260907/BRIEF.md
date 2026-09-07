# S0c — the canonical prompt, so our prompt stops being a variable

**Question.** With the context compiler that produced this workspace's published
ladder — imported from `../verified-runtime`, not reimplemented — does
`gemma4:12b` reproduce something near its published score, and do the three
models separate at all on this suite?

**Falsification.** The models still tie. That does not kill the architecture; it
kills **this suite** as the place to test it, and S1/S2 move to the
`held_out_delta` split (whose rule inverts, so memorised protocol fails) or to
another domain.

**Why this is not prompt tuning.** The frozen prompt scored `gemma4:12b` at 3/12
where this workspace published 38–41/50 for the same model on the same split. The
difference is not a wording preference: the canonical prompt states the rule that
a document attached but no longer valid still counts as missing. Rather than
adjust a prompt of our own until the numbers look familiar, the prompt that
produced the published number is called directly.

**Arms.** One, local, $0. The frontier arm stays unbought.

**Suite.** `clinical_learning` held-out, the same 12 cases as S0b, so the only
thing that changed is the prompt.

**Models.** Target `ollama:gemma4:12b-mlx`; drafters `ollama:qwen3.5:4b`,
`ollama:qwen3.5:9b`. Unchanged.

**Parameters.** temperature 0, top_k 1, seed 0, window 24, positions 1,
max_tokens 700, prompt `canonical` (hash `2e4126b1e3fc8091`).

**Cost.** Zero dollars, ~4 minutes.

**Abort rule.** Kill at 5 minutes per case.

**Redesign count.** **3 — the stopping condition fires with this run.** The three
were: the thinking channel and the missing prefill; measuring the payload instead
of the format; and this reversion to the canonical prompt. The first two moved the
instrument toward measuring the thing; the third removes our own prompt from the
experiment. Either way the rule stands as written: no further change to the
instrument without a review by someone who has not been building it.
