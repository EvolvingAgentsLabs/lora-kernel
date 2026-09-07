# S1 + S2 — the frontier arm, with a small model in the candidate set

**Question, in two parts that share the same frontier calls.**
**S1 (the gate):** does the target score materially above the strongest local
model on this split? **S2 (the criterion):** does semantic answer agreement with
that target order the candidates the way verified quality orders them?

**Why these are one run and not a grid.** The target generation is the only thing
that costs money; the three candidates are local and free. Buying them separately
would pay for the same frontier tokens twice.

**Falsification, written now.**
- **S1 fails** if the target does not clear `gemma4:12b`'s **12/20** by a margin
  the withdrawal gap could live in. Then this Gemini is not frontier-grade *for
  this suite*, S2's numbers measure agreement with a peer rather than
  distillation, and the next step is a stronger target — not a better treatment.
- **S2 fails** if agreement is flat across candidates that differ in verified
  quality, or orders them against it. Either kills acceptance as the promotion
  criterion; the adapter pool survives, the free router does not.
- **S2 is untestable** if the candidates tie on verified quality, which is
  exactly what happened locally at n=20. Three candidates are used instead of two
  precisely because `gemma4:12b` (12/20) does not tie with the qwens (6/20).

**Arms.** One. The attribution arm (S3, a lexical/embedding router) is NOT bought
until S2 shows an effect.

**Suite.** `clinical_learning` **held_out_delta**, all 20 cases, canonical prompt
`2e4126b1e3fc8091`, exact verifier. This split was chosen by S1a, before any
frontier money existed, because it is the only configuration measured to have
headroom.

**Models.** Target `openai:google/gemini-3.5-flash-lite`
($0.30 / $2.50 per Mtok, declared in the run config). Candidates
`ollama:gemma4:12b-mlx`, `ollama:qwen3.5:9b`, `ollama:qwen3.5:4b` — all three
already scored on this exact split, so the ordering test has known ground truth.

**Parameters.** temperature 0, top_p 1, seed 0, positions 1 (no prefill),
window 24, max_tokens 700.

**Cost.** Measured, not estimated: **$0.00012 per case** in the smoke test →
about **$0.0024** for the run. The ceiling at which it stops is $1.

**Abort rule.** Stop if the target's verified score is at or below 12/20 after
the first 10 cases — S1 has then already failed and the remaining calls buy
nothing.

**Redesign count.** 0 since the criterion was decided under review. Token and
cost recording was added to the run record; it changes no metric.

---

## Amendment — a fourth candidate, and why it improves the test

`qwen3.5:2b` joins `gemma4:12b-mlx`, `qwen3.5:9b` and `qwen3.5:4b`. It is the
smallest qwen3.5 the registry has — `1.5b`, `1.7b`, `1b`, `0.6b` and `3b` all
return "file does not exist" **[ran]**.

This is not a cost decision, it is a **test-power** decision. S2 needs candidates
that differ in verified quality: the local ladder tied at 6/20 for both qwens on
this split, and a tie makes the ordering test unbuyable however good the
criterion is. A 2B ought to sit below them, which turns a two-way tie into a
four-point spread and gives agreement something to be right or wrong about.

It also removes the crash that stopped the three-candidate run: three local
models totalling ~18 GB exceeded this machine's memory mid-run. Models are now
unloaded as soon as they answer.

The three-candidate run is kept at `../S1-frontier-20260907/` — 6 cases, superseded,
not deleted.
