# S1a — is there any local configuration where these models separate at all

**Question.** S0c found `gemma4:12b` (4/12) tied with its own 4B drafter (3/12)
on the held-out split. The plan's S1 falsification names the next configuration
to try before spending on a frontier arm: `held_out_delta`, whose planted rule
**inverts**, so a model that memorised the protocol fails where a model that
reads the case does not.

**Falsification.** The models tie again. Then no configuration available on this
machine separates them, and the frontier arm has nothing to be better *at* — S1
stops being worth its $5 until the suite itself changes.

**Arms.** One, local, $0. Verified score is the number being read; α is recorded
but not interpreted, because C9 says character agreement measures layout.

**Suite.** `clinical_learning` **held_out_delta**, 12 cases, canonical prompt —
the only change from S0c is the split.

**Models.** Target `ollama:gemma4:12b-mlx`; drafters `ollama:qwen3.5:4b`,
`ollama:qwen3.5:9b`. Unchanged, so the two runs are comparable.

**Parameters.** temperature 0, top_k 1, seed 0, window 24, positions 1,
max_tokens 700, prompt `canonical`.

**Cost.** Zero dollars, ~4 minutes.

**Abort rule.** Kill at 5 minutes per case.

**Redesign count.** Still 3. Nothing about the instrument changes for this run —
only the split, which the plan named in advance.
