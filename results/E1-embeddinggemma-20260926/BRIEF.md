# E1 — EmbeddingGemma in place of Qwen3-Embedding, on the two instruments that used it (pre-registered 2026-09-26)

**Why.** The user, 2026-09-26: the stack is Gemma 4, so the embeddings should be Gemma's. Two instruments ran
`Qwen/Qwen3-Embedding-0.6B` and **neither passed**: the note radar (W3 **[ran]**: recall@3 **0.638** against a bar of 0.80)
and the embedding router (M2b **[ran]**: safe, 15 foreign misrouted, but **120/120** unseen-sender requests lost). Neither
is in production — search is lexical, the route is the role — so the swap costs nothing live; what this buys is whether
Gemma's encoder moves either wall. **Baseline: ourselves** — the recorded Qwen runs, same sets, same verdicts.

**What.** `google/embeddinggemma-300m` [read: 308M, 768-d, Gemma 3 based] through sentence-transformers (its pooling and
dense projection; fp32 — the card says no fp16), one task prompt per space as the Qwen arm had one instruction per space:
radar `task: sentence similarity | query: `, router `task: classification | query: ` (`embed_router.GEMMA_TASK`). Probe
before scoring in both (paraphrase cosine clearly above unrelated, or nothing after it means anything). Two L4 sessions,
the instruments unchanged: `training.nursing.radar_r0`, `training.harness.embed_router`.

**Verdict — written first.**

| check | required | reading |
|---|---|---|
| radar: the instrument's own verdict | recall@3 ≥ 0.80 on P **and** beats lexical | passes → W3's radar exists on Gemma |
| radar: Gemma vs Qwen, *needed note in the top 3*, paired on P's 94 queries | sign test | improvement / tie / regression, reported whichever way |
| router: the instrument's own verdict | as M2b's table | PASSES / NOT SAFE / loses F |
| router: F lost, foreign misrouted | against Qwen's 120 and 15 | beside |

**The swap, decided before it runs:** by the user's parity rule, a tie or better chooses Gemma and the default `--base` of
both instruments becomes EmbeddingGemma; a paired **regression** is brought back to the user before any default moves.
Left out, said: EmbeddingGemma's asymmetric retrieval prompts (query/document) — the instruments encode both sides with
one prompt, and changing that is a redesign of the instrument, not a swap of the encoder. Redesign counter: 0.
