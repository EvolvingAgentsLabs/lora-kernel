# B4 — milestone 4: does the large half's LoRA raise acceptance of the small half's drafts? (pre-registered 2026-09-26)

**Why.** The pair exists to make the large verify what the small drafts: at temperature 0 a drafted token is accepted iff
it is the verifier's rank-1 token there. The design's claim is that a verifier trained on the SAME corpus accepts more of
the small member's drafts than the bare verifier does — otherwise the large half's LoRA buys nothing for latency.

**Instrument.** `training/harness/pair_accept.py` on `accept_rank.score_span` (P55's): the verifier's `prompt_logprobs` over
each span the small member WROTE (tags, sections, the cited answer — never the referee's results), rank-1 → accepted.
**Drafts:** E4B + `wiki-walks-s1` (the released member), its walks on W9's set (67) and on B3's hard band (40), recorded by B3's
session H with spans. **Arms:** `gemma-4-12B-it` bare and `gemma-4-12B-it` + `wiki12b-walks-s0` (B3's T), one A100 session.

**Verdict — written first (`pair_accept`).** Per draft record, the arm with the higher accepted fraction; exact two-sided
sign test on the discordant records: `large+LoRA vs large` must be an **improvement** → **MILESTONE 4 PASSES**; otherwise
NOT PASSED, with the pooled α of both arms. Beside: pooled α, longest accepted prefix per span, by question set.
**Not measured:** wall-clock speed-up (vLLM speculative decoding with a LoRA on both halves is its own gate), a Mac runtime.

## Result **[ran]** 2026-09-26 · MILESTONE 4 PASSES — the large half's LoRA raises acceptance, where its corpus reaches

One A100, `gemma-4-12B-it`, G1 applied on `wiki12b-walks-s0`; 107 draft records of the E4B member (67 on W9's set, 40 on the
hard band), 0 scoring errors (`pair_accept.json`).

| drafts | 12B bare | 12B + LoRA |
|---|--:|--:|
| all (107), pooled α | 0.871 | **0.898** |
| W9's set (67) | 0.855 | **0.914** |
| hard band (40) | 0.885 | 0.881 |

Per record, the arm with the higher accepted fraction: **large+LoRA 76, bare 18 — improvement, $p < 0.0001$. PASSED as
written.** Read where it happens: the gain is on the drafts in the corpus's distribution (0.855 → 0.914); on the comparison
band, which neither half was trained on, the LoRA moves nothing (0.885 → 0.881). The pair buys latency where the two halves
share a trained distribution. **Not measured:** wall-clock speed-up with speculative decoding actually running (vLLM with a
LoRA on both halves), a Mac runtime.
