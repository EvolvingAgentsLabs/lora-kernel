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

---

**Pre-registered follow-up, written before the composition arm reported
(2026-09-09).** Three arms were in hand — base 0/30 with 44 calls, kernel 1/30
with **169**, domain 0/30 with **0** — and the composition was still running. If
plain stacking fails, one alternative is bought and only one: `add_weighted_adapter`
at 0.5/0.5. The reason is mechanical rather than hopeful — `LoraModel` sums the
active deltas, so two adapters at α=32 apply twice the perturbation the base was
tuned under, and a weighted combination is the standard correction, not a second
chance at the hypothesis. If the weighted stack also fails, §4's separation is
falsified as implemented and the merged adapter is the configuration that works.

**The persistence fix is not a redesign.** `score()` now banks each case instead
of each arm, after a reclaimed session took 20 completed cases with it. It changes
what survives a crash, not what is measured, and the eval set, seed and gate are
untouched. **Redesign count: 0.**

---

**Outcome (2026-09-09).** Both composition modes fail, and the second one refutes
the explanation offered for the first.

| arm | accuracy | tool calls | cases with a rejected call |
|---|---|---|---|
| base + tool | 0/30 | 44 | — |
| kernel + tool | 1/30 | 169 | 0 / 30 |
| domain + tool | 0/30 | 0 | — |
| kernel + domain, stacked | 0/30 | 154 | 11 / 30 |
| kernel + domain, blended 0.5/0.5 | 0/30 | 129 | 12 / 30 |

Halving each delta did not restore call fidelity, so the doubled-perturbation
reason written above is **wrong**, and it is left standing rather than edited —
it was the prediction the blend arm tested, and it lost. What survives is that
two LoRAs trained independently on the same projections interfere rather than
compose, and the interference destroys exactly what each was most specific about.

The protocol **is** separable as a thing to learn: a kernel with no physics in its
corpus calls the tool on 30 of 30 fluid-mechanics cases while the physics expert
calls it 0 times. It is not separable as a thing to serve.

Sequential activation (§5 option 1) was **not** bought. One alternative was
pre-registered and one was run; a third mode chosen after two failures would be a
search, not a measurement.

**Redesign count: 0.**

---

**Correction, same day (2026-09-09), before any further arm was bought.**

Reading the corpora side by side after the run: the kernel corpus is 600/600
`<calc>` and 0 LaTeX; the domain corpus is 0/598 `<calc>` and 433/598 LaTeX; the
domain corpus's system prompt ("show no working") contradicts its own 598
working-showing targets; and **every arm was evaluated under that domain prompt**,
including the kernel's.

So the corruption I attributed to subspace interference is the superposition of
two surface forms the adapters were literally trained on, and P8 cannot separate
"composition fails" from "the halves were taught different languages and judged
under a prompt matching neither". The interference reading is **withdrawn**; the
arm numbers stand. The kernel's 30/30 well-formed calls stand and are stronger
than first reported, since they were produced under a hostile system prompt.

Composition is now **unmeasured**, not falsified. Redesign count still 0 — nothing
about the instrument was changed to reach a friendlier number; a confound was
found and published.
