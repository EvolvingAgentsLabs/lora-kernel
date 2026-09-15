# The harness inside the expert, narrower subdomains, and the routing that costs

**Analysis, 2026-09-15.** Prompted by the proposal: instead of a sequential
`harness.lora`, **fold the harness into each subdomain expert**, make the subdomains
**narrower**, keep **more** of them, and **improve the router**. Below: which half is
already the standing decision, what the existing data says about the other half, and
the one constraint that decides whether more experts helps or hurts.

Nothing new was run for this. Every number comes from `results/P41-routing-20260915/`,
re-read.

---

## 1. The harness-inside-the-expert half is already the decision, and it was paid for

The repository's first line says *a pool of **self-contained** QLoRAs*. Dropping
composition on 2026-09-15 committed us to exactly this: an expert carries its own
disposition to reach for tools, in the vocabulary it will be served with.

**And the alternative has a measured price.** P35 split the capability in two —
taught the tool vocabulary separately from the domain — and the vocabulary was
learned while **asking fell from 123 of 150 cases to 22** **[ran]**. Teaching the
harness apart from the expert cost the expert its disposition to use it.

So this half is not a new proposal. It is the standing architecture, and the framing
is the right one.

**The fluids expert already demonstrates the harness half works.** Across 90 cases
it made **604 tool calls, refused 0**, at **6.7 calls per case** against the
frontier's 7.6, and produced a number every single time **[ran]**. It is not failing
at tool use. It is failing at the physics.

---

## 2. The narrowing half: the failing expert has no already-good sub-region

The cheapest possible test of *narrower is better* is to slice the expert that fails
along the finest partition its suite already carries, and ask whether some slice is
competitive. Four families, paired against the frontier on the same 90 cases:

| family | n | local | frontier | only local | only frontier |
|---|---:|---:|---:|---:|---:|
| manning_channel | 23 | **0.304** | 0.826 | 1 | 13 |
| venturi_flow | 22 | 0.136 | 0.682 | 2 | 14 |
| hydrostatic_force | 23 | 0.043 | 0.609 | 0 | 13 |
| pipe_head_loss | 22 | 0.000 | 0.818 | 0 | 18 |
| **all** | **90** | **0.122** | **0.733** | **3** | **58** |

**[ran]** `results/P41-routing-20260915/`, re-read 2026-09-15.

**Every sub-region is dominated.** The frontier wins 58 cases the local expert
loses and loses 3 that it wins. There is no slice of this domain where the local
expert is already competitive and a finer router would have found it.

**This re-aims the proposal rather than killing it.** What the table measures is a
*broad* expert scored per family — not a *narrow* expert trained on one. So:

> **Narrowing has to create the gain through training. It cannot reveal one that is
> already sitting there.**

That is a weaker claim than "narrower is better", and it is the claim actually on
the table. It also hands the idea a target: **manning_channel, 0.304 → 0.826.**

### What the failures are made of

Of 79 failures: **44 are simply wrong**, **12 land within 10% but outside the
verifier's 2% tolerance** (precision, not physics), **2 are off by a factor of ten**
(a unit), 21 have no frontier reference. Repairing every near-miss and unit slip
would take fluids from 0.122 to about 0.26 — real, and still not near 0.733.

**So the remaining failure is reasoning, and narrowing the subdomain narrows what
has to be reasoned about.** That is the honest argument in favour, and it is a
decent one.

---

## 3. The constraint that decides whether more experts helps or hurts

This is the part worth being careful about, because P41 already measured both sides
of it:

| routing | delivered | leaves the machine |
|---|---:|---:|
| everything local | 0.546 | 0% |
| **by region** | **0.775** | 38% |
| by case · tripwire | 0.378 | 37% |
| by case · quality gate | 0.689 | 91% |

**Routing by region works. Routing by case does not.** The difference is not the
arithmetic — it is *when the decision can be taken*. A region is knowable **before
the model runs**; a case is knowable only by reading an answer, and the available
rules cannot see one that is coherent and wrong.

Which gives the rule the proposal has to respect:

> **More experts is safe exactly as far as the finer boundary stays visible before
> the model runs.**

- A partition by **tool surface, corpus, or vertical** is declarable — the request
  says which one. This is still by-region routing, just with more regions, and it is
  the arrangement that delivered 0.775.
- A partition that can only be told apart by **reading the statement's difficulty or
  the answer's quality** converts a solved routing problem into the unsolved one.
  Twenty experts split that way inherit 0.378, not 0.775.

Note also that `manning_channel` / `venturi_flow` / `pipe_head_loss` are *declarable*
— the generator knows the family. So the concrete partition on offer here is the
safe kind.

---

## 4. The cost multiplier lands on the expensive side

| | multiplies with N experts? | evidence |
|---|---|---|
| **serving** | barely | multi-LoRA on one resident base, measured three times **[ran]** P40/P41/P42; S-LoRA serves thousands |
| **routing** | no, if the partition is declarable | §3 |
| **training corpora** | **yes, linearly** | each expert needs a corpus that teaches **the exact prompt it will be served** |

**And the corpus is where this project has actually been hurt.** P38 drifted a
corpus from the served surface and produced **71 refusals of 606 calls that looked
like physics**, voiding a whole run **[ran]**. Today's OpenClaw demo hit the same
class from the other direction: an expert trained on **3** tools met a runtime
sending **54** with prefixed names, and did not call any of them **[ran]**.

N narrow experts is N corpora is N chances for that drift. That is the real bill,
and it is not the GPU.

---

## 5. Verdict, and the one arm worth buying

**Yes, it makes sense — with one correction and one guard.**

- The **harness-inside-the-expert** half is already the architecture. Keep it.
- The **narrower subdomain** half is plausible but unproven, and the existing data
  says it must *create* its gain rather than reveal one.
- The **more experts** half is safe only while the partition stays declarable.
- **Do not buy N. Buy one.**

**The arm:** train a single expert on `manning_channel` alone, the best of the four
and the only one above 0.30, and score it on fresh held-out cases of that family.

**Pre-registered gate, written before the run:** it must reach the frontier's
**0.826** on that family. Below that, the frontier still cannot be withdrawn there
and *narrowing does not fix a reasoning expert* — which kills the idea cheaply and
for good.

**It is affordable and it resolves.** The effect required is so large that power is
not the constraint: at n = 50, a 0.304 → 0.826 improvement is seen essentially
100% of the time, and `bar.n_for(0.304, effect=0.522)` returns **10** **[ran]**.
One corpus, one Colab session, one adapter.

**And it is the arm the pool is blocked on anyway.** The project needs a *second
useful member*; HuggingFace does not have one for this base. This produces one or
proves that a narrow reasoning expert is not where it comes from.

---

## 6. What this does not claim

- **Not that a narrow expert will reach 0.826.** Nothing here measures a narrow
  expert; §2 measures a broad one sliced up.
- **Not that the other three families are hopeless.** They were not tried narrow
  either. `manning_channel` is bought first because it is the most likely to clear,
  and a flat result there makes the other three unnecessary.
- **Not that the router needs work yet.** By-region already delivers 0.775 and the
  proposed partition is by-region. The router becomes the bottleneck only if a
  boundary appears that is not declarable.
