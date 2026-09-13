# P25 — the unbought experiment the S6 tie turns on

**Pre-registered 2026-09-12, before the domain was written.**

## Why this and not the guard

P21 ended in a tie: a learned protocol reproduced **94 of 96** of the oracle's tool
calls, a hand-written rule **93 of 96** **[ran]**. A tie is a real answer to the
question P13 opened, and it is also the weakest possible reading of the
architecture's claim — *if twenty lines of `re` do the same job, the weights are not
worth their memory.*

**But the rule is not twenty lines. It is 144**, and every one of them knows this
suite: the label vocabulary (`throat diameter`, `gate width`, `flow depth`), the
unit table, the fluid names, the phrasings (`X by Y`, `narrows from X to Y`), and
the shape of the invented handbook codes. The adapter learned from a corpus
containing none of the evaluation families.

**A tie between those two is not a tie in kind — and nothing in this repository has
measured that.** P9 showed the protocol travels to a new *domain* with the *same*
tool; this asks the question the tie actually turns on.

## The design

A second domain, written from scratch, with the same three tools and **none of this
suite's vocabulary**: different substances, different quantities, different units,
different phrasings, different handbook code shapes. Statements state their own
formula, so no subject expertise is needed from anyone and the protocol is what is
being measured.

**Neither competitor is touched.** The rule keeps its 144 lines; they simply do not
know this domain. The adapter keeps its weights. **Editing either one is the
experiment failing, not the experiment running** — the entire claim is about what
transfers without work, and a repaired rule is the work.

Three arms, same axis as P21, the oracle's tool steps:

| arm | what it tests |
|---|---|
| no tool layer | the killing arm — can the material be answered without querying |
| hand-written rule, **unchanged** | what 144 suite-specific lines are worth elsewhere |
| kernel adapter, **unchanged weights** | whether the protocol is a protocol |

## Falsification, fixed now

- **Portability is established** if the kernel holds near its 0.979 while the rule
  falls well below it. The rule's collapse is the point: it measures how much of a
  hand-written harness is the harness and how much is the suite.
- **Portability is falsified** if the kernel falls with the rule. The tie then
  stands as a plain tie, S6 stays amber, and the architecture's claim loses the
  argument it has been leaning on.
- **The arm is void if the rule does NOT fall.** A rule that scores well here was
  never suite-specific, so the new domain is not a new domain and nothing was
  tested. This is the condition most likely to fire and the easiest to rationalise
  away, so it is written down first.
- **The arm is void if the no-tool control answers the material**, exactly as in
  P21: per-case handbooks, values that did not exist at training time.

## What it cannot settle

The kernel keeps the three tool *names* it was trained on. This measures whether a
protocol survives a change of **subject**, not a change of **interface** — a domain
whose tools are called something else entirely is a third experiment, and the
adapter would have to be told the surface in the prompt to have any chance at it.
Claiming otherwise from this result would be claiming the thing that was not run.

---

## Built and checked before any GPU (2026-09-12) [ran]

**The domain.** Four families — bar elongation, thermal growth, conductor
resistance, heat to raise — over specimens named `8411-V`, `3323-L`, in gigapascals
and square millimetres and kelvin. Nothing in it resembles fluid mechanics, and the
oracle resolves **121 of 121** of its own tool calls with every answer reconstructed
exactly.

**Two fairness concessions to the competitor, made deliberately:**

1. **The new units live in the same `UNITS` table the rule reads.** Keeping them in
   a separate module would have handed the rule a defeat it did not earn — it would
   fail to convert GPa because its table is incomplete, not because its lines are
   suite-specific. The unit table is given away for free.
2. **`lookup` accepts `material=` as the same argument as `fluid=`**, and its
   error now names the properties a specimen has. An adapter meeting a new subject
   has to derive `property=modulus` from a label reading "Elastic modulus of the
   specimen"; refusing it without saying what the keys are would measure whether it
   guessed a noun.

### The voiding condition fires the other way: the rule collapses completely

| | oracle's tool values | declines | refused |
|---|--:|--:|--:|
| fluids (P21) | **93/96 = 0.969** | 0 | 0 |
| **materials (P25)** | **0/61 = 0.000** | **61** | 0 |

**It does not write a single wrong call. It writes none at all.** Every label misses
its `NEAR` table, every specimen code misses its name matcher, and every property
misses the `density`/`viscosity` branch — so `call_for` returns `None` sixty-one
times out of sixty-one.

### What a repair would cost, counted and not done

| what would have to be rewritten | lines |
|---|--:|
| `NEAR` label table | 11 |
| fluid names and handbook code shape | 9 |
| density/viscosity property branch | 10 |
| phrasing heuristics (`X by Y`, `narrows from`) | 8 |
| **total** | **38 of 109 lines of code** |

**Thirty-five per cent of the rule is the suite.** That number is the honest content
of "144 lines that know this suite", and it is why the tie in P21 was never a tie in
kind — but it is an argument until the kernel arm runs, and the kernel could equally
score zero here.

**The rule arm is still run** rather than assumed from this replay: `call_for` is
being asked in isolation, and the live arm asks it with the labels the expert
actually writes, which are not guaranteed to be the oracle's.
