
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

---

## The replacement target, pre-registered before the call (2026-09-12)

A target that is **naturally** weaker rather than artificially silenced: a smaller
frontier model at the **full 6k budget**, on the same 30 cases and seed, under the
same shared contract. Its errors have to be finished answers that are wrong.

**First and only purchase in this round: `google/gemini-3.5-flash-lite`.** It is
the weakest frontier model this project has already used, so nothing is being
shopped for.

### The three outcomes, and what each decides

| it scores | verdict |
|---|---|
| **30/30** | the suite has no gradient between the frontier and a 3B; the tautology is not escapable here |
| **≤ 14/30** | it is at or below `qwen3.5:4b`'s 14/30 and is not a target at all |
| **between** | **S2 has its arm** — but only if the next check passes |

### And the check that the last round did not have

**At least 80% of its failures must be complete responses.** The run stores `chars`,
`has_json` and the tail of every answer — fields the P10 records predate, which is
why the truncation had to be reconstructed from intermediate values. If its failures
are cut off mid-derivation, this is the same void arm with a different model on it,
and it is reported void rather than used.

**If no model lands in the band with complete failures, S2 is declared not
answerable on this suite and the objective closes at redesign 2.** There is no
third attempt; that was fixed before the first.

---

## The replacement target qualifies (2026-09-12) [ran]

`google/gemini-3.5-flash-lite`, 30 cases, seed 515151, shared contract, 6k budget.
**One API call's worth of work, $0.00 against a $10 ceiling.**

| | |
|---|---|
| verified | **21/30 = 0.700** |
| unparsed | **0/30** |
| failures that are **complete** responses | **9/9 = 1.00** (pre-registered bar: 0.80) |

It lands in the band: above `qwen3.5:4b`'s 14/30 and below the ceiling.

**And the failures are the kind the design needs.** Every one ends in a finished
derivation and a proper answer block, with a value that is plausible and wrong:

| | `want` | `got` | chars |
|---|--:|--:|--:|
| `phys-0001` manning | 13.78 | **20.252** | 914 |
| `phys-0002` head loss | 1.849 | **1.7946** | 1594 |
| `phys-0008` head loss | 10.16 | **19.467** | 1398 |
| `phys-0020` head loss | 26 | **31.621** | 1233 |
| `phys-0027` pump power | 453.5 | **442.27** | 1576 |

Compare the void arm, whose "answers" were `0.0`, `2.0`, `4.0` and `0.0359` — pipe
areas scraped off an unfinished page. These are wrong answers. Those were no
answers.

**So the 9 cases where agreement and correctness can disagree are real**, and S2's
ordering test has somewhere to be tested. The candidate ladder, cancelled when the
first target voided, is re-queued.
