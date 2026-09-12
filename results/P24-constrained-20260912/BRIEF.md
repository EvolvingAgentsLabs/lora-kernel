# P24 — the one number where code beats weights, attacked directly

**Pre-registered 2026-09-12, before anything was built.**

## The finding this exists to remove

P21 ended in a tie on coverage and a clear loss on cleanliness **[ran]**:

| | hand-written rule | kernel adapter |
|---|--:|--:|
| oracle's tool values | 93/96 = 0.969 | **94/96 = 0.979** |
| calls made | 96 | 116 |
| calls the tools **refused** | **0** | **20 — 17.2%** |

The adapter is not worse at knowing what to ask. It is worse at *saying* it. A
rule cannot emit a malformed call because a rule does not emit characters; it
assembles them. **That is the whole of code's remaining advantage here**, and it is
an advantage a sampler can take away.

## The hypothesis

**A grammar mask over the sampler drives the rejection rate to zero by
construction, without costing coverage.** Emitting a character that cannot begin a
valid call is made impossible rather than unlikely — the same move `capability-kernel`
and `llm_os` made with a token trie, applied to the tool-call surface instead of a
capability manifest.

This keeps the architecture's shape. The mask is a **runtime primitive, not a
second model**: no weights, no forward pass, a `LogitsProcessor` of about a hundred
lines. The intelligence of the protocol stays where it is, in the adapter.

## What the mask can and cannot do, said before the run

**It can** forbid `<lookup>fluid=water property=density` — a missing separator, an
unclosed tag, a tool name that does not exist, a key the tool never accepts.

**It cannot** forbid `<lookup>fluid=glycerin; property=density; T=20</lookup>` when
the problem was about water. A well-formed query for the wrong thing passes every
grammar. So the prediction is specific and it is not "the kernel gets better":

> Rejections go to **0**. Calls made fall from 116 toward 96. Coverage stays at
> **94/96 or above**. The cases that were `malformed` become `wrong args` or pass.

## Falsification, fixed now

- **The mask fails** if rejections reach 0 and coverage falls **below 93/96** — the
  rule's own number. Buying syntax with meaning is a loss, not a trade, and it would
  mean the mask is cutting off tokens the adapter needed.
- **The mask is pointless** if coverage rises above 94/96. It cannot add knowledge,
  so a coverage *gain* means the grammar is doing work the adapter was supposed to
  do, and the arm would be measuring the mask's built-in assumptions.
- **The step is void** if the unconstrained arm is not re-run on the same session
  and the same seed. P21's kernel arm ran across two reclaimed cards; comparing a
  masked run against that number instead of against a fresh one would put the
  session in the result.

## What it settles, and the honest limit

Settled if it passes: **the last measured advantage of a hand-written harness over
a learned one disappears**, and it disappears without adding a model — which is the
architecture's own claim rather than a workaround for it.

Not settled: whether any of this ports. The rule it ties is **144 lines** that know
this suite's label vocabulary, its unit table, its fluid names and its phrasings —
not the twenty a summary would suggest. A tie against that is not a tie in kind, but
**P21 did not measure portability and neither does this**. That experiment is still
unbought.

---

## The prediction, computed before buying anything (2026-09-12) [ran]

The mask is replayed character by character over **every call P21's tools actually
refused**, recovered from the stored transcripts. No GPU, no training.

| | |
|---|--:|
| refused calls visible in P21's records | 19 |
| the mask would have made impossible | **14 = 74%** |
| the mask lets through | **5** |

**And the five it misses are the right five.** Every one is syntactically perfect
and was refused for a reason no grammar can see:

    <lookup>fluid=water; property=viscosity; T=20</lookup>
      -> no entry for water at 20 C; this handbook lists []

The problem's handbook holds invented codes, and the adapter asked for water. That
is a knowledge failure wearing a valid syntax, and a mask that caught it would be
doing the adapter's job — which this brief's own falsification condition forbids.

**What it does catch** is the whole of the syntactic failure: a second key set
invented out of nothing (`<lookup>Re=1424; nu=1.51e-05; f=0.023</lookup>`), a
property the tool does not have (`property=f`), a unit that does not exist (`m2`),
and a body that ran off into prose (`<convert>value\n6. = 90.2**2</convert>`).

### So the pre-registration is tightened, before the run rather than after

The original prediction said rejections go to **0**. That is now known to be wrong
and it is corrected here rather than quietly met:

> **Rejections fall from 20 to about 5**, and the residue is semantic — the adapter
> asking for something that is not in this problem. Calls made fall from 116 toward
> 100. Coverage stays at **94/96 or above**.

A run that lands at 5 confirms the mechanism. A run that lands at 0 means the mask
is deciding content and the arm is void, which is the second falsification
condition and is now much more likely to be the interesting one.

## What the mask cannot see, recorded as a limitation

A missing separator inside a free-form value passes:

    <lookup>fluid=water property=density</lookup>     # accepted by the grammar

`fluid`'s value is an invented code, so any characters are legal there and the
grammar cannot know where the value was meant to end. Engineering around it would
mean guessing that a space before a known key name is a separator — a heuristic,
and this project has paid for heuristics that looked like rules before.

## The checker paid for itself three times over

`grammar_check.py` replays all **2226 calls** in both corpora and the evaluation
through the mask and fails if a single legal character is refused. It caught three
bugs in the grammar before any of it ran:

1. `T=20` blocked, because `_args` lowercases keys and the mask offered only `t`.
2. `to=m</convert>` blocked, because the value being completed included the closing
   tag and prefixes no unit.
3. `</convert>` blocked at the `/`, a dead end the mask had opened itself by
   allowing the `<`.

**A mask that blocks a legal call measures itself.** Each of those would have shown
up on a GPU as the adapter getting worse.

---

## How the arm is bought

The masked run inherits P21's finished arms rather than re-buying them, so only the
treatment costs GPU time:

    cp results/P21-handbook-20260911/multitool_results.json \
       results/P24-constrained-20260912/
    python3 -m training.harness.multitool_run --base Qwen/Qwen2.5-3B-Instruct \
        --n-eval 30 --masked

The runner skips every arm already marked complete, and the masked arm is written
under its own label — `kernel adapter, grammar-masked` — so **the unmasked number
is not overwritten by the thing it is being compared against.** All four arms end
up in one file, on the same cases, from the same adapters.

**The adapters are the same weights**, carried by the session cache rather than
retrained, or the comparison would include a second training run. Nothing about the
model changes between the two kernel arms; the only difference is a boolean mask
over the sampler on the kernel's turn.

**The mask is applied to the kernel turn only.** The domain adapter writes physics
and prose, and constraining that would be constraining the expert's work rather than
the protocol — which is this repository's recurring way of building an instrument
that does the subject's job.
