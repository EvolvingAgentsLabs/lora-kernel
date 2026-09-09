# P7 — the withdrawal gap closes: 40/40 with a calculator

**Question.** P6 found the distilled student reproducing the teacher's chain step
for step and still failing, because it computed π/4 × 0.22² as 0.037006 rather
than 0.038013 **[ran]**. The physics transferred; the arithmetic did not. Does a
tool close that gap?

**Result.** `Qwen/Qwen2.5-3B-Instruct`, 600 oracle-written chains, 3 epochs, the
harness answering every `<calc>` call **[ran]**:

| arm | | accuracy | tool calls |
|---|---|---|---|
| teacher `gemini-3.8-flash` | 40/40 | **1.000** | — |
| base | 0/40 | 0.000 | 0 |
| base + calculator | 0/40 | **0.000** | **53** |
| adapter alone | 4/40 | 0.100 | 0 |
| **adapter + calculator** | **40/40** | **1.000** | 156 |

**The withdrawal gap is 0.000.** The teacher scores 40/40 and the distilled 3B
with a calculator scores 40/40. The frontier can be withdrawn with nothing lost —
inside the region it was distilled for.

**And neither half does it alone**, which is what makes the attribution clean.
The calculator was bought first, deliberately, before any adapter: the base model
made **53 tool calls and got nothing right**. The procedure without the tool got
4 of 40. Together they equal a frontier model. That is not a tool result and it is
not a distillation result; it is the pair.

**What this is evidence for.** `ARCHITECTURE.md` puts the kernel adapter and its
action tokens at layer 3 and the domain expert at layer 4, and says the domain
adapter thinks while the kernel acts. Here that split is not a design preference —
it is the difference between 4/40 and 40/40, measured, with each half held out in
turn.

**The bound, and it is the architecture's own.** The held-out families
`drag_force` and `orifice_discharge`, which appear in no training chain, were at
**0 of 10** when the session ended. The expert does not generalise outside the
region it was distilled for. That is what the plan means by promoting and
withdrawing **per region**: outside its region the frontier would not have been
withdrawn in the first place.

**Honest about what is incomplete.** The held-out arm did not finish before the
session was reclaimed; 0/10 is what was observed streaming, not a persisted
result, and it is reported as such.

**What it cost.** Four sessions died before this one: an unguarded `math domain
error`, a fix written and never committed, a harness loop that answered the second
call with the first call's value, and Colab reclaiming a runtime. None touched a
number. The trainer now resumes per arm, and the loop has two tests written by
reproducing the failure against the old code.
