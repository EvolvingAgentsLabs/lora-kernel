# Typed adapters as a contract class — analysis against the repository as it is

**Requested 2026-09-15. Analysis only; nothing implemented, nothing touched in the
OpenClaw integration.** Every claim about this repository is **[ran]** or cites a
file; every claim about TypeSafe is **[read]** from the brief, which itself says no
paper, benchmark or API is public.

---

## 0. The thing to read first

**The brief describes a repository that mostly does not exist here**, and that is
not a quibble: H1 — *"a typed adapter requires no new infrastructure: it uses
multi-LoRA serving, agentvcs gates, the router and Sequential Activation as they
exist or are planned"* — names four things, and **three of them are absent**.

| named in the brief | here |
|---|---|
| multi-LoRA serving | **exists and is measured three times** — two adapters applied, distinct, one base, routed by `model` **[ran]** `results/P40-…`, `P41-…`, `P42-…` |
| agentvcs gates | **not checked out.** `CLAUDE.md` §agentvcs: *"no longer checked out here — treat it as the contract to follow if and when it returns"* |
| the router | **does not exist.** `training/route_offline.py` is an *offline computation over recorded runs*; `training/harness/routing.py` is today's region/case routing **report**. S3 ties |
| Sequential Activation | **dropped on 2026-09-15.** Composition is out and `harness.lora` is parked — `docs/EXPERIMENT_PLAN.md` §11 |

So the brief's premise is wrong. **Its conclusion survives anyway, for a different
reason**, and that reason is stronger than the one given — see §H1 and §10.

---

## Verdicts

### H1 — "no new infrastructure" · **PARTIAL, and right for the wrong reason**

**Refuted as stated**: three of the four pieces it leans on are absent.

**Confirmed on the one that matters**: a typed adapter needs a base, a delta, and a
server that applies the delta and returns logits. All three exist and are measured.
vLLM's OpenAI surface returns `logprobs`/`top_logprobs` on request, and
`openai_proxy` forwards the request body untouched apart from `tools`, `stream` and
`tool_choice` (`training/harness/openai_proxy.py`), so a restricted softmax over
value tokens needs **no server change** — see Q4.

**What it does need that does not exist**: somewhere to declare the contract (Q1)
and somewhere to gate calibration (Q6). Both are new artifacts, not edits.

### H2 — "the only spec change is an output-contract field" · **NOT FALSIFIABLE — there is no spec**

There is no adapter schema in this repository. The whole registry is a dict:

    # training/harness/train_pool.py:22
    POOL = {
        "adapters/kernel-mt":   "training/harness/data_mt/train.jsonl",
        "adapters/domain-mt":   "training/physics/data_mt/train.jsonl",
        "adapters/email-full":  "training/harness/data_ef/train.jsonl",
        "adapters/fluids-full": "training/physics/data_ff/train.jsonl",
    }

An adapter is a **path plus a corpus**. Its contract is implicit in whichever client
scores it. So there is no field to add and nothing to break — which is good news for
conflict and bad news for effort: the change is *creating* a schema, not extending
one.

### H3 — "the router is by definition a typed adapter" · **UNTESTABLE AGAINST CODE, and more interesting than the brief knew**

There is no router to compare against. But **today's P41 produced the problem a
typed adapter is shaped to solve**, and the brief predates it:

> routing **by case** delivers **0.378** (tripwire) and **0.689** (quality gate)
> against **0.775** for routing by region **[ran]** `results/P41-routing-20260915/`.
> Both rules detect a chain that is *dimensionally or mechanically inconsistent*;
> this expert's chains are **consistent and wrong**. The rules look for a failure it
> does not have.

The open problem is therefore **a cheap per-case signal that sees a coherent wrong
answer.** Two candidates were measured and rejected today: the escalation rules
(blind to this failure) and agreement with the frontier (a near-perfect predictor —
8/8 kept were right, 60 of 61 sent away were wrong — but **it requires calling the
frontier, so it buys quality and not savings** **[ran]**).

**A calibrated typed head is a third candidate, and it is the only one so far that
could be both cheap and per-case.** That is a much better argument for H3 than
"the router is a classifier".

### H4 — "cheapest to train and evaluate" · **PLAUSIBLE, with one measured caution**

Cheap to train: yes — the corpora here are 600 examples and nine to twelve minutes
on an L4 **[ran]**.

Cheap to evaluate: **only if the base has headroom**, and that is exactly where this
project has been burned. On 2026-09-15 a third-party ARC adapter was scored against
a base already at **0.815**, and the accuracy arm was **unresolvable before it was
bought** — 55% power for a +0.05 effect at n=200 **[ran]** `results/P42-…`. The rule
that came out of it is in `training/harness/bar.py`: `resolvable()` and `n_for()`.

**Any typed adapter proposal must run `bar.resolvable()` before training**, or it
will repeat P42.

---

## Answers

**1. Adapter definition.** `training/harness/train_pool.py:22`. A dict of
`path -> corpus`. No schema, no contract field, no metadata. Existing adapters and
what their contract *would* be: `kernel-mt`, `domain-mt`, `email-full`,
`fluids-full` are all **text**; nothing here is `isa` — grammar-constrained decoding
exists (`training/harness/grammar.py`, `mask.py`) but it is a **sampler mask used in
one experiment (P24)**, not a declared contract.

**2. Router.** None. `training/route_offline.py` computes, over runs already on disk,
whether agreement picks the right expert; `training/harness/routing.py` (today)
reports what region- and case-routing would deliver. S3 "the router beats a lookup
table" is 🟡 **ties** in `README.md`. A typed adapter could *become* the router; there
is nothing to lose because there is nothing there.

**3. Sequential Activation.** **Dropped.** `docs/EXPERIMENT_PLAN.md` §11, decision of
2026-09-15: composition is out and `harness.lora` is parked *(not falsified — P34's
0 → 123 of 150 result stands and waits)*. The brief's §3.5 two-mode fallback
therefore has **no representation to extend**; it would be new work, and it would
reopen a question this project closed today because it had never been measured
cleanly.

**4. Serving.** No change needed. vLLM's OpenAI server accepts `logprobs` and
`top_logprobs` **[read]**, and `openai_proxy` forwards the body untouched except for
`tools`, `tool_choice` and `stream`. A restricted softmax is computed **client-side**
from `top_logprobs` over the value tokens. *The one caveat*: the proxy renders a tag
surface when `tools` is present; a typed request should send **no tools**, and then
the proxy is a pass-through.

**5. Single-token values on the live base.** Verified against
`Qwen/Qwen2.5-3B-Instruct`'s own tokenizer on the running VM **[ran]** 2026-09-15 —
**all 24 candidates are exactly one token, none rejected**:

    A 32 · B 33 · C 34 · D 35 · E 36
    yes 9693 · no 2152 · Yes 9454 · No 2753 · " yes" 9834 · " no" 902
    0 15 · 1 16 · 2 17 · 3 18 · 4 19
    true 1866 · false 3849 · True 2514 · False 4049
    low 10303 · high 11892 · urgent 85053 · routine 52980

So §3.2's invariant — *never resize the embedding* — is satisfiable with ordinary
words on this base. **This is the single most solid part of the proposal.**

**6. agentvcs gates.** **Not checked out**, so the question cannot be answered
against code. What exists instead is `training/harness/bar.py`, which already holds
this project's gate vocabulary — exact binomial thresholds, paired comparison,
`resolvable()`, `n_for()`. **ECE/Brier/AURC would go there**, next to the tests that
pin them, rather than waiting for agentvcs to return.

**7. Verified traces available as `(context, value)` pairs.**

| source | what it holds | usable pairs |
|---|---|--:|
| `results/P43-…/arm_email_475.json` | 475 triage cases, verdict + tools + full transcript | **475** (351 human) |
| `results/P40-…/pool_results.json` | 90 fluids cases with chains, unit, statement | 90 |
| `results/P41-…/frontier_fluids.json` | the same 90, answered by a frontier | 90 |
| `results/P8-…/compose_results.json` | 4 arms × 30 physics cases | 120 |
| `results/P6-…/physics_results.json` | the withdrawal suite | ~40 |

**The email suite alone is the cheapest typed dataset in the building**: 475 cases
whose truth is `inbox.important`, a binary value, already scored, already on disk.
`gemma4nanoloop` and Histora are **not in this workspace** and cannot be counted.

**8. OpenClaw decisions that are free text today and could be typed.** Cheapest
first:

1. **`important / not important` itself.** It is *already* a typed decision answered
   as free text — the client parses the word out of a sentence
   (`training/harness/agent_sim.py`). Turning it typed costs no new data.
2. **Escalate or answer locally.** The per-case routing decision P41 left open; the
   value is `{keep, escalate}` and the training signal is whether the local answer
   was right, which `results/P41-…` already holds for 90 cases.
3. **Which expert.** `{email-full, fluids-full, forward}` — but this needs a pool
   with two useful members and there is **one**, so it is premature.

**9. Cost.** (a) spec: **2–4 h** — it is creating a schema plus a loader, not editing
a field. (b) first typed adapter end-to-end on candidate 1: **4–6 h** including a
headroom check, one L4 training run and one scored arm. (c) calibration gate in
`bar.py` with tests: **2–3 h**. These are the same shape as the work landed today
and the estimates come from it, not from a chart.

**10. Timing.** **There is a cycle already running**, and that changes the answer.
As of 2026-09-15 the end-to-end works: OpenClaw → local proxy → tunnel → vLLM on a
rented card → `email-full` → back, with the expert clearing its gate at
**260/351 = 0.741, exact p = 0.00036** **[ran]** `results/P43-…`. So a typed adapter
is **not** the first end-to-end cycle — that already happened.

**But it is the best candidate for the second**, for a reason the brief could not
have: the pool has **one useful expert and needs two**, and the one honest blocker
named in this session is finding a subdomain where *the base has the capability and
applies the wrong policy*. A typed decision the base already makes badly in free
text is exactly that shape.

**11. Conflicts with decisions already taken.**

| the brief says | the repository decided | the alternative |
|---|---|---|
| use Sequential Activation for the two-mode fallback (§3.5) | **composition dropped**, `harness.lora` parked (2026-09-15) | express the fallback as *two model names* on one server — which is how routing already works and needs no composition |
| gate in agentvcs (§6.6 of the article) | agentvcs not checked out | gate in `bar.py`, where the exact tests and the power rule already live |
| "Base Gemma 4 E4B o Qwen 4B" (article §7) | **Gemma 4 is not a peft base** (`Gemma4ClippableLinear` is not `nn.Linear`); **vLLM does not apply LoRA to `Qwen3.5-4B`** — measured against a control **[ran]** P33 | `Qwen/Qwen2.5-3B-Instruct`, which is the base the whole pool runs on |
| ISA traces as the data factory (§5.1 of the article) | grammar masking exists as a **sampler experiment** (P24), not an ISA with a verifier | the email suite: 475 scored cases with mechanical truth |
| "gemma4nanoloop 5.548 → 817 tokens" | that repository is **not in this workspace** | cite it as external **[read]**, not as this project's evidence |

---

## Proposed spec changes — conceptual, not applied

    # training/harness/train_pool.py — POOL entries become records, not paths
    POOL = {
      "adapters/email-full": {
        corpus: "training/harness/data_ef/train.jsonl",
        output_contract: {kind: "text"},          # every adapter today
      },
      "adapters/triage-typed": {
        corpus: "training/harness/data_tt/train.jsonl",
        output_contract: {
          kind:  "typed",
          type:  "enum",
          values: ["yes", "no"],                  # important / not
          value_tokens: [9693, 2152],             # VERIFIED single tokens [ran]
          calibration: {method: "temperature",
                        gate: {ece_max: 0.05, brier_max: 0.15}},
        },
      },
    }

    # training/harness/bar.py — the gate vocabulary it already owns
    def ece(probs, labels, bins=10) -> float
    def brier(probs, labels) -> float
    def aurc(probs, labels) -> float
    # and a `resolvable()` call REQUIRED before any typed arm is bought

**Two constraints this repository would add to the brief:**

- **`value_tokens` are verified at generation time, not trusted.** The corpus
  generators here assert their own invariants (`generate_email_protocol` refuses a
  leaked rule; `generate_fluids_full` refuses an answer outside the scorer's rtol).
  A typed corpus asserts that every value is one token **on the base it will be
  served by**.
- **A typed arm may not be bought without `bar.resolvable()`.** P42 is why.

---

## Recommendation: **(A) contract now, first typed adapter as the next cycle**

**Because the pool needs a second useful member and this is the cheapest honest
candidate.** The end-to-end already runs with one expert; the measured blocker is
that the fluids expert fails, HuggingFace has no public tool-using expert for this
base, and the shape that works is *the base has the capability but applies the wrong
policy*. `important/not important` is exactly that, its data is on disk, and its
value tokens are verified.

**And because P41 left an open problem that a calibrated head is the only cheap
candidate for.** Per-case escalation currently delivers *less* than region routing,
because the available rules cannot see a coherent wrong answer and the one signal
that can — agreeing with the frontier — costs a frontier call. A confidence a typed
head produces in one forward pass is the first candidate that could be both.

**Not (B)**, because a contract with no adapter is a schema nobody has exercised, and
this repository has a record of interfaces that were right until something used them.

**Not (C)**, because the invariant the whole idea rests on — single-token values with
no embedding resize — is **verified on the live base**, which is the cheapest
possible confirmation and it already happened.

**What would change this recommendation:** if a headroom check shows the base's free-
text `important/not important` is already well calibrated, the typed arm is
unresolvable and the honest move is to say so and stop — the P42 lesson, applied
before the spend rather than after.
