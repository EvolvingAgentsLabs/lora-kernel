# The plan

**A living document.** It is the single place where the project's position is recorded:
each milestone carries its objective, its gate and its falsification condition *before* it
runs, and its row is updated the same session a result lands — whichever way it lands.
Superseded text is struck, not deleted. What was measured before 2026-09-19 is in
[`RECORD.md`](RECORD.md); the plan that produced it is at the tag `v0.1-foundations`.

## 0. The objective, restated 2026-09-19

> **Build the service as experts defined by their corpora: a very small router that
> decides which expert's corpus a request falls in and abstains to a frontier model when
> it falls in none; and, per subdomain, a speculative pair — a LoRA on a small model and a
> LoRA on a large one, trained on the same corpus. Family: ~~Qwen 3.x~~ **Gemma 4 since 2026-09-25 (B1 [ran], the user's decision)**, small and large.**
>
> **Extended the same day: each expert also gets a knowledge base of its own subdomain —
> markdown notes, embedded, encyclopedic and operational — and what the LoRA learns is the
> *trajectory* through it: what to look up, in what order, and how to follow what it reads.
> The weights hold the navigation; the base holds the content. That is the harness.**

The restatement was the user's, and it is the reading the record supports. Three measured
facts carry it:

- **An expert is what its corpus taught — block, keys, order, prompt, band.** Under the
  runtime's prompt 2 of 32 live turns call a tool; under its own, 19 of 32 **[ran]** P63.
- **Routing is a question about corpora, not about inputs.** Keyed on what two members'
  inputs share, 15 of 60 misroute; keyed on what their corpora ask, 0 **[ran]** P64.
- **A bare large model is not a better expert.** Untrained, the 32B scored below the 3B
  expert in both regions tried — 0.967 < 1.000, 0.746 < 0.989 **[ran]** P55, P55b. So the
  large half of a pair is *trained on the same subdomain*, not borrowed as it ships.

- **Knowledge in the context is not followed by a small model unless following is what it was
  trained to do**, and **a fixed body of knowledge in a corpus is memorised, after which it
  measures nothing**: base + a procedure document made 0 tool calls on 351/351 **[ran]** P61;
  a control with no lookup tool at all scored 27/30 because fourteen table values fit in 600
  examples **[ran]** P15, P21. Both are why the knowledge base is *navigated by a trained
  policy* and its content is *unmemorisable by construction* (milestone 7).

**What version 1.0 is [spec].** Five things: experts defined by their corpora; the router with its
abstention; **the memory** (milestone 7, [`MEMORY.md`](MEMORY.md)); the runtime that referees it; the
release contract that hashes all of it. The speculative pair (milestones 3–4) attaches per subdomain
where it is measured to pay and is **not required by 1.0** — every piece of 1.0 has a gate that can
pass on one L4 inside a sixty-minute session, and a 27B cannot.

What stays from before: the frontier is a permanent component, used where no expert's
corpus covers the request or where a region is measured to fail (0.546 → 0.775 **[ran]**
P41); experts are trained by ordinary SFT; every region enters through the release gate;
the customisation service and its tooling are outside this runtime and the open source.

What is retired: acceptance as a way to *rank* unrelated experts against one target
(closed without a verdict after two failed preconditions; one redesign of three unspent,
and it is not going to be spent); composition of adapters; the character-level acceptance
instrument; ~~the fluid-mechanics expert~~ — **un-retired 2026-09-19 [ran] M7 arm 0b**: it was
retired on 11/90, and that was the serving path. As its corpus taught, it is 90/90.

### Addendum, 2026-09-20 — a pasted architecture, and the operative close it points at

A five-phase architecture arrived pasted into a session (educational centre + distributor, one
generic kernel, speculative decoding, Postgres RLS behind Auth0, Docker Compose). **It is not
entered here as fact** — none of its numbers were produced by this repository. Read in full against
[`FRAMEWORK.md`](FRAMEWORK.md) §9: it mostly re-derives that document's §5–§7 from further away, and
what it adds narrows to one open gap (permission enforced outside the model) that this repository
had already named and not yet closed. **Two things change; nothing else does:**

- **The next operative step is named:** `FRAMEWORK.md` §7 step 4, *a reference organisation on a
  neutral domain*, scoped to **one** domain — not the two the pasted plan assumed — with a toy
  permission check standing in for Auth0/Postgres RLS until the toy version is shown insufficient.
  Falsifier fixed in §9: an adversarial suite at **0 leaks** across a forbidden row, direct ask and
  injected off a note or a record.
- **The cheaper step ran first, and falsified as written:** **W5d** — the answer-policy split
  (`results/M7-W5d-answer-policy-20260920/BRIEF.md`), one L4 session, no training — `policy vs
  withlib` ties (5 : 0, $p=0.0625$). It still answers step 4's missing value, diagnosed rather than
  fixed: the base reads 21/21 where the walk opened a note; the eleven it never reached are the
  adapter's own memorised query.

Everything else in the pasted plan — a second domain, Postgres RLS and Auth0 by name, concurrency
and the cross-role canary, the bill, Docker Compose, speculative decoding — is **named, not bought**:
already sequenced later in `FRAMEWORK.md` §7 (steps 5–7), and moved earlier by nothing here, per the
rule against buying two arms as a grid (`../CLAUDE.md` §3). Milestones 1–7 below, their gates and
their numbers, are unchanged by this addendum; it only orders what follows F3.

## 1. The milestones

Arms are bought in sequence. The arm that can kill a milestone runs first; attribution
arms are bought only once there is an effect to attribute.

| # | milestone | depends on | gate | state |
|---|---|---|---|---|
| **1** | the pool on Qwen 3.x small | D2 ✅ | both members released on `Qwen3.5-4B`, each tying or beating its Qwen 2.5 release, paired | ✅ **[ran] 2026-09-19 — MOVED.** G1 `applied` on both full-recipe adapters; `email-full` **471/475 = its recorded 471**, tie 1 : 1; `desk-commitment` **240/240**, tie; `releases/*@v2.json`. Four sessions under an hour each ([`BRIEF`](../results/M1-pool-qwen35-20260919/BRIEF.md)) |
| **1b** | **the pool re-released on Gemma 4 E4B** | B1 ✅ | `email-full` and `desk-commitment` retrained on `google/gemma-4-E4B-it` from the same corpora and recipe, each tying or beating its `@v2` Qwen3.5-4B release on the same cases, paired; `@v3` manifests | **[ran] 2026-09-25 — NOT MOVED as a pool:** `email-full` ties its `@v2` (469 vs 471, 1 : 3) and beats the bare Gemma (119 : 0) → **`email-full@v3` on Gemma**; `desk-commitment` ties `@v2` and the bare Gemma alike (240/240, the ceiling) — no adapter needed there, stays `@v2` ([`BRIEF`](../results/M1b-pool-gemma4-20260925/BRIEF.md)) |
| **2** | the router as a tiny model of the corpora | the members' corpora | misrouted-to-local no higher than the dictionary's on prompts the dictionary was not written for; abstains on out-of-distribution text | **arm 1 [ran] 2026-09-19 — does not pass.** Foreign text, fresh sets: dictionary 59/128 served locally, n-gram router **0/128**; legitimate requests from unseen senders: dictionary loses 0/120, router loses **120/120**. The dictionary stays; **arm 2 is an embedding model**, shared with milestone 7 |
| **3** | the large half of one pair | 1 | a LoRA on ~~`Qwen3.8-27B`~~ `gemma-4-31B-it` (family.LARGE) is applied when served; large + LoRA beats small + LoRA on the deep band, paired | — |
| **4** | the speculative pair | 3 | acceptance of small-LoRA drafts under large-LoRA verification exceeds acceptance under the bare large model | — |
| **5** | the first real region, by hand | 1, 2, a sandbox, keys rotated | the release gate, on a suite with a verifier nobody here generated | **region named 2026-09-19: nursing procedures and health-education material** (Open RN *Nursing Skills*, CC BY 4.0, first); headroom arm next, zero GPU |
| **6** | the service policy, with the bill | 2, 4, 5 | the local share saves more than it costs, on real traffic | 🔶 **first pass [ran] 2026-09-21, zero GPU:** the P41/P62 replay priced at real `gemini-3.8-flash` rates — today's actual frontier bill (90 fluids cases) **$0.18**, avoided by keeping 150 email cases local **$0.11**, ceiling if everything left **$0.30**. **The local GPU's own dollar cost is not priced** — the rental rate could not be fetched live; not guessed around |
| **7** | **a knowledge base per subdomain, and the trajectory through it as the harness** — on fluid mechanics, split into subdomains | 1; shares its embedding model with 2's arm 2; independent of 3–6, **runs next** | an expert trained to navigate and follow notes answers families it never trained on, where the same expert without the base is at 1/20 | 🔶 **W1–W4 built [ran]; W3's radar and W5's kill arm [ran] and not passed.** W5: the library arm 35/56 against the untrained base that reads at 45/56 (6 : 16, $p=0.052$), 35 : 2 over no-library — navigation transferred, reading a two-valued note did not. Next is the user's call: composition, no training. **2026-09-24: the library's unit becomes the atomic statement (user's design, `MEMORY.md` §1.6) — W9 pre-registered: an invented distributor wiki, headroom on the untrained base first** |

### Milestone 1 — the pool on Qwen 3.x small

**Objective.** `email-full` and `desk-commitment` retrained on `Qwen/Qwen3.5-4B` from their
released corpora, unchanged recipe, and released through `release_gate` / `pool_second`.

**Why it is possible now.** D2 **[ran]** 2026-09-19: the adapter P33 saw ignored was named
for the text-only class while vLLM serves `Qwen3_5ForConditionalGeneration`. Train through
the class vLLM serves, or rename at release (`training/harness/rekey.py`).

**Kill arm, first.** The identity gate on a *real* member adapter — D2's was a 60-step toy
judged only on whether served text differs. If a full-recipe adapter is not `applied`, stop.

**Gate.** Paired against the recorded Qwen 2.5 run on the same cases: ties or beats,
exact sign test on discordant pairs,

$$p = 2\sum_{k=0}^{\min(b,c)} \binom{b+c}{k}\,2^{-(b+c)} .$$

**Falsified by** a member that loses to its own Qwen 2.5 release — the family move costs
quality in that region, and the pool stays on 2.5 until a reason is found.

**Not measured by it:** whether the 4B's headroom arm moved. Run `knowledge_arm` once on
the new base: P61's "the procedure has to be in the weights" was a fact about a 3B.

### Milestone 2 — the router as a tiny model of the corpora

**Objective.** Replace the keyword dictionary in `route.py` with a classifier trained on
the released corpora — one class per member — that **abstains** when a request falls in no
corpus. Abstention is the frontier. The measured `serve: local | out` table still decides
whether a recognised region is served locally: the router answers *whose distribution is
this*, never *is this expert good*.

**Headroom, before anything is built.** The dictionary is at 1.000 on every generated
prompt set, so on those any challenger ties and the tie reads as success. The router is
measured on prompts the dictionary was **not** written for: the two members' shared-inbox
collisions (the 15-of-60 set), paraphrases of each member's question, held-out generator
seeds, and out-of-region text — OpenClaw's recorded shapes and the fluids statements.

**Arms, in order.**

1. A zero-GPU classifier — character n-grams or TF-IDF into logistic regression — trained
   on the corpora's user turns. Minutes on a laptop. If it clears the gate, the router *is*
   this, and nothing larger is built.
2. Only if 1 fails: the smallest model of the family with a classification head.

**The metric is the term a router can change** ([`FOUNDATIONS.md`](FOUNDATIONS.md) §8.4):

$$\text{delivered} = \tfrac1n\sum_x [r(x)=(\text{local},m^*)]\,L_{m^*}(x) + [r(x)=\text{out}]\,F(x) + [r(x)=(\text{local},m\ne m^*)]\cdot 0 ,$$

so it is scored on **misrouted-to-local** and on the out share, not on routing accuracy.

**Falsified by** more requests misrouted to a local member than the dictionary, or no
abstention on out-of-distribution text. A model asked to choose always chooses; the
abstention arm is bought first.

**Result [ran] 2026-09-19 — arm 1 does not pass**
([`results/M2-corpus-router-20260919/BRIEF.md`](../results/M2-corpus-router-20260919/BRIEF.md)).
One smoothed uni+bigram model per member over the corpus's *frame* — tokens in at least half
its documents; everything else one `<slot>` symbol — accepting a request iff its least likely
frame transition and its frame coverage are typical of the corpus. Three attempts, two counted
redesigns, each written into the brief first; the design was then frozen and **fresh sets were
written afterwards and scored once**:

| set | dictionary | n-gram router |
|---|---|---|
| in distribution, 715 | 0 misrouted · 0 lost | 0 misrouted · 0 lost |
| foreign text, fresh — keyed texts and a listing followed by another task, 128 | **59 served by a local member** | **0** |
| legitimate requests from senders outside the generator's pools, 120 | 0 lost | **120 lost** |
| the member's question paraphrased, 240 | 131 lost | 240 lost |

It learned the generator's uniformity: every generated address ends `.com`, so `. com >` is
*frame*, and a real sender leaves the distribution. Real traffic is all of the third row. And to
a lexical model a paraphrase of the member's question and a different task are one thing — a
familiar listing, then an unfamiliar sentence. **Telling them apart is semantics, so arm 2 is an
embedding model** (the smallest of the family's embedding line), with the four rows above as its
kill sets. The dictionary stays the proxy's default; `corpus_router.py` stays as the measured
arm. The third redesign was not spent.

**Arm 2 [ran] 2026-09-19 — an embedding model; does not pass either**
([`BRIEF`](../results/M2b-embed-router-20260919/BRIEF.md)). `Qwen3-Embedding-0.6B`, mean cosine to the five
nearest corpus requests, every text embedded as *the task being asked*: foreign text 15/338 served
locally (dictionary 119, n-grams 0), paraphrases 99/240 recovered — and **120/120 requests from unseen
senders lost**, like arm 1. With the per-case scores kept, it is **not calibration**: unseen senders
(median 0.89, max 0.964) and *a member's own listing followed by another task* (0.87–0.91, max 0.966)
occupy the same range, so no threshold separates what should stay from what should leave. In this
space, changing who writes moves a request as far as changing what is asked. **What is left is a
representation that factors task from content** — a small projection trained contrastively (same
task / other content against same content / other task), which is the radar's stage R1
([`MEMORY.md`](MEMORY.md) §2.2) reached from the router's side. It needs new evaluation sets; the
dictionary stays the default.

**Where the router's problem does not arise — restored 2026-09-19** (the analysis is `docs/CASE-TEAM.md`
at the tag `v0.1-foundations`; the rewrite dropped it and should not have). A team running the agent
runtime in multiplayer mode — every person in chat, several agents, dozens of concurrent sessions,
conversations in **standing groups per area** — has its regions by construction: a group repeats, has
its own vocabulary and a stable membership. **The group's id is the route**; nothing is inferred,
because the client already knows which room it is in. Both learned arms above fail on *who writes*;
in a team deployment that is not a signal anyone has to read. It is also the first setting that
exercises the pool as a pool — mixed batches across dozens of sessions, **unmeasured** here — and it
makes headroom a per-group question: a company-wide average hides the group with a gap and the group
without one. What it does **not** address is the infrastructure half of such a deployment — a
session list that fills up, a gateway unreachable behind an access proxy, a websocket that drops.
Not built for it: isolation between users, streaming, a per-group adapter lifecycle.

**Arm 3, headroom only [ran] 2026-09-21 — `cactus-compute/needle`, stock weights; no real arm
bought** ([`BRIEF`](../results/M2c-needle-router-20260921/BRIEF.md)). Read [read] as a
candidate not for size but for the two pieces arm 2 lacked — a calibrated confidence head and
local LoRA fine-tuning from a contrastive `query`/`answers` format — the same `EmbedRouter`,
`score_cases` and `verdict` arm 2 used, only the encoder swapped. Subsampled (40 per
bucket, up to 715 in a bucket) after the first attempt ran ~15 minutes with no progress line —
fixed with per-call progress printing and a seeded `--limit`, not compared at arm 2's own
resolution. **`NOT SAFE: serves foreign text locally`** — 62 of 142 out-of-region cases served
locally (a same-content-different-task swap, E/E2: 29/40 and 33/40), against arm 2's 15/338
(4.4%) — roughly **10×** the leak rate. It does recover real traffic arm 2 lost completely
(unseen senders, F: 19/40 vs 0/120) but not reliably (52.5% still lost). Neither of the brief's
two named outcomes: not "safe but loses F" and not "F improves without foreign text getting
worse" — it trades away the property the router exists to guarantee. Stock weights and a
borrowed τ do not exercise the two pieces this arm was chosen for; a real arm (its own BRIEF,
the fine-tuned weights Needle's own README points at) is not justified by this look.

### Milestone 3 — the large half of one pair

**Objective.** One LoRA on `Qwen/Qwen3.8-27B`, QLoRA NF4, from the *same corpus* as one
small member, on the band where the small member has headroom — the desk's
`commitment_deep`, since the shallow band saturates at 75 examples **[ran]** P55b.

**Kill arms, in order.** (a) The serving gate: a LoRA over the quantised 27B is `applied`
— the logprob gate with its base-vs-base control, not the text gate, which misread a toy
adapter on a 32B **[ran]** P60 §3b. (b) Headroom: the small member is below the ceiling on
the chosen band. If it is already at 1.000 there, the large half has nothing to buy.

**Gate.** Large + LoRA beats small + LoRA on that band, paired, $p \le 0.05$.

**Falsified by** a tie or a loss: in this subdomain the large half buys nothing, and the
pair is not built here. That is a result about the subdomain, not about the design.

**Constraint.** A100, 4-bit. It does not run on the L4 the pool is served from.

### Milestone 4 — the speculative pair

**Objective.** Measure acceptance of the small member's drafts under the large member's
verification, both carrying the LoRA of the same subdomain.

**How it is measured, and why.** vLLM ships multi-LoRA and speculative decoding, but a
LoRA-adapted drafter is an RFC, not a feature **[read]**. So acceptance is measured as this
repository already measures it (`accept_rank.py`): the small member generates, the large
one scores the draft in a single teacher-forced pass (`prompt_logprobs`), and a token is
accepted when it is the large model's argmax at temperature 0. With per-token acceptance
$\alpha$ and draft length $k$, the expected tokens per large-model pass are

$$\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha} .$$

**α is reported with its $k$ and beside the verified score of the same run.** α alone is
not a decision.

**Arms, in order.** The pair against **small-LoRA drafts under the bare large model** —
the comparison that can kill it. Only if the pair wins: bare small drafts under the
large-LoRA, to say which half carries the gain.

**Falsified by** α(pair) ≤ α(small-LoRA, bare large): training the large half on the
subdomain does not make it agree more with the small expert, and the pair is a quality
device (milestone 3) but not a speculative one.

**Not claimed:** wall-clock speed-up. That needs the runtime feature and is a separate
measurement.

### Milestone 5 — the first real region

**Named by the user, 2026-09-19: nursing procedures, and health-education material for training
local experts.** It is the right first region for reasons the record supplies:

- **It is knowledge nobody here generated.** Every suite so far was written by this repository, and
  a generated suite cannot contain a difficulty its author did not think of (`RECORD.md` §3); the
  n-gram router learned a generator's `.com` (M2). A procedure manual is someone else's text.
- **It is operational knowledge in its purest form** — ordered steps, checks before acting, what
  to do when a check fails — beside encyclopedic knowledge (indications, ranges, tables). Both
  kinds of milestone 7's base, in one real source.
- **It has mechanical verifiers**, which is what the clinical suite of S0–S1 lacked the headroom
  for, not the verifiers: the next step of a procedure, the order of a shuffled one, a check that
  must precede an action, and the arithmetic — drip rates, dilutions, weight-based doses from a
  table — which is fluids' `lookup` + `calc` shape over real content. The calculator stays: a
  distilled expert writes π/4·0.22² as 0.037006 (P5–P7), and here that is a dose.
- **"Local experts" is the unmemorisable base, for real.** A ward's or a ministry's adaptation of a
  guideline — a different dilution, an extra check — is exactly a note whose content the weights
  cannot hold because it changes by site. Milestone 7's arm 5 (edit a note, the answer follows the
  base, no retraining) stops being an instrument trick and becomes the product.

**Constraints, as facts.**

- **Licence decides the source, before quality does [read] 2026-09-19.** WHO publications default
  to **CC BY-NC-SA 3.0 IGO**: no commercial use, and adaptations inherit the licence — usable to
  measure, not to ship in a service, and not committable to this Apache-2.0 repository. **Open RN's
  *Nursing Skills*** (Chippewa Valley Technical College, on NCBI Bookshelf) is **CC BY 4.0**:
  commercial use and adaptation with attribution. So the open textbook is the first source; a WHO
  text is a second, non-commercial arm; a customer's own procedures are the real case and live on
  the customisation side, outside this repository (§0). Verify the licence of each document used.
- **It is training material, not advice to a patient.** The region's questions are a student's or a
  local trainer's. Nothing here is a medical device, and the release gate for this region is
  stricter, not looser: what the expert is not measured to answer goes out.
- **No patient data**, by construction: procedures and teaching text only.
- **Language is one more unknown.** Start in the source's language; a Spanish edition is a second
  arm, not a free assumption about a 4B.

**Order — the cheapest thing that can kill it first.**

1. **Headroom first:** three checklists, 72 verifiable questions of the four kinds above, the bare
   base against them closed book and open book — on Colab, ten minutes of an L4
   (`training/nursing/headroom.py`). **[ran] 2026-09-19 — headroom exists, and reading closes most of
   it:** step order and next step 29/48 closed-book → **45/48 with the note open**; a quantity the
   unit's protocol changed **0/12 → 12/12**; drip rates 7/12 → 6/12 — arithmetic, not knowledge
   ([`BRIEF`](../results/M5-nursing-headroom-20260919/BRIEF.md)). **Consequence:** a small base
   *answers about* a note it merely reads, though it does not *act under* one (P61). The trained
   trajectory has to be measured on **walks**, never on question-answering, and every arm from here
   carries the baseline *bare base + the oracle's note open*. If the base already orders the steps of a procedure it has
   never been shown, there is nothing to buy — that is how the clinical suite died (S1: no model
   ahead of a free local 12B). Headroom first, again.
2. Then milestone 7's design, unchanged, on this content: trajectories over the chapter's notes,
   **a held-out procedure that exists only in the base**, the oracle trajectory first.
3. Fluid mechanics keeps its job beside it: it is the **instrument** — an exact oracle and content
   unmemorisable by construction. Nursing is the **region**. A result that appears in one and not
   the other is a finding about generated suites.

Seventy-five to a hundred hand-written examples is the right first size — the shallow desk band
saturated there. It needs a sandbox for anything that executes and rotated keys.

### Milestone 6 — the service policy, with the bill

Router → small member → pair where the region is measured to need it → frontier. The
number that has never been measured is money: the frontier bill with and without the local
share, on real traffic. **Falsified by** a local share that costs more to run than it saves.

**First pass [ran] 2026-09-21, zero GPU** (`training/harness/bill.py`,
[`BRIEF`](../results/M6-bill-20260921/BRIEF.md)). Not real traffic — the closest thing on disk: the
P41/P62 replay (150 email-full cases served locally, 90 fluids cases actually sent to
`google/gemini-3.8-flash`, confirmed in `frontier_fluids.json`'s own `model` field), priced at that
model's real paid-tier rate ($0.75 / $3.75 per 1M input/output tokens, sourced
`ai.google.dev/gemini-api/docs/pricing`, fetched the same day). Email priced exactly, turn by turn,
the way a chat API bills a multi-turn call; fluids priced with a stated approximation (the whole
tool-call chain at the output rate) biased to **overstate**, never understate, the frontier's cost.

| | tokens (in / out) | USD |
|---|---|--:|
| today's actual frontier bill (90 fluids cases) | 8,961 / 47,255 | **$0.1839** |
| avoided by keeping 150 email cases local | 72,745 / 15,184 | **$0.1115** |
| ceiling if everything had gone to the frontier | — | **$0.2954** |

**What this does not answer, named rather than guessed at:** the local GPU's own dollar cost. The
Colab rental rate renders client-side and two live fetch attempts returned no usable number — not
fabricated. `local_token_volume_for_rate_substitution` in `bill.json` is what a real $/hour or
$/token rate multiplies against once supplied. **At this replay's scale (240 cases) every number
above is a fraction of a dollar** — before any verdict on "saves more than it costs" is read off
these figures, note that money is not yet the deciding quantity at this volume; the shape of the
answer, not its size, is what a first pass like this can show.

### Milestone 7 — a knowledge base per subdomain, and the trajectory through it as the harness

**This is the core of version 1.0. What is built, piece by piece and in what order, is
[`MEMORY.md`](MEMORY.md)** — the library's two shelves, the radar, three verbs, the LoRA's habit of
navigating, the software referee. The *why*, written to be argued with by other models, is
[`KNOWLEDGE-TRAJECTORIES.md`](KNOWLEDGE-TRAJECTORIES.md).

**The idea, the user's.** An expert's subdomain has a body of knowledge of two kinds:
**encyclopedic** — hierarchical: what a quantity is, which correlation holds in which regime,
what a material's properties are — and **operational** — sequences: how this kind of problem is
solved, step by step, and what to check. Put both in a knowledge base that belongs to the
subdomain (markdown notes, linked, embedded; memory is markdown and git — `ARCHITECTURE.md` §7).
What the LoRA then learns is not the content but the **trajectory**: which note to open first,
which link to follow, when to stop reading and compute. *A trajectory through operational notes
is a harness* — the thing `harness.lora` was reaching for, now per subdomain and outside the
weights, where it can be edited.

**Why fluid mechanics, and why split.** It is the one domain here with real headroom — the
frontier 66/90, the expert ~~12/90~~ **[ran]** P40, P41. *(Corrected the same day by arm 0b: 12/90
was the serving path; in its region, as taught, the expert is 90/90. Fluid mechanics stays the test
bed for what that does **not** cover — a sibling family it never trained on, 1/20 **[ran]** P14 —
and because its content is unmemorisable by construction.)* One adapter over all of it was trained at one depth and over-solved below it
**[ran]** P45. So: subdomains of two sibling families each — internal flow (`pipe_head_loss`,
`pump_power`), metering (`venturi_flow`, `orifice_discharge`), external flow
(`terminal_velocity`, `drag_force`), channels and statics (`manning_channel`,
`hydrostatic_force`) — each across the difficulty ladder (`training/physics/ladder.py`), so
region and depth are two variables.

**Three measured facts shape the design — constraints, not objections.**

1. **A small model does not follow what it reads unless following is what it was trained on**
   **[ran]** P61. → Navigation and note-following are *the content of the adapter*: the corpus is
   trajectories — `<search>…</search>`, `<open>id</open>`, then `<calc>` — written by the oracle.
2. **Fixed knowledge in a corpus is memorised, and then the base measures nothing** **[ran]** P15,
   P21. → The notes a case needs are **unmemorisable by construction**, P21's per-case handbook
   extended from values to procedures: properties of a fluid that exists only in this case, and a
   correlation variant whose coefficients are drawn per case. The expert can learn *which* note
   a step needs; it cannot learn *what the note says*.
3. **A specialist is confidently wrong just outside its region** — 30/30 on its formulas inside,
   **1/20 on families it never saw**, prose equally fluent **[ran]** P14. → That is the headroom
   and the claim: *with the sibling family's notes in the base and no retraining, the
   navigation-trained expert answers the sibling family.*

And one from the workspace: a memory hierarchy lost to flat lexical search in its first benchmark,
and an exact-answer physics suite was the wrong instrument for memory because everything in it
was derivable. → The channel must be *needed* (fact 2 guarantees it; the run asserts the leak's
absence: no looked-up value appears in the statement), and hierarchy is an arm, not an assumption.

**Arms, in order — the one that can kill it first.**

| # | arm | what it decides |
|---|---|---|
| **0** | headroom, zero GPU: P41's 90 recorded chains replayed against each case's own handbook (`training/physics/result_use.py`) | **[ran] 2026-09-19.** Of 79 failures, **74** hold a `<calc>` with a number that came from nowhere and **75** leave a tool result unused; 217 of 456 non-final results are ignored — the expert looks the density up, 882.3, and multiplies by 1359.7. **The dominant failure is not a wrong relation: it is not using what was returned.** *(Corrected the same day: the first replay passed the handbook in its JSON shape, every `<lookup>` raised inside a broad `except`, and the published 74 unused / 132 of 371 ignored were wrong. With lookups evaluated — 0 tool errors — it is 75 and 217 of 456; the 74 with a number from nowhere stood.)* |
| **0b** | **the same adapter, the same 90 cases, served in corpus mode** — result inline after the closing tag, as its corpus taught | **[ran] 2026-09-19 — THE PATH WAS PART OF IT: 90/90** against 11/90 through `tool_calls`, 79 : 0 paired; 24 : 0 against the frontier's 66/90; no evaluated case in the corpus ([`BRIEF`](../results/M7-arm0b-corpus-mode-20260919/BRIEF.md)). **A 3B does use what it reads, when it reads it as taught — the memory has a channel that works.** Opens two things: `fluids-full` back through the release gate before its region stops being sent out; and P45 (below training depth), measured through the same path, is open again |
| **0c** | **the same member back through the gate on the base the pool runs on** — retrained on `Qwen3.5-4B`, same corpus and recipe, corpus mode, same 90 cases; three paired sign tests; Colab, two sessions | ❌ **[ran] — not released.** 80/90 against its own 90/90 (**0 : 10**, $p=0.002$); 80 : 0 against the bare 4B; 21 : 7 against the frontier. All ten are venturi chains identical to the 3B's up to the final line, which the 4B writes as an `<answer>` tag the corpus never taught; the number verifies 10/10. The region stays `out` · `results/M7-arm0c-fluids-rerelease-20260919` |
| **1** | **oracle trajectory.** Two adapters on one subdomain, same cases: trained *with* the notes the oracle would open, injected through the `<search>`/`<open>` protocol, and *without*. Scored on the trained family and on its **held-out sibling**, paired | the upper bound: if reading exactly the right notes does not lift the sibling off ~1/20, no navigation will — **stop** |
| **2** | learned navigation: the expert issues its own queries; retrieval by embedding inside the subdomain's base. Measured **where it happens** — was the needed note retrieved, was it opened, was it followed — not only at the final answer | what navigation loses against the oracle trajectory |
| **3** | attribution: encyclopedic notes only · operational notes only · both | which kind of knowledge carries the gain — the two kinds, priced separately |
| **4** | retrieval: flat lexical · embedding · embedding restricted to the trajectory so far (links and neighbours of the last note opened) | whether a trajectory strategy beats a flat search; the workspace's earlier result says do not assume it |
| **5** | edit without retraining: change one note's coefficient after training; the answer must follow the base, not the weights | that the knowledge lives where it can be edited |

**What is reused from `evolving-memory`, and what its one measurement says — audited [read]/[ran]
2026-09-19** (the user's suggestion; `EvolvingAgentsLabs/evolving-memory` at `a635898`, Apache-2.0,
its suite run here: 184 pass, 12 skip for want of an API key). It is a *trace-consolidation*
engine — agent traces compressed by an LLM into a strategy with ordered steps, embedded, retrieved
by flat top-k. It is **not** a base of authored, editable notes, and **no code in it reads an edge
to decide what to retrieve next**: the typed graph is written and never walked; step order is
`ORDER BY step_index`. So the trajectory arm (arm 4) is new work, not a port. What is taken:

- **`resolver/` (~370 lines) — the dual index.** Each item embedded twice, *what it is* and *what
  it is for*, the **union** of both searched, every sub-score kept on the match rather than
  collapsed — which is what comparing three retrieval arms needs. Encyclopedic and operational
  notes are that same split. Its capped track-record boost (`MAX_BOOST = 0.05`: popularity breaks a
  tie, never overturns relevance) is copied as a rule.
- **The offline test doubles** — a hashed bag-of-words encoder and an exhaustive cosine index, ~40
  lines — so the base is testable in CI with no GPU and no key. At the size of a subdomain's base
  the exhaustive index *is* the production index: a matrix product, no ANN library. **With its bug
  fixed first:** it buckets by Python's `hash()`, randomised per process, and the test carrying that
  repository's central claim fails on 6 of 30 seeds **[ran]**.
- **`storage/migrations.py` (95 lines)** and the `nodes / children / edges(source, target, type,
  weight)` shape, with the edge vocabulary — containment, `NEXT_STEP`/`PREVIOUS_STEP`, cross-links —
  this time *read* at retrieval.
- **`isa/parser.py` + the VM's accumulate-then-commit loop**, if a trajectory is emitted as actions:
  a never-raises text parser with errors as data, a bounded dispatch loop, and a log of the walk to
  score it by.

Left behind: the FastAPI server, the Gemini-only embedder imported at package root, the three
API-bound LLM providers, the LLM consolidation pipeline (notes here are authored), faiss, and a
declared-and-unused `networkx`. The embedder is a small open model **served on Colab** like every
other model here — nothing runs on the user's machine (instruction of 2026-09-19).

**And its one honest benchmark is a negative result, which arm 4 inherits as its prior.** Indexing
*what a thing is for* beside *what it is* changed nothing: acc@1 80 % at every mixing weight, n = 10,
the second embedding genuinely distinct (cosine 0.753) — committed as *"measure that it does not
help"*. The misses are **within-topic**: the right area, the wrong item inside it. That is where a
neighbourhood restriction should pay if anything does, and it is also a warning to expect a small
delta over flat similarity. With this workspace's own earlier result — a hierarchy lost to lexical
search — that makes two priors against structure. The harness comes before the clever retriever,
and a null is reported as a null.

**Gate.** Arm 1: with-base beats without-base on the held-out sibling family, paired, exact sign
test, $p \le 0.05$ — and the without-base arm reproduces P14's collapse there, or the sibling was
not outside the region and the run says nothing.

**Falsified by** a tie on the sibling under the oracle trajectory: at this size, reading does not
extend a region even when the right page is open. One arm then remains and it is cheap: the same
on the 4B of milestone 1. After that the question belongs to the large half of a pair.

**The release contract grows one field.** A member is its corpus *and its base*: the manifest
records the knowledge base's path and hash and the embedding index's hash beside the corpus hash.
The router's arm 2 and the base share one embedding model, so a subdomain is one region of one
space — what falls in it is routed to the member, and what the member looks up is found in it.

**Not claimed until measured:** that a hierarchy helps; that embeddings beat lexical search inside
a small base; that any of it transfers from a generated suite to a real one.

**W1 [ran] 2026-09-19 — the first library and its lint: PASSED.** `memory/notes.py`, `memory/lint.py`,
`knowledge/nursing-iv/`: three Open RN procedures as skeleton + 70 step notes, a 21-note wiki, one
example site layer; no model involved. Gate, written first —
$\text{passed} \iff |\text{findings}| = 0 \wedge \forall q: \text{walk}(q)$ exists — lint **0 findings**,
oracle walks **72/72**, and the gate fails when a step is removed
([`BRIEF`](../results/M7-W1-library-20260919/BRIEF.md)). The lint's first run found the spec's own
skeleton over its own limit (230 tokens > 150): a skeleton lists step *labels*, not titles. Next is
**W2** — the runtime, the layers and the guard on the corpus-mode loop, still no model.

**W2 [ran] 2026-09-19 — the runtime: PASSED.** `memory/runtime.py` (three verbs, opaque ids re-drawn per
conversation, budgets, the walk log), `memory/layers.py`, `memory/guard.py` — an answer function with
state, on `accept_rank.run_chain` **unchanged**. Gate, written first: every oracle walk replayed as a
scripted generation that reads its ids off the runtime's own output. **72/72** walks, 949 commands, 0
refused, 0 malformed, guard silent; site values arrive marked (`8 [site]`), the 12 rate walks' `<calc>`
gives the answer; no library id in any text shown. The guard's rule is
$\text{violation}(n) \iff \text{requires}(n) \setminus \text{opened} \ne \emptyset$: three violating walks
are cut in `strict` and continue in `recover`, and the gate fails on a library with a broken link
([`BRIEF`](../results/M7-W2-runtime-20260919/BRIEF.md)). **Not measured:** whether a *model* recovers, and
search — it is lexical here and the oracle queries a note by its own `when`, so its 72/72 at rank 1 is
no evidence about ranking. §3's 24-open budget was below the library's 32-step procedure: now 48. Next is
**W3** — the radar R0 beside this lexical baseline.

**W3 — [ran] 2026-09-19: not passed.** `memory/index.py`: per note
$e_{\text{when}}, e_{\text{what}}$, $s(n\mid q)=\langle e(q),e_{\text{when}}(n)\rangle+\beta\langle e(q),e_{\text{what}}(n)\rangle$,
top 3, a `Searcher` the runtime takes unchanged, the encoder injected (no model here, ever). The queries
that count were written **after** the design was frozen: **P**, one bedside paraphrase per note (94
targets, mean word overlap with the target 0.039, 56 queries at zero) — the gate; **E**, the 72 question
stems → the first note of the oracle walk (4 targets) — beside it. The word-matcher's recall@3 is
**0.064 on P** and 0.125 on E: headroom, and on P a floor *by construction*, so "beats lexical" alone
would be a formality and the verdict also requires recall@3 ≥ 0.80. Falsified if R0 only ties the
word-matcher — then the radar has no job at this library size and W5 runs on lexical search
([`BRIEF`](../results/M7-W3-radar-r0-20260919/BRIEF.md)).

**R0 [ran] 2026-09-19 — beats a word-matcher and is not enough.** `Qwen3-Embedding-0.6B`, one L4 session: on P
recall@3 **0.638** against lexical 0.064, paired **56 : 2** — and under the 0.80 written before the run, so W3 is
**not passed**; β = 0.5 beats `when:`-only 30 : 4. Where the 34 misses sit: 13 at rank 4–6 (recall@6 0.777,
recall@10 0.830), 16 past rank 10, four of which collapse inside their own shelf. Nothing is loosened and the set
is not reshaped (redesigns: 0). Two consequences: **W5 counts a retrieval miss apart from the expert's score** — or
runs on the oracle's search results — and the gap belongs to **W6 (R1)**, measured on new query sets, never on P again.

**W4 [ran] 2026-09-19 — the corpus of the habit: PASSED.** `training/nursing/generate_walks.py` writes no
observation itself: every row is a plan *driven through* `memory/runtime.py` inside `run_chain`, the verb
block by `render_tools` (`memory/prompt.py`, the one place a member's prompt is written), the carried page by
`Conversation.resume`. Gate, per row, with $V$ the values read off a slot or a `<calc>` and $N$ the numbers a
statement states: $V(r)\cap N(r)=\varnothing$ — **0** of 740; no evaluated walk or case in the corpus — **0**
of 140; no open of the 17 notes that are `discontinue-iv`'s alone — **0** of 600; every row reproduced byte
for byte by the referee in `strict` — **0** failures; each clause broken once by a test. 600 rows over four
families (carry 286 · rate 144 · quantity 108 · *not in my library* 62), 0 to 9 notes opened, 24 deliberate
dead ends, and the same 600 cases with no verbs as W5's second arm. **Held out: `discontinue-iv`** — the two
infusions share 11 source lines nearly word for word, so either would score a memorised sibling; removal
shares 4 and 6 generic lines, and the 24 of its 80 evaluation walks that end on one are marked. **A 32-step
walk does not fit `max_seq` 1536 and is not truncated:** a task is a window of 1–8 steps, and one entered in
the middle carries its state — by the referee's last page, or by finding its place through the skeleton and
a search (two verbs; following a page is one, and one tool is copying **[ran]** P13). Longest row 1 298
tokens under the base's tokenizer. One redesign, of G2's statement clause, recorded in the brief. Next is
**W5**, the arm that can kill the memory; if R0 wins W3 the corpus is regenerated with the index first
([`BRIEF`](../results/M7-W4-corpus-20260919/BRIEF.md)).

**W4's grader, replaced before anything was read through it (redesign 2) [ran] 2026-09-19.** An
adversarial review found it wrong both ways: a paraphrase of the right step failed (exact substring,
`[site]` marker and all — 57 of the 80 held-out rows), and *"15 years old … waits 8 seconds"* passed a
check for 15 seconds. `training/nursing/grade_walks.py` reads the final line only; a number counts only
attached to its unit; a step is *attributed* among the 70 step notes, $s(n)=|W(\text{line})\cap
W(n)|/|W(n)|\ge 0.5$, with the numbers the note supplies; the walk is read off the referee's log.
`right` · `format` · `unread` · `wrong`. All 740 oracle rows are `right` under it; no row was
regenerated. A third redesign ends the step.

**W5 [ran] 2026-09-19 — DOES NOT PASS AS WRITTEN.** On the headline (n = 56) the library arm scores
**35**, the untrained base reading the oracle's notes **45**, the no-library arm 2, the untrained base
navigating by itself 0. `withlib` vs `nolib` 35 : 2 and vs `base-walks` 35 : 0 — but **vs `base-reads`
6 : 16, $p = 0.052$**: a tie that leans to a loss, and the verdict asks for *beats*. Twelve of the 21
failures are one failure: the held-out note states two values for one quantity, no trained quantity row
ever read such a note (0 of 108), and the adapter answers the first value — 11/12 when the first is
asked, 0/11 when the second is, the base that reads right on all 12. Eight are `carry/middle-find`, where
the base is also wrong on 5. Navigation itself transferred: 0 retrieval misses on the headline, 3 refused
verbs in 140 walks against 368, control 58/60 against 41/60. Redesigns: 0; the grader is not touched.
**Composition — the adapter walks, the bare base writes the final line — [ran] W5b: 0 of the 12 quantity
failures remain, and on everything the adapter was taught the base reads worse (control 39 against 58), so it is
attribution, not a serving design. Next, the user's decision:** a library and a corpus that show two-valued
notes inside trained procedures, both adapters retrained, scored on a new held-out set ([`BRIEF`](../results/M7-W5-kill-arm-20260919/BRIEF.md)).

**W5c — the corpus-shape arm [ran]: FALSIFIED, see the result below.** *(As pre-registered:)* The source has no two-valued statement
inside the trained procedures (checked line by line), so the shape comes from **A** the chapter's one real
sentence (macro- against micro-drip sets, byte-checked, now the body of `rates/drop-factor`) and **B**
sentences a site ADDS to seven trained notes (`Site.adds`; **invented example content, approved by the user
and marked as invented**). Corpus v2 (`data_walks_v2/`, generator by import, v1 untouched): 153 of 600 rows ask
one of a note's two values, half each, the condition explicit or implicit; "copy the first number" is worth
0.51. New held-out set (88; headline 66) and control (80); v2 gate PASSED, floor 6/66, headroom stop 61/66.
Falsifier, exact and coded: conditional-slice credit ≤ 4/15 is indistinguishable from W5's 0/11 (Fisher).
W5's pairs are asked again on the new headline; a tie is a tie ([`BRIEF`](../results/M7-W5c-conditional-corpus-20260919/BRIEF.md)).

**W5c result [ran] — the diagnosis is falsified: 4 of 15.** Conditional-value credit on the new held-out set is
4/15 against the first corpus's 0/11 (Fisher $p=0.091$; the band ≤ 4 was fixed before the run). W5's pair on
the new headline ($n=66$): `withlib` 42, `base-reads` 46 — **12 : 16, $p=0.57$, a tie: not passed**; against
`nolib` 39 : 0, against the base walking 42 : 0. All 14 quantity failures have a clean walk and `base-reads`
right; the adapter writes **the first number, as one integer** (wanted 22 → `7 minutes`; `5-10` → `5`). On
the eight notes it trained on it reads the condition (17/18): it learned those notes, not the skill. What v2
did buy is navigation: shared line 22/22 (base 8), `middle-find` 14/22 (base 5), control 78/80 (base 56).
Next, the user's decision: a split by task kind (exploratory, post-hoc on W5's set: 47/56), gentler
training, or many more notes — which is option E.

**W5, as built and pre-registered.** `training/nursing/walks_arm.py`: `base-reads` (untrained
base, the oracle's notes open), `base-walks`, `nolib`, `withlib`. Headroom session first: `base-reads`
at ≥ 51/56 on the headline stops the step before training. Headline n = 56 (held-out, depth ≤ 9, final
line not shared); beside it the 2 depth-15 rows, the 22 shared-line rows, quantity by layer, control
without `rate`, retrieval misses, `context`, `format`. Floor of the trivial policy **3/56** [ran]; the
oracle is 140/140 through the same function ([`BRIEF`](../results/M7-W5-kill-arm-20260919/BRIEF.md)).

## 2. The family, and the alternative

**Adopted, 2026-09-25: Gemma 4** — `google/gemma-4-E4B-it` for every new member; `gemma-4-31B-it` named for the
large half, not measured. B1 **[ran]**: a tie with Qwen3.5-4B on W9 (38 vs 35, 35), which by the user's rule written
before the comparison chooses Gemma. P29's block is lifted by excluding the vision/audio towers. The released members
move one by one: `email-full@v3` on Gemma (M1b [ran]); `desk-commitment@v2` stays on `Qwen3.5-4B`; Qwen 2.5 stays the control arm.

**Previous, until re-release: Qwen 3.x** (`Qwen3.5-4B`, `Qwen3.8-27B`) — one id space **[ran]** D0, the family of every
release so far. ~~Adopted: Qwen 3.x … Alternative, not now: Gemma 4, blocked at PEFT [ran] P29.~~

## 3. Rules every step follows

The measurement rules that were paid for are in [`../CLAUDE.md`](../CLAUDE.md) §3. The four
that decide the shape of a step:

- **Headroom before treatment** — and the floor as well as the ceiling.
- **The brief before the run**: what, why, which model, which provider, what falsifies it,
  in `results/<run>/BRIEF.md` before the chain starts.
- **One unknown per run**, and the verdict read from the file, never from the exit code.
- **Count the redesigns.** Once is fine, twice is suspicious, the third is looking for the
  result. The stopping condition goes in the brief.

## 4. Ledger of agents and skills

| date | change | why |
|---|---|---|
| 2026-09-19 | `alpha-runner` → `deprecated/`; skill `alpha-surface` removed | the character-level acceptance instrument it drove measured format, not agreement (S0), and was removed with the rewrite |
| 2026-09-19 | kept: `colab-runner`, `headroom-auditor`, `instrument-skeptic`, `mirror-keeper`; skill `experiment-brief` | each has a step in §1 |

## 5. History

- **2026-09-25** — **M1b [ran]: `email-full` released on Gemma 4 E4B (`@v3`)** — a tie with its Qwen `@v2` (469 vs 471 of 475) and 119 : 0 over the bare Gemma. `desk-commitment` ties both `@v2` and the bare Gemma at 240/240: the pool does not move as a unit by the verdict as written; desk stays on Qwen until a suite with room above the base decides it ([`BRIEF`](../results/M1b-pool-gemma4-20260925/BRIEF.md)).
- **2026-09-25** — **the school demo [ran]: 8/8 on Gemma 4 E4B, the system end to end.** M8: a school-staff trajectory
  LoRA on 700 full gateway turns — held-out 70/70 on both seeds against the bare Gemma's 27/70 (43 : 0), demo day 8/8
  against 3/8. Read where it happens it can still invent a line in a tool result's format and quote a planted
  instruction; the gateway now grounds every reply in real tool results and redacts planted instructions, outside the
  model — on the recorded demo day it replaced 2 of 5 local replies, the user saw neither. Two images withdrawn to be
  redrawn (`memory-walkthrough.png`, `request-path.png`); the documents carry their placeholders
  ([`M8`](../results/M8-school-staff-20260925/BRIEF.md), [`demo`](../results/DEMO-school-gemma-20260925/README.md)).
- **2026-09-25** — **everything moves to Gemma 4, the user's decision on B1's tie.** New members are trained on
  `gemma-4-E4B-it` (`training/harness/family.py`: SMALL; the active runners default to it); the large half of a pair is
  named `gemma-4-31B-it`, not measured; milestone 1b re-releases the two Qwen members on Gemma through the gate. The
  school demo's gateway now grounds every reply in real tool results and redacts planted instructions, outside the
  model, after M8 [ran] showed the school-staff LoRA can invent a line of a tool's list.
- **2026-09-25** — **B1 [ran]: Gemma 4 E4B against Qwen3.5-4B — a tie, which by the user's rule chooses Gemma.**
  P29's block is lifted (the LoRA excludes Gemma's vision/audio towers; vLLM serves it applied). Untrained, Gemma walks
  W9's wiki 19/40 where Qwen walks 0/40, and reads 40/40 where Qwen reads 29/40. With W9's corpus and recipe, Gemma's
  member 38/40 against Qwen's 35 and 35 — 4 : 1 against each, a tie. The user decided before any stage ran that parity
  chooses Gemma (the development stack targets it): **new members are trained on Gemma 4 E4B**; the released Qwen
  members stay until re-released ([`BRIEF`](../results/B1-gemma4-vs-qwen35-20260925/BRIEF.md)).
- **2026-09-25** — memory **W9 [ran]: PASSED.** A trajectory LoRA on a wiki of atomic statements: both seeds
  (`wiki-walks-s0`, `-s1`, trained on 32 worlds never evaluated) beat the untrained base walking the evaluation
  world **35 : 0** on the 40-row headline (35/40 against 0/40, verified citations); against the base handed the
  oracle's statements, ties (9 : 3, 8 : 2). 3-hop 16/16. The two draws agree on 57 of 67 rows. Three scoring
  attempts were lost to harness bugs, now reproduced by a fake `vllm serve` on the Mac
  ([`BRIEF`](../results/M7-W9-atomic-statements-20260924/BRIEF.md)).
- **2026-09-24** — memory **W9 pre-registered, not run: atomic statements.** The user's design: the
  library shaped like Wikipedia, a page a list of one-sentence checkable statements under anchors,
  links inside the statement that names them, the same shape for operative recipes; every answer cites
  `[id§anchor]` and the runtime verifies the citation mechanically (`MEMORY.md` §1.6). Test bed: a
  distributor wiki — pages for products, suppliers, warehouses, carriers and staff, and operative
  recipes following the reference organisation's roles (purchasing, receiving, dispatch, claims and
  returns, communications, finance, HR, marketing, IT) — **generated per world** so no value is known
  by heart; one committed evaluation world. One L4, no training: the closed-book arm must fail, then
  `base-walks` against `base-reads` decides whether a trajectory LoRA is needed; if it is, two seeds
  (W5e: two draws of one recipe disagreed on 25 of 67)
  ([`BRIEF`](../results/M7-W9-atomic-statements-20260924/BRIEF.md)).
- **2026-09-22** — `examples/school`'s first LoRA **[ran]: FALSIFIED before training — headroom
  already exhausted.** One role (`educador`, its largest single-tool corpus, regenerated at the
  generator's own default: 114 train / 19 eval), one unknown (tool-call fidelity), gate ≥ 0.90 —
  the bare `Qwen3.5-4B` scored **18/19 = 0.9474** before any adapter existed, clearing the gate on
  its own: one of the three falsification conditions written before the run. The corpus's one
  tool, one argument, stated outright in the system prompt and named or implied in every
  request, is too thin a gap for training to close. No adapter arm bought; the other six roles
  share the same shape and are not bought either
  ([`BRIEF`](../results/M7-school-pilot-20260922/BRIEF.md)).
- **2026-09-22** — memory **W8 [ran]: the schema question only, passed.** Not fluid mechanics, not
  gated on W1–W7 — from the user's own Mona Lisa → painter → drawings example: does the note format
  express a reference that is not a tree edge? Added `refs`, one generic untyped field, either
  shelf; proved on a three-note slice, `knowledge/wikipedia-arts/` (CC BY-SA 4.0, isolated), 0 lint
  findings, the named trajectory resolves mechanically. Not radar-indexed, not walked, not trained
  ([`MEMORY.md`](MEMORY.md) §1.2a, [`BRIEF`](../results/W8-wikipedia-refs-20260922/BRIEF.md)).
- **2026-09-21** — milestone 2 **arm 3 [ran]: no real arm bought.** `cactus-compute/needle`,
  stock weights, same grader as arm 2 — `NOT SAFE: serves foreign text locally`, 62/142
  out-of-region cases served locally (~10× arm 2's leak rate), against 19/40 unseen-sender
  traffic recovered that arm 2 lost completely. Headroom on a subsample, not arm 2's own
  resolution; the dictionary stays the default
  ([`BRIEF`](../results/M2c-needle-router-20260921/BRIEF.md)).
- **2026-09-20** — **re-plan from a pasted architecture, addendum in §0.** Read against
  [`FRAMEWORK.md`](FRAMEWORK.md) §9: mostly already built (role packs F3) or already sequenced later
  (concurrency, the bill, installation) or blocked (a LoRA drafter is a vLLM RFC, not a feature). One
  gap it named correctly and this repository had not closed — permission enforced outside the model
  — becomes `FRAMEWORK.md` §7 step 4, scoped to one domain with a toy store and a 0-leaks adversarial
  gate, Postgres/Auth0 deferred as an implementation choice. **W5d runs first** — cheaper, already
  pre-registered, and step 4's role packs need its answer before they can be built. No milestone
  gate below moved.
- **2026-09-19** — memory **W4 [ran]: PASSED.** The corpus generator drives the runtime: 600 walks, 0 values in a
  statement, 0 evaluated cases in the corpus, 0 held-out opens, 0 rows the referee does not reproduce; `discontinue-iv`
  held out; long walks are windows with the state carried. No model yet.
- **2026-09-19** — memory **W5 [ran]: does not pass as written.** Headline 35/56 against the untrained base that
  reads at 45/56 (6 : 16, $p=0.052$); 35 : 2 over no-library, 35 : 0 over the base navigating alone. 12 of 21 failures
  are the second of two values on a kind of note the corpus never showed. Navigation transferred; that reading did not.
- **2026-09-19** — memory **W5c built and pre-registered, not run.** The source has no conditional value in the
  trained procedures; the user chose one real sentence (drop factors, byte-checked) plus site-added sentences
  declared as invented. A site may now ADD a sentence, never rewrite one. Corpus v2, new held-out and control
  sets, v2 gate PASSED, exact falsifier coded ([`BRIEF`](../results/M7-W5c-conditional-corpus-20260919/BRIEF.md)).
- **2026-09-20** — framework steps 2 and 3 **[ran]**, zero GPU. **F2, the role as the route:** the role rides in the
  model id (`auto:<role>`) and says *which* member, never *whether*: `role_confirmed` passes (never more misroutes
  than the keys, nothing served under a wrong role, replay 0.775) and is the proxy's default; `role_first` fails
  (120/120 foreign tasks served). **F3, the role pack:** `roles/` + `rolepack.lint`; gate passed — served prompt and
  block byte-identical for both released members, registries derivable and equal; the memory's member expressed as
  unreleased, its loop unservable through the API. The chain now stops when the backend rejects the accelerator
  ([`F2`](../results/F2-role-as-route-20260920/BRIEF.md), [`F3`](../results/F3-role-pack-20260920/BRIEF.md)).
- **2026-09-20** — memory **W5d [ran]: FALSIFIED as written.** On the set written after the freeze,
  `policy vs withlib` is 5 : 0, $p=0.0625$ — a tie, as the brief's power line had said that case would be read
  (headline 67: policy 42, withlib 37, base-reads 52; vs base-reads 6 : 16); control holds, 75 vs 73. Read where
  it happens: where the walk opened the supplying note the base reads it right **21 of 21**; the other 11 are
  retrieval misses **the adapter's own query caused** — on a new wording it writes a training query for another
  topic, verbatim in 9 of 11, and computes a drip rate — while the same lexical searcher, given the request's
  statement, lists the needed note 16 of 16 (zero GPU). On W5c's sets, 0 misses, not the claim: 56/66, 14 : 0 and
  12 : 2 vs base-reads, control 75/80. Next, one unknown: the runtime issues the first search from the statement
  ([`BRIEF`](../results/M7-W5d-answer-policy-20260920/BRIEF.md)).
- **2026-09-20** — memory **W5d pre-registered, not run** — step 1 of [`FRAMEWORK.md`](FRAMEWORK.md) §7, *decide who
  reads*. The answer policy: the adapter walks always; it writes the line when the task is to carry a procedure,
  to say it is not in the library, or to compute a rate (rate decided on the trained band only: 15/15 and 12/12
  against the base's 7/15 and 5/12); the bare base writes it when the task asks for a value, from the pages the
  adapter's walk opened. The kind is read off the statement alone (600/600 with the generator's family — which
  shows the rule is wired to the generator's wording, not that a live ask can be classified). Frozen in commit
  `d3e5056`; THEN a new held-out set (89, headline 67) and control (78) were written, gate PASSED, floor 5/67.
  Falsifier: `policy vs withlib` a tie or worse on the new headline; control must not regress; against
  `base-reads` a tie is a tie. One L4 session, W5c's adapter carried in, no training
  ([`BRIEF`](../results/M7-W5d-answer-policy-20260920/BRIEF.md)).
- **2026-09-20** — memory **W5c [ran]: FALSIFIED.** Conditional value 4/15 (0/11 before, Fisher $p=0.091$); W5's
  pair on the new headline 12 : 16, a tie — not passed. The adapter reads the conditionals of the eight notes
  it saw (17/18) and on an unseen note writes the first number; navigation improved (shared line 22/22,
  control 78/80). Five sessions of six; one lost at boot ([`BRIEF`](../results/M7-W5c-conditional-corpus-20260919/BRIEF.md)).
- **2026-09-19** — memory **W5b [ran]: the diagnosis holds, and composition is not a serving design.**
  `withlib`'s recorded walks replayed, the bare base writes the final line: **0 of the 12** clean-walk
  quantity failures remain; `composed` 41/54, exactly its zero-GPU ceiling; 12 : 4 against `withlib`
  ($p=0.077$, a tie), 1 : 5 against `base-reads`; `carry/middle-find` 8 of 8 remain. But on what the adapter
  was taught it reads far better than the base — control 58 against 39 (0 : 19), shared line 15 against 8.
  The reader fails on one shape its corpus never showed; both two-valued notes in the library sit in the
  held-out procedure. W5's verdict stands ([`BRIEF`](../results/M7-W5b-composition-20260919/BRIEF.md)).
- **2026-09-19** — W4's grader replaced after an adversarial review (redesign 2: it failed on a paraphrase and passed
  on a decoy number); **W5 built and pre-registered**, headroom session first, headline n = 56, floor 3/56. Not run.
- **2026-09-19** — memory **W2 [ran]: PASSED.** The runtime, layers and guard on the unchanged corpus-mode loop;
  72/72 oracle walks, 0 refused, three violating walks cut in `strict`. No model yet.
- **2026-09-19** — memory **W3 built, headroom [ran]:** the index, a query set written after the freeze (P 94, E 72),
  lexical recall@3 0.064 / 0.125. The R0 session on Colab is pending; the verdict and its 0.80 standard are in the brief.
- **2026-09-19** — memory **W3 R0 [ran]: not passed.** recall@3 0.638 on P, 56 : 2 against lexical, under the 0.80
  fixed before the run; half the misses are at rank 4–10, half are far. The gap is W6's; W5 counts retrieval misses apart.
- **2026-09-19** — memory **W1 [ran]: PASSED.** The first library (`knowledge/nursing-iv/`, 94 notes from
  three Open RN checklists, CC BY 4.0), `memory/notes.py` and the lint; 0 findings, 72/72 oracle walks.
- **2026-09-19** — milestone 1 **[ran]: MOVED.** Both released members retrained on `Qwen3.5-4B` tie
  their Qwen 2.5 releases (471/475, 240/240); `@v2` manifests; the pool is on the 3.x family. Four
  sessions under an hour each, five relaunches, every one a harness fix.
- **2026-09-19** — the memory specified as the core of 1.0 ([`MEMORY.md`](MEMORY.md)), from the
  user's five-piece explanation: library, radar, three verbs, a LoRA trained on the habit of
  navigating, a software referee. Milestone 7 arm 0b **[ran]**: the fluids expert, served as its
  corpus taught, is 90/90 where it had been 11/90 — *"the expert that reasons fails"* is withdrawn.
- **2026-09-19** — milestone 7 arm 0c **[ran]**: `fluids-full` retrained on `Qwen3.5-4B` is **not
  released** — 80/90 against its own 90/90 (0 : 10, paired). All ten are venturi chains, right to the
  number, that end in an `<answer>` tag the corpus never taught instead of the JSON line. The region
  stays `out`; next, the same member under the memory's runtime, whose guard names an unknown tag inline.
- **2026-09-19** — milestone 2 arm 1 **[ran]**: safe on foreign text, loses every request from an
  unseen sender; the dictionary stays, arm 2 is an embedding model. Milestone 7 added: a knowledge
  base per subdomain with the trajectory through it as the harness, on fluid mechanics split into
  subdomains — shaped by P61, P21 and P14.
- **2026-09-19** — objective restated around corpus-distribution routing and the
  speculative pair; the tree cleaned to what works; the previous plan and its seventy-four
  runs kept at `v0.1-foundations`.
- **2026-09-06 → 2026-09-19** — see [`RECORD.md`](RECORD.md).
