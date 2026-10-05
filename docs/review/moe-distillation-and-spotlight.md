# Two outside proposals, read against what this repository has measured: an MoE base with distillation, and Spotlight Memory

**Written 2026-10-04 at the user's request.** It is an analysis and a plan, not a result. Nothing below has run yet,
unless a claim names a run. The two sources are treated as hypotheses: a design note pasted by the user, and Percepta's
post *Spotlight Memory* (2026-10-02, [read] at <https://www.percepta.ai/blog/spotlight-memory>). A claim taken from
either is marked **[read: source]** and is not repeated as a fact until a run here instantiates it.

## 1. What is already measured that bears on both

| fact | run |
|---|---|
| On W9's generated wiki, a 12B member ties the E4B member (9/40 vs 10/40); once taught, the E4B alone does 37/40 | B3, B5 **[ran]** |
| Untrained on real documents under the served runtime, the 12B loses to the E4B, 11/44 vs 21/44 (2 : 12) | PAIR0 **[ran]** |
| Trained on the same real-document corpus, the 12B member ties the E4B member, 33/44 vs 34/44 (5 : 6) | PAIR1 **[ran]** |
| The two members err on different rows; when both agree, wrong answers delivered fall from 9 to 3 (one seen set, post-hoc) | PAIR1 note **[ran]**, hypothesis |
| Speculative decoding with the LoRA preserves the member's output up to every stop at 1.98× | F0c **[ran]** |
| A whole-request embedding cannot separate who writes from what is asked; unseen senders are lost 120/120 | M2b **[ran]** |
| A router that factors task from content passes: 0 of 600 foreign texts served locally, 0 of 480 legitimate requests lost | ROUTE0 **[ran]** |
| Open-task members are routed by the role in the token, and abstain through their corpus, now in all three organisations measured — school, distributor (M10), tracker | F2, M10, ROUTE1 **[ran]** `results/ROUTE1-tracker-abstain-20261003/BRIEF.md` |
| A page shown as the question's best 8 statements; an operational memory read as one constant line | PAGE0, H3 **[ran]** |
| `gemma-4-26B-A4B-it`: 30 layers, 128 experts per layer, 8 active; 15.37 GB in 4 bits; the domain concentrates its routing strongly (80 % of decode activations in 17–21 % of experts; a domain-pinned cache at 8 GB reads 93 % fewer bytes per token than LRU) | H1A **[ran]** `results/H1A-moe-routing-by-domain-20261004/BRIEF.md`; [`flash-inference/00-analysis.md`](../flash-inference/00-analysis.md) |
| New members are trained on Gemma 4 E4B | the user's decision, 2026-09-25 (CLAUDE.md §0) |

The facts in this table constrain every proposal below. The most important is this: **in the regions this project has, a larger
model has not bought accuracy, trained or untrained.** Any proposal whose return rests on a stronger teacher or base has to
show that headroom first, before anything is built for it.

## 2. The MoE proposal, point by point

### 2.0 Two routers, two granularities — agreed

An MoE's router picks feed-forward experts **per token and per layer**. An expert is an FFN inside one layer, with no
attention of its own and no meaning outside its stack. **[read: source]**, and consistent with the 26B's configuration
above. This repository's router picks a member **per request**. The source's conclusion holds, and it is the one this
design already acts on: an MoE expert cannot be extracted as a specialist, and one router cannot be distilled into the
other. **Nothing to implement; the distinction goes into the vocabulary.**

### 2.1 A router distilled into a probe on the base's hidden state — test first, and only for the gap that is left

**Claim [read: source]:** a linear probe or a small MLP on an intermediate layer's hidden state, labelled offline by a
teacher that runs each candidate adapter and keeps the one a verifier (or the loss) prefers. Routing then costs almost
nothing (X-LoRA, LoRA-Switch, MoLE).

**What our data says.** The routing problem the probe solves is already solved here in the two forms the system uses. For
fixed-task members, ROUTE0 factors task from content with no model and passes. For open-task members, the role names the
member and the member abstains. What remains open is narrower:
- **paraphrases** of a member's task, which ROUTE0 sends out by design (B3: 0/120 kept local);
- requests that arrive **without a role**.

There is also a warning in M2b. A representation of the *whole* request — an embedding, or very likely a mid-layer hidden
state too — places "the member's content plus another task" exactly where "an unseen sender plus the member's task"
sits. A probe trained without hard negatives of both kinds would learn the content.

**What a probe has that M2b did not:** supervision. The labels can come from our own verifiers: the citation gate
(GATE0) and each region's grader.

**Verdict: tested, cheapest first — the line stops at step 1.**
1. **P2a — headroom [ran]** `results/P2A-paraphrase-headroom-20261004/BRIEF.md`. Verdict **PARAPHRASES COST**:
   `email-full` on email ties (469 → 470) and `desk-commitment` on the shallow desk band ties (240 → 240), but the deep
   band regresses, 239 → 198 (1:42) — a paired loss on 4 of 16 rewordings of its compound rule ("the latest commitment
   counts"). Read where it happens: the members follow a reworded *question*, not reliably a reworded *rule* attached to
   one. A probe that kept every paraphrase local would serve the deep band's four rewordings wrong.
2. **ROUTE2 — not built.** P2a's regression on the deep band is enough to stop the line (the verdict table above requires
   every suite of both members to hold): a probe cannot tell which wordings a member follows, so it cannot be trusted to
   keep the unsafe ones local. ROUTE0's literal rule — off-wording leaves — stays the router for fixed-task members.

### 2.2 Distillation of specialists, 26B → a LoRA on the E4B — gated on a headroom the project has not seen, and the gating run is closed

**Claim [read: source]:** the 26B, with or without a LoRA, is the teacher. Each E4B adapter learns from its logits,
ideally on-policy (GKD, MiniLLM). The family shares a tokenizer. B2 **[ran]** confirms one id space for the E4B and the
12B; the 26B is not yet checked.

**What our data says.** Distillation transfers what the teacher knows and the student does not. Here the student
*trained on oracle walks* has matched every larger model measured (B3, PAIR1). The supervision our corpora give is
already exact: verified walks, a cited statement, a grade. Soft targets add information where the hard target is noisy
or underspecified. They add little where it is a verified walk. **Distillation has no teacher until a larger model is
shown to beat the E4B member.**

**Verdict: one headroom run was to decide it — it ran 2026-10-04, was blocked by the serving engine, and is closed
without a result by the user's decision of 2026-10-05.** In **TEACH0**, `gemma-4-26B-A4B-it`
runs untrained under the served runtime, with `--empty-thought` (PAIR0's lesson for Gemma 4's larger models). It is
compared against the bare E4B and against `real-none-s0`, on PAGE0's 52 rows. It needs one A100 session. The 26B does
not fit an A100 in bf16, so it runs in FP8 or 4 bits; that is a second unknown, and it is said.
- **Status 2026-10-05: CLOSED by the user's decision — blocked by the serving engine, no result [ran]**
  (`results/TEACH0-26b-headroom-20261004/BRIEF.md`). FP8 failed twice on the A100 (inductor compile; then vLLM's FP8
  kernel does not run on sm80); the A100 was refused three times (quota); the same bitsandbytes 4-bit run on an L4
  (attempt 4, a declared provider change) reached a server that refused the configuration: **vLLM 0.30 has no
  `bitsandbytes` quantisation method.** The brief's one allowed retry is spent. Nothing is read from TEACH0: whether
  the 26B is a teacher stays unanswered by this instrument. What vLLM 0.30 does list (`experts_int8`, about 29 GB, an
  A100 40 GB; or a pre-quantised AWQ/GPTQ checkpoint) would be a new instrument under its own brief, and none was
  opened.
- **The question moves.** "Is there a teacher?" is now asked on an external verifier, in the τ²-bench line: T1 compares
  Gemma 4 31B (self-hosted, Apache 2.0) with the E4B base on τ² airline test, k = 4, gate: a gap
  (`results/TAU2-T0-recon-20261005/BRIEF.md`, `docs/tau2/RECON.md` §3). The user's decision of 2026-10-05 closes the 26B
  line: PAIR0, PAIR1 and Google's own card put the large half level with or behind the small one **[read]**: τ²
  (average over 3) 68.2 % for the 26B-A4B against 69.0 % for the 12B and 76.9 % for the 31B
  (`docs/tau2/TEACHER-TERMS.md` §2.1; self-reported by the card).
- ~~**Kill:** the 26B does not beat `real-none-s0` (34/44), paired, $p \lt 0.05$. Then no distillation is built, and the
  26B is not proposed as a base.~~ Never evaluated: the run was blocked. By the closing decision, no distillation is built
  on the 26B and it is not proposed as a base.
- ~~**Pass:** a distillation pilot, under its own brief. GKD on one region's corpus, the student against `real-none-s0`.~~
  Not reached. A distillation pilot would be opened by τ² T1 showing a teacher gap, under its own brief.

### 2.3 Pruning experts by domain (REAP), and "a specialist is a LoRA plus an expert mask" — research; its first step already exists

**Claim [read: source]:** domain calibration data shows which experts activate. The rest are pruned or masked; REAP
prunes keep quality in-domain. A member could be a LoRA plus an expert mask, swapped by changing the router's mask. The
source itself calls this unexplored territory.

**What our data says.** The measurement REAP starts from — per-domain expert activation statistics — is exactly the flash
line's **H1a**: does the domain concentrate the 26B's routing (entropy per layer, the experts covering 80 % of
activations, within-domain Jaccard against between-domain Jaccard)? The user approved resuming the flash line on
2026-10-04 and H1a ran. **Result [ran]** `results/H1A-moe-routing-by-domain-20261004/BRIEF.md`: **FALSIFIED as written**
on the gate's one absolute-margin clause (affinity must beat LRU by ≥ 10 points at 8 GB; LRU was already at 92.1 %, so
+10 points had no headroom — the instrument flagged `no_headroom` itself). The other two clauses pass easily, and the
substance is strong: 80 % of a domain's decode activations sit in 17–21 % of the experts (against 40 % on general
text), within-domain weighted Jaccard 0.49 against 0.26 between domains (120 : 0), and a domain-pinned cache reads
93 % fewer bytes per decode token than LRU at 8 GB (62.4 → 4.1 MB), winning on 60/60 prompts; the general-text control
runs the other way (affinity −6 points against LRU), so the gain is the domain's, not pinning's.

**Verdict:** the data REAP needs now exists and says the domain concentrates routing strongly. Masks plus LoRA
switching stay research behind this and H1b (does an attention-only adapter concentrate it further; the user's call,
not yet taken). They need their own benchmark and a serving engine with per-request expert masks, which vLLM does not
offer **[read]**.

### 2.4 The 26B as the base for every member — not now; it is the user's decision, and the evidence does not ask for it

**Claim [read: source]:** per-token compute is close to the E4B's (about 4B active), at 15–17 GB in 4 bits plus the KV
cache. It fits a "base in flash, adapters in RAM" design, and a stronger base usually beats any distillation.

**What our data says.**
- The decision is the user's (E4B, 2026-09-25).
- Size has not bought accuracy in any region measured (§1).
- On the 16 GB Mac, 15.37 GB of weights leave no room for the KV cache. The 12B was already tight there (MAC2 **[ran]**).
  The flash line is precisely the plan to make that fit, by keeping about 60 % of the experts cached.

**Verdict: not proposed.** ~~until TEACH0 passes~~ TEACH0 is closed without a result (§2.2) and the user closed the 26B
line on 2026-10-05, so the 26B as a base stays not proposed; a change of base would need a larger model to show value
first, which is what τ² T1 asks of the 31B.

**Two cautions in the source, adopted as rules for any MoE LoRA:**
- **Placement.** Attention and shared experts only, not routed experts. Phase 0 already proposes attention-only.
- **The router.** Freeze it, and measure routing entropy before and after training.

## 3. Spotlight Memory — the architecture cannot be adopted; three of its ideas can be tested on what exists

**What it is [read: source].** A sequence-mixing layer for pretraining. Keys and queries map to addresses in a 2D lattice of
cells. Each read or write touches a fixed 3×3 neighbourhood through a smooth bump kernel. Cells are DeltaNet states,
allocated on the first write. Memory grows with the context, and access costs a constant per token. Routing (2D) is
separated from content (high-dimensional). Updating a key replaces its value, so the stale-value rate on rewritten keys is
zero.

**Why it cannot be adopted here.** It is an architecture trained from scratch: 140M–670M models pretrained on FineWeb-Edu.
This project fine-tunes adapters on a fixed Gemma base and trains nothing from scratch. **No part of the layer can be added
to Gemma 4 E4B without pretraining.**

**What maps onto this project's memory, and how each can be tested:**

| Spotlight's property | this project's counterpart | status | the cheap test |
|---|---|---|---|
| memory grows, access per step is constant | the library and the operational memory grow; a turn reads one state line (H3) and a page shows 8 statements (PAGE0) | measured **[ran]** for access; growth not stressed | — |
| **separate routing from content** | ROUTE0 (task vs content); the library addresses by id and anchor, its content is the statement | measured **[ran]** for the router | — |
| **updating a key replaces its value — stale rate 0** (its "forgetting" MQAR variant) | an opmemory `put` overwrites a key; a library statement can be edited without retraining | **measured [ran]**: EDIT0, 17/17, 0 stale; PLAN milestone 7's arm 5, *edit without retraining*, passes | **EDIT0**, below |
| learned, low-dimensional addressing (2D suffices) | the radar's stage R1 (`MEMORY.md` §2.2): a learned projection to a small $d$, designed and not built; its brief tests $d$ = 64 | not built | after R1 exists, test $d \ll 64$ |
| recall at 16× the training length | not applicable: this design keeps the context short on purpose | — | — |

**EDIT0 — the edit test, Spotlight's overwrite property on our memory. Result [ran]** `results/EDIT0-edit-without-retraining-20261004/BRIEF.md`.
A copy of `knowledge/hazwaste-regs` was made with one number changed in each of 17 supporting statements of PAGE0's
rows (20 numbers total), and nothing else. `real-none-s0` was asked those rows under the served runtime; it has never
seen this library, so there was no retraining to undo.
- **EDITS HOLD: 17/17** rows answer the **new** value, each cited to the edited statement, **0** stale (bar was ≥ 16/17
  with at most 1 stale). Changing one number in a statement changed the answer, with no retraining.
- One L4 session, no training. It closes milestone 7's arm 5, open since 2026-09-19 — **it now passes.**

Beside it, at zero GPU: a test that an operational-memory `put` on an existing key makes the next `get` return the new value
and only it.

## 4. The plan, in order

Each step is pre-registered with a brief before it runs, buys the cheapest falsification first, and stops the line it
belongs to if it fails.

| step | what | cost | stops the line if |
|---|---|---|---|
| 1 | **EDIT0** — edit without retraining (Spotlight's overwrite property); opmemory overwrite test | one L4 · zero GPU | the member writes stale values: the memory is not where the knowledge lives |
| 2 | **P2a** — does a member answer paraphrases of its task? | one L4 | members fail paraphrases: they leave correctly, and no probe is built |
| 3 | **ROUTE2** — a router probe on the E4B's hidden state, with M2b's hard negatives, on fresh sets | one L4 + seconds | it loses ROUTE0's safety, or recovers no paraphrases |
| 4 | ~~**TEACH0** — does `gemma-4-26B-A4B-it` beat the E4B member untrained?~~ **closed 2026-10-05: blocked by the serving engine, no result** | one A100 (never ran) | no: no distillation, no 26B base |
| 5 | **H1a** — does the domain concentrate the 26B's routing? (the flash line's first step; the data REAP needs) | hours of one GPU | **only with the user's approval to resume the flash line** |
| — | deferred: distillation (after τ² T1 shows a teacher gap; was: after TEACH0), expert masks plus LoRA switching (after H1a/H1b), tiny-$d$ learned addressing (after R1) | — | — |
| — | not done: implementing Spotlight's layer (needs pretraining); extracting MoE experts as specialists (they are not specialists) | — | — |

**Status (2026-10-04).** Step 1 **EDIT0 passed** — 17/17 the new value, 0 stale (§3). Step 2 **P2a ran: PARAPHRASES
COST** — a paired regression on the deep desk band (239 → 198) stops the line; step 3 **ROUTE2 is not built** (§2.1).
Step 4 **TEACH0 is closed (2026-10-05, the user's decision)**: blocked by the serving engine, no result (FP8 failed
on the A100's sm80; vLLM 0.30 has no `bitsandbytes`; the one retry is spent) — §2.2 and §2.4 stay "not proposed", and
the "is there a teacher?" question moves to τ² T1 (`docs/tau2/RECON.md`). Step 5 **H1a ran:
FALSIFIED as written** on its one no-headroom clause, but the substance it was for — does the domain concentrate
routing — holds strongly (§2.3); H1b and the flash line's next step are the user's call.

**Decisions that are the user's:**
- whether to resume the flash line (step 5);
- any change of base, which would follow only a larger model that shows value (τ² T1 on the 31B; TEACH0 is closed).
