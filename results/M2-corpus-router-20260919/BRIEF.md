# M2 — the router as a tiny model of the members' corpora (pre-registered 2026-09-19)

**Question.** Can a very small model of the released corpora decide *whose distribution a
request falls in* — and abstain to the frontier when it falls in none — at least as safely as
the keyword dictionary in `route.py`, on requests the dictionary was **not** written for?

**Why.** [`docs/PLAN.md`](../../docs/PLAN.md) milestone 2, [`FOUNDATIONS.md`](../../docs/FOUNDATIONS.md) §8.5.
The dictionary is at 1.000 on every generated prompt set — nothing can beat it there — and a
dictionary's failure grows with the pool (Adaptive Minds **[read]**: 48.3 % → 31.7 % from 5 to 30).

**Model, provider, cost.** No model is called and no GPU is used. Arm 1 is a generative
classifier in pure Python with no dependency, so it can live inside the proxy:

- one word-level uni+bigram model per member, add-α smoothed (α = 0.1), trained on the user
  turns of the member's **released corpus** with the proxy-appended tool block cut off — what
  the router actually sees;
- **which member:** $\hat m = \arg\max_m \log p_m(x)$;
- **abstain unless the whole request looks like the corpus:** with $\ell_m(t)$ the per-token
  log-probability, $s_m(x) = \min_{i} \tfrac1w\sum_{t=i}^{i+w-1}\ell_m(t)$ over windows of
  $w = 8$ tokens, accept iff $s_{\hat m}(x) \ge \tau_{\hat m}$, where $\tau_m$ is the **1st
  percentile** of $s_m$ on a 20 % split of the corpus held out of the counts. A window-minimum,
  not a mean, because both members share one long inbox listing: a foreign question after a
  familiar listing must not be averaged away.

$\alpha$, $w$ and the percentile are fixed **here, before any router number exists**. Changing one
after seeing a result is a counted redesign.

**The sets — five, and the dictionary was written for the first only.**

| set | what | truth |
|---|---|---|
| A | the evaluation draws the corpora never saw: email 475 (seed 717171), desk 240 (seed 424242) | the member |
| B | A's prompts with the member's question **paraphrased** — 8 fixed variants each | the member by intent; *its quality there is unmeasured* — counted as recovered local share, never as correct |
| C | out-of-region text that **contains a member's key phrase** ("…is this important to merge today?") | out |
| D | plain out-of-region text: fluids statements from the physics generator, runtime finalisation requests, general requests | out |
| E | a real inbox listing followed by **another task** ("Draft a reply to this.") — 8 fixed variants | out |

Sets B–E were written by the same author as the router. That is the known limit of every
suite here (`RECORD.md` §3); the real test is milestone 5's traffic.

**Order (arms in sequence).** 1. **Headroom:** the dictionary alone on A–E. If it misroutes
nothing to local on C–E and loses nothing on B, there is nothing to buy and the run stops. 2. The
corpus router on the same sets.

**The metric is the term a router can change** (§8.4): **misrouted-to-local** — a request served
by a member whose corpus it does not belong to (wrong member, or any local on C, D, E) — and
beside it the **lost-local** share (A or B sent out), which costs money, not correctness.

**Verdict, written first.**

| outcome | reading |
|---|---|
| router misrouted-to-local ≤ dictionary's over B–E, **0 on A**, lost-local on A ≤ 1 %, and ≥ 95 % of C ∪ D ∪ E abstained | **PASSES** — it becomes `--router corpus`; the measured `serve: local\|out` table still decides what a recognised region does |
| more misrouted-to-local than the dictionary, or < 95 % abstention | **FALSIFIED** as specified. One arm remains in the plan (a small LM with a classification head); it is not bought in this session |
| passes safety and recovers nothing on B | safe and pointless: report it, keep the dictionary |

**Redesign counter: 0.**

## Attempt 1 **[ran]** 2026-09-19 — safe, and it does not pass as specified (`router_attempt1.json`)

Headroom exists: the dictionary misroutes to local **13 of 14** on C and **47 of 120** on E, and
loses 131 of 240 on B. The corpus router: **0 misrouted-to-local on every set**, 210 of 210
abstained on C ∪ D ∪ E — and **17 of 715 lost on A (2.4 %, gate ≤ 1 %)**, **0 of 240 recovered on B**.

**Why A loses 17, read per case:** every one has its worst window on the **sender's name and
address** — no unseen token at all, only a first-name/surname/company *combination* the corpus
never drew. The threshold was measuring the name pool's combinatorics. On real traffic every
sender is unseen. A check that fails while the capability works is measuring something else.

## Redesign 1 of 3, written before it runs

**The corpus itself says what is frame and what is data.** A token type is **frame** for member
$m$ iff it occurs in at least **half** of $m$'s corpus documents (document frequency ≥ 0.5); every
other token becomes one symbol, `<slot>`. Names, subjects and previews are slots; `from :`,
`subject :`, the question are frame. The n-gram model and the window-minimum run on that sequence.

A window-minimum only sees what is *present*, and a listing with its question **removed** is all
familiar. So a second criterion, from the same counts: **frame coverage** $c_m(x)$ — the share of
$m$'s frame bigrams (those in ≥ half its documents) that occur in $x$. Accept iff
$s_m(x) \ge \tau_m$ **and** $c_m(x) \ge \kappa_m$, both the 1st percentile on the held-out split.

It is a dictionary **learned from the corpus** with an anomaly test beside it — no hand-written
key. DF = 0.5 is fixed here. Same sets, same verdict table, no other change.

**What I expect and would count against it:** B still unrecovered — a lexical model cannot tell
a paraphrase of the member's question from a different task; both are "a familiar listing, then
an unfamiliar sentence". If that holds, paraphrase recall needs *semantics* and belongs to arm 2.

## Attempt 2 **[ran]** — redesign 1 (`router_attempt2.json`)

First run of it lost 60 of 715 on A: **my bug, not the design** — the code picked the "nearest"
member before asking who *claims* the request, and an email model covering 0.84 of its own frame
(the shared listing) displaced a desk request it never claimed. With the code doing what this
brief says: **A 715/715, 0 lost, 0 misrouted; C 14/14 and D 76/76 abstained; E 16 of 120
misrouted** (dictionary 47); B 15 of 240 recovered (dictionary 109). Misrouted-to-local 16 against
the dictionary's 60 — and abstention 194/210 = **92.4 %, under the 95 % written above: as
specified, it does not pass.**

**Why E leaks, read per case:** all 16 are desk listings. Foreign words become `<slot>`, and a run
of slots is what a subject line looks like — a foreign sentence reads as data; and the desk corpus
has two sub-shapes (coverage 0.75 and 1.0), which loosens κ to 0.75, so a full-shape listing with
its question removed still covers enough.

## Redesign 2 of 3 — the last one in this session, whatever it gives

Twice is suspicious: sets B–E have now been looked at twice by the person designing against them.
So this attempt carries its own check. **The design is frozen first; then new sets C₂ and E₂ are
written — new foreign tasks, new keyed texts, never scored before — and the verdict is read on
those.** No redesign 3 here: if it fails on the fresh sets, milestone 2's arm 1 is closed as
*safer than the dictionary, not passing as specified*, and the dictionary stays the default.

**The change, one idea:** a request's frame has a *grammar*, and the corpus wrote all of it. Score
the **least likely single frame transition** (window $w = 1$ instead of 8) and add an
end-of-request symbol, so that "…`<slot>` `.` `</s>`" or "`<slot>` `?`" — transitions the corpus
never wrote — cannot be averaged away by seven familiar slot-to-slot steps beside them. Coverage
stays as it is. Nothing else moves.

## Attempt 3 **[ran]** — redesign 2, frozen, then scored once on sets written afterwards (`router.json`)

| set | n | dictionary: misrouted-to-local · lost | corpus router: misrouted-to-local · lost |
|---|--:|---|---|
| A in distribution | 715 | 0 · 0 | **0 · 0** |
| B paraphrased question | 240 | 0 · 131 | 0 · **240** |
| C keyed foreign text | 14 | **13** · — | **0** · — |
| D foreign text | 76 | 0 · — | 0 · — |
| E listing + another task | 120 | **47** · — | **0** · — |
| **C₂ fresh** keyed foreign text | 8 | **8** · — | **0** · — |
| **E₂ fresh** listing + another task | 120 | **51** · — | **0** · — |
| **F fresh** legitimate request, sender and subject outside the generator's pools | 120 | 0 · **0** | 0 · **120** |

## Verdict — arm 1 does **not** pass, and the fresh sets are why it is believed

**What it buys, out of sample:** on foreign text the dictionary sends **59 of 128** to a local
member (C₂ ∪ E₂) and the corpus router **0 of 128**. The safety claim survived sets it was never
iterated on.

**What kills it:** on F it sends **every** legitimate request out. Read on one case: coverage 0.9
< κ 1.0 and the least likely transition −4.96 < τ −4.59 — every address the generator ever wrote
ends `.com`, so `. com >` is *frame* in the corpus and `.io`, `.nz`, `.se` leave the distribution.
**It learned the generator's uniformity.** `RECORD.md` §3 again: a generated suite cannot contain
a difficulty nobody thought of — and neither can a model of one. Real traffic is all F.

**And B is structural, as expected:** 0 of 240 paraphrases recovered. To a lexical model "a
familiar listing, then an unfamiliar sentence" is one thing whether the sentence paraphrases the
member's question or asks for something else. Telling those apart is **semantics**.

**Decision.** The dictionary stays the proxy's default. `corpus_router.py` stays in the tree as the
measured arm, not wired into `route.decide`. Redesigns spent: 2 of 3; the third is not spent here.
**Arm 2 is therefore an embedding model, not a larger n-gram model** — the same embedding space a
per-subdomain knowledge base would retrieve in (PLAN, milestone 7), which is a reason to build it
once. Its kill set already exists: **F**, plus C₂ and E₂ for safety and B for recall.

Two things the run taught about the instrument, both now in the code: the acceptance rule has to
ask *who claims* before *who is nearest* (60 requests lost to a bug the first fresh look caught);
and a set written **after** the freeze found in one pass what three looks at the old sets did not.
