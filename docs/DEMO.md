# The demo — a reference organisation on a small local model, in five minutes

What this shows is what already runs, on the code the measurements used, with what does not yet run
said beside it. It is written for a conversation with a team that already runs agents per role —
an agent system in front of an admin backend, one database, identity and permissions outside the
model — and wants to know what a small local model can take off the frontier bill.

One command produces the whole walkthrough, on Colab, under an hour, in one L4 session:

```bash
GPU=L4 BRANCH=main RUN_DIR=results/DEMO-org-20260924 MODULE=training.harness.demo_org \
  MARGS="" RESULTS_NAME=demo.json BASE=Qwen/Qwen3.5-4B SESSIONS=1 training/harness/chain_serve.sh
python -m training.harness.demo_org --render results/DEMO-org-20260924/demo.json > transcript.md
```

*~~This walkthrough ran on `Qwen3.5-4B`~~ — corrected 2026-09-26: **this command had never been run**; no
`results/DEMO-org-*` exists in any commit, and part A was marked [ran] without one. Its first run, on Gemma 4 E4B with
`distributor-wiki@v2` and checks on every scene, is `results/DEMO-org-gemma-20260926/` — the wiki member 2/2, the bare model on the roles 1/5. The school demo below has run, 8/8.*

For the live version — the same model behind OpenClaw, turn by turn — see [`OPENCLAW.md`](OPENCLAW.md);
it ran live, 40 turns, all local **[ran]** P63.

## 1. The five minutes

| minute | what is on screen | what it shows | status |
|---|---|---|---|
| 1 | one OpenAI-compatible endpoint; several adapters on one resident `Qwen3.5-4B`; each request routed to its own | the service is a drop-in for an agent runtime's model setting | **[ran]** P62, P63 |
| 2 | **school demo [ran] 2026-09-26: 15/15 across every role and box of the reference diagram — and 15/15 again through the real OpenClaw with Claude Haiku 4.5 as the frontier** ([`LIVE`](../results/LIVE-school-openclaw-20260926/BRIEF.md)) ([`results/DEMO-school-diagram-20260926/`](../results/DEMO-school-diagram-20260926/BRIEF.md)); first 8/8 on 2026-09-25 — **on Gemma 4 E4B + the school-staff LoRA, every reply grounded by the gateway** ([`results/DEMO-school-gemma-20260925/`](../results/DEMO-school-gemma-20260925/README.md)) · roles of a distributor — customer service, purchasing, IT — asking the local model; it calls the real tool layer and answers from what the tool returned | a small model serves routine role tasks with tools, locally | school **[ran]** 8/8; distributor **[ran]**: the bare E4B **1/5** (`DEMO-org-gemma-20260926`, it asks for an order id it was given) → with the distributor-staff LoRA **5/5** (M9: held-out 70/70) |
| 3 | the same user asks for another tenant's order: **the tool refuses**; a delivery note carries a planted instruction: it is reported, not obeyed | permission lives outside the model; a prompt cannot widen it | tool layer **[ran]** 77 adversarial cases, 0 leaks; model side, this demo |
| 4 | a question two or three hops deep — *what extension reaches the manager of the depot that stocks this product?* — walked through a wiki of **atomic statements**, answered with the citation `[id§anchor]` the runtime checks | facts live in editable pages, not weights; every answer names the statement it rests on | **[ran]** W9 — PASSED: 35/40 against the untrained walk's 0/40; on Gemma 4 E4B 38/40; with comparisons in its corpus, 37/40 on a comparison band (B5); in the demo run, `distributor-wiki@v2` 2/2 right and cited |
| 5 | the route: a request in a trained member's region stays local, one outside every region leaves for the frontier; the bill for the turns served locally, at the frontier's own rates | where the money is — and what is not priced | route **[ran]** M2; bill **[ran]** M6 first pass |

## 2. What to say plainly

| claim | honest status |
|---|---|
| "a 4B serves your routine role tasks locally" | for one-tool role tasks the **untrained** 4B already reaches 18/19 **[ran]** school pilot — the value there is moving the traffic local, not an adapter |
| "an adapter makes it an expert" | shown on inbox triage (0.989 against a bare base's 0.345) and on the school's staff roles: 70/70 held-out turns against the bare Gemma's 27/70, demo day 8/8 against 3/8 **[ran]** M8 — on generated turns, not real traffic |
| "it knows when to hand off" | the router today is a keyword dictionary; two learned routers were measured and **neither passed** (a paraphrase leaves — the demo shows it) **[ran]** M2 |
| "the memory is verifiable" | every answer on the wiki cites the statement it rests on and the referee checks it (W9 **[ran]**); in front of tools, the gateway shows no line that a tool did not return — it replaced 2 of 5 local replies on the demo day, so the model still invents and the system still catches it |
| "it saves money" | **not shown on real traffic.** The replay bill is cents; the local GPU's cost is not priced. The number that decides it is your traffic, measured |

## 3. What would make it a real result

A sample of the team's own agent traffic — requests per role, with the tools each one used — replayed
through the proxy's null arm (`training/harness/null_arm.py`): the share a local member could take,
the share that must leave, and the bill both ways. That is the measurement this repository cannot
make on generated suites, and the one a demo should end by asking for.
