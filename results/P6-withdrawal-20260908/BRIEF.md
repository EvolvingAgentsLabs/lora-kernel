# P6 — distil the teacher, withdraw it, and see what falls

**Question.** The teacher scores 40/40 on this domain and the student 1/40. After
distilling 598 oracle-verified chains into a LoRA over `Qwen2.5-3B-Instruct`, how
much of that capability survives when the teacher is withdrawn?

**Result — the procedure transferred, the arithmetic did not.**

| arm | | accuracy |
|---|---|---|
| teacher `gemini-3.8-flash` | 40/40 | **1.000** |
| base `Qwen2.5-3B-Instruct` | 0/40 | 0.000 |
| **adapter** | **1/40** | **0.025** |
| adapter · held-out families | 0/20 | 0.000 |

**Withdrawal gap: −0.975.** Essentially everything.

**And the reason is specific, which makes it useful.** The adapter reproduces the
teacher's chain step for step. On a head-loss case, against the oracle's own
workings:

| step | oracle | adapter |
|---|---|---|
| area | 0.03801 | **0.037006** |
| velocity | 1.17064 | 1.1941 |
| Reynolds | 321 283 | "≈ 300000" |

Same steps, same formulas, same order — and **π/4 × 0.22² is 0.038013**, which
the model got wrong in the first line. Every later value inherits the error.

**So what failed is execution, not reasoning.** Training loss fell 1.011 → 0.175
with 0.93 token accuracy; the style transferred; 0 of 40 outputs are identical to
the base, so the adapter is applied. The student learned the physics and cannot
multiply.

**Why that is the most useful negative this project has had.** It points at a
specific missing component rather than at a failed idea, and the component is one
the architecture already names: **the kernel adapter and its tools**. A chain that
is structurally correct and arithmetically wrong is exactly what a calculator
fixes. `harness.lora` was untestable on the clinical suite for want of a real tool
distribution; this domain has one by construction, and it is now the next step
rather than a deferred one.

**What was ruled out before concluding.** Truncation (max 846 tokens against a
1536 limit, nothing cut); a mis-rendered target (the training text ends with the
full chain, the fenced JSON and `<|im_end|>`); an unapplied adapter (0 of 40
outputs identical to the base); and undertraining in the loss sense (loss
converged).

**What is still open, in order of cheapness.** Completion-only loss, so the
gradient lands on the teacher's chain instead of on re-deriving the prompt. More
epochs. A larger student. And the one this result actually argues for: a
calculator the student can call.
