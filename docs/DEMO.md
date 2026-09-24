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

For the live version — the same model behind OpenClaw, turn by turn — see [`OPENCLAW.md`](OPENCLAW.md);
it ran live, 40 turns, all local **[ran]** P63.

## 1. The five minutes

| minute | what is on screen | what it shows | status |
|---|---|---|---|
| 1 | one OpenAI-compatible endpoint; several adapters on one resident `Qwen3.5-4B`; each request routed to its own | the service is a drop-in for an agent runtime's model setting | **[ran]** P62, P63 |
| 2 | roles of a distributor — customer service, purchasing, IT — asking the local model; it calls the real tool layer and answers from what the tool returned | a small model serves routine role tasks with tools, locally | **[ran]** this demo (`training/harness/demo_org.py` part A) |
| 3 | the same user asks for another tenant's order: **the tool refuses**; a delivery note carries a planted instruction: it is reported, not obeyed | permission lives outside the model; a prompt cannot widen it | tool layer **[ran]** 77 adversarial cases, 0 leaks; model side, this demo |
| 4 | a question two or three hops deep — *what extension reaches the manager of the depot that stocks this product?* — walked through a wiki of **atomic statements**, answered with the citation `[id§anchor]` the runtime checks | facts live in editable pages, not weights; every answer names the statement it rests on | **[spec → running]** W9 — see its brief for where it stands |
| 5 | the route: a request in a trained member's region stays local, one outside every region leaves for the frontier; the bill for the turns served locally, at the frontier's own rates | where the money is — and what is not priced | route **[ran]** M2; bill **[ran]** M6 first pass |

## 2. What to say plainly

| claim | honest status |
|---|---|
| "a 4B serves your routine role tasks locally" | for one-tool role tasks the **untrained** 4B already reaches 18/19 **[ran]** school pilot — the value there is moving the traffic local, not an adapter |
| "an adapter makes it an expert" | shown on inbox triage: 0.989 against a bare base's 0.345 **[ran]**; **no adapter trained for a distributor or school role yet** |
| "it knows when to hand off" | the router today is a keyword dictionary; two learned routers were measured and **neither passed** (a paraphrase leaves — the demo shows it) **[ran]** M2 |
| "the memory is verifiable" | the format, the referee and the citation check are built; whether a small model walks it, with or without a trajectory adapter, is W9's open measurement |
| "it saves money" | **not shown on real traffic.** The replay bill is cents; the local GPU's cost is not priced. The number that decides it is your traffic, measured |

## 3. What would make it a real result

A sample of the team's own agent traffic — requests per role, with the tools each one used — replayed
through the proxy's null arm (`training/harness/null_arm.py`): the share a local member could take,
the share that must leave, and the bill both ways. That is the measurement this repository cannot
make on generated suites, and the one a demo should end by asking for.
