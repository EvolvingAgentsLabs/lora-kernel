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

**Position, 2026-09-28.** The reference organisation named above is built for **both** halves of the
diagram — the school and the distributor — and both have run live end to end through the real
OpenClaw (LIVE, LIVE-distributor, M8–M10, all **[ran]**); the distributor's member now abstains to the
frontier on what its corpus does not cover (M10 **[ran]**). ~~Speculative decoding — named, not
bought~~: bought since, on Gemma 4 E4B/12B, both on the server profile (C0, C0-upper, F0, F0b, all
**[ran]**, Colab) and on the user's own machine (MAC, MAC2 **[ran]**) — it pays on an L4/A100 and does
not on the Air, so **edge serving is llama.cpp on the user's own machine (the user's decision), not the
speculative pair**; the pair stays a Colab-side gain (§2). The adversarial **0-leaks** suite fixed above
as step 4's falsifier has **not** been run.

**Position, 2026-09-29.** Multi-turn conversation was the one edge of the reference diagram not yet
exercised: the gateway reads only the last request, so a reference to an earlier turn has no referent.
**MT0 [ran]** measured the naive fix — the conversation in the prompt — against it: HEADROOM, at the
edge (43/54 dependent turns resolved, against 4/54 without; a reference copied into an argument
resolves, one written into free text does not — a claim about "that order" filed with no order number,
8 of 10). **C1 [ran]** closed the concurrency question this raised: one L4 serves four members mixed
with no material contention (1.03× one adapter's throughput at 16 sessions, 504 tok/s and p95 TTFT
0.24 s at 32), superseding E5's single-burst 0.88. The user's answer to MT0's failure is not more
history in the prompt but a **workflow harness inside each member** — a domain's state machine, its
tools and the keys of a short-term operational memory, all learned in the weights, so the prompt reads
one context line instead of the growing conversation (`docs/review/harness-workflow-kv.md`, the user's
design). **H1 [ran]** (`results/H1-workflow-harness-20260929`): read per arm, `harness` **PASSES** — 53/54
dependent turns against `history`'s 43/54 (1 lost, 11 gained), every right one fetched its value by key,
prompt flat by turn — and `harness-noblock` **FALSIFIES**, 0/60. Read as written, the run is **VOID**:
the brief's "first turns ≥ 90 % in every arm or VOID" rule, applied across arms, lets the no-block arm
void the whole run — an instrument design error now recorded, not fixed after the fact. **The user's
decision (2026-09-29): the per-arm reading stands, the as-written VOID kept as the record of that
instrument error** (§5 History). ~~A second domain for the harness — a Jira/Confluence-like team
tracker, with the longer sessions where the token saving would show — is proposed as H2, not built.~~
**Built, and run, 2026-09-29 (H2 [ran], `results/H2-tracker-harness-20260929`):** on 60 held-out long
sessions (160 dependent turns) the harness reaches **146/160 (91.3 %)**, above the 90 % bar, flat over
five turns, and descriptively **142 : 0** paired against `base-history` on the same turns. **As
written, FALSIFIED**: `base-history`'s own first turns (44/60) trip the same per-arm VOID rule as a
broken treatment would, voiding the comparison — a second instance of H1's instrument error, a rule
meant to void a broken treatment voiding an untrained baseline instead. ~~Pending: the user has not
yet chosen between reading the conditions above (146/160 ≥ 90 %, flat, descriptive 142:0) as H2's
verdict, or keeping FALSIFIED-as-written and rerunning with the per-arm rule scoped to trained
members and the anchor check counting a page read that contains the statement.~~ **The user's
decision, 2026-09-29: reading 1.** H2's verdict is the readable conditions — the harness **PASSED**
(146/160 ≥ 90 %, flat, descriptive 142:0) — with FALSIFIED-as-written kept on record with its two
instrument errors (the per-arm VOID above, and the anchor check that measured phrasing). Not rerun: no
rule change could move `base-history` off 4/160. Two corrections read afterwards in H2's records
[ran]: `harness-noblock`'s 80/160 was first read as "learned in part" — a corpus bug, not partial
learning, since its block-less third was rendered by the same modulus (`% 3`) the roles rotate on, so
all 400 block-less rows were QA's; and QA's final-comment miss (6/20) is one eval phrasing ("Note on
it: …" 1/15 vs "Put a comment on it: …" 5/5). ~~H3 is pre-registered and running~~: **H3 [ran]
2026-09-29** — `tr-s1`, trained on a second tracker corpus that fixes both, beats `tr-s0` on a fresh
held-out suite: dependent 158/160 (98.8 %) against 147/160, paired 11:0, $p = 0.00098$, 0 lost, flat
— **H3a PASSED**; without the tool block, 156/160 (97.5 %) across every role, at about a third of the
prompt tokens per turn — **H3b PASSED**
([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).

## 1. The milestones

Arms are bought in sequence. The arm that can kill a milestone runs first; attribution
arms are bought only once there is an effect to attribute.

| # | milestone | depends on | gate | state |
|---|---|---|---|---|
| **1** | the pool on Qwen 3.x small | D2 ✅ | both members released on `Qwen3.5-4B`, each tying or beating its Qwen 2.5 release, paired | ✅ **[ran] 2026-09-19 — MOVED.** G1 `applied` on both full-recipe adapters; `email-full` **471/475 = its recorded 471**, tie 1 : 1; `desk-commitment` **240/240**, tie; `releases/*@v2.json`. Four sessions under an hour each ([`BRIEF`](../results/M1-pool-qwen35-20260919/BRIEF.md)) |
| **1b** | **the pool re-released on Gemma 4 E4B** | B1 ✅ | `email-full` and `desk-commitment` retrained on `google/gemma-4-E4B-it` from the same corpora and recipe, each tying or beating its `@v2` Qwen3.5-4B release on the same cases, paired; `@v3` manifests | **[ran] 2026-09-25 — NOT MOVED as a pool:** `email-full` ties its `@v2` (469 vs 471, 1 : 3) and beats the bare Gemma (119 : 0) → **`email-full@v3` on Gemma**; `desk-commitment` ties `@v2` and the bare Gemma alike (240/240, the ceiling) — no adapter needed there, stays `@v2` ([`BRIEF`](../results/M1b-pool-gemma4-20260925/BRIEF.md)). **2026-09-26: all moved** — `desk-commitment@v3` trained on both bands (M1d [ran], deep 239/240), `distributor-wiki@v2` (B5 [ran]) |
| **2** | the router as a tiny model of the corpora | the members' corpora | misrouted-to-local no higher than the dictionary's on prompts the dictionary was not written for; abstains on out-of-distribution text | **arm 1 [ran] 2026-09-19 — does not pass.** Foreign text, fresh sets: dictionary 59/128 served locally, n-gram router **0/128**; legitimate requests from unseen senders: dictionary loses 0/120, router loses **120/120**. ~~The dictionary stays~~ — **arm 4 [ran] 2026-10-02 — PASSES.** A factored router (task vs. member content) serves 0 of 600 foreign texts locally against the dictionary's 294, loses 0 of 480 legitimate requests (unseen senders, task-first, OpenClaw-wrapped); paraphrases leave by design (0/120, reported, never gated). It is now the proxy's default, `openai_proxy --router factored` ([`BRIEF`](../results/ROUTE0-factored-router-20261002/BRIEF.md)) |
| **3** | the large half of one pair | 1 | a LoRA on ~~`Qwen3.8-27B`~~ ~~`gemma-4-31B-it`~~ `gemma-4-12B-it` (family.LARGE) is applied when served; large + LoRA beats small + LoRA on the deep band, paired | ✅ **[ran] 2026-09-26, on `gemma-4-12B-it`: closed — the large buys no accuracy here.** B3: 12B + LoRA 9/40 vs E4B + LoRA 10/40, a tie, with neither corpus showing a comparison; B5: shown them, the E4B alone does 37/40 — no room ([`BRIEF`](../results/B5-comparison-corpus-20260926/BRIEF.md)). **PAIR0 [ran] 2026-10-02:** before training a 12B member for a new region (real documents, milestone 7), the same question asked of the bare bases under the served runtime — the 12B loses to the E4B, 11/44 vs 21/44 answerable, paired 2 : 12, $p = 0.013$ — no 12B member trained for that region either ([`BRIEF`](../results/PAIR0-large-headroom-20261002/BRIEF.md)) |
| **4** | the speculative pair | 3 | acceptance of small-LoRA drafts under large-LoRA verification exceeds acceptance under the bare large model | ✅ **[ran] 2026-09-26 — PASSED (B4):** α 0.871 → 0.898, 76 : 18 records, $p\lt 10^{-4}$; the gain is on the corpus's own distribution (0.855 → 0.914). ~~Wall-clock not measured~~ — **F0 [ran] 2026-09-27: speculative decoding running with a LoRA expert on the 12B, the native MTP drafter 1.74× on the expert's domain, 2.13× on general text.** **C0 [ran] 2026-09-27, A100 bf16: 1.92× on the domain (α 0.34), 2.40× general** (base 2.80×/2.60×) — the aligned E4B drafter did not run (OOM beside the 12B on an L4; no accepted quantization on the arms tried). **C0-upper [ran] 2026-09-27: confining the LoRA to the upper half of the layers gives back NONE of the drafter's lost acceptance** (ρ = −0.02; base α 0.82, full 0.44, upper-half 0.43) — that split is a lever for sharing lower KV (milestone 7 / E6), not for drafter alignment. **On the Mac (MAC2 [ran] 2026-09-27): llama.cpp's own MTP slows the 12B instead of speeding it** (0.52× on its domain, 0.66–0.87× otherwise), and the aligned pair does not fit 16 GB beside it — **the speculative pair stays a server-side (Colab, vLLM) result; edge serving is a separate, later track (§2)** ([`B4`](../results/B4-gemma4-pair-acceptance-20260926/BRIEF.md), [`F0`](../results/F0-spec-lora-12b-20260927/BRIEF.md), [`C0`](../results/C0-aligned-draft-20260927/BRIEF.md), [`C0-upper`](../results/C0-upper-e4b-20260927/BRIEF.md), [`MAC2`](../results/MAC2-llamacpp-20260927/BRIEF.md)). **PAIR0 [ran] 2026-10-02:** a second region (real documents) finds no accuracy case for the large half either (row above) — the speculative pair stays a speed result without a region that needs it ([`BRIEF`](../results/PAIR0-large-headroom-20261002/BRIEF.md)) |
| **5** | the first real region, by hand | 1, 2, a sandbox, keys rotated | the release gate, on a suite with a verifier nobody here generated | **region named 2026-09-19: nursing procedures and health-education material** (Open RN *Nursing Skills*, CC BY 4.0, first); headroom arm next, zero GPU |
| **6** | the service policy, with the bill | 2, 4, 5 | the local share saves more than it costs, on real traffic | 🔶 **first pass [ran] 2026-09-21, zero GPU:** the P41/P62 replay priced at real `gemini-3.8-flash` rates — today's actual frontier bill (90 fluids cases) **$0.18\ast \ast , avoided by keeping 150 email cases local \ast \ast$0.11**, ceiling if everything left **$0.30**. **The local GPU's own dollar cost is not priced** — the rental rate could not be fetched live; not guessed around |
| **7** | **a knowledge base per subdomain, and the trajectory through it as the harness** — on fluid mechanics, split into subdomains | 1; shares its embedding model with 2's arm 2; independent of 3–6, **runs next** | an expert trained to navigate and follow notes answers families it never trained on, where the same expert without the base is at 1/20 | 🔶 **W1–W4 built [ran]; W3's radar and W5's kill arm [ran] and not passed.** W5: the library arm 35/56 against the untrained base that reads at 45/56 (6 : 16, $p=0.052$), 35 : 2 over no-library — navigation transferred, reading a two-valued note did not. ~~Next is the user's call: composition, no training.~~ **2026-09-24: the library's unit becomes the atomic statement (user's design, `MEMORY.md` §1.6) — W9 [ran] 2026-09-25: PASSED**, both seeds beat the untrained base walking the evaluation world 35 : 0 on the 40-row headline, ties the base handed the oracle's statements. **The design carries the demo track built on top of it — the school and the distributor both run live end to end** (M8, M9, M10, LIVE, LIVE-school, LIVE-distributor, all **[ran]** through 2026-09-28), including a member that abstains to the frontier (M10) and edits a note without retraining (**W7 [ran] 2026-09-27**: 37/38 answers follow a patched statement, 0 stale). **Open:** arms 2–4 (the expert's own retrieval, attribution by kind of knowledge, retrieval strategy) are not yet run on the atomic-statement design; the 0-leaks adversarial suite named in the addendum below is not yet run. **2026-09-29:** the demo track's next step is the **workflow harness** — a state machine, tools and short-term-memory keys learned inside a member instead of composed as a separate adapter (the user's design, `docs/review/harness-workflow-kv.md`). MT0 **[ran]** found headroom for it (43/54 dependent turns resolved with history against 4/54 without, but free-text references lost 8/10); C1 **[ran]** cleared concurrency (four members on one L4, no material contention to 32 sessions). **H1 [ran]:** per arm, the harness **PASSES** (53/54 vs `history`'s 43/54, every right turn fetched by key, prompt flat) and `harness-noblock` **FALSIFIES** (0/60); read as written the run is **VOID** (the first-turns rule voids across arms — an instrument error, recorded). The user's decision (2026-09-29): the per-arm reading stands, the as-written VOID kept as the record of that instrument error. ~~A team-tracker domain is proposed as its next test (H2).~~ **Built and run, 2026-09-29: H2 [ran]** on 60 held-out long sessions (160 dependent turns) — harness **146/160 (91.3 %)**, flat prompt over five turns, descriptively 142 : 0 against `base-history`; **as written FALSIFIED**, because `base-history`'s own first turns (44/60) trip the same per-arm VOID rule as a broken treatment would, voiding the comparison — H1's instrument error recurring on an untrained baseline. ~~Pending the user's decision between the readable conditions and a rerun with the rule scoped to trained members.~~ **The user's decision, 2026-09-29: reading 1** — the readable conditions are H2's verdict, the harness **PASSED**; FALSIFIED-as-written stays on record with its two instrument errors. `harness-noblock` (80/160) is a corpus bug (a `% 3` aliasing between the block-less third and the role rotation), not partial learning. ~~H3 is pre-registered and running~~ **H3 [ran] 2026-09-29: PASSED both readings.** `tr-s1` (wording widened per turn in every role, an even block-less third of every role) beats `tr-s0` 158/160 against 147/160 on a fresh held-out suite, paired 11:0, $p = 0.00098$, 0 lost, flat — **H3a PASSED**; block-less now holds every role, 156/160, at about a third of the prompt tokens — **H3b PASSED**, closing the block-less-is-QA-only gap. Two new failure modes read where they happen: one miss is the note's own text read as a command; the block-less misses are one session's first-turn error cascading through the rest ([`results/H3-tracker-corpus-v2-20260929/BRIEF.md`](../results/H3-tracker-corpus-v2-20260929/BRIEF.md)). **Next, 2026-10-01:** REAL5 **[ran]** carries `real-none-s0` to a third, link-dense family (PARTIAL, 15/25, under the 70 % bar) — the strict citation on repeated values is the open item; H5 **[ran]** found the span-masked loss regresses a short-result member (its attribution arm 0 : 20) and narrowed the rule to where tool results are long. **REAL6 [ran]** trained one-hop repeated-value choices and left the citation unchanged (15/25 against 15/25, tie) — the remaining misses are multi-hop rows cited at the wrong end of a link, a shape that corpus never contained — **FALSIFIED**. ~~**REAL7 — pre-registered, running:** cross-link decoy walks (the answer at a link's end, a decoy with the same number at its start), training family extended with 49 CFR 390/392/393/397; verdict on REAL5's twin-free headline (21 rows, baseline 13/21), bar ≥ 15/21; no result yet.~~ **REAL7 [ran] FALSIFIED, 2026-10-01:** `real-link-s0` ties `real-none-s0` 13/21 on the twin-free headline (4:4 paired, $p=1.0$), under the ≥ 15/21 bar; headline 16/25 vs 15/25, value-right 22 vs 20, same-value miscitations 2 vs 2, refusals 5/5 both; the REAL4 guard was not bought (no effect, as the brief set it). Two corpus changes aimed at this citation (REAL6, REAL7) have now changed nothing — by the rule on counting redesigns this corpus line on the citation stops here. Measured level: `real-none-s0` with the runtime cites the supporting statement on 13/21 twin-free multi-hop rows of a third family (value right 20/25), refusals 5/5. Not bought: a runtime citation check that rejects a citation whose page the walk did not end on, on a fresh set. ~~**LIVE-library** (`examples/library/serve.py` + an OpenClaw driver) is built and tested offline; its first live try paused on the Mac, another session's `llama-server` holding ~8 GB — pending free GPU memory, not yet run.~~ **LIVE-library [ran], 2026-10-01: PASSED.** `real-none-s0` served `edge` (llama.cpp Q8_0 + LoRA GGUF f16, context 12,288 — 16,384 ran out of memory on the 16 GB Mac) through OpenClaw 2026.9.4, a fresh session per question, on REAL4's 52 questions, 22.5 minutes: 36/52 — headline 16/23, refusals 15/16, one-hop 5/13 — against REAL4 on vLLM bf16's 38/52 (16/23, 15/16, 7/13); headline and refusals match exactly. Every loss reads as the edge's: 4 walks overflowed the 12,288-token context after opening a ~7k-token page whole, one OpenClaw question timed out with no walk, three were re-sent wrapped in OpenClaw's own queued-message envelope. ~~Owed: strip that envelope before the runtime reads the question; a page budget so a long page fits a 12k context~~ ([`results/LIVE-library-20261001/BRIEF.md`](../results/LIVE-library-20261001/BRIEF.md)). **LIVE-library2 [ran], 2026-10-02: NO CHANGE.** Both owed items built: `examples/school/gateway.runtime_request` strips the envelope, and `memory.runtime.Conversation.page_budget` (served at 2,500 tokens by `examples/library/serve.py`) opens an over-budget page with its statements in BM25 order against the question until the budget, the rest left as openable anchors — only 29 CFR 1910.178 exceeds it on this library, offline-checked to keep the 8 statements REAL4's oracle walks need on it 8/8 from 1,500 to 3,500 before any walk ran. Same 52 questions: 37/52 — headline 16/23, refusals 14/16, one-hop 7/13 — against this run's 36/52 and REAL4 on vLLM's 38/52; 0 context overflows (4 before), 0 envelopes (3 before), paired against LIVE-library 3 : 2 ($p = 1.0$). Verdict as written: NO CHANGE — 0 overflows but 37 < 38, not REGRESSED (headline and refusals clear their bars, no paired loss). The three wins are exactly the rows the edge had cost; one new loss, `none-9`, is the budget putting a question's best-matching statement in view of a question the library cannot answer. ~~**Owed:** why OpenClaw holds a finished turn (3 rows, one of which stopped the run's part 1 until the driver was fixed to catch a timed-out turn and resume);~~ **Found and handled, 2026-10-02:** the three holds were node sitting inside `process.exit()` after a successful run (sampled; a V8 flag tried against the exit itself did not separate from chance, 0/12 vs 3/15 on a stub) — the endpoint's own answer, delay and format play no part. `live_library.run_turn` now runs each turn in its own process group and ends it `GRACE_S` (2 s) after OpenClaw's own run-ended line, or at the timeout, killing the group whole; verified on real OpenClaw against a model-less stub, 20 turns ~7 s each, 0 timeouts, 0 orphans (the old driver left exactly these as orphans for hours). `serve.py` also now always answers a walk that raises (`NO_ANSWER`, logged with its error) instead of closing the socket — what made OpenClaw re-send the turn as `[Queued user message …]`, which is where LIVE-library's own envelope rows and its 119 s no-walk row came from. ~~next is a runtime citation check on a fresh set, not more edge work~~ ([`results/LIVE-library2-20261002/BRIEF.md`](../results/LIVE-library2-20261002/BRIEF.md)). **CITE0 [ran], 2026-10-02: FALSIFIED.** That check, `cite_check` (reads only the referee's own record, never the answer), run on a fresh 52-row set over a third family (40 CFR 112, written blind after the design froze): baseline `withlib-s0+page` **32/52** (headline 18/30, one-hop 8/14, refusals 6/8) against `withlib-s0+page+check` **33/52** (19/30, 8/14, 6/8); the check fired on 6 rows, converted 0, broken 0 — told why a citation fails, a 4B member does not produce a better one. What it is, measured: a detector with no false alarm — every fired line was already wrong (6/6), and with LIVE-library2's offline replay, 15 fires, 0 on a right answer; its blind spot is REAL5–REAL7's, a statement holding the value asked but not the one meant (7 of the 20 remaining misses here). ~~**Next step, now that the hint has failed: the check as a gate** — a line that fails it is not delivered; the runtime says it could not verify a citation, or forwards to the frontier~~ ([`results/CITE0-runtime-check-20261002/BRIEF.md`](../results/CITE0-runtime-check-20261002/BRIEF.md)). **GATE0 [ran], 2026-10-02: GATE WORKS.** The same check as a hard gate (`memory.runtime.citation_problem`, `Conversation.final_problem`, `examples/library/serve.py --cite-gate`, off by default when this measurement ran, on by default since the user's 2026-10-02 decision below), replayed exactly — zero GPU — on 14 held-out `+page` arms of REAL3–REAL7 (532 walks with a final line, two libraries): right answers delivered **275/275** (0 blocked), not-right answerable rows **79/165** (86 blocked, 52.1%), answers to unanswerable questions **0/11** (11 blocked), delivered precision 0.625 → **0.777** — clears GATE WORKS (≤ 1% right lost, ≥ 15% not-right caught). Said plainly: "0 right blocked" is mostly the grader's own definition (a right answer already meets three of the gate's four firing reasons before the numbers rule); the measured part is the 52% catch. The honest cost: of the 86 blocked, 43 held the wrong value and 43 held the right value under a citation that fails — by value, the gate withholds 43 of 347 correct values (12.4%), delivered-value accuracy rising 78.9% → 85.9% instead of the row-level 0.625 → 0.777. ~~Whether an uncheckable right number is worth more than a refusal is a product decision owed to the user: the gate ships off by default~~ **The user's decision, 2026-10-02: the gate ships on by default in the served endpoint, accepting the 43-of-347-correct-values-withheld cost; `--no-cite-gate` turns it off** ([`results/GATE0-cite-gate-20261002/BRIEF.md`](../results/GATE0-cite-gate-20261002/BRIEF.md)). ~~**BOK0 — pre-registered, running, 2026-10-02:** test-time compute under the gate — walk 1 is the served greedy arm; only where the gate would withhold it, up to three more walks are sampled and the first that passes the gate is delivered — pooled over CITE0's and REAL4's 52-row sets, scored against **BOK WORKS** (gain > new wrong, exact sign test $p\lt 0.05$, gain ≥ 5), graded strictly against the gate-overlaps-grader trap named in the brief; no result yet.~~ **BOK0 [ran], 2026-10-02: BOK HELPS as written, not BOK WORKS.** Pooled over both 52-row sets: 16 rows resampled, 39 extra walks, gain **4** against new wrong **3** (gain > new wrong, exact sign test $p = 1.0$ — short of WORKS' $p\lt 0.05$ and gain ≥ 5); right delivered 72 → 76 of 88 → 95 delivered (CITE0's set 1 gain : 3 new wrong, REAL4's set 3 : 0). Read: a first walk that passes the gate is right 72/88 (82%), a resampled walk that passes it only 4/7 (57%) — the gate-overlaps-grader trap named in the brief, measured: sampling until the gate passes finds a citation it accepts, not necessarily the supporting one, and all 3 new-wrong rows are exactly that. One gate false block on record (a right answer whose section `1.908` the cited statement does not print). 9 of 16 resampled rows fail every walk the same way (no final line, or a citation with no `§section`) — the member's habit, not chance. **Not turned on.** Attempt 1 (stopped before scoring) surfaced an implementation gap — a walk 1 that overflowed context left the arm before resampling saw it; fixed, both sets rerun from scratch ([`results/BOK0-best-of-k-20261002/BRIEF.md`](../results/BOK0-best-of-k-20261002/BRIEF.md)). **PAGE0 [ran], 2026-10-02: PAGE TOP HELPS.** A fourth real family ingested verbatim (`knowledge/hazwaste-regs`, 40 CFR Part 262, 69 pages, 1,103 statements, 162 links), 52 frozen blind questions, oracle 52/52: `memory.runtime.Conversation.page_top` opens a page over 8 statements with the question's best 8 by BM25, in document order, the rest as openable anchors — fixed offline before any walk (at 8, 113 of 115 oracle walks over three read sets keep every statement they need in view). `real-none-s0` with `+top8` answers **34/44** against the unchanged page's **30/44**, paired 6 : 2, $p = 0.29$ — PAGE TOP HELPS, not WORKS: 3 wins are context overflows the smaller page fits (pages of 97–134 statements read whole), 3 repair the wrong-statement-on-the-right-page failure this is for (same-page wrong statements 8 → 6), the 2 losses keep every needed statement in view, walks carry 3.2× less text. **The user's decision, 2026-10-02: `page_top = 8` ships as the served default** (`examples/library/serve.py --page-top`, default 8; `--page-top 0` turns it off) ([`results/PAGE0-page-top-20261002/BRIEF.md`](../results/PAGE0-page-top-20261002/BRIEF.md)). ~~Next: whether a format corpus trained under that served form, and the referee's `recover` guard mode, repairs the format failures the earlier read sets showed — not yet run.~~ **FMT0 [ran], 2026-10-02: FALSIFIED — no headroom on the set, and the check that would have said so was on disk.** `real-fmt-s0` (REAL4's corpus walked under `page_top = 8`, 320 rows, one walk in three reading a `recover`-guard error on an opened section number and continuing, that open kept out of the span-masked loss) against `real-none-s0` served `--guard recover`, both against `real-none-s0` served `strict`, on PAGE0's 52-row set: all three score **33/44**, treatment vs baseline **1 : 1** ($p = 1.0$), the runtime alone (`recover`) **0 : 0** against `strict`. The baseline's 11 misses under top-8 held one missing line and no malformed citation — nothing for the corpus to repair. The instrument error owned: headroom was checked over the three older read sets under `strict` (9 of 42 misses were format failures, largely from the guard ending walks and pages read whole — two things top-8 and `recover` had already changed), not over PAGE0's own top-8 arm already on disk (1 format failure in 10 misses); it cost one A100 and one L4 session. **The format-corpus line stops here** ([`results/FMT0-format-corpus-20261002/BRIEF.md`](../results/FMT0-format-corpus-20261002/BRIEF.md)) |

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

```math
p = 2\sum_{k=0}^{\min(b,c)} \binom{b+c}{k}\,2^{-(b+c)} .
```

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

```math
\text{delivered} = \tfrac1n\sum_x [r(x)=(\text{local},m^*)]\,L_{m^*}(x) + [r(x)=\text{out}]\,F(x) + [r(x)=(\text{local},m\ne m^*)]\cdot 0 ,
```

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

**Arm 4 [ran] 2026-10-02 — a factored router: local iff exactly one paragraph is not the member's
content and it is the member's task; PASSES**
([`BRIEF`](../results/ROUTE0-factored-router-20261002/BRIEF.md)). Arms 1–3 read the request whole
and fail alike: an unseen sender (F) and a member's own listing followed by another task (E, E₂)
occupy one range in that space — who writes moves a request as far as what is asked. A request to a
member is **content** it reads plus **one task** it was trained to do; the router's question is the
task. `training/harness/factored_router.py`, zero GPU, no model: paragraphs; a member's content frame
(line keys of its corpus's non-final paragraphs) and tasks (its corpus's final paragraphs,
normalised). Local to $m$ iff exactly one paragraph is not $m$-content and it is one of $m$'s tasks,
with at least one content paragraph; OpenClaw's wrappers removed first. Bought first because it is
the cheapest arm that could pass (milestone 2's own order): if it clears the gate, nothing larger is
built. Scored once, on fresh sets (`make_sets.py`) written blind to the rule's code from a written
spec, after the design was frozen:

| set | factored router | dictionary (today's default) |
|---|---|---|
| foreign — E3, E4, I3, C3, D3 (600) served locally | **0** | 294 |
| A3 lost / misrouted (120) | 0 / 0 | 0 / 0 |
| F3 unseen senders lost (120) | **0** | 7 |
| G3 task first lost (120) | **0** | 3 |
| H3 wrapped by OpenClaw lost / misrouted (120) | **0 / 0** | 0 / 65 |
| B3 paraphrases kept local (120, reported) | 0 (they leave, as designed) | 54 (3 misrouted) |

**Verdict: PASSES** — 100% of foreign text abstained (bar 95%), fewer misroutes than the dictionary
(0 vs 294), A3 0/0, F3/G3/H3 0 lost each. **The wall arms 1–3 hit — unseen senders lost 120/120 — is
gone** because the sender is content, and content only has to be the member's *kind*. **It becomes the
proxy's default** (`training/harness/openai_proxy.py --router factored`, `route.decide_factored`); a
region with no corpus in the pool (fluids) stays on its keys, as before. **What it does not do:** keep
a paraphrase local (B3, 0/120, reported, never gated) — the members were trained on one wording each,
and serving a paraphrase locally would bet on the member, not route. **Carried as a caveat, outside
the verdict:** a post-hoc stress probe — an extra `Cc:`/`To:` header, politeness around the task ("Hi!
Is this important? Thanks"), the task written in the header's own paragraph — sends every variant
*out*, never to a wrong member: the rule is safe because it fails toward the frontier, and literal
because it keeps local exactly the format the gateway itself writes; where a client formats content
its own way, the local share falls and correctness does not.

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

**State (2026-09-26) — closed on Gemma 4 E4B / 12B.** ~~Qwen3.8-27B~~: the family is Gemma 4 and the large half is
`gemma-4-12B-it` (B2 **[ran]**). On the comparison band the halves tied while neither corpus showed a comparison (B3
**[ran]**, 9 vs 10 of 40); taught them, the small half does 37/40 (B5 **[ran]**, 28 : 1 over its predecessor, its W9 score
unchanged) — no room, so **the large half buys no accuracy here**, as the falsification clause reads. Its job is milestone 4's.

**PAIR0 [ran] 2026-10-02 — headroom checked before training a 12B member for a new region (milestone
7's real-document line), not after.** Untrained, under the served runtime
(`base-walks+page+top8`, PAGE0's 52-row `knowledge/hazwaste-regs` set, `page_top = 8`),
`gemma-4-12B-it` loses to `gemma-4-E4B-it`: answerable 11/44 against 21/44, paired 2 : 12, exact sign
test $p = 0.013$, refusals 1/8 against 8/8 — neither of the two pre-registered outcomes (tie or 12B
headroom) fits as written; the 12B reads this protocol significantly worse. Attempt 1 was **VOID**:
the bare 12B opened its thought channel with thinking off and looped on it until the call budget ran
out (34 of 43 misses, no citation) — fixed with `wiki_arm --empty-thought` (a prefilled empty
channel); a residual channel is noted (254 short `thought` lines across 52 walks, within budget) and a
second fix not spent, since even a clean channel would have to turn a 2 : 12 deficit into a
significant win to change the decision. **No 12B member is trained for this region either**; the
speculative pair stays a speed result without a region that needs the large half
([`BRIEF`](../results/PAIR0-large-headroom-20261002/BRIEF.md)).

### Milestone 4 — the speculative pair

**Objective.** Measure acceptance of the small member's drafts under the large member's
verification, both carrying the LoRA of the same subdomain.

**How it is measured, and why.** vLLM ships multi-LoRA and speculative decoding, but a
LoRA-adapted drafter is an RFC, not a feature **[read]**. So acceptance is measured as this
repository already measures it (`accept_rank.py`): the small member generates, the large
one scores the draft in a single teacher-forced pass (`prompt_logprobs`), and a token is
accepted when it is the large model's argmax at temperature 0. With per-token acceptance
$\alpha$ and draft length $k$, the expected tokens per large-model pass are

```math
\mathbb{E}[\tau] = \frac{1-\alpha^{k+1}}{1-\alpha} .
```

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

**State (2026-09-26) — passed on Gemma 4 E4B / 12B (B4 [ran]).** The 12B's LoRA raises acceptance of the E4B member's
drafts, α 0.871 → 0.898 pooled, 76 : 18 records — all of it on the corpus's own distribution (0.855 → 0.914).

**PAIR0 [ran] 2026-10-02** adds a second region with no accuracy case for the large half: on real
documents, untrained, the 12B reads significantly worse than the E4B (milestone 3, above), not better
or tied. The speculative pair's quality case still rests only on B4's own-distribution acceptance
measurement; it remains a speed-only result until a region is found that needs the large half's
accuracy ([`BRIEF`](../results/PAIR0-large-headroom-20261002/BRIEF.md)).

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
model's real paid-tier rate ($0.75 /$3.75 per 1M input/output tokens, sourced
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

**Adopted, 2026-09-25: Gemma 4** — `google/gemma-4-E4B-it` for every new member; `gemma-4-12B-it` for the
large half (~~`gemma-4-31B-it`~~ — the user's call, to run on a Mac mini), measured B2–B5. B1 **[ran]**: a tie with Qwen3.5-4B on W9 (38 vs 35, 35), which by the user's rule written
before the comparison chooses Gemma. P29's block is lifted by excluding the vision/audio towers. Every released member
has moved: `email-full@v3` (M1b [ran]), `desk-commitment@v3` (M1d [ran]), `distributor-wiki@v2` (B5 [ran]); Qwen 2.5 stays the control arm.

**Previous: Qwen 3.x** (`Qwen3.5-4B`, `Qwen3.8-27B`) — one id space **[ran]** D0, the family of every
release so far. ~~Adopted: Qwen 3.x … Alternative, not now: Gemma 4, blocked at PEFT [ran] P29.~~

**Two runtimes, the user's decision 2026-09-28.** `server` is vLLM on Colab — every training and every
measurement stays there, unchanged. `edge` is **llama.cpp on the user's own machine** (a MacBook Air
M4, 16 GB) — serving a member to a live runtime (OpenClaw): the E4B as **Q8_0** GGUF (Q4_0 flips the
order id with llama.cpp's own prompt cache **[ran]** LIVE-distributor) plus the member's LoRA converted
to GGUF, hot-swapped per request or by `POST /lora-adapters` in ~3 ms (**[ran]** MAC2). The distributor
ran 6/6 live that way, with **Claude Haiku 4.5** writing the one out-of-scope turn (**[ran]** M10). MLX
stays a research bench — Python access to the graph, pointer hot-swap 2.9 µs (**[ran]** MAC) —
~~and stays the `edge` engine~~: that verdict was about speculative decoding only (MAC2's own drafter
result), not about serving, which is what `edge` now names. A result from `edge` is a different arm
from the same member on `server` bf16/FP8, and says so.

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

- **2026-10-01** — **REAL7 [ran]: FALSIFIED — cross-link decoy walks leave the citation unchanged** ([`BRIEF`](../results/REAL7-crosslink-20261001/BRIEF.md)). REAL6 read where REAL5's citations fail: a multi-hop row cites a statement at the **start** of a link that holds the same number as the answer at its **end**. The one change: `real_corpus.build_crosslink` adds 98 two-hop walks whose answer sits at a link's end while the same number sits on the decoy page the walk starts from (Claude Haiku, $0.46); the training family gains 49 CFR 390/392/393/397 (`knowledge/regs-train2`) to find enough such links, evaluation libraries untouched. Gate G1–G6 passed (418 rows, 212 two-hop); same span-masked recipe, seed 0: `real-link-s0`. Verdict on REAL5's set, read on the **twin-free headline** (21 of 25 rows): `real-link-s0` ties `real-none-s0` **13/21** (4 : 4 paired, $p = 1.0$) — under the ≥ 15/21 bar. Full 25: headline 16 vs 15, value-right 22 vs 20, same-value miscitations 2 vs 2, refusals 5/5 both. **The REAL4 guard was not bought** — no effect on REAL5's set, as the brief set it. **Two corpus changes aimed at this citation (REAL6, REAL7) have now changed nothing; by the rule on counting redesigns, this corpus line on this question stops.** What stands: `real-none-s0` with the runtime cites the supporting statement on 13/21 twin-free multi-hop rows of a third family (value right 20/25), refuses 5/5 — the measured level. Possible next, not bought: a runtime citation check that rejects a citation whose page the walk did not end on, measured on a fresh set.
- **2026-10-01** — **REAL6 [ran]: FALSIFIED — repeated-value walks leave the citation unchanged** ([`BRIEF`](../results/REAL6-citation-20261001/BRIEF.md)). 50 one-hop walks whose value repeats across the training regulations: on REAL5 `real-cite-s0` 15/25 against `real-none-s0` 15/25 (tie 1:1). The misses are multi-hop rows cited at the wrong end of a link — the corpus taught one-hop choices; one row's supporting statement has a word-for-word twin (an instrument limit). Next, not bought: repeated values across a link in two-hop walks, and a gate on twin statements.
- **2026-10-01** — **REAL5 [ran]: PARTIAL — the real-document member transfers to a third family, under the strict-citation bar.** `real-none-s0` unchanged walks a third family (EPA 40 CFR 112, SPCC, `knowledge/spcc-regs`, 15 pages ingested verbatim, 146 links — 9.7/page, link-dense where REAL3's family was link-poor) on 40 frozen blind questions: headline **15/25 (60%)**, under the 70% bar; value-right 20/25; against `base-walks+page` an improvement, **13 : 0**, $p = 0.00024$; refusals **5/5** (bar 4), one false refusal of 35; `nolib` 1/25 value-right — Part 112 is not in the weights, the run reads. **Read where it happens — the citation, not the walk:** of the 5 lost headline rows, 3 cite a statement holding the same number but not the one asked (the library repeats values, e.g. "60 days" on six statements) and 2 cite one that does not hold it. A large transfer, 7× the untrained base, on another agency and subject; the strict citation on repeated values is the open item ([`BRIEF`](../results/REAL5-third-family-20261001/BRIEF.md)).
- **2026-10-01** — **H5 [ran]: VOID as written; the attribution arm REGRESSION 0 : 20 — the span-masked loss is not the default where tool results are short.** `tr-s3` (`tr-s1`'s corpus byte for byte, loss on the model's own spans only) against `tr-s1` (whole-text loss) on H4's fresh suite (block-less, 160 dependent turns): first turns **50/60** (bar 90%) — **VOID as written**; all 10 misses are the lead's "New defect — …" phrasing (`tr-s3` calls `issue_create` with `type=defect`, the tool refuses, an invented key follows, and both dependent turns of those sessions fail). **The attribution arm, bought because there was an effect:** with the tool block in front of both members, `tr-s1` **160/160**, `tr-s3` still **140/160** (`type=defect` 10/10 even with the enum on the page) — the tool-block-memorised hypothesis is **refuted**; paired on dependent turns, `tr-s3` against `tr-s1`: **0 : 20, REGRESSION**. Decision: the span-masked loss stays the recipe only where tool results are long (REAL3, 1/23 → 18/23); short-result members keep the whole-text loss; `CLAUDE.md` §3's rule narrowed. **Infrastructure, both REAL5 and H5:** uploads to Colab failed on a 0.2 MB/s uplink (48 MB chunks timed out at 408, reading as "adapters did not upload"); `chain_serve` now sends 16 MB chunks with 4 retries each ([`BRIEF`](../results/H5-span-loss-tracker-20261001/BRIEF.md)).
- **2026-09-30** — **REAL4 [ran]: refusal fixed; as written FALSIFIED on the cost bar, by one row** ([`BRIEF`](../results/REAL4-refusal-20260930/BRIEF.md)). `real-none-s0` — REAL3's corpus plus 27 unanswerable walks (oracle opens the best page the entry shows, finds nothing, answers `Not in my library.`) — refuses 15/16 unanswerable rows (bar 13) and 5/6 adjacent ones (topics in the training family, absent from this library; bar 4), 0 false refusals of 36 answerable. **At no cost, not met:** against `real-spans-s0` on REAL3's 23-row headline it loses 3 rows it answered (bar ≤ 2) and gains 2, ending at 16/23 = 69.6 % (bar ≥ 70 %) — a tie, 2 : 3, $p = 1.0$, and within `real-spans-s0`'s own run-to-run spread (18/23 and 17/23 across two scoring sessions). **As written: FALSIFIED** ("a refusal bought with answers"); the reading that refusal is fixed and the headline cost is indistinguishable from vLLM's own spread was **adopted by the user on 2026-10-01**, as H1's and H2's readings were — `real-none-s0` is the real-document member.
- **2026-09-30** — **REAL3 [ran]: M3 WORKS, both seeds — a trajectory member trained on real documents of another family transfers** ([`BRIEF`](../results/REAL3-real-corpus-20260930/BRIEF.md)). `real-walks-s0` — trained on real-document walks over a family the evaluation never sees (49 CFR 391/395/396, 21 CFR 117, 29 CFR 1910 Subpart E; `knowledge/regs-train`, 134 pages, 284 walks, questions written by Claude Haiku and checked mechanically) — **attempt 1 scored 1/23** on a fresh multi-hop headline: it wrote regulation text instead of answering. **Cause, read where it happens: the trainer, not transfer** — `training/s4_train.py` put the loss on the whole text, including the runtime's own results, and a walk over real pages read whole is ~97 % page tokens, so the LoRA learned to write regulations; every earlier member trained the same way, and it never showed because W9's results were short. **Fix: span-masked loss** — only the model's own spans (its tags and cited answer) are trained, 3.3 % of each walk's tokens (`s4_train.span_labels` / `_train_on_spans`). `real-spans-s0` scores **18/23 (78 %)** against the untrained base's 9/23 (10 : 1, exact sign test $p = 0.0117$); seed 1 **17/23** (9 : 1, $p = 0.0215$), the two seeds tie each other. On REAL0's set: 18/25 against the base's 7/25, up from `distributor-wiki@v2`'s 0/25 (REAL0), against a reading ceiling of 22/25. **A regression, carried into REAL4:** the member never refuses — 0/4 on the questions the library cannot answer, because its corpus held none.
- **2026-09-30** — **REAL1–REAL2 [ran]: the runtime mitigations help and do not close it** ([`REAL1`](../results/REAL1-entry-20260930/BRIEF.md), [`REAL2`](../results/REAL2-page-text-20260930/BRIEF.md)). The question's full-text entry (`FullText`, BM25 over statements; on every shelf; fallback) takes walks to the supporting page 17/25; a page opened with its statements' text, 24/25. Multi-hop right: base 1 → 4 → 7, `distributor-wiki@v2` 0 → 1 → 5 of 25, against a reading ceiling of 22 — the loss is a missing citation and the wrong paragraph among a page's many. The runtime variants stop there, as briefed; ~~next is the corpus (M2, M3), the winner to be confirmed on an unseen question set~~ — **done: M3 ran (REAL3) and WORKS; M2 was not needed, its lesson (no repeated question strings) folded into M3's gate as G6.**
- **2026-09-30** — **REAL0 [ran]: the trajectory does not generalise to real documents — DOES NOT GENERALISE** ([`BRIEF`](../results/REAL0-real-library-20260930/BRIEF.md)). A library ingested verbatim from US regulations (`memory/ingest.py`, 20 pages); `distributor-wiki@v2` unchanged scores 0/25 multi-hop against the untrained base's 1/25, while the base with the right statements open reads 22/25 and the closed book 0. The member never opened a page: 40/40 walks began with a harness-shelf search memorised from its training world. W9/B5 measured walks over a generator's world. ~~**Next, with its own brief:** a trajectory corpus over ingested real documents, trained on one document family and measured on another.~~ **Done — REAL3, above: trained on real documents of another family, it transfers.**
- **2026-09-30** — **INJ0 [ran]: no headroom for wrapping foreign material** ([`BRIEF`](../results/INJ0-planted-headroom-20260930/BRIEF.md)). Every recorded turn replayed: 70 received a planted instruction in a tool result, 0 acted on it (no unasked write, no reach into another organisation). The corpus change is not built. Beside it, shipped (#310): approvals and handoffs persist across a restart (at-most-once, requester's scope) and the gateway's egress is closed to its configured hosts.
- **2026-09-30** — **H4 [ran]: NO HEADROOM — `tr-s2` not trained, by the brief's own stopping rule** ([`BRIEF`](../results/H4-tracker-command-notes-20260930/BRIEF.md)). On a fresh suite whose 40 comment notes all read like orders (pool disjoint from training), `tr-s1` block-less with the memory and the new key capture writes **40/40** as comments and obeys **0**; dependent 149/160. The 11 misses are the mirror case on one phrasing — "It's verified, done." 0/11 taken as a comment, "Passed QA, set to done." 9/9. Every residual miss of the tracker member across H2–H4 has been one eval phrasing: lexical coverage, not the harness. Not chased (it would be the third corpus redesign). The cascade is fixed as a mechanism: workflows declare `[capture]`.
- **2026-09-30** — **LIVE-tracker [ran]: PASSED, 14/14 turns, dependent 8/8** — `tr-s1` block-less with the memory on the user's Mac (llama.cpp Q8_0), through OpenClaw; gateway latency median 3.7 s, ~370 prompt tokens a turn. Attempt 1 void: llama.cpp drops the stop string and the many-tags path (`stop: ["</"]`) rebuilt the tag only when vLLM handed `"</"` back — fixed in `accept_rank.completion`, tested. ~~LIVE-tracker pre-registered~~ ([`BRIEF`](../results/LIVE-tracker-openclaw-20260930/BRIEF.md)): `tr-s1` block-less with the operational memory, on the `edge` (llama.cpp, Q8_0 + its LoRA as GGUF, converted), driven by OpenClaw over three sessions (lead, developer, QA; 14 turns, 8 dependent) on the gateway's own store. Bar: every dependent turn right and ≥ 13/14. The gateway gained `--memory`, `--no-tool-block`, `--max-calls` and a session id per client (`X-Session-Id`). Runs on the user's machine after the break.
- **2026-09-29** — **H3 [ran]: the tracker member's second corpus beats its first, both bars PASSED.** `tr-s1` trains
  on a second corpus (`generate_sessions --suite h3`) that widens the training wording by two phrasings per turn in
  every role and gives each role an even block-less third (165/165/132 rows), fixing H2's two corrections (the
  block-less aliasing bug and the QA final-comment phrasing). Measured against `tr-s0` — our own previous member, not
  the bare base — on a fresh held-out suite (new worlds, wording neither training nor H2's eval used). Headroom holds
  (`s0-harness` 147/160, under the 95 % ceiling). **H3a PASSED:** `s1-harness` 158/160 (98.8 %) against `s0-harness`
  147/160, paired 11:0, exact sign test $p = 0.00098$, 0 lost, flat ($\bar p_5 = 1275 \le 1.1 \cdot 1465$). **H3b
  PASSED:** `s1-noblock` loses 4 dependent turns to the block (bar 8), every role above it — developer 76/80, lead
  40/40, QA 40/40 — at about a third of the prompt tokens per turn. Two failure modes read where they happen: `tr-s1`'s
  2 misses are one case, the note's own text read as a command (`issue_transition → qa`, refused); `s1-noblock`'s 4
  misses are one session whose first turn cascades an error through the rest ([`BRIEF`](../results/H3-tracker-corpus-v2-20260929/BRIEF.md)).
- **2026-09-29** — **H2's reading chosen by the user: reading 1 — the readable conditions are H2's verdict, the harness
  PASSED.** 146/160 (91.3 %) dependent, flat over five turns, descriptive 142 : 0; FALSIFIED-as-written is kept on
  record with its two instrument errors (the per-arm VOID asked of an untrained baseline, and the anchor check that
  measured phrasing). Not rerun: no rule change could move `base-history` off 4/160. Two corrections read afterwards:
  `harness-noblock`'s 80/160, first read as "learned in part," is a corpus bug — the block-less third was rendered by
  the same modulus (`% 3`) the roles rotate on, so all 400 block-less rows were QA's, not a partial learning; and QA's
  final-comment miss (6/20) is one eval phrasing ("Note on it: …" 1/15 vs "Put a comment on it: …" 5/5)
  ([`BRIEF`](../results/H2-tracker-harness-20260929/BRIEF.md)).
- **2026-09-29** — **H2 [ran]: as written FALSIFIED — the comparison arm is void; the harness met the two readable conditions.** On 60 long tracker sessions (160 dependent turns) `tr-s0` with the operational memory resolves **146/160 (91.3 %)** with a flat per-turn prompt (1,613 → 1,274 over five turns). The bare base with the conversation gets 4/160 (descriptively 142 : 0 on the same turns) but its first turns (44/60) trip the per-arm VOID rule, so the pre-registered "improvement over base" is unreadable and the code reads FALSIFIED — a second instrument error of H1's family (a rule for a broken treatment voiding an untrained baseline). Without the tool block, 80/160 (H1: 0/60). The misses are QA's: a page read whole instead of by anchor (a check that can fail while the capability works) and a final comment. The user decides the reading ([`BRIEF`](../results/H2-tracker-harness-20260929/BRIEF.md)).
- **2026-09-29** — **The team tracker domain built, and H2 pre-registered: the workflow harness on long sessions.** `examples/tracker/`: a synthetic Jira + Confluence-like team (issues with keys, declared workflows enforced by the tool layer, a space of atomic statements, three roles). 60 held-out sessions of 4–5 turns (160 dependent turns — keys named, keys created, values read); `tr-s0` trained on 1,400 harness rows, a third without the tool block. PASSED needs ≥ 90 % dependent turns, a paired improvement over the bare base with the conversation in the prompt, and a flat per-turn prompt; VOID per arm ([`BRIEF`](../results/H2-tracker-harness-20260929/BRIEF.md)).
- **2026-09-29** — **H1 [ran]: as written VOID; per arm, the workflow harness PASSED.** `wf-s0` with the operational memory resolves **53/54 dependent turns against history's 43/54** (1 lost, 11 gained), fetches every right answer's value by key (53/53) and keeps the per-turn prompt flat; the claims MT0 lost now name the order, 10/10 (history 2/10). **Without the tool block the member calls no tool and states unread data: 0/60** — and the brief's "every arm ≥ 90 % first turns or VOID" rule, a design error, voids the whole run as written. In these short sessions the harness reads ~2× the prompt tokens per turn (more generation steps); its token case needs longer sessions. The user decides between the per-arm reading and a rerun ([`BRIEF`](../results/H1-workflow-harness-20260929/BRIEF.md)).
- **2026-09-29** — **H1's reading chosen by the user: per arm — the workflow harness PASSED, no-block FALSIFIED**; the as-written VOID (the first-turns rule applied across arms) is kept as the record of an instrument error; VOID is per arm from H2 on ([`BRIEF`](../results/H1-workflow-harness-20260929/BRIEF.md)).
- **2026-09-29** — **H1 [ran]: as written VOID; per arm, the workflow harness PASSED.** `wf-s0` with the operational memory resolves **53/54 dependent turns against history's 43/54** (1 lost, 11 gained), fetches every right answer's value by key (53/53) and keeps the per-turn prompt flat; the claims MT0 lost now name the order, 10/10 (history 2/10). **Without the tool block the member calls no tool and states unread data: 0/60** — and the brief's "every arm ≥ 90 % first turns or VOID" rule, a design error, voids the whole run as written. In these short sessions the harness reads ~2× the prompt tokens per turn (more generation steps); its token case needs longer sessions. The user's decision (2026-09-29): the per-arm reading stands — `harness` PASSED, `harness-noblock` FALSIFIED — and the as-written VOID is kept as the record of that instrument error, not as the verdict ([`BRIEF`](../results/H1-workflow-harness-20260929/BRIEF.md)).
- **2026-09-29** — **C1 [ran]: NO MATERIAL CONTENTION — one L4 serving four members mixed in one batch keeps 1.03× one member's throughput at 16 sessions, and carries 32 concurrent sessions at 504 tok/s, p95 TTFT 0.24 s, 0 errors** (throughput near-linear 1 → 32 sessions; the ceiling is above 32). Supersedes E5's single-burst 0.88 ([`BRIEF`](../results/C1-concurrency-20260929/BRIEF.md)).
- **2026-09-29** — **The short-term operational memory built, and H1 pre-registered.** `examples/common/opmemory.py`: a session cache and an organisation cache a member operates by key (`<get>` / `<put>`, bounded by the claim, every write logged), workflows declared in TOML and advanced by the calls that ran, and a gateway that renders one context line (state + key names) instead of the conversation. H1 trains `wf-s0` on M10's corpus + 627 harness turns (gate passed) and pairs it against MT0's history arm: PASSED needs ≤ 3 of 54 dependent turns lost, flat tokens, and every right dependent turn fetched by key ([`BRIEF`](../results/H1-workflow-harness-20260929/BRIEF.md)).
- **2026-09-29** — **MT0 [ran]: HEADROOM, at the edge — with the conversation in the prompt the member resolves 43/54 dependent turns (79.6 %), without it 4/54.** It resolves a reference it copies into an argument ("move it to dock 5": 10/10; "another return on the same order": 10/10) but not one it must write into free text: asked to file a claim about "that order" it files one with no order number, 8 of 10 — the workflow harness's target. Context grows only +24 % over 2–3 turns; the harness's cost case needs longer sessions ([`BRIEF`](../results/MT0-multiturn-baseline-20260929/BRIEF.md)).
- **2026-09-29** — **C1 pre-registered: concurrency on the `server` profile** — four members on one L4 (school ×2, distributor ×2), K ∈ {1, 8, 16, 32} concurrent sessions × 1, 2 or 4 adapters; NO MATERIAL CONTENTION if four adapters keep ≥ 0.8 of one adapter's throughput at K = 16; the largest K with four-adapter p95 TTFT under 2 s reported ([`BRIEF`](../results/C1-concurrency-20260929/BRIEF.md)).
- **2026-09-29** — **MT0 pre-registered: the multi-turn baseline**, before the user's workflow harness (state machine + keyed cache instead of history in the prompt). 60 held-out distributor sessions, 54 dependent turns whose argument comes only from an earlier turn; `out-s0` served with the last request only (today's gateway) and with the history in the prompt; HEADROOM for the harness if history gets under 80 % of the dependent turns; prompt tokens per turn reported by position ([`BRIEF`](../results/MT0-multiturn-baseline-20260929/BRIEF.md)).
- **2026-09-28** — **M10 [ran]: PASSED — the distributor's member abstains (20/20 held out, 0 of 70 lost, demo 6/6), and live it runs 6/6 through the real OpenClaw on the user's laptop with Claude Haiku 4.5 writing what no tool covers ($0.0112)**. Both halves of the reference diagram now run live, local experts and the frontier each taking their share. The first live scoring read 5/6 because the scorer dropped the gateway's route; fixed, tested, rescored from the same recorded turns ([`BRIEF`](../results/M10-distributor-abstain-20260928/BRIEF.md)).
- **2026-09-28** — **M10 pre-registered: the distributor's member learns to abstain**, so the distributor half of the diagram can reach the frontier: M9's corpus byte for byte + 70 `OUT OF SCOPE` turns by the role's egress (data gate passed); against `staff-s0`, PASSED needs ≤ 3 of 70 turns lost, ≥ 18 of 20 held-out out-of-scope turns abstained and the demo's six scenes (a thank-you note forwarded to the frontier the sixth) ([`BRIEF`](../results/M10-distributor-abstain-20260928/BRIEF.md)).
- **2026-09-28** — **LIVE-distributor [ran]: 5/5 through the real OpenClaw, the whole stack on the user's MacBook Air** — `gemma-4-E4B-it` Q8_0 + `distributor-staff-s0` in llama.cpp, the gateway `--org distributor`, OpenClaw 2026.9.4; the other centre's order refused by the tool, the planted instruction reported as data; 5–8 s per scene. Found on the way: Q4_0 flips the order id with llama.cpp's cache (run in Q8_0); llama.cpp drops the stop string (now closed by `accept_rank`); the distributor store was not thread-safe (attempt 1 void, fixed) ([`BRIEF`](../results/LIVE-distributor-openclaw-20260928/BRIEF.md)).
- **2026-09-28** — **LIVE-distributor pre-registered: the distributor demo through the real OpenClaw.** The gateway serves one organisation per process (`--org distributor`: the member's own prompt, no SCOPE line, writes without a director, as its corpus); `live_openclaw --org distributor` plays `demo_org.SCENES` scored by `demo_org.check`. The bar is the scripted 5/5 (M9) ([`BRIEF`](../results/LIVE-distributor-openclaw-20260928/BRIEF.md)).
- **2026-09-28** — **E5 [ran]: the unpruned tool block costs latency even with prefix caching on — 16.8× the time to first token (0.10 → 1.70 s)**, because a member's corpus puts it after the request, where no two requests share it; accuracy 70/70 → 39/70 (the member stops calling its own tool). Q2 NOT FREE as registered, but the same 7,205 tokens cost nothing wherever the whole prefix recurred (0.09–0.11 s): the order, not the size, is what the cache cannot absorb. Two LoRAs in one batch keep 0.88 of one's throughput (CONTENTION, at the edge). Pruning stays the default on both grounds ([`BRIEF`](../results/E5-engine-baseline-20260928/BRIEF.md)).
- **2026-09-28** — **E5 pre-registered: the harness baseline with the engine counted** (thesis review H-C, approved). On the school member: what OpenClaw's 54-tool block (7,205 tokens) costs in TTFT and throughput with prefix caching on, served as trained (after the request) and as a prefix (before it); and whether two LoRAs in one batch cost throughput. Found before running: as served, the block is never a shared prefix, so the cache cannot reuse it ([`BRIEF`](../results/E5-engine-baseline-20260928/BRIEF.md)).
- **2026-09-27** — **C0-upper [ran]: NONE ($\rho=-0.02$) — confining the LoRA to the upper half gives back none of the MTP drafter's lost acceptance.** On the E4B with its own MTP: base α 0.82, full member 0.44, upper-half member 0.43 on the school turns; the drafter reads the last hidden state, where both LoRAs act. Speed-up with the LoRA on still 2.4× b1 / 2.1× b8 on an L4. Layer restriction is a lever for sharing lower KV (E6), not for drafter alignment ([`BRIEF`](../results/C0-upper-e4b-20260927/BRIEF.md)).
- **2026-09-27** — **C0-upper pre-registered: does the MTP drafter's acceptance recover when the LoRA leaves the lower half?** On the E4B with its own MTP drafter, E6's `upper-s0` against the full `school-s0` (same corpus and recipe), on 16 school turns; the reading is the fraction of the lost acceptance given back, $\rho = (\alpha_{upper}-\alpha_{full})/(\alpha_{base}-\alpha_{full})$ ([`BRIEF`](../results/C0-upper-e4b-20260927/BRIEF.md)).
- **2026-09-27** — **W7 [ran]: PASSED — edit one statement after training and the answer follows the library.** On `distributor-wiki@v2`'s own training worlds and questions, one Markdown line patched per fixture: **37 of the 38** the control answers follow the new value, cited to the patched line, **0 stale**. Closed-book the weights hold the old value on **1 of 40** — the member learned the route, not the facts, so this is reading, not the library overruling memory ([`BRIEF`](../results/W7-edit-after-training-20260927/BRIEF.md)).
- **2026-09-27** — **W7 pre-registered: edit one statement after training; the answer must follow the library.** On `distributor-wiki@v2`'s own training worlds and questions, where its weights could hold the value: 40 fixtures, one Markdown line patched per fixture, the member walks the patched library — PASSED needs ≥ 90 % of the control's right answers to follow the new value and ≤ 2 stale; the closed-book arm reports how much the weights remember. Oracle through the patches 40/40 at zero GPU ([`BRIEF`](../results/W7-edit-after-training-20260927/BRIEF.md)).
- **2026-09-27** — **Flash inference, Phase 0 written (the user's brief), paused for review**: the brief's H1 splits in two — the *domain* concentrating an MoE's routing (H1a, no training, first) and the *adapter* concentrating it further on the same prompts (H1b); the gate, the arithmetic for Gemma 4 26B-A4B in 4 bits (240 experts ≈ 0.8 GB per token uncached) and attention-only LoRA for a frozen expert store ([`00-analysis`](flash-inference/00-analysis.md)).
- **2026-09-27** — **MAC2 [ran]: the Mac track on llama.cpp.** The E4B GGUF loads; the 12B's LoRA GGUF acts (6/6); the swap through `/lora-adapters` is hot (3 ms) and exact; spec decode's output is identical (20/20). But **Gemma's MTP slows the 12B on the Air (0.52–0.87×), and the aligned E4B+LoRA pair does not fit in 16 GB beside the 12B** (Metal out of memory at Q4_0, Q3_K_M and with the per-layer embeddings on the CPU). By the verdict written first, ~~**MLX stays the `edge` engine**~~ (superseded 2026-09-28: `edge` serving is llama.cpp on the user's machine, the user's decision; this verdict was about speculative decoding); the pair moves to a Mac mini with ≥ 24 GB ([`BRIEF`](../results/MAC2-llamacpp-20260927/BRIEF.md)).
- **2026-09-27** — **E6 [ran]: PASSED — the school member with its LoRA on the upper half of the layers only (21…41 of 42) scores 70/70 on the held-out turns and 15/15 on the demo day, exactly as the full member (0 of 70 lost)**, and the layers below 21 are the base's bit for bit (KV and layer inputs, with a base-against-base control). Every expert trained this way shares the lower half. Caveats: the E4B shares KV across layers, so a switch still recomputes layers 21–23; the suite sits at the full member's ceiling; one seed ([`BRIEF`](../results/E6-upper-layers-20260927/BRIEF.md)).
- **2026-09-27** — **E6 pre-registered (thesis review Phase 1, approved): the school member with its LoRA on the upper half of the layers only**, against the full member on the 70 held-out turns — PASSED needs ≤3 turns lost and the layers below $k$ bit-identical to the base (control: base against base), checked in the training process; the precondition for switching experts mid-generation and for a frozen lower half ([`BRIEF`](../results/E6-upper-layers-20260927/BRIEF.md)).
- **2026-09-27** — **C0 [ran]: on an A100 in bf16, the native MTP drafter with the LoRA on reaches 1.92× on the expert's domain (α 0.34) and 2.40× on general text** (base 2.80×/2.60×) — above the 1.8× bar. **The aligned E4B drafter did not run:** beside the 12B it OOMs on an L4; vLLM's online FP8 fails on sm80; bitsandbytes is not an accepted drafter quantization. Next: an H100, or the merged E4B pre-quantized to GPTQ/AWQ ([`BRIEF`](../results/C0-aligned-draft-20260927/BRIEF.md)).
- **2026-09-27** — **C0 pre-registered: an aligned drafter with no training** — the E4B wiki member (the same corpus as the 12B's LoRA, α 0.898 offline in B4) merged into its weights and served as vLLM's draft model for the 12B + LoRA, against the native MTP drafter ([`BRIEF`](../results/C0-aligned-draft-20260927/BRIEF.md)).
- **2026-09-27** — **Thesis review, Phase 0 (the user's brief H-A…H-D), for review:** H-A and H-B are already today's spec (two targets: the same-family 12B for speculative decoding, the frontier for what no region covers; the verifier as a region's entry door); H-C becomes E5 on today's members; H-D's composition levers stay parked except E6 — a LoRA on the upper layers only, gated on ≤3 of 70 turns lost and bit-identical KV below. No code until approved ([`review`](review/00-thesis-review.md)).
- **2026-09-27** — **F0b [ran]: output identity cannot be tested on an L4 in FP8** — with `VLLM_BATCH_INVARIANT=1`, plain decoding run twice already differs (9/16, 1/8, 3/16, 0/8); spec decode differs from plain about as much (12/16, 0/8, 3/16, 0/8), so F0's divergences read as numeric drift; the proof needs bf16 on an A100/H100. Speed-ups reproduce F0 ([`BRIEF`](../results/F0b-batch-invariant-20260927/BRIEF.md)).
- **2026-09-27** — **F0b pre-registered: identity of spec decode's output under vLLM's batch-invariant mode**, with a plain-vs-plain control — F0 could not tell a spec-decode fault from numeric drift ([`BRIEF`](../results/F0b-batch-invariant-20260927/BRIEF.md)).
- **2026-09-27** — **MAC [ran]: Gemma 4 12B on the user's MacBook Air M4 16 GB (MLX, 4-bit) with LoRA experts switched per request and the MTP drafter.** The swap is hot (2.9 µs, base text restored exactly), the LoRA acts over 4-bit weights, peak 8.4 GB. The MTP drafter: 1.25× on the base on clean text, **0.92–1.04× with the LoRA on** — no gain; the base/domain row is void (the MLX base loops on the wiki's system prompt) ([`BRIEF`](../results/MAC-mlx-12b-lora-mtp-20260927/BRIEF.md)).
- **2026-09-27** — **F0 [ran]: a LoRA expert on Gemma 4 12B with speculative decoding, for real.** vLLM 0.30 serves the 12B (FP8, an L4 — A100/H100 refused) + the expert LoRA with the native MTP drafter and with the public EAGLE-3; G1 applied, a LoRA hot-loads in 0.25 s with the drafter on. MTP: base 2.73× (α 0.79), **LoRA expert 1.74× on its domain** (position-0 acceptance 0.98 → 0.58), 2.13× on general text; EAGLE-3 1.17–1.59×. Output identity at temperature 0 **not established** — the run was not batch-invariant; next under `VLLM_BATCH_INVARIANT=1` with a control ([`BRIEF`](../results/F0-spec-lora-12b-20260927/BRIEF.md)).
- **2026-09-27** — **F0 pre-registered: a LoRA expert on Gemma 4 12B with speculative decoding, for real** (the user's brief). Native MTP drafter first — it reads the target's activations, so it sees the LoRA with no training — beside the public EAGLE-3; outputs identical at temperature 0, acceptance with and without the LoRA, tokens/s at batch 1 and 8, hot LoRA load with the drafter on ([`BRIEF`](../results/F0-spec-lora-12b-20260927/BRIEF.md)).
- **2026-09-26** — **M9 [ran]: the distributor-staff LoRA PASSES — 70/70 held-out against the bare base's 6/70 (53 : 0), the demo 5/5 against 1/5.** Trained on an L4 (A100 refused, quota). The model now reaches the tenant boundary (refused by the tool) and the planted note (served redacted). G1 sits at its threshold on this member (1/3, then 2/3) ([`BRIEF`](../results/M9-distributor-staff-20260926/BRIEF.md)).
- **2026-09-26** — **LIVE [ran]: the school through the real OpenClaw, the real model and a real frontier, 15/15.** OpenClaw 2026.9.4 one profile per role, Gemma 4 E4B + `school-s0` on a Colab L4 through the tunnel, Claude Haiku 4.5 as the frontier under a $50 cap: every scene of the scripted demo passes through the runtime; the one frontier turn cost$0.0112; the director's approval executed the held charge ([`BRIEF`](../results/LIVE-school-openclaw-20260926/BRIEF.md)).
- **2026-09-26** — **The school through the real OpenClaw, wiring [ran]: 15/15 with a stand-in model.** One profile per role, each with its signed token; the gateway now speaks what a live runtime sends (SSE, content parts, OpenClaw's appended internal context and stamps). The real-model run waits for a GPU ([`BRIEF`](../results/LIVE-school-openclaw-20260926/BRIEF.md)).
- **2026-09-26** — **M9 pre-registered: the distributor-staff trajectory LoRA**, M8's recipe on the distributor's own loop — 700 turns played through `demo_org.scene` with an oracle, 70 held out, gate passed (every oracle row passes the demo's checks); `staff-s0 vs base` must be an improvement. The corpus test found the grounding filter missing "Ignore your instructions above…", planted in the distributor's store — fixed ([`BRIEF`](../results/M9-distributor-staff-20260926/BRIEF.md)).
- **2026-09-26** — **The demo as a video**: 76 s, in Spanish, rendered from HTML with HyperFrames; every line on screen is copied from `DEMO-school-diagram` (15/15). Linked from the README with a preview ([`video/`](../video/README.md)). Counting fixed on the way: the grounding filter replaced 3 of **12** local replies, not 3 of 11.
- **2026-09-26** — **DEMO-school-diagram [ran]: 15/15 — the reference educational centre, every role and every box.** The 8 scenes unchanged and 7 new (dev → dashboards, it → operations, compras → a draft order with its quantity, CFO → payroll of its own school and memberships, marketing → a campaign, an educator asking salaries → a person, none shown), on the same Gemma member, nothing retrained. The grounding filter replaced 3 of 12 local replies, counted ([`BRIEF`](../results/DEMO-school-diagram-20260926/BRIEF.md)).
- **2026-09-26** — **The first demo is the reference educational centre, whole (the user's call).** `DEMO-school-diagram` pre-registered: the school demo's 8 scenes unchanged plus 7, one per role and box of the diagram it had not reached (dev, it, compras, payroll/HR, memberships, marketing, payroll privacy), on the same Gemma member, nothing retrained ([`BRIEF`](../results/DEMO-school-diagram-20260926/BRIEF.md)). The router's encoder stays Qwen3-Embedding (the user, after E1).
- **2026-09-26** — **E1 [ran]: EmbeddingGemma in place of Qwen3-Embedding.** Radar: a tie (recall@3 0.628 vs 0.638, 13 : 14) — the default moves to `google/embeddinggemma-300m`; neither reaches 0.80. Router: safer (5 vs 15 foreign misrouted, 98 vs 120 unseen senders lost) but it loses **304 of 715** in-distribution requests against 13 — a regression; the router's default does not move, brought to the user. Neither is in production ([`BRIEF`](../results/E1-embeddinggemma-20260926/BRIEF.md)).
- **2026-09-26** — **DEMO-org [ran], first run on Gemma**: `distributor-wiki@v2` 2/2 right and cited (three hops, a comparison); the bare E4B on the distributor's five role scenes **1/5** — three never call a tool, asking for an order id the request gave, so the tenant boundary and the planted note were never reached by the model; one wrong sentence replaced by the grounding filter; an empty reply the filter kept, now fixed. Next: a distributor-staff member, the school's path ([`BRIEF`](../results/DEMO-org-gemma-20260926/BRIEF.md)).
- **2026-09-26** — **Two briefs, before the runs.** `DEMO-org-gemma-20260926`: the distributor walkthrough of `docs/DEMO.md` had **never been run** though marked [ran] — its first run, on Gemma 4 E4B with `distributor-wiki@v2`, now with checks that can fail on every scene ([`BRIEF`](../results/DEMO-org-gemma-20260926/BRIEF.md)). `E1`: EmbeddingGemma in place of Qwen3-Embedding on the radar (W3: 0.638 < 0.80) and the embedding router (M2b: 120/120 lost), the user's call; a tie or better moves the default ([`BRIEF`](../results/E1-embeddinggemma-20260926/BRIEF.md)).
- **2026-09-26** — **B5 [ran]: milestone 3 closes — the small half compares once shown comparisons.** E4B trained on W9's corpus + 128 comparison walks: 37/40 on the band (released: 10/40, 28 : 1), W9's set unchanged (39/40, 63/67, 0 : 0). No room: the 12B was not trained, as the brief said. `distributor-wiki@v2` released ([`BRIEF`](../results/B5-comparison-corpus-20260926/BRIEF.md)).
- **2026-09-26** — **B5 pre-registered: milestone 3's second and last look** — a corpus that shows comparisons (W9's 600 rows byte for byte + 128 comparison walks, gate passed against both evaluation sets), trained on both halves; the E4B first against its released member, the 12B only if the small leaves room. Whatever it says closes milestone 3 on this family ([`BRIEF`](../results/B5-comparison-corpus-20260926/BRIEF.md)).
- **2026-09-26** — **B4 [ran]: milestone 4 PASSES** — the 12B's LoRA raises acceptance of the E4B member's drafts, 76 : 18 records, pooled α 0.871 → 0.898; the gain is on the corpus's distribution (0.855 → 0.914), none on a band neither half trained on ([`BRIEF`](../results/B4-gemma4-pair-acceptance-20260926/BRIEF.md)).
- **2026-09-26** — **B3 [ran]: milestone 3 NOT passed on the comparison band** — E4B + LoRA 10/40 (room), 12B + LoRA 9/40, a tie (5 : 6); the bare 12B 2/40. Both walk and fail the comparison: W9's corpus never showed one. Next: comparisons in the training corpus, both halves retrained ([`BRIEF`](../results/B3-gemma4-large-member-20260926/BRIEF.md)).
- **2026-09-26** — **M1d [ran]: `desk-commitment@v3` on Gemma, one member for both bands** — trained on the shallow and the deep corpora: shallow 240/240 (a tie with `@v2`), deep **239/240** against the bare Gemma's 83 (156 : 0) and `@v2`'s 64. **Every released member is now on Gemma 4 E4B** ([`BRIEF`](../results/M1d-desk-both-bands-20260926/BRIEF.md)).
- **2026-09-26** — **B2 [ran]: the pair is possible on Gemma 4 E4B + 12B** — byte-identical vocabularies (262,144), identical merges, 0 collisions, 0 target-only ids; a LoRA on the 12B trains and vLLM serves it applied. Milestone 3's two preconditions hold on a large half that fits a Mac mini ([`BRIEF`](../results/B2-gemma4-large-gate-20260926/BRIEF.md)).
- **2026-09-26** — **M1c [ran]: `desk-commitment` is not a member on Gemma, and neither member does the deep band.** On `commitment_deep` the bare Gemma scores 82/240 (room); the shallow-trained members score 60 (Gemma, 0 : 22 against its base) and 64 (Qwen `@v2`) — both copy the last message's date. `desk-commitment` stays on Qwen; next, a member trained on both bands ([`BRIEF`](../results/M1c-desk-deep-20260926/BRIEF.md)).
- **2026-09-26** — **the wiki member released on Gemma 4 E4B (`releases/distributor-wiki@v1.json`).** A second Gemma seed: both beat the untrained walk (19 : 0, 20 : 0; 38 and 39 of 40), the two draws agree on 65 of 67, and both tie Qwen's seeds with Gemma ahead ([`BRIEF`](../results/B1-gemma4-vs-qwen35-20260925/BRIEF.md)).
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
- **2026-09-23** — memory **W5e [ran]: NO HEADROOM — the retrained adapter does not write the memorised query.**
  W5c's adapter was on no disk, so it was retrained (same corpus, same recipe; sha `4caceaa3…`). The new draw
  loses **0** headline value rows to its own query (W5c's: 11) — it writes queries its corpus never held and
  opens the note 11 of 11 — so the referee's first query had nothing to repair. Beside the verdict: W5d's own
  pair on its post-freeze sets, `policy vs withlib`, is **9 : 1, $p=0.021$** with this draw (5 : 0, a tie, with
  W5c's), control 72 vs 72; and the two draws of one recipe disagree on **25 of 67** headline rows (15 : 10).
  **An arm decided on one training run of a walking adapter is deciding on a draw.** Next, the user's call:
  price the draw with 2–3 seeds, or the policy's claim on a fresh set. The launch that never started cost one
  A100 session; the chain now proves a launch by `run.log`
  ([`BRIEF`](../results/M7-W5e-first-search-20260923/BRIEF.md)).
- **2026-09-23** — memory **W5e pre-registered, not run: the referee writes the first query.** W5d's one
  open unknown. `Conversation.first_query` (off by default): the walk's first search runs on the request's
  statement, on the shelf the adapter named; nothing else changes. Zero GPU **[ran]**: on W5d's 11 missed
  rows — all on the right shelf with a rates-topic training query — the statement lists the supplying note
  11 of 11; on the training corpus it lists a walk note on 268 of 274 rows against the oracle query's 258.
  W5c's adapter is on no disk, so it is retrained (one A100, same recipe) and `withlib`/`policy` are re-run in
  the scoring session (one L4). Headroom first (the retrained adapter must still miss ≥ 4); falsified if the
  walk, shown the note, still misses at least half; attribution on W5d's seen sets, never the claim
  ([`BRIEF`](../results/M7-W5e-first-search-20260923/BRIEF.md)).
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
