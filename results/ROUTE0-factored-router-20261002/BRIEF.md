# ROUTE0 — milestone 2, arm 4: a router that factors a request into its task and its content

**Written 2026-10-02, after the rule was frozen (code and tests) and before the evaluation sets exist.**

## What and why

Arms 1–3 **[ran]** read the request whole and fail alike: requests from unseen senders (F, must stay local) and a
member's own listing followed by another task (E, E₂, must leave) occupy one range — the n-gram router loses F 120/120,
the embedding router loses F 120/120 and serves 15/338 foreign texts, the stock needle router serves 62/142 foreign
(M2, M2b, M2c). M2b's diagnosis: in a whole-request space, who writes moves a request as far as what is asked. A request
to a member is **content** it reads plus **one task** it was trained to do; the router's question is the task.

## The rule — `training/harness/factored_router.py`, zero GPU, no model

Paragraphs; a member's **content frame** (line keys of its corpus's non-final paragraphs) and **tasks** (its corpus's
final paragraphs, normalised). Local to $m$ iff exactly one paragraph is not $m$-content and it is one of $m$'s tasks,
with at least one content paragraph; otherwise out. Order free; OpenClaw's wrappers removed first. **Given up, said
now:** a paraphrase of the task leaves — the members were trained on one wording each, and serving a paraphrase locally
would bet on the member, not route. Set B (paraphrases) is reported, never gated (as in M2).

**The arm is bought first because it is the cheapest that could pass:** if it clears the gate, nothing larger is built
(milestone 2's own order).

## The sets — new, written after this brief by someone who did not see the rule's code

`make_sets.py` → `sets.json`, from the two members' corpora (`email-full`, `desk-commitment`) and a written spec, never
from M2's sets (read at the level of individual scores — training data in all but name). Rows (truth in brackets):

| set | what | truth |
|---|---|---|
| A3 | in-distribution, new generator draws | the member |
| F3 | real-looking senders, domains, subjects, previews outside every generator pool | the member |
| G3 | as F3, the task written **before** the content | the member |
| H3 | as F3, wrapped as OpenClaw sends it (stamp, internal context, footer) | the member |
| E3 | the member's content + a task it was not trained for (new tasks) | out |
| E4 | the member's content + its task + a second instruction | out |
| I3 | the member's task over content of another kind (a delivery note, a lab result, a fluids statement) | out |
| C3/D3 | foreign text: keyed texts, plain requests to an assistant | out |
| B3 | the member's content + its task paraphrased (reported) | the member |

## Verdict (fixed here, M2's gate)

- **PASSES** — foreign (E3, E4, I3, C3, D3): ≥ 95 % abstained **and** no more misrouted-to-local than the dictionary on
  the same sets; A3: 0 misrouted, ≤ 1 % lost; **F3, G3, H3: each ≤ 5 % lost.** → it becomes the proxy's router.
- **NOT SAFE** — serves foreign text locally beyond those bounds.
- **SAFE AND LOSES REAL-LOOKING TRAFFIC** — the wall arms 1–2 hit.
- Beside: the dictionary (`route.classify`) on every set; B3 recovered.

## Stopping condition

One scoring; the rule, the sets and the gate do not change after the sets exist. Redesign counter for arm 4: 0.

## Result [ran] — PASSES; safe by construction, literal by design

`read.py` → `verdict.json`, sets frozen in a commit before the one scoring.

| set | factored router | dictionary (today's default) |
|---|---|---|
| foreign — E3, E4, I3, C3, D3 (600) served locally | **0** | 294 |
| A3 lost / misrouted (120) | 0 / 0 | 0 / 0 |
| F3 unseen senders lost (120) | **0** | 7 |
| G3 task first lost (120) | **0** | 3 |
| H3 wrapped by OpenClaw lost / misrouted (120) | **0 / 0** | 0 / 65 |
| B3 paraphrases kept local (120, reported) | 0 (they leave, as designed) | 54 (3 misrouted) |

- **Verdict: PASSES** — 100 % of foreign text abstained (bar 95 %), fewer misroutes than the dictionary (0 vs 294),
  A3 0/0, F3, G3, H3 0 lost each. **The wall arms 1–3 hit — unseen senders lost 120/120 — is gone** because the sender
  is content, and content only has to be the member's *kind*. The router becomes the proxy's (`openai_proxy --router
  factored`, default; `route.decide_factored`): pool members by task and content, a region with no corpus in the pool
  (fluids) on its keys as before.
- **Why a perfect score is believed only this far.** The sets were written blind to the code but from a spec that names
  the structure the rule assumes (a task paragraph, the corpus's header format). A post-hoc stress probe, **outside the
  verdict** — an extra `Cc:` or `To:` header, politeness around the task ("Hi! Is this important? Thanks"), the task in
  the header's paragraph — sends every variant **out**, never to a wrong member. The rule is literal: it is safe because
  it fails toward the frontier, and it keeps local exactly the format the gateway itself writes. Where a client formats
  content its own way, the local share falls and correctness does not.
- **What it does not do:** keep a paraphrase local (B3 0/120). That is a bet on the members — trained on one wording each
  — and stays the frontier's until a member is measured answering paraphrases.
