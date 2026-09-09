# P8 — `harness.lora`: does the protocol compose, or must every expert carry it?

**The claim under test, and why it is the last one standing.**
`ARCHITECTURE.md` §4: the kernel owns *how to act* — action tokens, tool syntax,
state — and a domain adapter owns *what is true*. They must stay separate,
because merging them "would make every domain adapter re-learn the protocol,
which is the cost this design exists to remove".

P7 measured the **merged** case at 40/40 **[ran]**: one adapter that learned
fluid mechanics and `<calc>` syntax together. That is
`TECHNICAL-REFERENCE.md` §5's option 3 — the one listed in order to be rejected.
**Separation itself has never been measured**, and everything downstream of it —
a pool of experts sharing one kernel, a tool surface that can change without
retraining every expert — depends on it holding.

**Four arms, each isolating one thing.**

| arm | what it answers |
|---|---|
| base + tool | already 0/40 with 53 calls: the tool alone is nothing |
| **kernel + tool** | a protocol adapter that has never seen physics: can call, cannot compute |
| **domain + tool** | the P6 expert: physics in prose, no tags. Knows what, not how to ask |
| **kernel + domain + tool** | **the claim** — both deltas over one base, at once |

**Falsification, written before the run.** If the composition does not clearly
beat both halves alone, the protocol does not compose: every expert must carry
it, which is the merged adapter, and changing the tool surface then costs a
retrain of the whole pool — precisely the price the architecture claims to avoid.

**The kernel corpus contains no domain.** 600 examples of shop receipts, means,
compound growth, average rates, cone volumes and logarithms — the same protocol
(numbered chain, `<calc>` call, carry the returned value, final JSON) with no
pipe, no fluid, no Reynolds. If a kernel trained only on that can make a physics
expert start calling the tool, the protocol is genuinely separable.

**The domain corpus contains no protocol.** The 598 prose chains the teacher
wrote for P6, where the model computes inline and gets it wrong — the expert that
thinks without knowing how to ask.

**Composition.** Both adapters loaded over one resident base and activated
together, which is `TECHNICAL-REFERENCE.md` §5's option 2 (stacked). Option 1
(sequential) is the cheaper fallback if stacking is unavailable, and option 3 is
what P7 already measured.

**Cost.** Two adapter trainings on an L4, then four evaluation arms of 30 cases
each with the harness loop. No frontier calls: the teacher's contribution is
already in the corpora.

**Redesign count.** 0.
