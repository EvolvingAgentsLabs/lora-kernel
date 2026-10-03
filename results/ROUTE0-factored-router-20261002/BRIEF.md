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

## Result

*(written after the run)*
