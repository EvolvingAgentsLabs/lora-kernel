# P38 — two experts, one resident base, selected by the `model` field

**Pre-registered 2026-09-15, before either adapter was served together.**

## What is already measured, and why none of it is a pool

| | what it showed | why it is not this |
|---|---|---|
| P26 | two adapters register as separate model names and produce different text **[ran]** | two *personalities*, neither of which had a job |
| P36 | one adapter clears a real gate on its own subdomain — 84/113, p = 0.028 **[ran]** | one expert |
| P37 | a second adapter trained on a genuinely different subdomain | untested |

The thesis is that **the whole agentic system is a pool of QLoRAs over one resident
base**. That sentence earns its words only when two experts, each useful, live in one
server and are chosen by nothing more than the `model` field of an HTTP request.

## The arrangement

`email-full` and `fluids-full` in **one** vLLM. Each scored on its own suite, by its
own client, against its own oracle and its own bar:

| member | client | truth | bar |
|---|---|---|---|
| `email-full` | `agent_sim` | `inbox.important` | majority class, exact binomial at α = 0.05 → **83/113** |
| `fluids-full` | `fluids_sim` | the suite's computed answer at rtol 0.02 | the hand-written rule, **paired** on the same cases |

**The two domains share nothing but the base.** Different tools, different verifiers,
different bars. Sharing a gate would have been easier and would have measured a suite
rather than a pool.

## The gate checks two things

1. **Every member differs from the base.** vLLM accepts a LoRA, logs that it loaded
   it, and can serve the base anyway — measured on a named class in P33 **[ran]**.
2. **The members differ from each other.** Two names over one adapter would produce
   two respectable numbers and be one expert. **That is the failure that looks most
   like success**, and nothing before today checked for it.

Either failing stops the run before a case is scored.

## The fluids bar, and why n = 90

The fluids answer is numeric, so guessing scores zero and a majority-class bar means
nothing. The honest competitor is the **hand-written rule**, which P24 measured
beating the kernel adapter 12/30 to 5/30 **[ran]** — code beating weights, and the
hardest bar available.

At the default n = 30, a paired sign test detecting an expert at 0.70 against the
rule's 0.40 has **55% power** — a coin flip, and exactly the mistake P31 made and
this project corrected afterwards. **n = 90 gives 98%**, with a 4% false-alarm rate
**[ran]** 2026-09-15.

## Falsification

- **The pool is real** if both members clear their own gates in one server.
- **It is not a pool** if the members are indistinguishable from each other or from
  the base — and the run stops there rather than reporting two numbers.
- **One member clearing and one failing is a result, not a half-result**: it would
  say the architecture serves, and that the failing subdomain is harder than the
  corpus that was built for it. Which one failed is the finding.
- **The run is void** if either client runs out of turns in quantity. A fluids chain
  is seven calls deep and `fluids_sim` records that outcome separately, precisely so
  it cannot be read as wrong physics.

## What it will not claim

**Not routing.** Nothing here chooses the expert; the client names it. A router that
picks the member from the request is S3, it ties today, and it is not this step.
