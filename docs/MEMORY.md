# The memory — implementation

> **The LoRA is not the textbook. It is the specialist who knows how to use the library.**
> It memorises no data: it learns **which shelf to go to, which card to open, and which step to
> run next.**

This is the implementation specification of the per-expert memory, the core of version 1.0. The
*why* — ten measured findings, five trajectory strategies, the questions put to reviewers — is
[`KNOWLEDGE-TRAJECTORIES.md`](KNOWLEDGE-TRAJECTORIES.md); this document is the *what to build*. The
explanation it implements is the user's, 2026-09-19. Status markers as everywhere here: **[ran]**
measured in this repository, **[read]** read in source or a paper, **[spec]** decided and not yet
built. **Nothing in this document is built yet**; §10 says in what order it will be, and what can
stop it.

Five pieces:

| # | piece | one line | neural? |
|---|---|---|---|
| 1 | **the library** | small markdown notes on two shelves — the operational harness and the encyclopedic wiki | no — text in git |
| 2 | **the radar** | embeddings compressed to one subdomain: *when is this note for*, *what does it define* | a small encoder, frozen at serving |
| 3 | **the language** | three verbs the expert may write: `<search>`, `<open>`, `<calc>` | no — a grammar |
| 4 | **the LoRA** | trained on the *habit of navigating*, never on the data | yes — the only trained part |
| 5 | **the runtime** | a small Python referee: turns the pages, applies local rules, enforces the order | no — pure software |

> **[ILLUSTRATION PLACEHOLDER — `docs/img/memory-five-pieces.png`]**
> *A single wide diagram, left to right, flat technical style, light background. Far left, a
> bookcase with two labelled shelves: the top shelf "Operational harness" holds cards joined by
> arrows in a line (a procedure); the bottom shelf "Encyclopedic wiki" holds cards arranged as a
> tree. In the middle, a small radar dish labelled "radar — embeddings of this subdomain only"
> sweeping over the bookcase and lighting up three cards. To its right, a figure at a desk labelled
> "LoRA — the specialist" holding exactly three tools labelled `search`, `open`, `calc`. Beneath
> everything, a thin band labelled "runtime — referee" with three icons: a page being turned, a
> stamp reading "site rule applied", and a barrier gate reading "requires step 1". No robots, no
> brains, no glowing neural nets: the point of the picture is that four of the five pieces are not
> neural.*

---

## 1. The library — two shelves of markdown

One folder per subdomain, one file per note, **under half a page** (hard limit: 150 tokens of
body — a note has to fit a 4B's attention with room to spare, and a long note is two notes).

```
knowledge/
  nursing-iv/
    harness/                     # how it is done
      primary-infusion.md            ← a procedure: the skeleton, step titles only
      primary-infusion/
        03-cleanse-catheter-cap.md   ← a step
        04-assess-patency.md
    wiki/                        # what it is, which formula applies
      asepsis/scrub-the-hub.md
      rates/gravity-drip-rate.md
    site/                        # a ward's adaptations — overrides only (§5.2)
      ward-7b.md
```

### 1.1 The operational harness — *how is it done?*

Recipe-like notes. Their links are **fixed and typed**, and they are the control flow:

| link | reads as | used by |
|---|---|---|
| `requires` | *before this you must have done …* | the expert — and **the runtime, as a guard** (§5.3) |
| `next` | *the step that follows is …* | the expert, to advance |
| `uses` | *for this step consult …* (a wiki note, or a sub-procedure) | the expert, to make a stop in the wiki |

```markdown
---
id: nursing-iv/harness/primary-infusion/03-cleanse-catheter-cap
shelf: harness
kind: step                       # procedure | step | check
title: Cleanse the catheter cap before attaching tubing
when: You are about to connect a syringe or tubing to a patient's IV port.
what: Disinfection of the IV port's cap with an alcohol pad or scrub hub.
requires: [nursing-iv/harness/primary-infusion/02-safety-steps]
next: nursing-iv/harness/primary-infusion/04-assess-patency
uses: [nursing-iv/wiki/asepsis/scrub-the-hub]
slots: {seconds: 5}
source: Nursing Skills (Open RN), ch. 23 — CC BY 4.0
---
Vigorously cleanse the catheter cap for at least {{seconds}} seconds and allow it to dry.
```

A **procedure** note is only a skeleton — its ordered step ~~titles~~ **labels** (the slug of each step's id: `20 cleanse cap`) and the id of the first step. *Amended by W1 **[ran]**: thirty-two numbered titles are 230 tokens against this document's own limit of 150; labels are 98.* The
detail lives in the steps. Reading a 32-step checklist at once and *walking* it are different
tasks, and the second is the one being built.

### 1.2 The encyclopedic wiki — *what is it, which formula applies?*

Tree-shaped notes, general to specific, joined by `parent` → `children`. They exist to **classify
which case you are in before you compute**:

```markdown
---
id: fluids/wiki/pipe-flow/turbulent/friction-factor
shelf: wiki
kind: formula                    # concept | formula | table
title: Friction factor in turbulent pipe flow
when: Reynolds number above 2300 and you need the Darcy friction factor.
what: The Swamee–Jain correlation for f from Reynolds number and relative roughness.
parent: fluids/wiki/pipe-flow/turbulent
children: []
slots: {a: 5.74, b: 3.7}
---
f = 0.25 / ( log10( eps/({{b}}·D) + {{a}}/Re^0.9 ) )^2
```

### 1.3 Two fields every note carries, and why

`when:` — *what situation is this note for.* `what:` — *what concept does it define.* These two
lines, not the body, are what the radar indexes (§2). They are written by whoever writes the note,
in the words a practitioner would use to ask.

### 1.4 Slots

`{{seconds}}`, `{{a}}` — values the runtime fills when it serves the note. They are how the three
sources of variation enter without touching the text: **the textbook's default** (`slots:` in the
note), **a site's rule** (§5.2), and, in training and evaluation only, **a value drawn for one
case** (§4.1).

### 1.5 The library is linted, like code **[spec]**

`python -m memory.lint knowledge/<subdomain>` fails the build when: a link does not resolve; a
`next` chain has a cycle or a step belongs to no procedure; a body exceeds the token limit; a
`{{slot}}` is used and not declared; a `when:` or `what:` is missing; two notes of one subdomain
have the same `when:`. Knowledge that lives in git gets the gates code gets.

---

## 2. The radar — embeddings compressed to one subdomain

Not a general search engine, and not a large embedding model built to know history, pop culture and
cooking at once.

### 2.1 What is indexed

Per note, two vectors: $e_{\text{when}}(n)$ and $e_{\text{what}}(n)$. One index **per subdomain** —
the router has already placed the request in the subdomain, so the radar never searches outside it.
A subdomain's library is a few hundred notes: the index is a matrix, search is a matrix product,
there is no ANN library and no server.

### 2.2 Why "compression" is the right word — the hypothesis **[spec]**

In a closed domain the vocabulary has exact functional meaning. *Patency*, *drip factor*, *relative
roughness* each point at one thing. A general encoder spends most of its dimensions telling a
recipe from a sonnet — distinctions that never occur inside *IV therapy*. So a **very small vector,
or a light encoder tuned to the jargon, should be enough** to separate the only two intents that
matter here: *what situation is this for*, and *what does this define*.

That is a hypothesis with a cheap test, and it is built in two stages so the test comes first:

| stage | the radar | cost |
|---|---|---|
| **R0** | an off-the-shelf small encoder of the pool's family (`Qwen3-Embedding-0.6B` **[read]**), every text embedded under one instruction — *represent the situation this is for* | none: no training |
| **R1** | R0's vectors passed through a **learned projection to a small dimension** $d$ (64–128), trained on this subdomain only | minutes |

**R1's training data is free.** The oracle walks that train the LoRA (§4) already say, for every
step, *this query should have found this note*. Those (query, needed note) pairs, with the other
notes of the subdomain as negatives, are a contrastive training set nobody has to label:

$$\mathcal L = -\log \frac{\exp(\langle W e(q), W e_{\text{when}}(n^+)\rangle / \tau)}{\sum_{n \in \mathcal N}\exp(\langle W e(q), W e_{\text{when}}(n)\rangle/\tau)}, \qquad W \in \mathbb R^{d \times D},\ d \ll D .$$

**What would show the compression claim is true:** recall@3 of the needed note, on held-out walks,
staying flat as $d$ falls from $D$ to 64 — and R1 at $d = 64$ beating R0 at full width on
*within-topic* confusions, which is where flat retrieval failed before (F9 of the design
document). **What would show it false:** recall falling with $d$, or R1 no better than R0. Both are
reported.

### 2.3 Scoring a search

$$s(n \mid q) = \langle e(q), e_{\text{when}}(n)\rangle + \beta\,\langle e(q), e_{\text{what}}(n)\rangle, \qquad \text{return the top } k = 3 .$$

A search may be restricted to a shelf: `<search shelf=harness>` for "find me the protocol",
`<search shelf=wiki>` for "which formula". $\beta$ and the trajectory-conditioned terms of the
design document (§4, S4) are arms over this baseline, not part of it.

**Two priors against cleverness [read]**, carried here so they are not forgotten: a memory hierarchy
lost to flat lexical search in this workspace's earlier benchmark, and indexing *what it is for*
beside *what it is* changed nothing in `evolving-memory`'s own (acc@1 80 % at every weight, n = 10).
So R0 with a single `when` vector, and plain lexical search, are both kept as baselines, and a null
is reported as a null.

**The same encoder is the router's** (milestone 2, arm 2): a subdomain is one region of one space —
what falls in it is routed to the member, and what the member looks up is found in it.

---

## 3. The language — three verbs, and nothing else

The expert may write exactly three commands in its own text. Generation stops at each closing tag;
the runtime writes the result **inline, right after the tag**, and hands the turn back — the form
every expert in this pool is already trained and served in (0.992 that way against 0.808 through
`tool_calls` messages **[ran]** P55).

| verb | the expert writes | the runtime answers |
|---|---|---|
| **search** | `<search>situation or doubt</search>` | `= 3 notes` and, per note, `[id] kind · title — when: …`. **Titles and `when` lines only — never bodies** |
| **open** | `<open>id</open>` | the note's body, slots filled and local rules applied, then its links: `next …` · `requires …` · `uses …` (on the wiki shelf `parent …` · `children …`; every link but `next` carries the note's title beside its id — W2 **[ran]**) |
| **calc** | `<calc>500 * 20 / (4 * 60)</calc>` | `= 41.6667` — so the model **never does arithmetic in its head**, where it always fails (adapter alone 4/40, adapter + calculator 40/40 **[ran]** P5–P7) |

```
<search shelf=harness>start a primary IV infusion by gravity</search>= 3 notes
  [k3f] procedure · Primary IV solution administration — when: a provider orders IV fluids
  [9c1] procedure · Secondary IV solution administration — when: adding a piggyback medication
  [77e] procedure · Discontinuing an IV — when: an IV is to be removed
<open>k3f</open>= Primary IV solution administration — 32 steps. First step: a01
  next a01
```

Rules of the grammar:

- **Following a link is `<open>` on its id.** There is no fourth verb.
- **Ids shown to the expert are short and opaque, and re-drawn per conversation.** The expert
  cannot learn "for cleansing, open `k3f`"; it has to read what `<search>` and `<open>` returned.
  Navigation by rote works until the library changes, and then fails silently.
- **Errors are observations, not exceptions:** `= ERROR: no note k3x in this conversation`,
  `= ERROR: requires a02 first` (§5.3). The expert reads them like any other result.
- **The verbs are taught, so they are frozen with the release** — tag names, attribute order,
  rendering of results. A member trained in another language is taught that language's verbs
  (`<buscar>`, `<abrir>`, `<calcular>`); the release manifest records the grammar's version.
- **Budgets belong to the runtime:** $k = 3$ notes per search, the token cap per note, at most ~~24~~ **48**
  opens and 12 searches per task. A walk that reaches a cap ends as *not answered* and the request
  goes to the frontier.
  *Amended by W2 **[ran]**: the first library's longest procedure is 32 steps, and a cap below the
  corpus's own depth scores the cap.*

---

## 4. The LoRA — training the habit of navigation

**What is taught is the method of work, never the data.**

### 4.1 Synthetic cases whose data always changes

Every training case draws its own constants: a liquid invented for this exercise (`TD-78`, density
882.3), a local dwell time of 15 seconds instead of 5, a correlation whose coefficients differ from
the textbook's. The values are delivered **only through the note's slots**, so the model cannot
memorise an answer — *it is forced to open the note to see the number*. This is not a nicety: over a
fixed 14-value table a control with **no lookup tool at all** scored 27/30, because 600 examples
memorise 14 numbers **[ran]** P15, P21. The generator asserts, per case, that no slot value appears
in the task statement.

### 4.2 The choreography

1. Read the problem.
2. `<search shelf=harness>` to find the protocol.
3. `<open>` the protocol.
4. If a step says it `uses` something — *verify the flow regime* — make a stop in the wiki:
   `<open>` that note, or `<search shelf=wiki>` if the step only names the need.
5. Send the numbers to `<calc>`.
6. Follow `next` until the procedure ends, then answer.

### 4.3 How a case becomes a training example **[spec]**

For each generated case the **oracle knows the walk** — which notes the solution needs, in which
order. The corpus is that walk rendered as the expert's own turn, commands and inline results
together, **byte for byte as it will be served**: the generator *calls* the runtime to render every
observation rather than imitating its output, because a copy is what drifted last time (71 refused
calls that looked like physics **[ran]** P38).

```
[user]      A provider orders 500 mL of IV fluid over 4 hours by gravity; the tubing's drop factor
            is 20 gtt/mL. Set the rate.
[assistant] <search shelf=harness>set the rate of a primary IV infusion by gravity</search>= 3 notes
              [k3f] procedure · Primary IV solution administration — when: a provider orders IV fluids
              …
            <open>k3f</open>= … First step: a01
            …
            <open>a26</open>= Set the infusion rate based on the provider order. For gravity: calculate
              drops per minute.  uses q81 · next a27
            <open>q81</open>= Gravity drip rate: drops/min = volume (mL) × drop factor (gtt/mL) ÷ time (min).
            <calc>500 * 20 / (4 * 60)</calc>= 41.6667
            Set the roller clamp to 42 drops per minute.
```

Four properties the corpus must have, each from a measurement:

| property | because |
|---|---|
| **distractors** in every `<search>` result, and some cases where **no note applies** — the taught walk ends *not in my library*, which the proxy turns into the frontier | a specialist is confidently wrong just outside its region: 30/30 inside, 1/20 on sibling families **[ran]** P14 |
| **every depth the expert will serve** — walks of one, two, five opens; procedures entered at the first step and in the middle | a corpus with one difficulty teaches a floor: over-solved 18/18 below its training depth **[ran]** P45 |
| **held-out sibling procedures** whose notes are in the library and whose walks were never trained | that is the claim: *the library extends the region with no retraining* |
| the tool block, the system prompt and the result format **exactly as served** | a member is what its corpus taught: 2/32 → 19/32 tool-calling turns under its own prompt **[ran]** P63 |

### 4.4 What "memory" does **not** mean here

The adapter holds no facts about the subdomain and the library holds no behaviour. A finding the
design has to survive: a small model does not follow a procedure it merely reads — base + a
procedure document made 0 tool calls on 351/351 messages **[ran]** P61 — which is exactly why
*following what it reads* is the thing the adapter is trained on, and the only thing.

**And the other half of that finding, measured on real text [ran] M5:** the same kind of small base
*answers questions about* a note it merely reads very well — step order and next step in three IV
checklists go from 29/48 closed-book to **45/48 with the note open**, and a quantity a unit's
protocol changed from **0/12 to 12/12**, with no training at all. Comprehension is there; *acting
under a procedure* is what is missing. So the trained part of this memory earns its place only on
**walks** — several steps, tools, a check that gates an action — and never on question-answering over
a note. Every arm from W5 on carries the baseline that says so: *the bare base with the oracle's note
open.*

---

## 5. The runtime — the software referee

Pure Python, no model, a few hundred lines, inside the proxy. It does the work between one command
and the next.

### 5.1 It turns the pages

On `<open>id</open>`: find the file, fill the slots, render body and links, write them after the
tag, return the turn. This is the corpus-mode loop the pool already runs — stop at the closing tag,
inject `= result`, continue (`training/harness/accept_rank.py::run_chain`) — with a new answer
function that has **state per conversation**: the id map, the notes opened so far, the budgets.

```
memory/
  notes.py      load, validate and lint a subdomain's library
  index.py      build and query the radar; exhaustive cosine; R0 and R1
  layers.py     textbook → site → case resolution of slots
  guard.py      conformance: `requires` before the step it guards
  runtime.py    the three verbs; ids; budgets; the walk log
```

### 5.2 It applies local rules automatically

If a hospital or a customer has its own rule — *"here we cleanse for 20 seconds, not 15"* — it is
one line in the site layer:

```markdown
---
site: ward-7b
overrides:
  nursing-iv/harness/primary-infusion/03-cleanse-catheter-cap: {seconds: 20}
---
```

The runtime substitutes the value **before** the note reaches the expert, and marks it:
`…for at least 20 [site] seconds…`. **The model never sees the conflict; it reads the rule already
resolved.** Resolution order, nearest wins: *case* (training and evaluation only) → *site* →
*textbook*. It is deterministic and auditable, and it spares the expert the one thing the record
says it does worst — reconciling two things it has read.

### 5.3 It watches for cheating — the conformance guard

If step 4 says `requires: step-1` and the expert tries to run step 4 without ever having opened
step 1, **the runtime cuts the execution and reports the error — without needing to know whether
the final answer was right.** That is a verifier that consults no answer key and that the training
loop never sees, which is what any signal used to accept or reject an answer has to be; its
precedent here is dimensional analysis on a physics chain, which catches an invented relation
without knowing the number **[ran]** P22.

**[spec]** Two modes. `strict` — the default in 1.0: the first violation ends the walk as *not
answered* and the request goes to the frontier. `recover` — the violation is written inline as an
observation (`= ERROR: requires a02 first`) and the expert may go back; whether small experts *do*
recover is an arm, not an assumption.

### 5.4 It writes the walk down

One JSON line per command: verb, argument, ids returned, note opened, slots resolved and from which
layer, guard verdict, tokens. It is what every measurement in §9 is computed from, and the raw
material of the episodic memory of the design document (§7) — logged in 1.0, consolidated later.
Whether a customer's log may keep note *content* or only *shapes* is a setting, default shapes.

**Carried over, W4 [ran].** A walk longer than a context is served in windows, and a window entered in
the middle needs what `strict` needs — the steps already done — and an id to go on from. The referee
resumes from this record: `Conversation.resume(done)` counts those steps as opened and renders the **last
page** again, ids re-drawn, to stand in the turn that continues. The corpus calls it; nothing imitates it.

---

## 6. In operation — one task, end to end

![Seven numbered panels joined by one line, like a subway map: a request, a search that lights three cards, a procedure opening, the line running along the harness shelf, a detour down to the wiki shelf and back, a calculator, the answer.](img/memory-walkthrough.png)

*One task, end to end. The detour from the harness to the wiki and back is the point.*

1. **The task comes in:** *"Infuse 500 mL over 4 hours by gravity; drop factor 20 gtt/mL."*
2. **The expert consults its radar:** `<search shelf=harness>start a primary infusion</search>`.
3. **The radar answers:** `[k3f] procedure · Primary IV solution administration`.
4. **The expert walks the harness:** `<open>k3f</open>`, then step by step along `next`. At *set
   the rate* the step `uses` a wiki note.
5. **The expert makes a stop in the wiki:** `<open>q81</open>` — the drip-rate formula.
6. **The expert delegates the arithmetic:** `<calc>500 * 20 / (4 * 60)</calc>` → `41.6667`.
7. **The expert moves on:** follows `next` to the following step of the harness, until the task closes.

**The gain.** If the protocol changes tomorrow, **you edit one markdown file in git**. The LoRA is
not retrained, because what it learned was to obey the links and read the notes; the operational and
factual knowledge lives outside it, structured and versioned.

## 7. What can be edited without retraining — and what cannot

| change | retrain? | why |
|---|---|---|
| a value, a wording, a site rule | **no** | the expert reads it fresh every time |
| a new step inside a procedure; a re-ordered `next` | **no** | it follows links, it does not remember them |
| a new procedure of a kind it was trained on (a sibling) | **no — this is the claim §4.3 tests** | |
| a new wiki branch | **no** | |
| a new **verb**, a new **link type**, a new **kind** of note, a changed **rendering** of results | **yes** | that is the grammar the adapter was taught (§3) |
| a procedure of a *shape* it never saw — branching, loops, waiting | **yes, probably** | the choreography is what is in the weights |

The second group is small on purpose. It is the version number of the grammar.

## 8. What a release records

A member is its corpus, its library and the way it was taught to walk it. The manifest
(`releases/*.json`) gains: the library's hash and path, the radar's encoder id, stage (R0/R1) and
index hash, the grammar version, the guard mode. Re-serving a release re-checks all of them, as it
already re-checks the adapter and the corpus.

## 9. How it is measured

Per command, not only at the answer — a reader that got lucky over an empty note is a case a final
score cannot see:

| metric | question |
|---|---|
| **retrieved** | was the needed note among the three `<search>` returned? |
| **opened** | did the expert open it? |
| **used** | did its value reach a later step? (`training/physics/result_use.py` — the instrument that found the fluids expert looks a density up, 882.3, and multiplies by 1359.7 **[ran]**) |
| **conformant** | did the walk respect every `requires`? |
| **correct** | the verifier's verdict |
| **tokens** | a walk is not free |

Arms and their order are [`PLAN.md`](PLAN.md) milestone 7. Two test beds with different jobs: **fluid
mechanics** is the instrument — an exact oracle, content unmemorisable by construction; **nursing
procedures** (Open RN *Nursing Skills*, CC BY 4.0) are the region — text nobody here generated, and
a real site layer.

## 10. Build order for 1.0 **[spec]**

Each package ends in a gate, fits a sixty-minute Colab session where it needs a GPU at all, and
**no model runs on the user's machine**.

| # | package | needs a model? | gate |
|---|---|---|---|
| W1 | `memory/notes.py`, the lint, and the first library: IV therapy, three procedures as skeleton + steps, a small wiki | no | the lint passes; every walk the oracle needs exists — ✅ **[ran] 2026-09-19**: 94 notes, 0 findings, 72/72 walks ([`BRIEF`](../results/M7-W1-library-20260919/BRIEF.md)) |
| W2 | `memory/runtime.py`, `layers.py`, `guard.py` on the existing corpus-mode loop | no | **every oracle walk passes through the runtime**, 0 refusals, guard silent; a violating walk is cut — ✅ **[ran] 2026-09-19**: 72/72 walks, 949 commands (72 searches, 865 opens, 12 calcs), 0 refused, 0 malformed, guard silent; three violating walks cut in `strict`, continued in `recover`; `<search>` is lexical until W3 ([`BRIEF`](../results/M7-W2-runtime-20260919/BRIEF.md)) |
| W3 | `memory/index.py`, radar **R0**, beside a lexical baseline | Colab, minutes | recall@3 of the needed note on oracle queries; the baseline reported beside it — ❌ **[ran] 2026-09-19 — not passed: R0 beats a word-matcher and is not enough.** Built, then run: W2's queries are void here (a note ranks first for its own `when:`), so the radar is measured on a set written after the design was frozen — **P**, one bedside paraphrase per note (94, mean word overlap with the target 0.039), the gate; **E**, the 72 question stems → the walk's first note, beside it. Lexical baseline recall@3: **0.064** on P, 0.125 on E — headroom, and a floor by construction, so the gate also carries an absolute standard: R0 wins the pair **and** recall@3 ≥ 0.80. **R0 (`Qwen3-Embedding-0.6B`, one L4 session): recall@3 0.638 on P — 56 : 2 against lexical, and under the 0.80 fixed before the run.** β = 0.5 beats `when:`-only 30 : 4. Of 34 misses, 13 sit at rank 4–6 (recall@6 0.777, recall@10 0.830) and 16 past rank 10; four of those collapse inside their shelf. The standard is not loosened: the gap is W6's, on new sets, and W5 counts a retrieval miss apart from the expert's score ([`BRIEF`](../results/M7-W3-radar-r0-20260919/BRIEF.md)) |
| W4 | the corpus generator: unmemorisable slots, opaque ids, distractors, dead ends, depth mix | no | no slot value in any statement; no evaluated walk in the corpus — ✅ **[ran] 2026-09-19**: `training/nursing/generate_walks.py` *drives* the runtime — 600 rows (and the same 600 cases with no verbs, W5's second arm), 80 held-out and 60 control evaluation walks; **0** values in a statement, **0** evaluated cases in the corpus, **0** opens of the 17 notes that are `discontinue-iv`'s alone, **0** rows the referee does not reproduce byte for byte in `strict`; each clause broken by a test. Long walks are **windows** with the state carried (`Conversation.resume`); max 1 298 of 1 536 tokens. **The grader was replaced before W5 read through it** (redesign 2, a third ends the step): an adversarial review found it failed on a paraphrase and passed on a decoy number; it now reads the final line only, a number only where it is attached to its unit, a step by *attribution* among the step notes, and the walk off the referee's log — states `right` · `format` · `unread` · `wrong` ([`BRIEF`](../results/M7-W4-corpus-20260919/BRIEF.md)) |
| W5 | **the kill arm** — two adapters on one subdomain, with and without the library, scored on a held-out sibling procedure, **as walks, not as questions**; beside them the *bare base with the oracle's notes open* | Colab, two sessions | with-library beats without, paired — **and beats the untrained base reading the same notes**, which on question-answering is already at 45/48 **[ran]** M5 — or the memory stops here at this model size — 🔶 **built and pre-registered 2026-09-19, not run**: `training/nursing/walks_arm.py`, four sessions with the untrained-base **headroom session first** (≥ 51/56 on the headline stops the step before any training); headline = held-out rows at depth ≤ 9 whose final line is the procedure's own, **n = 56**; trivial-policy floor **3/56** [ran], oracle 140/140 through the same function ([`BRIEF`](../results/M7-W5-kill-arm-20260919/BRIEF.md)) |
| W6 | radar **R1**, the compression claim | Colab, minutes | recall@3 flat as $d$ falls to 64 |
| W7 | edit one note after training; the answer must follow the library | Colab, minutes | it does |

**What could have stopped it, and did not [ran] 2026-09-19.** Milestone 7's arm 0b asked whether the
fluids expert uses a tool's result when it arrives inline, as its corpus taught — it had scored 11
of 90 through `tool_calls` messages, looking a density up and then multiplying by a number of its
own. Served inline: **90 of 90**, 79 : 0 paired, no evaluated case in its corpus. **A 3B does use
what it reads, when it reads it the way it was taught**, and this memory delivers everything through
exactly that channel. What remains unproven is the claim itself — W5: that a library extends the
region to a procedure the expert never trained on.
