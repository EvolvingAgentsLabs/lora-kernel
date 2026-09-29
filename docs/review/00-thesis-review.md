# Thesis review — Phase 0: findings H-A…H-D against today's spec

*The user's brief of 2026-09-27, "thesis review, adapter composition and the harness as an FSM". This is the Phase 0 it asks
for: each finding checked against the spec, proposed decisions, diffs not applied, and a pause for review.*

**A preliminary note that changes how the whole brief reads.** The findings come from a review of the README from before
the 2026-09-19 rewrite, the one that now lives at the tag `v0.1-foundations`. `harness.lora`, `TECHNICAL-REFERENCE.md`, S0,
P5, P7, P8, P9 and P13 are there **[read]** `git show v0.1-foundations:…`. The architecture has changed since: each expert
learns its protocol inside its own corpus, the speculative target is of the same family, and the frontier is where whatever
falls in no region goes. Several findings are already resolved; others still hold, in another form.

---

## 1. The four findings

### H-A — "the central mechanism is no longer speculative decoding": **already resolved; the two-target form is accepted, and it is today's**

- **The frontier is never a speculative target.** Over an API there are no logprobs for a forced continuation and the tokenizer
  is another: "impossible, not just expensive" **[ran]** P48, `RECORD.md` §2. `CLAUDE.md` §0 fixes it: *"It is never a
  speculative target"*.
- **Character-level acceptance measures format, not agreement** **[ran]** S0–S2, `RECORD.md` §2. The criterion did not become
  "semantic agreement": it became **token-level, rank-1 acceptance between models of the same family**.
- **The speculative target is an open model of the same family, trained on the same corpus**: `gemma-4-12B-it`. Its vocabulary
  is byte-identical to the E4B's (262,144, 0 target-only ids) **[ran]** B2, and it is described in `ARCHITECTURE.md` §3.
- **Speculative decoding runs for real with a LoRA active** **[ran]**: 1.74× on the domain with FP8 on an L4 (F0) and
  **1.92×** with bf16 on an A100 (C0).
- **What is not accepted: the frontier as an offline semantic judge.** The spec already decided that a gate copied from the
  frontier answers another question: whether an expert is sufficient is gated on an absolute standard with a mechanical
  verifier (`CLAUDE.md` §3). The frontier stays the destination of what no expert covers, live and under a spend cap (Haiku,
  **[ran]** LIVE). Today's runtime has no "dream pass".

### H-B — "the verifier is the real target": **already adopted as a region's entry door; proposed to make it explicit in the README**

- **A region enters through one door:** "a suite with a verifier the training loop never sees" (`ARCHITECTURE.md` §5). Every
  expert today is measured by a mechanical verifier: the wiki's verified citation, the demo's checks, the email grader.
- **Distillation from the frontier transfers the procedure, not the arithmetic:** adapter + calculator 40/40, the frontier alone
  below it **[ran]** P5–P7, `RECORD.md` §2. And no frontier beat the local 12B on the first suite **[ran]** S1.
- **Proposed diff, not applied:** one sentence in the README's one-minute summary.

  > *Every expert is admitted and measured by a mechanical verifier of its region — the verifier, not a frontier model, is
  > what a member is held to; the frontier answers what falls in no region.*

  And in `ARCHITECTURE.md` §1, a line naming the verifier as a first-class piece, beside the router and the memory.

### H-C — "the harness baseline ignores the engine": **partly valid; accepted as E5, in a modified form**

- **Prefix caching is already on** in every server of this project: vLLM 0.30 enables it by default
  (`enable_prefix_caching=True`) **[ran]** `results/F0-spec-lora-12b-20260927/vllm.log`.
- **The grammar was already measured:** a mask over tool calls "buys cleanliness, not accuracy" (refusals 23 → 10, answers
  5/30 → 4/30) **[ran]** P8, P24, `RECORD.md` §2.
- **What today's claims state is not token savings but accuracy.**
  - Pruning the runtime's 54 tools to the member's own takes refused calls from 225/227 to 8/1160 **[ran]** P59.
  - Serving in *corpus mode* takes the expert from 11/90 to 90/90 **[ran]** M7 arm 0b.
  - The token numbers (~7,956 against ~77 for the tool block, P59) do deserve the correct baseline: with prefix caching, a
    static block costs KV memory and first-time TTFT, not compute per request.
- **Modification:** measure E5 on today's members (school staff, distributor staff), not on P9. The metrics are TTFT, tok/s,
  throughput at batch > 1, malformed calls and accuracy.

### H-D — "P9's composition has unexplored levers": **mostly obsolete; proposed not to reopen it, except E6**

- **`harness.lora` was parked.** Today there is no shared protocol adapter: *"a member is its corpus — block and prompt"*
  (`CLAUDE.md` §3), and the protocol is learned inside each expert. `ARCHITECTURE.md` §4 puts it this way: *"This is what
  `harness.lora` was reaching for … parked when composition could not be measured cleanly — now per subdomain"*.
- **Sequential activation was measured:** P13, 2026-09-10 **[read]** `v0.1-foundations:results/P13-sequential-20260910/`. At
  the time it was read as the one that worked (delegation from 0.6 to 4.7 calls per case). But `RECORD.md` §2 classifies all of
  composition, P13 included, as *"never measured cleanly … Parked"*, because the two corpora taught different notations. E2 is
  not "never measured": it is "measured with a confound".
- **E1 (scales), E3 (merged kernel) and E4 (an "act now" probe) assume a separate protocol adapter.**
  - They only make sense if composition comes back. **E3 is already today's design in spirit**: the protocol is inside each
    member.
  - The **P9 fluids suite** stayed at the tag. Running E1–E4 on it is drifting from `CLAUDE.md` §0's objective.
- **E6 is worth it, and more than before.** Restricting the LoRA to the upper layers connects with three open fronts:
  - switching experts within a generation, if the KV of the unadapted layers is identical between experts;
  - inference from flash, with the lower half frozen;
  - aligning the draft. The MTP reads the target's final activations and the LoRA moves them: we measured domain acceptance
    falling from 0.79 to 0.34 **[ran]** C0.

  If the LoRA touches only the upper half, how much that distribution moves is measurable too.

---

## 2. Decision on targets

**Two targets, which is today's spec:**

| | model | for what | verified |
|---|---|---|---|
| speculative target | `google/gemma-4-12B-it` + a LoRA from the same corpus | verify per token, at temperature 0 | vocabulary identical to the E4B's **[ran]** B2; speculative decoding running **[ran]** F0, C0 |
| frontier | Claude Haiku 4.5 (live), `gemini-3.8-flash` (named) | what no region covers | **[ran]** LIVE |

The brief's alternative (one target, paying the cost of generating twice) is not needed.

---

## 3. Runtime profiles

| profile | engine | what already runs here | valid experiments |
|---|---|---|---|
| **`server`** | vLLM 0.30 | multi-LoRA per request; hot LoRA load 0.23–0.28 s; **speculative decoding with a LoRA on the target and the native MTP**, 1.74–2.40× **[ran]** F0, C0; the draft is one per server and takes no LoRA **[read]** | everything in `results/` from M1; F0, F0b, C0; E5 and E6 as proposed |
| **`edge`** | ~~MLX (mlx-vlm)~~ **llama.cpp** (2026-09-28, §6) | the 12B in 4 bits, switching experts by pointer in 2.9 µs, 8.4 GB; MTP 1.25× on the base, no gain with the LoRA on **[ran]** MAC — MLX's own numbers, now the research bench, not the serving engine | MAC; the flash-inference line (H1a in the cloud, M3 on the Mac mini); one draft LoRA per expert (strategy B, the guide's §6.5) |

A correction to the brief: speculative decoding on `server` does not wait for the RFC. It runs today with a LoRA on the target;
what waits for the RFC is a LoRA **on the draft**.

---

## 4. The harness as a state machine: what already exists

Today's loop is already an FSM, just written in code rather than declared:

- `run_chain` (`training/harness/accept_rank.py`) generates up to a closing tag (`</tool>`), calls the tool, injects `= result`
  and continues. It has the round cap, the stops and the referee's guard that cuts a skipped step (**[ran]** W2).
- The gateway adds states around it: identity, permission, hold, grounding and egress.

**Spec proposal, not implemented:** declare those states as in the brief (`state`, `adapters`, `grammar`, `tools`, `sampling`,
`transitions`), in one file per role, loaded by the gateway. There are two differences from the brief:

1. `adapters` is **one per state** while composition stays parked.
2. Transitions fire on the closing tag, as today. A probe (E4) stays an extension.

What it buys: making explicit and versionable what is code today, with tools per phase already measured (P59). I would write it
in `docs/review/harness-fsm-spec.md` only if you approve this Phase 0.

**Built since, 2026-09-29 [ran].** The FSM this section describes is no longer only a proposal:
`examples/<org>/workflows/*.toml` declares each role's states and the calls that move between them
(TOML, not YAML — `tomllib` is in the standard library, so the format adds no dependency, one of the
four decisions the user approved in
[`harness-workflow-kv.md`](harness-workflow-kv.md) §6), and `examples/common/opmemory.py` gives it the
other half this section did not yet have: a short-term operational memory, read and written by key, so
a member reads one context line (`state: <workflow>/<state> · keys: <names>`) instead of the
conversation. What this section called "declared, versionable" is the hand-written half; **H1**
(`results/H1-workflow-harness-20260929/`, running, no result yet) tests the half that has to be
*learned* — whether a member trained on it actually reads and writes the right key at the right step.

---

## 5. Proposal for Phase 1

| experiment | proposal | why |
|---|---|---|
| E1 scales | **no** | assumes composition; parked |
| E2 sequential | **no** | already run (P13), with a confound the redesign removed |
| E3 merged kernel | **no** | in spirit it is today's design |
| E4 probe | **not for now** | useful only with composition or a multi-adapter FSM |
| **E5 corrected baseline** | **yes, modified** | on today's members; TTFT, tok/s, throughput and malformed calls with prefix caching; corrects the wording of any token-savings claim |
| **E6 LoRA on the upper layers** | **yes, first** | cheap (one retraining of the school member on the upper half; its 70-turn suite and the demo already exist); connects with hot expert switching, inference from flash and draft alignment |

**E6's gate, written first:** the member on the upper half of the layers may not lose more than 3 of the 70 held-out turns
against the full member (paired sign test), and **the KV of the unadapted layers must be identical between experts and base,
bit for bit, under the same prefix**. That is a mechanical test, not a metric.

**Paused for review.** No code until you approve: the reading of H-A…H-D, the two profiles, the FSM as a declaration of the
current loop, and E6 and E5 as Phase 1's only experiments.

---

## 6. Phase 1 outcomes (2026-09-28)

**E6 — PASSED.** `results/E6-upper-layers-20260927`: the school member on layers 21–41 of 42 held its gate — 70/70
held-out, 15/15 demo, 0 lost against the full member — and the KV of the layers below the adapted range came back
bit-identical under a base-vs-base control, exactly the mechanical test §5's gate asked for.

**E5 — ran, and sharper than H-C's own reading.** `results/E5-engine-baseline-20260928`: prefix caching does not
save a static tool block served after the request — TTFT 0.10 → 1.70 s (16.8×), b8 throughput 132 → 108 tok/s,
accuracy 70/70 → 39/70. The block costs nothing only where the *whole* prefix recurs from position 0: **order, not
size, defeats the cache** — sharper than H-C's reading, which named the size.

**C0-upper — NONE, and it corrects what E6's proposal expected of it.** §1's H-D read E6 as connecting with "the
alignment of the draft" — the hope that a LoRA confined to the upper layers would leave the native MTP head's
input closer to the base's, recovering the acceptance a domain LoRA costs it. `results/C0-upper-e4b-20260927`
measured that directly on the E4B and its own drafter: $\rho = (\alpha_{\text{upper}} - \alpha_{\text{full}}) / (\alpha_{\text{base}} - \alpha_{\text{full}}) = -0.02$ — **layer restriction does not help the drafter.** The head
reads the *last* layer's state, and an adapter confined to the layers nearest the head still moves exactly that
state. E6's KV-identity result (below the adapted depth) and the hoped-for drafter-alignment benefit (at the
adapted depth) are different claims; the first held, the second did not.
