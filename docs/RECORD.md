# The record

**What this repository measured between 2026-09-06 and 2026-09-19, including what failed.**
Every line names its run. A run directory that is not under `results/` on `main` lives at
the tag [`v0.1-foundations`](https://github.com/EvolvingAgentsLabs/lora-kernel/tree/v0.1-foundations),
with the plan entry that pre-registered it. All of it is **[ran]** unless marked **[read]**,
and all of it is on **generated suites**: no real traffic has been measured.

Do not re-derive what is here. Do not cite a number from it without the caveat beside it.

## 1. What works

| finding | number | run |
|---|---|---|
| Multi-LoRA serving: one vLLM, one base, each request served by its own adapter; co-residence costs the serving member nothing | identity `applied`, tools reachable, stop honoured, on every member | P36–P40, P56 |
| `email-full` — tools and judgement in one adapter. It learned *when* to ask, not "always ask": it skips almost exactly the automatic messages | 0.989 human accuracy vs base 0.345; 393 calls, 0 refused | P36, P57 |
| `email-full@v1` is reproducible: re-served and re-trained from the manifest, both tie the recorded run | 471/475, 471/475, 472/475; 0 and 1 discordant | P57 |
| `desk-commitment@v1` — a second member on the same inbox, a different question | 240/240 vs base 38/240, 202 : 0; ties its recorded run with 0 discordant | P64 |
| On a 3B, a written procedure in the context is not followed | base + 914-token procedure: 0 tool calls on 351/351, 0.601, under the 0.655 majority bar; expert 137 : 1 | P61 |
| Routing by region to a frontier model | 0.546 → 0.775, 38 % of cases leave; `gemini-3.8-flash` 66/90 on fluids. *The mechanism stands; this instance does not: the region sent out was one the pool served through the wrong path — locally, as taught, it is 90/90 (below)* | P41 |
| Routing per request ties routing by region | 0.775 = 0.775, 0 misrouted, 37.5 % out | P62 |
| A region is its question, not its listing | keyed on shared input markers 15/60 misroute; keyed on the question 60/60, 60/60, 150/150, 140/140 | P64 |
| OpenClaw live, from a laptop through a tunnel | 40/40 local, 0 invented calls, 19/32 human turns call a tool, 0.688 vs bar 0.655 ($p = 0.43$, descriptive) | P63 |
| A member is what its corpus taught — the block *and* the prompt | under the runtime's 37 KB prompt 2/32 turns call a tool, 0.281; under its own, 19/32 | P63 |
| Served an unknown tool surface, an expert copies tags off the block | 54 tools offered: 225 of 227 calls refused; pruned to its own: 8 of 1160 | P59 |
| Corpus mode — stop at the closing tag, inject the result, continue — is how an expert is served | `email-full` 0.992 that way, 0.808 through `tool_calls` | P55 |
| vLLM applies a LoRA over a quantised large model | `Qwen2.5-32B-AWQ`: logprob gate 3/3, mean \|Δℓ\| 0.22–0.49 nats vs base-vs-base 0.000; the text gate alone read a 60-step toy as *not applied* | P60 §3b |
| `Qwen3.5-2B/4B` and `Qwen3.8-27B` share one id space | 248,044 ids, 7 large-only (audio/TTS); `<think>` shared | D0 |
| On foreign text a model of the corpora is safer than the keyword dictionary | fresh sets, written after the design was frozen: keyed foreign text and a listing followed by another task, 128 — dictionary serves **59** locally, the n-gram corpus router **0** | M2 |
| **An expert that reasons, served the way its corpus taught.** `fluids-full` on its own 6-to-9-step chains, the result written inline after the closing tag | **90/90**, where the same adapter on the same 90 cases scored 11/90 through `tool_calls` — **79 : 0** paired; **24 : 0** against the frontier's 66/90. Checked before it was believed: 0/90 evaluated statements in the corpus, 0/90 answers recur, the final answer is the model's own last `<calc>` in 89/90 | M7 arm 0b |
| **The pool moves to another family and holds.** Both released members retrained on `Qwen3.5-4B` from the same corpora, unchanged recipe, tensors named for the class vLLM serves, thinking off | `email-full` **471/475**, its recorded 471 — tie 1 : 1; `desk-commitment` **240/240** — tie. G1 `applied` on both *full-recipe* adapters. The recipe's projections reach only 8 of 32 attention layers of the hybrid stack, and it was enough. *The new base alone is far stronger on email — human 0.632 against the 3B's 0.345 — so an adapter has less to add there; and its 0/240 on the desk is an untrained model copying the tool block's `...` placeholder 7 times a case, which says nothing about the task* | M1 |
| **A real procedure has headroom, and an open note closes most of it.** `Qwen3.5-4B`, untrained, on 72 checkable questions over three Open RN IV checklists (CC BY 4.0) | step order + next step **29/48 closed-book → 45/48 with the note open**; a quantity a unit's protocol changed **0/12 → 12/12** — the model follows the note over its prior; drip rates 7/12 → 6/12, so arithmetic stays with a calculator. Paired 29 : 2. *The open-book arm was handed the right note: retrieval is untested.* A small base **answers about** what it reads (here) though it does not **act under** it (P61) | M5 headroom |
| **The memory's first library exists and is linted like code** — no model involved. Three Open RN IV procedures (CC BY 4.0) as skeleton + step notes, a wiki tree, a site layer; layers resolve case ▸ site ▸ textbook | 94 notes, lint **0 findings**, oracle walks **72/72**; the gate fails when a step is removed. The lint's first finding was the spec itself: a 32-title skeleton is 230 tokens > 150 | M7-W1 |
| **The memory's referee runs on the pool's own corpus-mode loop, unchanged** — no model involved. Three verbs, opaque ids re-drawn per conversation, site rules applied before a note is shown, a guard that consults no answer: $\text{requires}(n) \setminus \text{opened} \ne \emptyset$ | **72/72** oracle walks replayed as scripted generations, 949 commands, 0 refused, 0 malformed, guard silent; three violating walks cut in `strict`, continued in `recover`; the gate fails on a broken link. Search is lexical and unmeasured here | M7-W2 |
| **A word-matcher cannot find a note from a question that does not use its words — the headroom the radar is for** — zero GPU, no model. 94 bedside paraphrases, one per note, written after the design was frozen; mean word overlap with the target 0.039. $\text{recall@}3 = \lvert\{q : \operatorname{rank}_q \le 3\}\rvert / \lvert Q\rvert$ | lexical recall@3 **0.064** (6/94), 56 queries match no note at all; on the 72 question stems 0.125. A floor by construction, so R0's gate also carries an absolute 0.80. **R0 itself is not run yet** | M7-W3 (headroom) |
| Qwen 3.5 adapters are servable: C18 was a naming mismatch | same weights, 496 tensors renamed: `not applied` → `applied`; real activation 0 → 152 of 178 modules | D2 |

## 2. What failed, and what each failure taught

| what was tried | what happened | run |
|---|---|---|
| **The expert that reasons.** A fluid-mechanics member, 600 supervised chains | follows the protocol perfectly — 0 refusals, 6–8 calls against the 7 taught — and gets the physics wrong on 78 of 90; loses, paired, to a hand-written rule ($p = 0.022$). 600 examples taught the protocol and not the physics | P37–P40 |
| …read where it happens, four days later | of those failures, **74 of 79** hold a computation with a number that came from nowhere and leave a tool result unused — 75 (217 of 456 results ignored): it looks up 882.3 and multiplies by 1359.7. **Not mainly wrong physics — it does not use what the tool returned.** And that run served it through `tool_calls`, not the inline form its corpus taught; fluids was never re-served in corpus mode. *"The expert that reasons fails" stands as a score and is open as an explanation* | M7 arm 0 |
| …**and then re-served as its corpus taught — the line above is withdrawn as an explanation and as an in-region score.** | 11/90 was the `tool_calls` path, not the expert: inline, **90/90** (§1). *"The expert that decides works, the expert that reasons fails"* was this record's most quoted line for four days and it described a harness. What is still unmeasured is outside the region: below its training depth (P45 came through the same path and is **open again**) and on sibling families (P14, an earlier harness) | M7 arm 0b |
| …and below its training depth it over-solves | trained on 6-to-9-step chains only: 18 of 18 over-solved below that band; on three-step problems the bare base beats it, 0.167 to 0.000. **A corpus with one difficulty teaches a floor** | P45 |
| **Distillation from a frontier teacher** | transfers the procedure, not the arithmetic: π/4·0.22² comes out 0.037006 for 0.038013. Adapter + calculator 40/40; base + calculator 0/40 with 53 calls; adapter alone 4/40 | P5–P7 |
| **Acceptance as a ranking of experts** against one larger target | the precondition failed twice: an *untrained* target scores below the best expert, 0.746 < 0.989 and 0.967 < 1.000; where the target is strong the grades saturate (`g75` ≡ `g600` = 1.000). Closed without a verdict | P55, P55b, P58 |
| **Acceptance against a frontier API** | impossible, not just expensive: no logprobs for a forced continuation, a different tokenizer | P48 |
| **Character-level acceptance** | measures format, not agreement: identical answers score 0.00 across formats; concordance between targets went 1/5 → 4/5 only because one target indents | S0–S2 |
| **A frontier ahead of a local 12B** on the first suite | none was: `gemini-3.5-flash-lite` 13/20, `gemini-3.8-flash` 13/20, `gemini-3.1-pro-preview` 8/20, against `gemma4:12b` 12/20 free. Paying 100× more scored worse | S1 |
| **Routing per case** by hand-written escalation rules | worse than by region: 0.378 and 0.689 against 0.775. The rules look for inconsistent chains; this expert writes chains that are **coherent and wrong** | P41 |
| …agreement with the frontier as the per-case signal | it works — agree: 8 of 8 right; disagree: 60 of 61 wrong — but it calls the frontier every time, so it buys quality and **no saving** | P41 |
| **Composition** of a protocol adapter with a domain adapter | never measured cleanly: the two corpora taught different notations and every arm was scored under one prompt. Stacked 0/30 and mixed 0/30 are real and say nothing causal. Parked | P8, P9, P13 |
| **Tool use as one capability** | it is two: the *disposition* to ask transfers broadly (a physics kernel makes the base reach for email tools in 123 of 150 cases — with the wrong names, 127 refused); the *vocabulary* transfers narrowly (the email kernel is never refused and asks in 22). All three arms tie on accuracy | P31, P34, P35 |
| **The router as an n-gram model of each member's corpus** (milestone 2, arm 1) | safe (row in §1) and unusable: **120 of 120** legitimate requests from senders outside the generator's pools are sent out, where the dictionary loses none — every generated address ends `.com`, so `. com >` became *frame*. **It learned the generator's uniformity.** And 0 of 240 paraphrases of a member's question recovered: to a lexical model a paraphrase and a different task are the same thing. Arm 2 is an embedding model | M2 |
| **The router as an embedding model of the corpora** (milestone 2, arm 2) — `Qwen3-Embedding-0.6B`, every text embedded as *the task being asked* | safer than the dictionary on foreign text (15/338 served locally against 119), recovers 99/240 paraphrases — and **loses 120/120 requests from unseen senders**, like arm 1. **Not calibration:** unseen senders (median cosine 0.89, max 0.964) and *a member's own listing followed by another task* (0.87–0.91, max 0.966) occupy the same range; a threshold keeping 95 % of the first serves 219 of 338 foreign texts. **Changing who writes moves a request as far as changing what is asked.** What is left: a learned projection that factors task from content | M2 arm 2 |
| **A lookup tool priced on a fixed table** | a control with **no tool layer at all** scored 27/30: seven fluids × two properties is fourteen numbers and 600 examples memorise them. *A suite whose tool calls can be recalled cannot price a tool layer.* Fixed by a handbook drawn per case — and it is the rule every knowledge base here inherits | P15, P21 |
| **A specialist outside its region** | 30/30 on its formulas inside, **1/20** on two sibling families it never saw, prose equally fluent; the tool layer's refusals do not mark the edge (0.18 outside, 0.15 inside; a guard at 0.62 where chance was 0.60). An invented relation does fail dimensional analysis — a guard that consults no model | P14, P18, P22 |
| **A grammar mask** over tool calls | buys cleanliness, not accuracy: refusals 23 → 10, final answers 5/30 → 4/30. Of 30 failures 19 had every call clean | P8, P24 |
| **A generated code suite** | an adapter memorises shapes: one tail per family (180/180 held-out completions verbatim in training), then one skeleton per (family, cut), then ~60 shapes covered twelve times over by 720 examples. Stopped at three | P52–P54 |
| **A third party's expert** from a model hub | none exists at this size with tools and a mechanical verifier; on GSM8K the base is already at 87.6 | P42 |
| **`Qwen3.5-4B` as a base** under vLLM 0.29.0 | the adapter is loaded, logged, and the base is served. Read for five days as a serving-stack limit; it is tensor names (§1, D2) | P33 |
| **Gemma 4 as a PEFT base** | `Gemma4ClippableLinear` is not `nn.Linear` | P29 |

## 3. What the suites themselves turned out to be

All four suites ever measured on fail at least one of `training/suite_gates.py` — P50:
every region of every suite sits at exactly one depth, so region and difficulty are one
variable; the region is readable off the prompt at 0.856 (fluids) and 0.940 (triage);
email drafting has one difficulty for all 180 cases. And the deepest finding has no gate:
**a generated suite cannot contain a difficulty nobody thought of.**

A calibration number has its own ceiling, set by the information in the input: a 0.400 AURC
gap read as room for a typed head was 69–82 % the suite — P44, P46.

## 4. Instruments that lied

Each produced a clean number that was wrong, and each is now a rule in
[`../CLAUDE.md`](../CLAUDE.md) §3 or a failing test.

| the lie | how it was caught |
|---|---|
| T4 reports bf16 support it emulates; the run scored 0/60, which read as the step's falsification | compute capability, not the flag — P2 |
| Gradient checkpointing left on during generation: 0/60 with it, 44/60 without | the control arm |
| A corpus trained on the bare statement, served with the tool block appended: 71 refusals of 606 that looked like physics | the corpus must teach the served prompt; generators *call* `render_tools` — P38 |
| The same adapter, the same cases, temperature 0: 84, 81, 82 against a gate of 83 | vLLM is not deterministic run to run; a verdict is read beside the paired test — P36/P38/P40 |
| "Beats the bar" fires ~45 % of the time by chance on a model sitting at the bar | exact binomial, and paired comparison on shared fixtures (`bar.py`) |
| vLLM served without its tool-call parser: 240 of 240 requests HTTP 400, and the progress line read `correct 0` — what a model that cannot do the task looks like | an arm proves it can reach its tools before it scores — P51 |
| 180/180 against the base's 56/180 — and every held-out completion was in the training set verbatim | deduplicate on what gets written, not on what gets asked — P53 |
| A pre-registered `kb_pays` fired 164 : 74 because a default had flipped | the majority bar guards it — P61 |
| A released member on 60 cases with the weights left on the card | the suite's `eval_n`; the chain brings the adapters home — P64 attempt 1 |
| `modules_with_weights: 531` for an adapter that landed on 0 of 178 modules | vLLM activates three dummy LoRAs while profiling; 531 = 3 × 177. The brief's consistency check caught it — D2 |
| Three looks at the same test sets said the router was perfect; one set written **after** the design was frozen found it loses every real-looking request | freeze, *then* write the set that counts — M2 |
| An acceptance rule that asked *who is nearest* before *who claims* lost 60 of 240 requests to a member that claimed nothing | the code does what the brief says, and a test holds it — M2 |
| A replay that swallowed its tools' errors: every `<lookup>` raised on a handbook passed in its JSON shape, inside a broad `except`, and two of three published counts were wrong for a few hours (75 not 74 unused; 217 of 456 not 132 of 371). The conclusion stood; the numbers did not | errors are counted and reported (`tool_errors`), never skipped — M7 arm 0 |
| **A whole capability read off a serving path.** An expert trained on results written inline was scored through `tool_calls` messages; it called its tools, never saw their results where it had learned to read them, wrote numbers of its own, and scored 11/90. For four days that was *small models cannot reason*. Same adapter, inline: 90/90 | the failure was read where it happens (*was the result used?*) and the one re-serve that separated model from path was bought first — M7 arm 0, 0b |
| A run that died "because one liveness probe went unanswered" — my diagnosis, written into a brief — had in fact been ended by Colab at **exactly sixty minutes**, twice (`10:45:28 → 11:45:43`, `11:59:34 → 12:59:34`). And the fix for it killed the next run: `$(grep … \| tail -1)` exits 1 under `pipefail` on the first poll, and the EXIT trap stopped an A100 | read `colab log -s <session>` before blaming the chain; the unit of work is a session; a test now runs that shell line under the script's own options — M1 |
| Guards that read source fired on prose describing the absence they check for — four times | a guard reads the code, not the file |
| `grep -c` prints its zero and exits 1; a weights rescue skipped itself and cost an adapter | `weights_in()` |

## 5. Related work, read and not run **[read]**

- **Skill-to-LoRA** (arXiv 2606.16769): a `SKILL.md` turned into a per-skill LoRA on
  Qwen3.6-27B. 59 / 54 / 65 of 210 for no skill / full text / adapter — the sign of P61,
  with an effect inside the noise ($z = 1.19$ and $0.65$, unpaired, no seeds). A shared
  LoRA across skills hurts. Its self-distillation does not transfer to a base whose
  base + document teacher makes zero tool calls (P61).
- **Adaptive Minds** (arXiv 2510.15416): the base model reads adapter metadata and names
  the member. Keyword routing falls from 48.3 % at 5 adapters to 31.7 % at 30 — the
  predictable failure of a dictionary as a pool grows, and the reason milestone 2 exists.
  It routes by topical fit and defaults to a general adapter; here a measured table decides
  what is served locally and the default is the frontier.
- **vLLM**: multi-LoRA over one base and tree attention ship; a LoRA-adapted drafter for
  speculative decoding is an RFC (#52038). A drafting head trained on the target's hidden
  states exists for the 32B and beats any of this at latency — which is why acceptance here
  was never a speed claim.
