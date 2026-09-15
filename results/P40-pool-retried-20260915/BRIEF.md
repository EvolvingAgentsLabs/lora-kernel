# P40 — the pool serves two experts, and only one of them is good

Run 2026-09-15, after the corpus drift that voided P38's fluids arm was fixed.

## The substrate, for the third time

```
[pool] gate email-full:  applied
[pool] gate fluids-full: applied
[pool] members differ from each other: True
```

Two adapters, both applied, distinct from each other, in one vLLM, each routed by
the `model` field of an HTTP request to its own client and its own oracle **[ran]**.

## The two members

| member | score | calls | refused | out of turns |
|---|--:|--:|--:|--:|
| `email-full` | **82/113 = 0.726** human messages | 390 | 0 | — |
| `fluids-full` | **12/90 = 0.133** | 603 | **0** | **0** |

## The drift fix worked, and the number got worse

P38's fluids arm was void: 71 of 606 calls refused because the corpus never showed
the model the surface it was served with. Now: **0 refused, 0 out of turns, 90 of 90
answered, 6–8 calls per case** against the 7 the corpus teaches. **The protocol is
exactly right.** And the physics is wrong **78 times out of 90**.

Paired against P24 — same generator, same seed, and the first 30 of these cases are
*literally* P24's 30, verified by id — the fluids expert **loses to the hand-written
rule**:

| against | paired | p | |
|---|---|--:|---|
| hand-written rule, 12/30 | 2 : 11 | **0.022** | **loses** |
| no tool layer at all, 7/30 | 1 : 5 | 0.219 | tie |
| kernel adapter, 5/30 | 2 : 4 | 0.688 | tie |
| grammar-masked kernel, 4/30 | 2 : 3 | 1.000 | tie |

**A correction to this project's own brief.** P38 named "beat the hand-written rule,
paired" as the fluids bar. **The rule is not a solver** — it writes tool calls and a
model does the physics — so that bar was not directly measurable as stated. The
paired comparison against P24's *arms* is, and it is what is reported.

## The email member's gate verdict is not reproducible, and P36's headline needs qualifying

The same adapter, the same 150 cases, **temperature 0**, three runs:

| run | all cases | human messages | tool calls |
|---|--:|--:|--:|
| P36, alone | 121/150 | **84**/113 | 393 |
| P38, in the pool | 118/150 | **81**/113 | 393 |
| P40, in the pool | 119/150 | **82**/113 | 390 |

**Every pair is a tie** (4:1 p=0.375, 3:1 p=0.625, 2:3 p=1.000). The member does not
change. **The gate demands 83.**

So `vLLM` is not run-to-run deterministic at temperature 0 — continuous batching
changes the numerics — and this member's ±3-case spread straddles the threshold.
**P36 reported "the first pool member clears its gate". It cleared on one run of
three, and which side it lands on is decided by the scheduler.** That claim is
qualified here rather than left standing.

**What is not in doubt is the effect.** Against the base on the same cases:
**8 : 51 discordant, p ≈ 0** **[ran]**. The expert wins 51 cases the base loses and
loses 8 it wins. A marginal *gate verdict* and a marginal *effect* are not the same
thing, and only the first one is marginal here.

## What the split between the members says

**The member that needs to decide works; the member that needs to reason does not.**
Email is a two-of-four rule over facts the tools hand over. Fluids asks for Manning,
Swamee-Jain, centroid depths and areas composed over numbers that change per case.
600 supervised examples taught the protocol perfectly and taught the physics not at
all.

That sits against something already measured and not re-derived: in P6/P7 a fluids
expert reached **40/40 — with a calculator, on a suite whose values were given in the
statement** **[ran]**. Here it has a calculator and still fails, because it must also
*find* the values. The difficulty between those two suites is real, and it now has a
number on it.

## What this does not claim

- **Not that fluids is unlearnable.** One corpus, one size, 600 examples, three
  epochs. Nothing here says a larger or better-shaped corpus fails.
- **Not that the pool is disproved.** The substrate is measured three times; what is
  unproven is a *second useful member*.
- **Not routing.** The client still names the expert.
