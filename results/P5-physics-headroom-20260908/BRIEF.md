# The gate S1 failed, asked on a domain where capability can help

**Question.** Does a frontier model beat a small local model on multi-step fluid
mechanics by a margin a withdrawal gap could live in?

**Why this domain, and why the clinical one could never answer it.** The clinical
suite's difficulty is three rules the clinics **do not publish** — the benchmark's
own documentation says they "can only be discovered from experience" **[read]**.
A model that never saw the training split cannot know them, so general capability
buys nothing and every frontier arm ties or loses. That is why S1's three targets
came back 13/20, 13/20 and **8/20** against a local 12B's 12/20, with the most
expensive one worst. It was not a weak frontier; it was a task built to be
immune to capability.

Here everything needed is in the statement. What separates a 3B from a large
model is carrying a chain: flow and diameter → Reynolds → choose the regime →
the right friction correlation → head loss → pump power.

**Falsification, written before the run.** The gap is small again — under roughly
0.2 — and the domain is not the answer either. Then the problem is not the suite
and the plan needs a different account of where a frontier advantage lives.

**The oracle is arithmetic.** Every family computes its own answer in closed
form; a model's number is compared within a **1 % relative tolerance**. No judge,
no rubric. Seven tests recompute the physics by hand, including one asserting the
statement never contains its own answer, because an oracle nobody tests is a
claim.

**Arms.** Two, and only two: `ollama:qwen3.5:4b` locally and
`openai:google/gemini-3.5-flash-lite` — the cheapest of the three targets S1
bought, and the one that scored best. Buying a bigger target before this gap
exists would repeat S1's mistake.

**Models may think.** The reasoning channel is read separately and never scored,
with a generous budget: a chain the model had no room to carry would measure the
budget.

**Scale.** 40 problems across six families, seed recorded. Two families —
`drag_force` and `orifice_discharge` — are held out of everything and exist as
the generalisation probe for later, the way `delta` held out an inverted rule.

**Cost.** Cents. The local arm is free.

**Redesign count.** 1 — the pipe families sampled flow and diameter independently
and produced 17.8 m/s in a 37 mm pipe and a 2 706 m head loss: arithmetically
correct, physically absurd, and an invitation for a capable model to argue with
the question instead of answering it. Velocity is now sampled and the flow
derived from it, with a test pinning the range.


---

## Result — the gate passes, by a distance the project has never seen

| model | | accuracy |
|---|---|---|
| `ollama:qwen3.5:4b` | 1/40 | **0.025** |
| `openai:google/gemini-3.1-pro-preview` | 40/40 | **1.000** |

**Gap +0.975.** On the clinical suite the best gap was **+0.05**, and every
frontier arm there tied or lost. Perfect on all six families, 7/7, 7/7, 7/7, 7/7,
6/6, 6/6, against a small model that managed one problem in forty. **[ran]**

**Phase A finally has its precondition.** The architecture assumes you pay
frontier prices, get frontier answers, and collect a distillation signal for
free. That assumption needs a frontier that is actually better, and here it is
better by 97.5 points.

**Two honest notes.** The frontier is at the *ceiling*, so this measures the gap
and not the frontier's limit — which is what a distillation target should be, but
it means the domain cannot be made harder later without regenerating. And the
frontier spent 42,795 characters of reasoning to get there against the small
model's zero: the advantage is a chain being carried, which is exactly the thing
this domain was built to require.

**What the first attempt cost, and what it bought.** Run one used
`gemini-3.5-flash-lite` — the cheapest tier — and scored 1/40 against the small
model's 0/40. Reported as a domain failure it would have killed the right idea
with the wrong arm. Three faults were mine: a Stokes range where creeping flow
could not hold, so a model was penalised for noticing; a 1 % tolerance that
scored a correct hydrostatic force wrong for hand-rounding; and the cheapest
possible target for a multi-step reasoning task.

**Next**, and only now that the gate has passed: generate a training corpus,
distil the frontier's answers into an adapter, withdraw the frontier, and measure
what falls. The held-out families `drag_force` and `orifice_discharge` are the
generalisation probe, untouched.
