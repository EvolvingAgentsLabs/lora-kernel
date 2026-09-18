# Two outside systems read against the record: Skill-to-LoRA and Adaptive Minds

**Analysis, 2026-09-18.** Prompted by two published systems that sit on this project's
two halves: *Skill-to-LoRA* (S2L, [arXiv 2606.16769](https://arxiv.org/abs/2606.16769))
turns a `SKILL.md` into a per-skill adapter — milestone 1's question; *Adaptive Minds*
([arXiv 2510.15416](https://arxiv.org/abs/2510.15416),
[repo](https://github.com/qpiai/adaptive-minds)) serves a named pool of LoRAs on one vLLM
and lets the base model pick the member — milestone 2's question. Everything about them
below is **[read]**; nothing was run. No GPU.

**Neither moves the critical path.** They leave one related-work line, one parked router
candidate with its metric written down, and one first arm for D2.

---

## 1. S2L — the same direction as P61, on weaker evidence

Qwen3.6-27B, 21 skills of SWE-Skills-Bench × 10 tasks, deterministic verifier:

| arm | passed of 210 |
|---|--:|
| no skill | 59 |
| full `SKILL.md` in the context | 54 |
| S2L — skill-specific LoRA, no text | 65 |

Wrong-LoRA and Shared-LoRA both lower the score; no aggregate is given for them.

**The effect is inside the noise, and the paper does not say so.** No seeds, no
intervals, no discordant pairs. Unpaired, with $\hat p$ pooled,

$$z = \frac{\hat p_a - \hat p_b}{\sqrt{2\,\hat p(1-\hat p)/n}}:\qquad
\text{S2L vs text } \frac{0.3095-0.2571}{0.0440} = 1.19\ (p \approx 0.23),\qquad
\text{S2L vs none } 0.65\ (p \approx 0.52).$$

The selection shows the same thing from the other side: the 21 skills are *all seven
where skill text had helped* plus fourteen zero-delta ones, and on that subset the text
arm lands **below** no-skill. The positive deltas did not replicate — this project's
84 / 81 / 82 (§3, *a threshold inside the run-to-run spread*).

**So it is cited as related work, never as support.** P61 is 137 : 1 on discordant
pairs with base + document making 0 tool calls on 351/351 **[ran]**; that is the
evidence for *the procedure has to be in the weights*, and S2L agrees with its sign.

What it adds that the record did not have:

- **At 27B the document still does not help [read].** §8b allows a procedure document
  when *the base is larger and that is measured first*. S2L is a reason not to assume
  milestone 7 rescues the harness-only arm. `knowledge_arm` over the AWQ 32B is already
  buildable (P60 §3b) and is the measurement.
- **Its self-distillation cannot be copied onto this base.** S2L's teacher is the base
  with the `SKILL.md` in context. On `Qwen2.5-3B-Instruct` that teacher makes zero tool
  calls **[ran]** P61 — it would write a corpus that teaches not calling. The teacher
  stays a generator with an oracle, or the frontier. S2L also does not filter its
  demonstrations through a verifier; Phase 1's door is stricter and stays.
- **64 examples per skill** agrees with `g75` ≡ `g600` = 1.000 on desk **[ran]** P55b.
  For milestone 4 it means a first real region's corpus is writable by hand; Phase 3's
  *smallest grade alone first* already encodes it.
- **Shared-LoRA hurts [read]** agrees with Decision 2 (self-contained members). It is one
  adapter trained on all skills, not two adapters stacked: P8/P34 remain unmeasured.
- **The token saving is 6.6% per step.** Not the argument. The argument is behaviour:
  2/32 → 19/32 tool-calling turns under the member's own prompt **[ran]** P63.
- **A first arm for D2.** S2L serves Qwen3.6-27B through vLLM with dynamic LoRA, and a
  *wrong* adapter changes the outcome — so the adapter is applied there **[read]**. Its
  adapters target `q_proj, v_proj` only. P33's covered twelve projections including the
  linear-attention `in_proj_qkv` and `out_proj`. D2 is *the PEFT-key ↔ vLLM-module
  mapping*; the cheapest probe of it is `tiny_adapter` with `q_proj,v_proj` on
  `Qwen3.5-4B` through `serve_openai --gate-only`, beside the Qwen2.5-3B control.
  `applied` localises C18 to the target modules; `not applied` rules that out in
  minutes. Hypothesis, not finding — and it runs when D2 does, not before.

The `SKILL.md` → corpus → adapter pipeline itself is customisation tooling (§7): out of
scope for this runtime and the open-source version.

## 2. Adaptive Minds — our substrate, with the router we have priced and not bought

vLLM multi-LoRA by name behind FastAPI: the substrate P36–P40 measured three times. The
part that differs is the router — one base-model call reads each adapter's metadata and
names the member:

| library | base-as-router | keyword match |
|---|--:|--:|
| 5 adapters | 100% | 48.3% |
| 30 adapters | 98.3% | 31.7% |

Self-authored 151-query gold set; the v1 paper is 25 queries and scores routing only.

**The useful number is the keyword column falling with pool size.** That is `route.py`'s
predictable failure at milestone 5, and its first crack is on record: with two members
on one inbox, desk prompts routed to triage 15 of 60 until the keys moved from the
listing to the question **[ran]** P64.

**It is the cheapest candidate for the router the plan prices "only once the dictionary
fails on real traffic"** — no training, one adapter-less call on the resident vLLM, and
the release contract needs one `description` field. **It is not measurable today**: the
dictionary is at 1.000 on every generated set, so any challenger ties (headroom rule).
Parked for milestone 4, with its conditions written now:

- **The classifier picks the region; the measured table still decides.** Adaptive Minds
  routes by topical fit. Fluids is a perfect topical fit and is measured to fail. In
  FOUNDATIONS §8.4's terms the only term a classifier can change is the misroute one,

  $$\text{delivered} = \tfrac1n\sum_x [r(x)=(\text{local},m^*)]\,L_{m^*}(x) + [r(x)=\text{out}]\,F(x) + [r(x)=(\text{local},m\neq m^*)]\cdot 0,$$

  so the metric is **misrouted-to-local**, not routing accuracy.
- **The default is the frontier.** Theirs is a "General" adapter. A 3B asked to choose
  will always choose; the kill arm for this candidate is abstention on out-of-region
  text, and it is bought first.

**LoRAs-as-tools (their Agent mode) does not pay here yet.** A frontier controller is
called on every request — quality, not saving, the same trap as agreement-with-the-
frontier (P41). A 3B controller is predicted to fail by P61. It becomes a question only
with a resident 27B.

Their −20.7 pp on GPQA when routing sends an out-of-format question to an adapter is an
independent reading of P63 and P45: *a member is what its corpus taught*.

## 3. What neither has

A verifier on the adapter, a paired comparison, a reproducible release, or a measured
way out to a larger model. Those four are this project's claim; the two systems are
evidence that the substrate and the direction are shared, and nothing more.
