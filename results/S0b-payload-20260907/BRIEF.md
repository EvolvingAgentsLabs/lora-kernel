# S0b — the same instrument, measuring the payload instead of the format

**Question.** With acceptance measured over the payload rather than the answer
format, does the surface show dispersion between candidates that differ in
verified quality — and does this prompt reproduce the local ladder this workspace
already published for these models?

**Falsification.** Still no dispersion (every candidate says the same thing on
this suite → nothing to route on, and S2 would be unbuyable here); or the target
scores near the floor, which would mean the number is about this prompt rather
than about the model.

**Arms.** One, again, and still local. The frontier arm stays unbought until the
instrument produces a non-degenerate surface.

**Suite.** `clinical_learning` held-out, 12 cases — three times run 1, because
run 1's `+0` headroom line came from n = 4 and n = 4 cannot carry that claim.

**Models.** Target `ollama:gemma4:12b-mlx`; drafters `ollama:qwen3.5:4b`,
`ollama:qwen3.5:9b`. Same as run 1 so the two runs are comparable.

**Parameters.** Unchanged except the metric: temperature 0, top_k 1, seed 0,
window 24, positions 1, max_tokens 700, prompt hash `5cc2c73086192d43`.

**Cost.** Zero dollars, ~4 minutes.

**Abort rule.** Kill at 5 minutes per case.

**Redesign count.** 2. Run 1 showed α = 1.00 between three models that produced
the same wrong answer, and α = 0.00 between two identical answers one of which
was fenced — both numbers were about formatting. One more redesign and the
stopping condition fires.
