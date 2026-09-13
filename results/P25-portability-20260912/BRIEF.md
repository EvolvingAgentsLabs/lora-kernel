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

---

## A third voiding condition, named before the numbers arrive (2026-09-12)

The domain adapter that writes the chain **was trained on fluid mechanics**, and
P25's problems are not. The statements carry their own formula so no subject
knowledge is needed to solve them — but the expert still has to *name the steps*,
and a fluids-trained adapter naming steps on a materials problem may write labels
that correspond to nothing the oracle looked up.

**If that happens, a kernel score of zero is ambiguous**: it could be a protocol
that does not travel, or an expert that never gave it a step worth answering. Those
are different findings and only one of them is about the thing being tested.

So, fixed now:

- **The arm is void if the chains do not contain the steps.** Measured from the
  transcripts afterwards: for each case, does the expert's chain name the quantity
  the oracle looked up? If the labels do not correspond, the tool arms had nothing
  to hit and this experiment measured a domain adapter, not a protocol.
- **Both tool arms receive identical labels**, so the *comparison* between them
  survives even when the absolute numbers are low. The rule's 0/61 replay already
  stands on the oracle's own labels — its collapse is not caused by this.
- **The kernel adapter is carried, not retrained.** The cached tarball now holds
  only `kernel-mt`, which is complete; the `domain-mt` directory in the old one was
  empty, a stale artefact from before the watcher was fixed, and the runner's weight
  check would have caught it. It is deleted rather than kept.

This is the failure this repository has paid for most often: a number that is real,
low, and about something other than the question. It is cheaper to name it now than
to argue about it on Monday.

---

## Redesign 1 — a defect I created, caught by the run (2026-09-12) [ran]

The kernel arm was stopped after three cases. Not because of the score, but because
of what the transcript showed:

    1. Part mass: <convert>value=0.81; from=kg; to=g</convert>= 810
    2. Density: <lookup>specimen=5262-N; property=density; T=300</lookup>
       = ERROR: lookup needs ['fluid']
    4. Density: <lookup>fluid=water; property=density; T=300</lookup>
       = ERROR: no entry for water at 300 C; this handbook lists ['5262-n']

**The adapter chose the right tool, read the code out of the prose, and built keyed
arguments — and was refused for the name of a key.** It wrote `specimen=` because
**the statement says "a part of specimen 5262-N" while the oracle's chain writes
`material=`.** That inconsistency is mine, introduced when the domain was written.

This brief's own concession says refusing a noun *measures the noun*. So the arm was
measuring a mismatch I authored, and a zero from it would have been reported as
portability falsified.

**The fix is to the material, not to the checker.** The prose now says "material"
everywhere the oracle's key says `material`. **The tool was not loosened** — no new
alias, no relaxed matching — because relaxing the gate after seeing which arm it
catches is how an instrument starts working for a result. `grammar`-style
concessions stay exactly where they were pre-registered.

**All three arms are re-run**, not just the kernel: the statements changed, so the
cases are not the same cases. The 0/30 and 0/63 already banked are discarded rather
than reused.

**What survives from the aborted run, because it is not about the noun:**

- The expert names **8 of 9** of the oracle's lookup steps on a subject it never saw,
  and invents the value in 8 of 9 — so the third voiding condition does not fire and
  the no-tool arm's 0/30 is the gate working, not the expert collapsing.
- The rule's live 0/63 matched its offline 0/61 prediction exactly.
- `<convert>value=0.81; from=kg; to=g</convert>` is a **real** protocol failure and
  stays on the record: kilograms were already SI and the conversion runs backwards.
  The noun fix does not touch it.

**Redesign count: 1.** The stopping condition for this experiment is the project's
usual one — a third redesign means it is looking for its result.
