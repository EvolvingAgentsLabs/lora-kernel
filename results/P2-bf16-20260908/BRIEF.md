# P2 — does S4 survive real bf16?

**Question.** S4's +63.3 points were measured on a T4, in **fp16**, because a
Turing card has no real bf16. Three false zeros in this project came from
precision. Does the result hold on a card where bf16 is real?

**Falsification.** The adapter's advantage shrinks materially, or the arms move
in a way the interval cannot absorb. Then every S4 number was partly a precision
artefact and the plan's strongest claim needs re-stating.

**Why it is worth minutes.** S4 is the only evidence this project has for its own
thesis, and it was collected on the same hardware path that produced
`0/60`, `0/60` and `3/20` — all of them wrong, all of them from precision or
training configuration rather than from models. Replicating on an L4 removes that
doubt for the cost of a coffee.

**Arms.** Base and adapter, `val` and `val_delta`, in one session — Pro tenure
means the arms no longer have to be chained.

**Suite and model.** Identical to
[`../S4-qwen35-2b-20260908/BRIEF.md`](../S4-qwen35-2b-20260908/BRIEF.md):
`Qwen/Qwen3.5-2B`, 600 training cases, 60 `val`, 30 `val_delta`, LoRA r=16 α=32
on `v_proj,o_proj,gate_proj,up_proj,down_proj`, 2 epochs, greedy. The **only**
change is the card, and with it the precision the code selects by capability.

**Expected, stated before the run.** base ≈ 6/60 and 6/30; adapter ≈ 44/60 and
12/30. Writing the expectation down is what makes a surprise legible as one.

**Cost.** L4, one session, roughly half an hour. The A100 is not touched.

**Redesign count.** 0. Nothing about the instrument changes.


---

## Result — S4 is not a precision artefact

| | fp16 (T4) | **bf16 (L4)** |
|---|---|---|
| base `val` | 6/60 · 0.100 | **6/60 · 0.100** |
| base `val_delta` | 6/30 · 0.200 | **6/30 · 0.200** |
| adapter `val` | 44/60 · 0.733 | **42/60 · 0.700** |
| adapter `val_delta` | 12/30 · 0.400 | **11/30 · 0.367** |

The base arms are **identical**; the adapter arms differ by one and two cases.
The gain moves from +63.3 to **+60.0** and the false-promotion probe from +20.0
to **+16.7**. Both survive, so the strongest claim this project has does not rest
on the precision path that produced three false zeros. **[ran]**

**The region arms were not replicated**, and the reason is this repository's, not
Colab's: the chain script polled 40 times at 45 seconds and then stopped a
perfectly healthy session in the middle of the alpha expert. Fixed — the poll
budget now scales with the arms a session is asked to run. The doubt those arms
carried is largely retired anyway by the main arms replicating.
