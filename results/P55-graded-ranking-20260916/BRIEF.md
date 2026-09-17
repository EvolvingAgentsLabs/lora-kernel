# P55 — acceptance as ranking, measured for the first time, on experts graded by construction

**Pre-registered 2026-09-16, before any session is bought.** The runner is
`training/harness/accept_rank.py`; the gates below are its code, tested in
`tests/test_accept_rank.py` on the two outcomes each can have.

## The claim, and why it has never been tested

The architecture's central claim: **a small expert's acceptance rate against a larger
target orders experts the way verified quality orders them**, so a pool can be ranked
with no judge. `REPORT.md` §6 records that this is the only claim that survives
EAGLE-3 — a purpose-built head wins latency outright and cannot rank. And it has never
been run, for a reason that is not the hardware: **ranking needs experts that differ
in quality**, and this project has had one useful expert. Far-apart domains never meet
in one problem; language experts on code are told apart by twelve keywords at 1.000
**[ran]** P1/S3; the generated-code expert reaches 1.000 and leaves nothing to order.

So the experts are made to differ **by construction**. One corpus, one base, one set
of hyperparameters, and only the amount of data changes:

| grade | rows | how |
|---|---:|---|
| `g75` | 75 | a seeded shuffle of `data_ef/train.jsonl`, first 75 |
| `g200` | 200 | the same shuffle, first 200 — so `g75 ⊂ g200` |
| `email-full` | 598 | the adapter that exists **[ran]** P43, 0.741 on human messages |

Nested, so a grade saw *fewer* examples and not *different* ones. Balance checked
(43 % / 49 % important). Files committed; `tests/test_accept_rank.py` regenerates them
and fails if they drift.

## What is unlocked, one mechanism per gate

The user's rule for this step: *desbloquear mecanismos necesarios uno por vez*. Each
row is a mechanism this project has never had, with the gate that says whether it now
exists. A gate that fails stops the run before the next mechanism is bought.

| # | mechanism | never existed because | gate |
|---|---|---|---|
| **M0** | the drafter served **in corpus mode** — generate to `</tag>`, stop, inject the real result, continue | every run served through `tool_calls`, and the expert **invents** the result it cannot receive: P43's record has `= {"turns": 1, "i_wrote_in_thread": false}` written by the expert where the tool said `2, true` **[ran]**; every later decision in that chain rests on a fact it made up | the server honours the stop string (preflight); the adapter's chains differ from the base's on 8 probe cases (C18) |
| **M-target** | a target worth accepting against **on this task** | P49 bought the 32B on *drafting*; nothing has scored it on *triage*, and the skill's trap is exact: verify against something not stronger and a high α means *drifted least* | the target beats `email-full` on the same human cases, paired sign test p ≤ 0.05, and clears the 0.655 majority bar itself |
| **M-α** | acceptance in **tokens**, by forced logprobs | every earlier target shared neither tokenizer nor format (C3, C9); with the 32B the id space is shared **[ran]** P48, and `prompt_logprobs` gives the target's rank of every drafted token in one prefill | chat templates identical; `prompt_logprobs` comes back one entry per prompt token with a `rank` (preflight); α not degenerate |
| **M1** | **experts that differ in quality** | see above | the verifier resolves ≥ 1 of the 3 pairs (paired sign test p ≤ 0.05); the target is **not served** otherwise |
| **M2** | **the ordering test** | needs all of the above | below |

## What is measured, exactly

At temperature 0 the target is one-hot, so speculative decoding's acceptance test —
accept with probability min(1, p_target/p_draft) — reduces to *is the drafted token
the target's argmax*. The target is handed the drafter's transcript verbatim and asked
for `prompt_logprobs`; **a token is accepted iff its rank under the target is 1**.
Nothing is sampled; the target generates nothing during scoring.

**Three α per case, pre-registered as primary and secondary:**

| | over | why it is reported |
|---|---|---|
| **α** (primary) | every decision token: the tags and the verdict | the claim as stated |
| `α_tags` | the tag spans only | protocol agreement |
| `α_verdict` | the verdict span only | the 1–2 tokens the verifier actually scores |
| `α_lcp` | accepted prefix per span, as one speculative round would take it | the number a serving loop would see |

**Why three.** A chain is ~40 tokens and the verdict is one or two. Acceptance weights
every token equally, so two grades that differ only in verdicts would differ in α by
a few percent. *"α does not rank"* could mean the mechanism fails, or that the quality
lives in a token α barely sees. Those are different findings, and the report has to be
able to say which.

**The harness-supplied text is never scored.** `= {result}` is injected by the loop,
exactly as a serving harness would; it sits in the target's prefix and in no span.

**Tokenization is the canonical one.** α is measured on the re-tokenized draft text;
a BPE merge across the prefix/span boundary is detected and counted (`shift`), never
hidden.

## Sessions

**Session A — the instrument, on the expert that exists. No training.**
3B + `email-full` → corpus-mode drafts for `base` and `email-full` → kill → 32B →
its own triage of the same inbox (M-target) → acceptance of both drafted arms.

**Session B+C — the graded experts, gated before the target is served.**
Train `g75`, `g200` in their own processes (P53's lesson) → 3B with three adapters →
drafts for `base`, `g75`, `g200`, `email-full` → **M1 gate** → only then the 32B →
triage → M-target gate → acceptance of all four arms → the ordering verdict.

`email-full` is drafted again in B so all three grades come from one serving session:
vLLM at temperature 0 scored the same adapter 84, 81, 82 on identical cases **[ran]**
P36/P38/P40, and pairing across sessions would put that inside the comparison.

## Pre-registered numbers

- **n = 475**, seed 717171, the suite P43 sized with `bar.n_for` — 351 human
  messages, majority bar on them **0.655**.
- **Grades 75 / 200 / 598**, chosen wide on purpose: at n = 351 over 0.741 the scorer
  resolves **+0.07 at 93 % power** and **+0.05 at only 71 %** (`bar.resolvable`), so
  adjacent grades need to sit ≥ 0.07 apart to be grades at all.
- Every comparison is a **paired sign test on the same cases, p ≤ 0.05**, decided on
  the discordant cases. Never two totals.
- Concurrency 8, `max_tokens` 160 per chunk, ≤ 6 calls per chain.

## The verdict table, written before the run

| M1 (verifier orders the grades) | M2 (α on each resolved pair) | reading |
|---|---|---|
| ≥ 1 pair resolved | every resolved pair **agrees**, p ≤ 0.05 | **SUPPORTED** — acceptance ranks the way quality ranks, for the first time |
| ≥ 1 pair resolved | any pair **DISAGREES**, p ≤ 0.05 | **FALSIFIED** — acceptance orders against quality; the claim is wrong as stated |
| ≥ 1 pair resolved | α flat on a resolved pair | **UNRESOLVED** — the verifier saw a difference at n = 351 and acceptance did not. **This is a failure of the claim as stated, not a tie**; `α_verdict` and `α_tags` then say where the agreement lived |
| 0 pairs resolved | not run | **M1 not unlocked** — the grades are not grades. The next redesign is of the grades (wider, or graded by steps), not of the instrument. Counter: 1 |
| — | target fails M-target | **UNBOUGHT** — no target worth accepting against on this task; the ordering test is not purchased |

A **pair the verifier resolves inverted** (more data scoring lower) is named in the
result and still used: the claim is about agreement with verified order, whichever way
that order came out.

## What voids it

- An adapter whose chains are identical to the base's on the probe (C18).
- Chat templates that differ between drafter and target — the prompt would not be the
  one the draft saw.
- `prompt_logprobs` not one entry per prompt token, or without `rank`.
- Transport errors on more than 5 % of cases in any arm. Counted, never folded in.
- A target below the majority bar: not a triager at all.

## What it cannot conclude

- **Nothing about per-case selection.** "Pick the grade with the highest α on this
  case" is reported beside the ordering, never gated: with graded experts the best
  grade should win almost everywhere and per-case selection is not the claim here.
- **Nothing about latency.** EAGLE owns that.
- **Nothing about a real pool.** Three grades of one expert are the cleanest ordering
  available, not three experts; `close-experts.md` is the next design if this passes.
- **Nothing about Qwen 3.8** — see track D.

## Cost

One A100 each. A ≈ 45 min (two model loads, 2 × 475 short chains, 475 chains on the
32B at concurrency 8, ~3,800 prefills). B+C ≈ 60 min (two adapters trained, four arms
drafted, one target). Both persist every case as it lands and resume from `--out`.

---

## Track D — reaching `Qwen3.8-27B` as the large model

The user's requirement: *es muy importante en la ruta de trabajo explorar llegar a
utilizar como modelo grande Qwen 3.8-27B*. It is on the route, and here is what
stands between here and there, as mechanisms in order. **Nothing in A–C depends on
D; D4 depends on everything in A–C**, because the instrument built there is the one
D4 runs.

| # | mechanism | status | cost |
|---|---|---|---|
| **D0** | a 3.x drafter that shares an id space with `Qwen3.8-27B` | **[ran] today**, [`D0-tokenizers.txt`](D0-tokenizers.txt): `Qwen3.5-2B` and `Qwen3.5-4B` — 248,044 ids, matching, **7 target-only ids, all audio/TTS specials**. `<think>` is *shared*, so the thinking channel is a serving flag, not an id problem. Smaller 3.6/3.8 variants answer HTTP 401 unauthenticated — **existence unconfirmed** | done |
| **D1** | vLLM applying a LoRA on a 3.x base — C18 re-checked under **the vLLM the chain installs today** (`vllm>=0.28` → latest; P33 ran 0.29.0) | not run. `lora_matrix.py` and P33's tiny adapter exist; one model load | ~20 min |
| **D2** | if D1 still says `not applied`: G3 (merge and serve) as P33 designed, and the PEFT-key ↔ vLLM-module mapping read **with the log in hand** — every `PunicaWrapper` line P33 logged names a `visual.` module and `_lora_expand_kernel` fired, so the mechanism is *unknown*, not the one the outside analysis asserts | not run | one session |
| **D3** | thinking off on `Qwen3.8-27B`, verified by counting `<think>` ids in greedy output on the suite: must be 0 | not run | minutes, inside D4 |
| **D4** | **this instrument**, `--base Qwen/Qwen3.5-4B --target Qwen/Qwen3.8-27B`, with the graded pool retrained on 3.5-4B | blocked on D1/D2 | ≈ B+C |

**Why D is not first.** A newer, slower target does not bring the ranking measurement
closer; α has never been measured on any target, and `Qwen2.5-32B` is enough to
measure it. If A–C say acceptance does not rank, D4 would have bought a faster version
of a mechanism that does not work.

---

## Notes during the run — appended, gates untouched

- **2026-09-17 session A launched**, `srv054155`, A100, branch `main` at `8d8ff52`.
- The chain's `pip install 'vllm>=0.28'` resolved to **0.29.0** **[ran]** — the version
  P33 ran. **D1 as designed is void**: there is no newer vLLM to re-check C18 under.
  D2 becomes the live step for the 3.x drafter.
- **2026-09-17 attempt 2**, `srv055733`, `main` at `1df7366` — ran to the target gate and
  stopped `UNBOUGHT`. Kept as `session_a_attempt2_positional.json`. What it bought:
  - **M0 is unlocked with a number.** `email-full` in corpus mode: **471/475 = 0.992**,
    human **347/351 = 0.989**, 1053 calls, **0 refused, 0 invented results**, in 32 s
    **[ran]**. Through `tool_calls` the same adapter scored 384/475 = 0.808 (P43). The
    drift was costing it ~18 points; served as the corpus teaches, it solves the task.
  - **The base reproduces P31 exactly**: human 121/351 = **0.345**, 0 calls **[ran]**.
  - **C18 `applied`** (6 of 8 probes differ); chat templates identical; `prompt_logprobs`
    came back one entry per token with `rank` — **M-α's preflights pass**.
  - **The target's number is an artefact of this harness, not a fact about the 32B.**
    1243 calls, 749 refused, human 0.339. The block renders one-parameter tools as
    `<tag>...</tag>` (P28's arity convention) and the 32B obeyed it — `<thread_history>
    thr-003</thread_history>` — while this loop, unlike `agent_sim`, had no shim mapping
    a positional body onto the parameter name. **351 of 475 cases opened with a
    positional call, i.e. every human case.** Refusals by kind: 352 positional, 337
    wrong key (the model hunting for the key after the first refusal), 60 wrong id.
    136 cases drifted into XML-attribute tags after refusals — the model's own
    deviation, but downstream of the first one. The 32B *adapts mid-chain* (retries
    `id=`, then `thread_id=`), which is why it still reached 0.51 overall.
  - **Fix:** the same convention on the way in — a positional body becomes `param=body`
    when the tool has exactly one parameter; keyed on the count, never on a name. The
    expert is unaffected (it writes keyed bodies, 0 refused before and after).
  - **The gate itself worked as written**: it refused a target that scored below the
    expert, p = 0.0, and did not serve acceptance. Attempt 3 re-runs everything under
    the repaired loop — one serving of each model, ~35 min.
- **2026-09-17 attempt 3**, `srv062147`, `main` at `5e2374a`, harness repaired — ran to
  the target gate and stopped **`UNBOUGHT`, cleanly**. `session_a.json`.
  - `email-full` **471/475 = 0.992** again (human 0.989, 0 refused) — **reproducible
    across sessions**, 31 s.
  - The 32B, positional calls accepted: **386/475 = 0.813**, human **262/351 = 0.746**,
    1248 calls, 195 refused (all `wrong id`: it passes `msg-003` where a thread id is
    needed, then recovers), 0 XML, 6 undecided. Paired on human cases against the
    expert: **target right where the expert is wrong: 2; expert right where the target
    is wrong: 87; p = 0.0**. The target is resolvably *worse*.
  - **Where it loses is the rule, not the protocol.** All 83 wrong verdicts are human
    cases where it made 3–4 calls, got every fact, and misapplied *"at least two of
    these hold"* — e.g. `i_wrote=true`, `frequent=false`, `addressed_directly=false`,
    a statement body → one signal → NOT IMPORTANT; it said IMPORTANT.
  - **So M-target fails for the reason the gate was written for**: on this task an
    untrained 32B is not stronger than the trained 3B, and acceptance against it would
    reward the expert for agreeing with wrong verdicts. **The ordering test is not
    purchased on this suite.** Two things fail at once and both are about the suite,
    not the instrument: the best expert sits at the ceiling (0.99), and the target
    sits below it (0.75).
  - Everything the instrument needed passed: C18, stop, templates, `prompt_logprobs`.
    **M0 and M-α are unlocked; M-target is not, here.**
