# P61 — weights or harness on the email region (2026-09-18)

**Question (one unknown).** Can the plain base, given a written procedure in its context,
resolve the email region as well as the QLoRA expert does?

**Why now.** The service resolves locally by weights (a LoRA) or by harness (knowledge in
context, markdown, lexical retrieval). Customising a customer's task by hand for the next
two or three months means writing that document; which side buys the region decides
what the customisation costs and what gets automated.

**Arms, one session, `Qwen/Qwen2.5-3B-Instruct` on Colab L4, vLLM 0.29.0, corpus-mode
loop (`accept_rank.draft_arm`), suite `email` n=475 seed 717171 (P55's cases):**

| arm | what | prior |
|---|---|---|
| base | the corpus's system prompt + tool block | P55 [ran] 0.516, human 0.345, **0 tool calls on 230/351 human** |
| base+kb | the same + `knowledge/email-triage.md` appended to the system prompt | unknown |
| expert | `email-full@v1` (sha `a73f6039…`) | P55 [ran] 0.992, human 0.989; P57 re-served 471/475 |

**Pre-registered (before the run), FOUNDATIONS §7.3 sign test on discordant pairs:**

- `kb_pays` iff base+kb > base, p < 0.05.
- `weights_needed` iff expert > base+kb, p < 0.05.
- `harness_replaces_weights` iff not `weights_needed` and human(base+kb) ≥ human(expert) − 0.05.
- otherwise unresolved at n=475; the power line says what n would.
- **Failure condition written first:** base+kb ≤ base means a 3B does not follow a written
  procedure in context on this region — the harness side is closed for this base, and the
  next document is not written. Errors VOID an arm (never folded into a score).

**Price line, recorded with the verdict:** tokens the document adds per request
(`kb_tokens`), tool calls per case in each arm.

**Not measured here:** retrieval (the document is the whole knowledge base — one region,
one file); a larger base; the desk suite.
