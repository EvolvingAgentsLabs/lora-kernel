# BOK0 — more walks, and the gate chooses: test-time compute under the citation gate

**Written 2026-10-02, before anything runs.**

## What and why

GATE0 **[ran]**: the citation check, as a gate, withholds 86 of 165 not-right answers and 0 of 275 right ones — the
evaluation works when it **acts on the system**, not when it is handed back to the member as a hint (CITE0 **[ran]**,
0 repaired of 6). The gate is now on by default; what it withholds reaches the person as "could not verify". The
cheapest way to turn some of those into answers is to spend compute, not training: **walk again, and deliver the first
walk the gate passes.**

## The treatment — `+k4` (`training/wiki/wiki_arm.best_of_k`)

Walk 1 is the greedy walk — exactly the served arm. Only if the gate would withhold its answer (no final line, or
`Conversation.final_problem` not None) up to three more walks are sampled at temperature 0.7 (vLLM seeds 1–3); the first
whose final line passes is delivered, and if none passes nothing is. Every walk is graded and kept (`rec["bok"]`).

**Walk 1 is the baseline, in the same record:** the served arm (greedy + gate) delivers walk 1 when it passes, nothing
otherwise. So the comparison is within each row, and vLLM's run-to-run spread cannot make or hide it.

**The trap, named before the run:** the gate overlaps the grader (shown, opened, holds the numbers), so selecting by it
partly optimises toward the grader. What the gate cannot see — whether the cited statement is *the one the question asks
about* (`cite = "support"`) — the grader still checks, and every gain below is graded strictly. A gained row that cites
a statement holding the value but not the supporting one counts as not right.

## Member, provider, sets

`real-none-s0`, Gemma 4 E4B bf16 + LoRA, vLLM on one Colab L4, `--max-model-len 16384`, REAL4's runtime (`+page`).
Two sets, run in sequence, verdict pooled: **CITE0's 52** (`knowledge/spcc-regs`) and **REAL4's 52**
(`knowledge/logistics-regs`). Neither was used to design the gate or this selection.

## Verdict (fixed here), pooled over both sets

Per row: *gain* = walk 1 not right, delivered walk right; *new wrong* = walk 1 withheld by the gate, delivered walk
not right (a wrong answer now reaches the person where "could not verify" did).

- **BOK WORKS** — gain > new wrong at exact sign test $p \lt 0.05$, **and** gain ≥ 5.
- **BOK HELPS** — gain > new wrong, not significant.
- **FALSIFIED** — gain ≤ new wrong: sampling past the gate delivers as many wrong answers as right ones.
- **NOT ENOUGH RESAMPLES** — fewer than 5 rows resampled across both sets; reported, not rerun on a set built to fire.
- Beside: rows resampled, extra walks spent, gains per set, refusal rows (an unanswerable question whose walk 1 answered
  unverifiably and whose resample answers verifiably is a new wrong), right delivered before/after.

## Stopping condition

Two scoring sessions (one per set); k, the temperature, the sets and the bars do not change after the first walk.

## Run log

- **Attempt 1 — stopped, not a verdict** (`attempt1_bok0_cite0.json`, `attempt1_S_*_chain.log`): CITE0's set scored
  (52/52, 0 errors), then the session for REAL4's set was stopped by hand before it scored (the user's machine, which
  drives the chain, had to sleep for an hour — longer than a Colab session lives). **Read before any verdict, an
  implementation gap:** a walk 1 that ran out of context left the arm before `best_of_k` saw it — 2 rows of CITE0's
  set — although this brief resamples every walk 1 with no final line. The implementation now matches the brief (test
  `test_best_of_k_resamples_a_first_walk_that_ran_out_of_context`). Attempt 1's partial counts on CITE0's set were seen
  (gain 1, new wrong 2, 5 resampled); they are not the verdict, and the bars, k, temperature and sets do not move. Both
  sets are rerun from scratch. **This is the first change to BOK0's instrument.**

## Result

*(written after the run)*
