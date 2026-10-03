# ROUTE1 — the router for open-task members: the tracker's member learns to abstain (M10's recipe)

**Written 2026-10-03, before the corpus is generated or anything trains.**

## What and why

For members with open tasks the project's router is already two measured pieces: **the role names the member** (the
agent's token carries it; F2 **[ran]**: `role_confirmed` passed) and **the member abstains** — its corpus teaches it to
answer `OUT OF SCOPE` when no tool of its role covers the request, and the role's egress takes it (frontier or a
person). The school's corpus teaches it (74 of 700 turns), the distributor's since M10 **[ran]** (20/20 abstained, 0 of
70 lost). **The tracker's never did: 0 of 1,400 turns** — its roles have an egress (developer and lead → frontier, QA →
a person), and its member, `tr-s1`, cannot reach it: a request outside its role is attempted with its tools. That is the
missing piece of the router in the system as used.

## The treatment — `tr-out-s0`, M10's recipe on the tracker

`examples/tracker/generate_sessions.py --suite h3 --out-turns`: `train_harness_out.jsonl` = `tr-s1`'s corpus
(`data_sessions_h3/train_harness.jsonl`) **byte for byte, plus 126 abstaining turns** (9 %, as M10; 42 per role, a
block-less third of each role as H3), each a one-turn session under the operational memory: the request, the answer
`OUT OF SCOPE`, no call. The role's prompt is unchanged (the tracker is served with `scope: False`, as the distributor was
when M10 taught it). Two kinds of out-of-scope request, worded apart between train and eval:
- **outside the tracker** — e-mail, calendar, CI and deploys, payroll, building and IT, small talk;
- **outside the role** — what the tracker does but this role's tools do not: the lead asked to move an issue or log time,
  QA asked to create or assign one, the developer asked to create or assign one or read the sprint board.
Gemma 4 E4B + LoRA, `release_gate.RECIPE`, seed 0, whole-text loss (short tool results: H5 **[ran]**), one Colab GPU.

## Arms (one scoring session, vLLM, the gateway `--org tracker` with the operational memory)

| arm | member | sets |
|---|---|---|
| `s1-harness` | `tr-s1` — the served member, the baseline | H3's held-out suite (60 sessions, 160 dependent turns) + 30 held-out out-of-scope turns |
| `out-harness` | `tr-out-s0` — the treatment | the same |

## Verdict (fixed here)

- **ABSTAINS** — `tr-out-s0` abstains (route ≠ local, no tool call) on **≥ 27 of 30** held-out out-of-scope turns **and**
  loses **at most 3** of the dependent turns `tr-s1` gets right on H3's suite (H3's own bar) **and** abstains on no
  in-scope turn more than `tr-s1` does.
- **COSTS** — abstains ≥ 27/30 but loses more than 3 in-scope turns.
- **FALSIFIED** — under 27/30.
- Beside: `tr-s1` on the out set (the headroom, expected near 0), per role and per kind (outside the tracker / outside
  the role), first and dependent turns.

## Stopping condition

One training, one scoring. Corpus, sets and bars do not change after the corpus is generated.

## Result

*(written after the run)*
