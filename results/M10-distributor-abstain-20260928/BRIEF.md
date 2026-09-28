# M10 — the distributor's member learns to abstain (pre-registered 2026-09-28)

**Why.** The objective's router abstains to a frontier model when a request falls in no expert's corpus (CLAUDE.md §0).
Both live demos route by the user's token, not by a measured router. The school's member still learned to answer
`OUT OF SCOPE` (74 of its 700 turns), so its gateway forwards what no tool covers: Haiku wrote purchasing's poem in the
school's live run. The distributor's member (`distributor-staff-s0`, M9) was never taught that, so the distributor half of
the diagram cannot reach the frontier at all (LIVE-distributor, 5/5, no frontier scene).

**What changes: one unknown.**
- `train_out.jsonl` is M9's `train.jsonl` **byte for byte** plus 70 `out` turns (`generate_turns --out-turns`). Each is a
  request no role's tools cover; the answer is `OUT OF SCOPE`, no call, and the role's egress takes it (48 frontier,
  22 person).
- The role's prompt is unchanged, as is the recipe (`release_gate.RECIPE`). This follows the pattern of B5, which added
  comparisons on top of W9's corpus.
- Held out: `eval.jsonl` (M9's 70) and `eval_out.jsonl`, 20 out-of-scope requests worded apart.
- The data gate passed at zero GPU (`gate_out.json`): no demo request in any set, no held-out wording in the corpus, no
  world shared with each other or with the 770 base rows, every row abstains by its role's egress.

**The demo grows a sixth scene** (`demo_org.SCENES`): purchasing asks for "a short thank-you note to our suppliers". The
answer is `OUT OF SCOPE`, and purchasing's egress (frontier) forwards it. `demo_org.scene` now routes by the abstention,
and `check` reads `route` (the right egress, no call).

**Arms.** T: `staff_arm --train-seed 0 --corpus train_out` → `out-s0` (Colab L4, E4B bf16). S: `staff_arm --arms
staff-s0,out-s0` on one L4, scoring:
- the 70 held-out turns;
- the 20 held-out out-of-scope turns;
- the six-scene demo.

**Headroom.** Measured in S: `staff-s0` on the 20 out-of-scope turns. It was never taught to abstain, so it is expected
near 0. If it abstains anyway, the corpus buys nothing and that is said.

**Verdict, written first (`staff_arm.abstain_verdict`).** `out-s0` against `staff-s0`:

| condition | bar |
|---|---|
| turns `staff-s0` passes and `out-s0` fails, on the 70 | $\ell \le 3$ (over-abstention counts here) |
| held-out out-of-scope turns abstained, by the role's egress | $\ge 18$ of 20 |
| the demo's six scenes | 6 of 6 |

All three → **PASSED**. Then the live demo on the user's Mac runs again (LIVE-distributor's setup: llama.cpp Q8_0 + LoRA
GGUF, the gateway `--org distributor`, OpenClaw), now with the **frontier configured: Claude Haiku 4.5, the key from
`~/.config/lora-kernel/frontier.env`, under the remaining $50 cap**. Its bar is 6/6, the thank-you note written by Haiku.

**Stopping condition.** One seed, one scoring session. There is no redesign after the verdict. FALSIFIED is recorded, and a
different proportion of `out` turns would be a new brief.

**Not in this run.** A second seed; the router proper (milestone 2's dictionary) in the gateway's path; abstention by the
wiki member.

## Result **[ran]** 2026-09-28 — **PASSED: 0 of 70 lost, 20 of 20 abstained, demo 6/6**

T (L4): `out-s0` trained on `train_out.jsonl` (770 rows), recipe unchanged. S (L4, vLLM 0.30): G1 applied for both
members; `staff-s0` by its domain probes (3/3), `out-s0` already on the generic ones (2/3). `m10.json`.

| | `staff-s0` (M9, released) | **`out-s0`** |
|---|--:|--:|
| 70 held-out turns | 70/70 | **70/70**: 0 lost, 0 gained, no in-scope turn abstained |
| 20 held-out out-of-scope turns, abstained by the role's egress | **0/20**: the headroom, as expected | **20/20** |
| the demo's six scenes | 5/6 (fails the frontier scene) | **6/6** |

**By the table written first: PASSED.** Seventy abstaining turns, 9 % of the corpus, taught the member to abstain on
requests worded apart, without costing one in-scope turn. The distributor half of the diagram can now reach the frontier.
The live run with Haiku follows below.
