
---

## The design is void, and the data that voids it was already on disk (2026-09-12) [ran]

An outside reading of the pre-registration raised a mechanism I had not: a target
whose budget is cut does not make *human* mistakes, it **truncates** — it runs out
of buffer mid-derivation and whatever number was last on the page becomes its
answer. If that is what the 13 failures are, the informative arm measures buffer
length, not reasoning, and any candidate that also stops early would agree with it
for reasons that have nothing to do with quality.

**Checked against `results/P10-baseline-recheck-20260909/`. All 13 are truncations.**

| | `want` | target @2k | target @6k | where the 2k text stops |
|---|--:|--:|--:|---|
| `phys-0002` | 1.849 | **0.9** | 1.8473 | `…1.17064 m/s$$` · **2. Reynolds numb** |
| `phys-0003` | 68.53 | **2.0** | 68.52 | `…(0.0705 m)^2 ≈ 0.0051530 m^2$$` |
| `phys-0009` | 1124 | **0.0** | 1137.92 | `…(0.247 m)^2 ≈ 0` |
| `phys-0015` | 226.2 | **0.0359** | 225.14 | `…(0.214 m)^2 ≈ 0.0359` |
| `phys-0021` | 842.9 | **0.029** | 850.09 | `…(0.194 m)^2 / 4 ≈ 0.029` |
| …and 8 more | | | | every one cut mid-derivation |

**The @2k answers are pipe areas, velocities and bare exponents** — intermediate
values that `parse_answer`'s last-number fallback picked up off an unfinished page.
**At 6k the same model answers all 13 correctly.** Not one is a reasoning error.

### So the fallible target does not exist, and that voids the arm

The pre-registration named three voiding conditions. The run hit a fourth that none
of them covered: **the target is not wrong, it is cut off.** The 13 cases that were
supposed to be the only place where agreement and correctness can disagree turn out
to be 13 places where the target has no opinion at all.

That leaves this suite with no usable target for S2. The one model that is ahead is
**30/30**, where agreeing with it is being correct and the ordering test passes by
definition. Reducing its budget does not make it fallible; it makes it silent.

**No GPU and no API call were spent finding this.** The columns that decide it —
`got` at two budgets and the tail of the truncated text — were written by P10 three
days earlier.

### What is bought next, and what is not

**Not bought:** the four candidate runs. They were queued behind P21 and are
cancelled. There is nothing for them to be ranked against, and running them would
produce a ladder with no rung to compare it to.

**Bought instead, and it is one API call:** a target that is *genuinely* weaker
rather than artificially truncated — a smaller frontier model at the full 6k budget,
so that its errors are finished answers that are wrong. If one lands between the
best candidate and 30/30 **with complete responses**, S2 has its arm. If every
available model is either at the ceiling or below the candidates, S2 is not
answerable on this suite and that is the finding.

**Redesign count: 2.** The first was a change of machine. This one is a change of
target, forced by the discovery that the target chosen does not have the property
the design required. The stopping condition stands: a third redesign is the point
at which this is looking for a result rather than measuring one, and S2 would be
reported unanswerable on this suite instead.
