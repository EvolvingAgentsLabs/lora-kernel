# Close experts on one problem, selected by acceptance

**Design, 2026-09-16. Nothing built yet.** The correction that produced it: *the two
subdomains we have are too far apart to ever meet in one problem, and a pool needs
several experts on **the same** problem.*

---

## 1. The number that proves the objection, and it is mine

P1 priced the subspecialty router and I reported the coarse route at **1.000** as
good news — *the layer is a dict, how cheap* **[ran]**. The other reading is the
right one: **a discrimination problem solved by twelve keywords is not a test of
expert selection.** Telling fluid mechanics from inbox triage requires nothing. A
pool whose members are that far apart cannot demonstrate a router, an acceptance
ranking, or a tournament, because nothing about choosing between them is hard.

And the same experiment shows where it *does* get hard: the fine route falls to
**0.845**, and its worst confusion is `L2_pressure → L3_pressure_converted` — the
same physics, differing only in whether a unit needs converting. **The lexical
baseline degrades exactly in the regime this design is about.**

## 2. Why acceptance, and not a router, is the selector here

When experts are far apart, a router reads the prompt and wins. When they are close,
the prompt stops carrying the answer — and the two questions come apart:

> A router asks **which expert looks relevant**.
> Acceptance asks **which expert actually wrote what the larger model would have
> written**.

Only the second survives when the candidates resemble each other, and it is the
question this project has never been able to ask.

### And drafting is the first task shape where acceptance is *necessary*

Triage has a mechanical verifier — importance is a definition over facts, so a score
exists without a judge. **Drafting a reply has none.** There is no rule that says a
draft is right, which is where S7's tournament has always stalled.

**Acceptance needs no verifier.** Same target, same prefix, same conditions; the
ranking falls out of a pass already being paid for. So this is not merely a better
test of selection — it is the first task where the metric is the only cheap one
available.

## 3. The three experts

One inbox, one set of tools (`thread_history`, `sender_stats`, `message`), one base.
**Only the policy differs**, which is the cleanest possible test of the pool thesis.

| expert | replies to | what makes it different |
|---|---|---|
| `draft-client` | client and commercial threads | commits to dates, hedges on price, formal register |
| `draft-team` | internal team threads | terse, references artefacts, assumes shared context |
| `draft-vendor` | invoices, contracts, admin | precise, cites reference numbers, requests documents |

They are deliberately **close**: all three are reply drafting, all three occur in one
person's inbox on the same day, and a keyword rule should struggle between the first
and the third.

## 3b. How close are they, actually? Measured before anything was trained

The design rests on the three being **close**, and the fluids/email pair was rejected
for being separable by twelve keywords. So the same keyword rule was written against
these three, knowing the generator — the generous direction — and run over 180 cases
**[ran]** 2026-09-16:

| what the selector can see | keyword accuracy |
|---|---:|
| **the listing alone**, before any tool | **0.000** |
| the listing **plus the thread** | **1.000** |

**Neither number is what the design assumed.** These three are not close in the sense
of *hard to tell apart*; they are a **step function** — impossible before the tool
call, trivial after it.

### What that does and does not break

**It does not break the reason to prefer this over fluids-vs-email.** There, the
listing itself gave the answer at 1.000, so selection was trivial *from the prompt*.
Here the prompt gives **nothing**, so *which expert looks relevant* genuinely cannot
be answered before the work starts.

**It does change what P50 can test.** Once the thread is read, a dict picks the
temática. So the question stops being *can we tell them apart* and becomes:

> **Does the obviously matching expert actually write the better reply?**

That is a sharper claim, and it is the one acceptance is for. A router says which
expert *looks* relevant; acceptance says which one **wrote what the larger model would
have written**. If the matching expert always wins, a dict suffices and acceptance is
redundant here. **If it does not — if `draft-client` writes better team replies than
`draft-team` does — then specialisation by temática is the wrong axis, and that is
worth knowing before three more corpora are built on it.**

### The alternative, named and not taken unilaterally

The temáticas could be redesigned to be genuinely confusable — three **registers on
the same subject matter** rather than three subject matters. That is closer to
*"depending on the draft or the idea, one of the two works better"*, and it would put
separability in the middle rather than at the ends.

**It is a redesign, and this repository counts them.** Once is fine, twice is
suspicious, three times is looking for the result. This would be the first, so it is
affordable — but it changes what the experiment claims, which makes it a decision to
take deliberately rather than while building.

## 4. The target is decided by a hash, not by quality

**`Qwen2.5-32B-Instruct`.** Every `Qwen2.5-Instruct` size shares a **byte-identical**
`tokenizer.json` with our base **[ran]** P48.

**`Qwen3.6-27B` cannot be the speculative target**, however good it is: its vocabulary
has **248,044 entries** against our 151,643. That is not a mismatch to work around —
a drafted id does not mean the same string to both models. It remains available as a
*quality reference*, which is a different job with different requirements.

## 5. The arms, bought in sequence

### P49 — headroom. Does the target write better drafts at all?

**No training.** If the target is not better than the bare base, acceptance against
it ranks nothing and all three arms tie — which is exactly how P42's third-party
adapter scored 0.825 against a base already at 0.815 **[ran]**.

**Measured without a judge** by a mechanical content check: a generated thread names
the facts a correct reply must carry — the date asked for, the reference number, the
amount, whether an ask is answered. **Did the draft include them?** That is
checkable, it is a floor rather than a quality score, and it catches the failure
acceptance alone cannot see: **an expert that mimics the target's style and says
nothing.**

**Gate:** the target must clear the base by a margin `bar.resolvable()` says is
detectable at the n we would run. **If it does not, the whole design is unbought.**

### P50 — are three experts three experts?

Train the three, serve them together, and check the pool gate already in the code:
each differs from the base **and from each other**. Then the real question:

**Does acceptance vary by temática?** For each case, compute each expert's acceptance
against the target on the same prefix. **Gate:** for each temática, the matching
expert beats the best of the other two on a **paired sign test** over cases
(`bar.sign_test`), because the arms share fixtures.

**Falsification, written before the run:** if acceptance is flat across the
expert × temática grid, they are one expert with three names — and the pool's
`members_are_distinct` gate is the thing that says so, not a reading of the numbers.

### P51 — back to OpenClaw

Only if P50 clears. The selection runs inside the agent: a reply is drafted by
whichever expert acceptance says fits, over the same MCP tools and the same synthetic
inbox that already run end to end **[ran]** P43.

## 6. What this design refuses to do

- **No grid.** P49 can kill the whole thing and costs no training, so it runs alone
  and first.
- **No judge.** If a step needs one, it is the wrong step. The content check is
  mechanical; acceptance needs no scorer; neither is a quality opinion.
- **No new suite.** The inbox generator, the tools, the MCP server and the OpenClaw
  path all exist. What is new is three corpora and a drafting task over the same
  fixtures.
- **No promise in the README.** Until P50 clears, this is analysis, and the README
  says so in the section that names what has not run.

## 7. The risks, named before they are excuses

- **The three may be indistinguishable in acceptance too.** Close enough to be
  interesting is close enough to be within noise; that is what the paired sign test
  and a power check before the run are for.
- **Acceptance can be high on a bad target.** P49 exists for this, and the content
  check is what keeps "both wrote nothing" from reading as agreement.
- **Three corpora is three chances at P38's drift** — a corpus that does not teach
  the prompt the model will be served. They are generated by *calling* the renderer,
  never by copying what it prints.
- **A drafting corpus has no oracle to check against.** Its invariant is weaker than
  the fluids one: we can assert the required facts appear in the reference reply, and
  that the decisive facts are *not* in the listing. Both are mechanical; neither says
  the reply is good.
