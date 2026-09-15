# Sufficiency, not parity: the suite had no easy end to measure

**Analysis, 2026-09-15.** Prompted by the objection that the gate is wrong: a small
expert may never reach a frontier model on research-level fluid mechanics, and the
target should be **a known and acceptable level of problem-solving**, with the ceiling
set by *the problem* rather than by what a frontier happens to find easy.

The objection is correct, and the data is worse than the objection. **The suite has
no difficulty axis at all.**

---

## 1. What was actually measured

Regenerating P41's 90 cases from their seed and reading the **oracle's own solution
length** **[ran]** 2026-09-15:

| family | oracle steps | distinct tools | local | frontier |
|---|---:|---:|---:|---:|
| manning_channel | 6 | 2 | 0.304 | 0.826 |
| hydrostatic_force | 6 | 3 | 0.043 | 0.609 |
| venturi_flow | 7 | 3 | 0.136 | 0.682 |
| pipe_head_loss | 9 | 3 | 0.000 | 0.818 |

- **The suite's floor is six steps.** There is not one case below it.
- **Each family is pinned at exactly one depth.** Depth and family are the same
  variable, so nothing in this suite separates *which physics* from *how long the
  chain is*.

**So the experiment could only ever ask one question**: can a 3B expert solve a
six-to-nine-step multi-tool chain? It could never ask whether a small expert is
sufficient at the easy end of its own domain, because the easy end was never
generated. Every conclusion drawn about "the reasoning expert fails" is a
conclusion about that band and no other.

---

## 2. This is a headroom failure upside down, and we had no rule for it

The standing rule in `CLAUDE.md` is to check the **ceiling** first: if the baseline
already passes everything, every arm ties and the tie reads as success. Two
instruments have been caught that way.

**The mirror has no rule and has now cost a conclusion:**

> **If every task sits above the treatment's floor, every arm fails — and the
> failure reads as "the approach does not work."**

A suite with one difficulty cannot tell *this expert is too weak* apart from *this
suite is too hard*. Both produce 0.122.

That is the finding, and it is added to §3 of `CLAUDE.md` beside the others.

---

## 3. And the base is a floor we did not choose

Qwen 2.5 is an old family, and the objection that it caps what an expert can reach
is fair. It is also **forced**: P33 measured that vLLM 0.29.0 accepts a LoRA on
`Qwen3.5-4B`, logs `Loaded new LoRA adapter`, and **serves the base anyway**
**[ran]** — the C18 identity gate. So every number here is a **lower bound** on what
a small expert can do today, not an estimate of it. Worth stating whenever one of
these numbers is quoted outward.

---

## 4. What was built, and what it makes askable

`training/physics/ladder.py` — four rungs **below** the suite's floor, same domain,
same three tools, same per-case invented handbook that cannot be memorised:

| rung | steps | what it adds over the one below |
|---|---:|---|
| `L1_property` | 1 | ask at all, and for the right property |
| `L2_pressure` | 2 | one formula, `p = ρ g h` |
| `L3_pressure_converted` | 3 | **choosing to convert** — the smallest place a harness decision is visible |
| `L4_force_on_base` | 4 | a second formula on the first's result |

`fluids_sim --families {suite,ladder,full}` runs them through the existing runner and
scorer — **no second instrument to keep honest** — and reports `by_steps`, accuracy
against **depth** rather than family name, so the output is a curve rather than four
numbers. A family of unknown depth lands in a visible `"?"` bucket rather than being
dropped, because a bucket nobody can see is exactly how the by-case arithmetic
published 0.957 for 0.733.

The ladder's own arithmetic is checked by **running its oracle chains with the real
tools** and matching the published answer. That test immediately caught a 1.3e-6
disagreement in `L4` — the answer had been computed in parallel with the chain
instead of *from* it, which is P38's rule (call the thing you teach, never copy what
it prints) broken in the oracle rather than in a corpus.

---

## 5. The arm to buy, and it replaces the one proposed an hour ago

**Superseded:** *train a narrow expert on `manning_channel`, gate 0.826.* That arm
takes the frontier's score as the gate on a family that has no easy end — exactly
the mistake this analysis is about. Not bought.

**Instead, and first: a headroom sweep, no training at all.**

Run three arms over the full ladder, 1 → 9, the cheap one first:

1. **The bare base, no adapter.** Where does `Qwen2.5-3B-Instruct` fall off the
   ceiling? Rungs it already passes cannot show an adapter anything — that is the
   ordinary ceiling check, and it decides which rungs are worth training for.
2. **The existing `fluids-full` expert, unchanged.** It has already been trained and
   costs only inference. Its curve against depth is the actual answer to *where does
   a small expert stop being sufficient* — and it is obtainable without training
   anything new.
3. **The frontier, as a ceiling check only.** A rung the frontier fails is a broken
   rung, not a hard one. It is **not** the gate.

**Falsification, written before the run:** if the expert's curve is flat — if it
fails a one-step lookup at roughly the rate it fails a nine-step chain — then
difficulty is not what is blocking it, this whole analysis is wrong, and the failure
is something the ladder does not measure.

### The gate is absolute, and it is a product decision

For the rungs where sufficiency is claimed, the bar is **not** the frontier's score.
It is what makes an expert usable without a checker behind it. **Pre-registered at
0.90**: at 0.80, one answer in five is wrong and every answer has to be verified by
hand, which removes the reason to have the expert. The frontier's number is reported
beside it and ranks nothing.

---

## 6. What this does not claim

- **Not that the expert will do well on the easy rungs.** Nothing here measures it;
  that is arm 2 and it has not run.
- **Not that the six-to-nine-step result was wrong.** It stands. What changes is its
  scope: it is a statement about that band, and it was being read as a statement
  about the expert.
- **Not that an absolute gate replaces the frontier gate everywhere.** Where the
  question is *can the frontier be withdrawn here*, the frontier's score is the right
  gate and P41 used it correctly. The two questions are different and the project had
  been asking only one.
