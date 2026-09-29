# The workflow harness — a member that knows the workflow, the tools and the keys (design for review, 2026-09-29)

*The user's idea, 2026-09-29. **Status, 2026-09-29: approved and built.** The user approved all four §6 decisions as
proposed; the memory (`examples/common/opmemory.py`) and its TOML workflows (`examples/<org>/workflows/*.toml`) are
built and tested at zero GPU. MT0 (`results/MT0-multiturn-baseline-20260929`) has run — headroom, 43/54 dependent
turns with the conversation against 4/54 without — and so has C1 (`results/C1-concurrency-20260929`, no material
contention, four members mixed keep 1.03× one at 16 sessions). H1 (`results/H1-workflow-harness-20260929`), the
harness's own scoring, **has a result, read two ways: `harness` 53/54 dependent turns, PASSED against its
own bar; `harness-noblock` 0/60, FALSIFIED. The run's own gate voids it as written, and the user's
decision (2026-09-29): the per-arm reading stands, the as-written VOID kept as the record of that
instrument error — §8.***

## 1. The idea, in the user's words and in ours

> For a domain or subdomain, the reference to an action and the way to perform it can be inferred when the action
> belongs only to that domain: "run the next step" in a domain with a state machine, a current state and a few context
> variables makes the next step and its tool obvious. […] Keep context values in a cache under keys the LoRA knows,
> write and read them by key, so the model finally operates on a summarised context that states steps. It knows the
> workflows, where the context components are, and in which step of the workflow each is used. […] Without reloading
> the LLM's context, all thanks to the LoRA.

Put as a mechanism: a member learns **three things in its weights**:
- the domain's **workflows**, as state machines;
- its **tools** and how each is called;
- the **keys** under which a session's context lives.

Per turn the model then reads a **compact context**: the role, the current state and the names of the keys that hold
values, not the values. The model decides the step, reads (`get`) and writes (`put`) the values it needs by key, and
calls the tool. The prompt stays the same size as the conversation grows. The values stay in a cache the gateway keeps,
out of the model's context until the step that needs them.

## 2. What it builds on, already measured

| piece | where it stands | run |
|---|---|---|
| **key-addressed reading** | the wiki member reads values by key (`<open>id§anchor</open>`) and cites them: 35/40 against 0/40 untrained | W9 **[ran]** |
| the value lives outside the weights | edit a statement after training → 37/38 answers follow it; the weights held 1/40 | W7 **[ran]** |
| the member knows its tools | a corpus with the role's tool block teaches the calls; an unknown tool surface breaks it | P59, E5 **[ran]** |
| context costs latency | a 7,205-token block after the request: TTFT 0.10 → 1.70 s | E5 **[ran]** |
| a member learns a new behaviour on top | 70 abstention turns: 20/20, 0 of 70 lost | M10 **[ran]** |
| the loop that runs calls | `run_chain`: generate to a closing tag, call, inject `= result`, continue | W2 **[ran]** |
| why `harness.lora` was parked | a separate protocol adapter composed with a domain one could not be measured cleanly | P9, P13 **[ran]** |

The design keeps the harness **inside each member**: one corpus teaches the domain's workflow, its tools and its keys. So
it never meets the composition problem that parked `harness.lora`.

## 3. The design

### 3.1 Two verbs beside the domain's tools

```
<get>order</get>= 41
<put>order=41</put>= stored
```

`get` returns the value under a key, or `ERROR: no key order`. `put` stores one. They are served by the same tool layer as
the domain's tools, so a tenant boundary holds: a session's cache is keyed by user and organisation, and nothing crosses.

### 3.2 The compact context

What the gateway renders on each turn, instead of the conversation:

```
[system] the role's prompt (unchanged)
[user]   state: receiving/assigned · keys: order, dock
         Move it to dock 5.
```

The keys are listed without their values, which stay in the cache. There is no history and, in one arm, **no tool
block**: the member knows its tools because its corpus taught them (§4).

### 3.3 The state machine, declared, not neural — TOML, not YAML **[ran]**

One file per workflow (`examples/distributor/workflows/receiving.toml`), loaded by the gateway. This is the FSM the thesis
review proposed (`00-thesis-review.md` §4), now with a job. **Built as TOML, not YAML** (§6 decision 4): `tomllib` is in
the standard library, so the format adds no dependency.

```toml
[workflow]
name = "receiving"
initial = "start"
keys = ["order", "dock"]
[states.start]
on = { dock_assign = "assigned", dock_status = "start" }
[states.assigned]
on = { dock_assign = "assigned", dock_status = "assigned" }
```

The gateway advances the state from the calls the tool layer ran. The model never sets it, and only reads it in the
context line.

### 3.4 A step, end to end

Turn 2 of a receiving session ("move it to dock 5"), under the harness:

```
state: receiving/assigned · keys: order, dock
Move it to dock 5.
<get>order</get>= 41
<dock_assign>order_id=41; dock_number=5</dock_assign>= assigned order #41 to dock 5 (#9)
<put>dock=5</put>= stored
Done: assigned order #41 to dock 5.
```

## 4. The corpus

- MT0's generator (`generate_sessions.py`) already has 300 training sessions with gold calls. Each turn is rendered in the
  harness format by an oracle that writes the `get`s the step needs, the call and the `put`s of what later steps use.
- M10's single-turn corpus stays in, byte for byte: one unknown is added, and the member's single-turn job is kept.
- A gate at zero GPU, as for every corpus:
  - every oracle trajectory passes through the gateway with the cache;
  - no evaluation wording in training;
  - no shared world;
  - no dependent turn solvable from its own request.

## 5. The measurement (H1), pre-registered once this design is approved

Arms, on MT0's 60 held-out sessions:
- `history` (MT0's naive arm);
- `harness` (compact context + cache, the tool block kept);
- `harness-noblock` (the same, without the tool block).

| condition | bar |
|---|---|
| dependent turns right, `harness` against `history` | not worse by more than 3 of 54 (paired) |
| prompt tokens on turn 3 against turn 1, `harness` | $\bar p_3 \le 1.1\ \bar p_1$: flat, where `history` grows |
| first turns | ≥ 90 % in every arm, or the arm is void |
| cache operations | every `get` that the right call depends on resolves to the right value, checked in the tool layer's record |

`harness-noblock` answers the second half of the idea: that the member knows its tools well enough that they need not be
described. Tokens fall further. It passes if it loses no more than 3 of the dependent turns to `harness`.

## 6. Decisions for the user — approved 2026-09-29, all four as proposed

1. **Who writes the cache.** (a) The model, with `put`, as the idea says: the LoRA knows the keys. (b) The gateway, which
   stores each call's entities under conventional keys, so the model only `get`s. **Approved: (a)**, with (b) kept as the
   fallback if `put`s turn out unreliable.
2. **The tool block.** Keep it in `harness` and remove it in `harness-noblock`. **Approved**, both arms run in H1.
   **How this reads after H1 (§8):** the decision itself held — both arms ran, as approved — but the corpus behind
   `harness-noblock` did not give the second half of the idea a fair test: every training row had the block, so the
   member never learned to work without it, and removing it at evaluation time produced a collapse (0/60) rather than
   a measurement of whether the tools were known well enough to go undescribed. The decision to run both arms stands;
   what needs revisiting is the corpus for `harness-noblock`, not the arm.
3. **The domain.** The distributor's six roles, where MT0 runs. **Approved: distributor first**; the school follows if H1
   passes.
4. **The workflows.** ~~Declared in YAML~~ **declared in TOML** (§3.3) — approved because `tomllib` is in the standard
   library and YAML is not: one file per role, with two or three states each at first, exactly as built
   (`examples/distributor/workflows/*.toml`).

## 7. Order

~~MT0 (running) → this review → corpus and its gate (zero GPU) → training (one L4) → H1 scoring (one L4) → if it
passes, the live demo with OpenClaw on the user's machine, multi-turn.~~

**As run, 2026-09-29:** MT0 **[ran]** (headroom: 43/54 dependent turns with the conversation, 4/54 without) → this
review, approved → corpus and its gate, zero GPU, passed → training, one L4 (`wf-s0`) → **C1 [ran]** (concurrency,
bought the same day on the same kind of L4 session, needing no training of its own: four members mixed cost no
throughput against one, 1.03× at 16 sessions, 504 tok/s at 32) → **H1 scored, one L4 — result in, read two ways,
resolved: the user's decision (2026-09-29), the per-arm reading stands** (§8) → **H2 built and scored the same
day** on the team tracker (`examples/tracker/`), `training/harness/accept_rank.py`'s stop-sequence fix required
first (attempt 1 void on a vLLM transport error, not a scoring one) — result in, as written FALSIFIED, **the
user's decision (2026-09-29): reading 1, the harness PASSED on the readable conditions** (§9) → two corrections
read afterwards in H2's records (the block-less "learned in part" reading was a corpus aliasing bug; the QA
final-comment miss is one eval phrasing) → **H3 pre-registered and running** on a second tracker corpus that
fixes both, `tr-s1` against `tr-s0` on a fresh held-out suite
([`../../results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md))
→ the live demo with OpenClaw on the user's machine, multi-turn, still
waits, now on H3's result.

**Next, running.** H2 ran on a second domain, built to let sessions run long enough for the token saving
to show: **the team tracker** (`examples/tracker/`, built and scored 2026-09-29) — a Jira + Confluence-like tool,
explicit longer workflows (To Do → In Progress → In Review → QA → Done for stories, Triage for bugs), natural keys
such as `RD-123`/`HW-123`, and Confluence-shaped pages read by `page` or `page#anchor` as the library. Synthetic
worlds only, as everywhere here. Result, both readings, and the user's decision: §9. **H3**, its successor,
trains `tr-s1` on a second corpus that fixes H2's two corrections and measures it against `tr-s0` on a fresh
held-out suite — pre-registered and running, no result yet
([`../../results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).

## 8. Result (H1)

![Two panels. Left, the conversation in the prompt: a scroll growing turn after turn and a claim form whose order field is empty, 43 of 54. Right, the keys in a memory: one index card with the state and the key names, a drawer opened on order 58, and the claim form filled with it, 53 of 54. Title: carry the keys, not the conversation.](../img/operational-memory.png)

*H1: fetching a value by key fixes what reading the history lost — the claim now names the order.*

`results/H1-workflow-harness-20260929/`, on vLLM (one L4), against MT0's `history` baseline on the same 60 held-out
distributor sessions (124 turns, 54 dependent):

| arm | dependent turns | first turns | prompt tokens (turns 1/2/3) | cache fetches right | reading |
|---|---|---|---|---|---|
| `history` (MT0's baseline) | 43/54 | — | 345/428/394 (grows) | — | — |
| `harness` (tool block kept) | **53/54** | — | 745/726/710 (flat) | 53/53 | **PASSED** against §5's bar (not worse than `history` by more than 3 of 54) |
| `harness-noblock` (no tool block) | **0/60** | under 90 % | — | — | **FALSIFIED** against §5's bar |

**What worked — the claims.** `harness` loses 1 of `history`'s 43 right dependent turns and gains 11 `history` got
wrong, net 53/54. The gain concentrates exactly where §5 predicted it would: customer-service claims about "that
order" — the case `history` filed with no order number 8 of 10 times — go **10/10** under `harness`, because the
claim now names the order the member fetched by key rather than one it read out of free text. Dispatch, the other
weak spot, is 14/14. Every one of the 53 right dependent turns fetched its value by key, checked in the tool layer's
record (53/53) — the fourth bar in §5, passed without qualification.

**What failed — `harness-noblock`, and why.** `harness-noblock` answers 0 of 60 sessions' first turns correctly,
which void the arm under §5's own rule before the 54 dependent turns are even scored. The member calls no tool and
states data it never read. The cause is not that the idea is wrong — that a member can know its tools well enough
to go undescribed — but that **its corpus never gave it the chance to learn that**: every training row, in both the
harness corpus and the M10 single-turn rows carried through byte for byte, rendered the tool block. Removing the
block only at evaluation time asks the member to generalise to a prompt shape it never saw once in training. The
fix is a corpus design question, not a re-run: **the next corpus for this arm should drop the block in part of its
training rows**, so the member has actually been shown sessions without it before it is scored on one.

**The token caveat.** `harness`'s prompt is flat across turns (745 → 726 → 710) where `history`'s grows (345 → 428
→ 394) — §5's third bar, passed. But on these short (2–3 turn) sessions the harness spends roughly **2× the
per-turn tokens** of a plain reply: a `get` → call → `put` → answer cycle costs more generation steps than history's
single answer. Prefix caching would likely reuse most of the repeated system and tool material across those steps —
**not measured here**. The token *advantage* the design is built for belongs to sessions long enough that a growing
conversation would otherwise dominate the prompt, which these are not.

**The verdict, read two ways.** §5 pre-registered a rule — first turns ≥ 90 % in every arm, or the arm is void —
written to catch an arm that cannot even do the easy part. Applied literally *across* arms rather than *within*
each one, that same rule lets `harness-noblock`'s collapse (0 % first turns) void the entire H1 run, `harness`
included, which is an instrument design error: the gate was meant to disqualify a broken arm, not a working one
sitting beside it. **As written, H1 is VOID.** Read per arm instead — which is how the bars in §5 were stated,
each against its own numbers — `harness` **PASSED** every one of its four bars and `harness-noblock` **FALSIFIED**
on the first. The code that applies the gate has not been changed after seeing this result. **The user's decision
(2026-09-29): the per-arm reading stands — `harness` PASSED, `harness-noblock` FALSIFIED — and the as-written
VOID is kept in this document as the record of that instrument error, not as the verdict. From H2 on, VOID is
applied per arm.**

**How §6 decision 2 now reads.** The decision to run both arms was correct — it is exactly what surfaced the corpus
gap above — but decision 2 did not anticipate that `harness-noblock`'s corpus would need to *teach* the
no-block condition, not merely omit the block at test time. See §6 decision 2 for the update in place.

**Next step.** With the per-arm reading chosen: **H2**, the Jira + Confluence-like team tracker
(`examples/tracker/`), where sessions run long enough for `harness`'s flat-prompt property to actually hold
across five turns rather than the two or three measured here. Built and scored the same day; result in §9.

## 9. Result (H2)

`results/H2-tracker-harness-20260929/`, on vLLM (one L4), on 60 held-out long tracker sessions (160 dependent
turns, 60 first turns, 60 independent turns):

| arm | first turns | dependent turns | independent turns | prompt tokens (turns 1–5) | reading |
|---|---|---|---|---|---|
| `base-history` (bare Gemma 4 E4B, conversation in the prompt) | 44/60 (< 90 %) | 4/160 | — | — | void by the first-turns rule; the pre-registered "beats `base-history`" comparison is unreadable |
| `harness` (`tr-s0` + operational memory + workflow) | **60/60** | **146/160 (91.3 %)** | 50/60 | 1613/1223/1011/1149/1274 (flat: $\bar p_5 \le 1.1\ \bar p_1$ holds) | reads ≥ its own 90 % bar, on the readable conditions |
| `harness-noblock` (tool block removed at serving) | 40/60 (< 90 %) | 80/160 | — | — | void by the same rule; a corpus aliasing bug, not partial learning — QA lane whole, lead/developer lanes missing |

**As written, H2 is FALSIFIED — not VOID, and the difference is the point.** §5's stopping rule was rewritten
after H1, on the user's own instruction (§8: "from H2 on, VOID is applied per arm"), precisely so one arm's
failure could not erase the other two's real result. It did that: `harness`'s own 146/160 is read on its own
terms, not voided by `base-history`'s collapse. But the rule then did something its author had not anticipated a
**second** time: **applying the same per-arm VOID to an *untrained* baseline throws away the comparison that
baseline exists to provide.** `base-history` is bare Gemma 4 E4B, never trained on the tracker's workflows or
tools, reading the raw conversation; its first-turn accuracy (44/60) is not a broken instrument — it **is** the
headroom `harness` is measured against. It gets `issue_get` right (40/40, a lookup the conversation already
states) and almost nothing that needs more than reading the last message back (`issue_create` 4/20, every
transition 0/40, every page read 0/60). Voiding it as though it were a failed trained arm makes the
pre-registered claim "`harness` beats `base-history`" unreadable — `None`, by the scoring code — and an
unreadable pre-registered claim is what the code reports as **FALSIFIED**. **The lesson: the per-arm first-turns
VOID rule applies to trained members, not to an untrained baseline whose failure IS the headroom.**

**Descriptively — paired on the same 160 dependent turns, arm void: 142 : 0 favouring `harness`, exact two-sided
sign test $p \lt  10^{-40}$.** This is not a substitute for the pre-registered verdict — a readable comparison
between two scored arms is exactly what the void takes away — but it is the same 160 turns, scored the same
way, stated here rather than hidden because it is inconvenient to the as-written result.

**`harness-noblock`'s 80/160 was read as "learned in part"; it was a corpus aliasing bug, not partial
learning.** `--harness-corpus` chose its block-less third by `j % 3 == 2`, and roles rotate by the same `% 3` —
**all 400 block-less training rows were QA's.** The member did not learn block-less partially: it learned it
exactly the role it was shown — QA's lane whole (80/80 block-less), the lead's lane never shown (0/20 except
`sprint_board`, a call with no argument), the developer's lane likewise 0/20. Two moduli sharing a period alias
unless checked; read afterwards in `gate_harness.json`'s `rows_without_tool_block_by_kind`. This corpus, unlike
H1's, put some training rows through without the block — the aliasing bug is in *which* rows, not in whether any
were.

**Where `harness` misses, all QA.** (a) The 14 dependent misses are one turn, QA's final comment, 6 of 20: the member re-reads the issue instead of commenting, or attempts a transition the workflow refuses (`done → in_review`). A real miss, on one eval phrasing: *"Note on it: …"* 1/15 against *"Put a comment on it: …"* 5/5. (b) Among the independent turns (50/60), "Where must tests pass?" reads the whole `definition-of-done` page instead of citing `#tests`, 10 of 20 times — the statement is inside what it read, so a check for the anchor can fail while the capability that matters (finding the right fact) works: **this is measuring phrasing**, recorded here rather than loosened.

**Tokens.** `harness` reads roughly **2.5×** `base-history`'s tokens per turn — more generation steps plus the
rendered block — and `base-history` is flat too, for the opposite reason: it writes almost nothing to carry
forward, so there is little for the conversation to grow by.

**Attempt 1 was void on a transport error, not a scoring one.** vLLM 0.30 refuses any request carrying more
than four stop sequences (HTTP 400); the tracker's tool surface closes more than four distinct tags, so every
turn of the first attempt failed in transit (`h2_attempt1_void_http400.json`). The fix, in
`training/harness/accept_rank.py` (`MAX_STOPS = 4`): past that many closing tags the request sends one generic
stop, `"</"`, and `close_open_tag` rebuilds the specific tag from what the text was left inside of — the same
function llama.cpp needed for a different reason (`docs/MECHANISMS.md` §3, §15). The resume path now replays
any session that hit a transport error, and the reading guards against crediting an arm with no scored turn.

**The user's decision, 2026-09-29, as it was for H1: reading 1.** H2's verdict is the readable conditions —
`harness` **PASSED**, 146/160 ≥ its 90 % bar, flat prompt across five turns, the descriptive 142 : 0 pairing.
FALSIFIED-as-written stays on record with both instrument errors on this page (the per-arm VOID asked of an
untrained baseline, and the anchor check that measured phrasing). Not rerun: no rule change could move
`base-history` off 4/160.

**Two corrections read afterwards in H2's records [ran] (no number above changes):** the block-less "learned in
part" reading was a corpus aliasing bug (above), and QA's final-comment miss is one eval phrasing (above). Both
are what H3 trains against.

**H3 is pre-registered and running.** `tr-s1`, trained on a second tracker corpus that widens the training
wording by two phrasings per turn in every role and gives each role an even block-less third, measured against
`tr-s0` — our own previous member, not the bare base — on a fresh held-out suite (new worlds, wording neither
training nor H2's eval used). Scorer `turn_right_h3` fixed before the run (a page#anchor turn is right when a
page read returned the statement). Bars: H3a needs `s1-harness` ≥ 90 % dependent, a paired improvement over
`s0-harness` (exact sign test, $p \lt 0.05$), losing ≤ 3 turns, and flat tokens — unless `s0-harness` already sits
at ≥ 95 % on the fresh suite, in which case H3a is reported as NO HEADROOM. H3b needs `s1-noblock` to lose ≤ 8
dependent turns to `s1-harness`, by role. No result yet:
[`../../results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../../results/H3-tracker-corpus-v2-20260929/BRIEF.md).
