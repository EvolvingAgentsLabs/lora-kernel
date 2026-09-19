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
> LoRA on a large one, trained on the same corpus. Family: Qwen 3.x, small and large.**

The restatement was the user's, and it is the reading the record supports. Three measured
facts carry it:

- **An expert is what its corpus taught — block, keys, order, prompt, band.** Under the
  runtime's prompt 2 of 32 live turns call a tool; under its own, 19 of 32 **[ran]** P63.
- **Routing is a question about corpora, not about inputs.** Keyed on what two members'
  inputs share, 15 of 60 misroute; keyed on what their corpora ask, 0 **[ran]** P64.
- **A bare large model is not a better expert.** Untrained, the 32B scored below the 3B
  expert in both regions tried — 0.967 < 1.000, 0.746 < 0.989 **[ran]** P55, P55b. So the
  large half of a pair is *trained on the same subdomain*, not borrowed as it ships.

What stays from before: the frontier is a permanent component, used where no expert's
corpus covers the request or where a region is measured to fail (0.546 → 0.775 **[ran]**
P41); experts are trained by ordinary SFT; every region enters through the release gate;
the customisation service and its tooling are outside this runtime and the open source.

What is retired: acceptance as a way to *rank* unrelated experts against one target
(closed without a verdict after two failed preconditions; one redesign of three unspent,
and it is not going to be spent); composition of adapters; the character-level acceptance
instrument; the fluid-mechanics expert.

## 1. The milestones

Arms are bought in sequence. The arm that can kill a milestone runs first; attribution
arms are bought only once there is an effect to attribute.

| # | milestone | depends on | gate | state |
|---|---|---|---|---|
| **1** | the pool on Qwen 3.x small | D2 ✅ | both members released on `Qwen3.5-4B`, each tying or beating its Qwen 2.5 release, paired | — |
| **2** | the router as a tiny model of the corpora | the members' corpora | misrouted-to-local no higher than the dictionary's on prompts the dictionary was not written for; abstains on out-of-distribution text | — |
| **3** | the large half of one pair | 1 | a LoRA on `Qwen3.8-27B` is applied when served; large + LoRA beats small + LoRA on the deep band, paired | — |
| **4** | the speculative pair | 3 | acceptance of small-LoRA drafts under large-LoRA verification exceeds acceptance under the bare large model | — |
| **5** | the first real region, by hand | 1, 2, a sandbox, keys rotated | the release gate, on a suite with a verifier nobody here generated | blocked: the user names the region |
| **6** | the service policy, with the bill | 2, 4, 5 | the local share saves more than it costs, on real traffic | — |

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

Customised by hand, released through the same door: a suite with a verifier, the base as
the headroom arm, the sign test. Seventy-five to a hundred hand-written examples is the
right first size — the shallow desk band saturated there. **Blocked on a decision that is
the user's: which region, whose data.** It needs a sandbox for anything that executes and
rotated keys.

### Milestone 6 — the service policy, with the bill

Router → small member → pair where the region is measured to need it → frontier. The
number that has never been measured is money: the frontier bill with and without the local
share, on real traffic. **Falsified by** a local share that costs more to run than it saves.

## 2. The family, and the alternative

**Adopted: Qwen 3.x.** `Qwen3.5-2B/4B` and `Qwen3.8-27B` share one id space — 248,044 ids,
7 large-only, all audio/TTS specials; `<think>` is shared **[ran]** D0. The thinking channel
is off for members: no corpus taught it. The released members are on `Qwen2.5-3B-Instruct`
until milestone 1 lands, and the Qwen 2.5 line stays the control in every gate.

**Alternative, not now: Gemma 4, 2B and 12B.** The design is family-agnostic — a pair needs
one id space and a base PEFT can attach to. Gemma 4 fails the second today:
`Gemma4ClippableLinear` is not `nn.Linear` **[ran]** P29. `lora_matrix` with a Gemma subject
is the gate that reopens it.

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

- **2026-09-19** — objective restated around corpus-distribution routing and the
  speculative pair; the tree cleaned to what works; the previous plan and its seventy-four
  runs kept at `v0.1-foundations`.
- **2026-09-06 → 2026-09-19** — see [`RECORD.md`](RECORD.md).
