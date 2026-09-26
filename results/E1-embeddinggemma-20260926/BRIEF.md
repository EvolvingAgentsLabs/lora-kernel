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

## Result **[ran]** 2026-09-26 · radar: a tie → the default moves to EmbeddingGemma; router: a regression on in-distribution traffic → brought back

Attempt 1 of both stopped at download: the model is gated, 401 (`attempt1_gated_401/`); the user accepted the license and
allowed the token, carried by the chain as a file (`HF_AUTH=1`). Not a redesign. Encoder recorded: `google/embeddinggemma-300m`,
sentence-transformers 5.7.0, prompts as briefed. Probes alive: radar paraphrase 0.581 vs unrelated 0.462; router 0.937 vs 0.300.

**Radar (W3's instrument, 94 queries on P):**

| encoder | recall@3 on P | needed note in top 3 | paired vs Qwen | set E (72) |
|---|--:|--:|--:|--:|
| Qwen3-Embedding-0.6B (W3) | 0.638 | 60 | — | 9 |
| **EmbeddingGemma-300m** | **0.628** | 59 | **13 : 14, p = 1.0 — a tie** | 12 (3 : 0, p = 0.25) |

The instrument's own verdict is unchanged: *beats a word-matcher (55 : 2) and is not enough* (< 0.80). **By the rule written
first, a tie chooses Gemma: `radar_r0 --base` defaults to EmbeddingGemma.**

**Router (M2b's instrument, arm 1's eight sets):**

| encoder | foreign misrouted (of 338) | **A in-distribution lost (of 715)** | F unseen senders lost (of 120) | B recovered | verdict |
|---|--:|--:|--:|--:|---|
| Qwen3-Embedding-0.6B (M2b) | 15 | 13 | 120 | 99 | safe, loses F |
| **EmbeddingGemma-300m** | **5** | **304** | 98 | 106 | safe, loses F |

Safer on foreign text and it recovers 22 of the 120 unseen senders — but it loses **304 of 715 in-distribution requests**
against 13: τ comes out at 0.931 / 0.935 (Qwen 0.977 / 0.944) and the held-out spread is wider, so the same percentile rule
cuts into the member's own traffic. **A regression where it matters most → the router's default does NOT move; brought to
the user**, as the brief says. Neither encoder passes; the production route stays the role.
