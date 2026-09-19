# We thought a small model couldn't reason. It was our harness.

*An article for LinkedIn — September 2026. Spanish version:
[`2026-09-era-el-arnes.es.md`](2026-09-era-el-arnes.es.md). Every number here comes from the
repository's record ([`../RECORD.md`](../RECORD.md)) and names its run.*

> **[COVER IMAGE PLACEHOLDER — `docs/img/article-harness.png`, 1200 × 627]**
> *Two panels side by side, in the repository's flat illustrated style. Left: a specialist at a desk
> writes a query on a card and posts it through a slot; the answer comes back through ANOTHER window,
> behind their back, unseen — and they keep writing a number from memory. Below, a counter: "11 / 90".
> Right: the same scene, but the answer comes back written on the same card, right under the query;
> they read it and carry on. Counter: "90 / 90". Title over the image: "Same model. Same problems.
> A different path."*

---

For four days, the most repeated sentence in our project was this one: **"the expert that decides
works; the expert that reasons fails."**

It was false. And how we found out is useful to anyone who puts a fine-tuned model behind an agent
runtime such as OpenClaw.

## The finding

We trained a small model — 3 billion parameters, with a LoRA adapter — to solve fluid-mechanics
problems: chains of 6 to 9 steps, each step using a tool (look a property up in a handbook, convert
units, calculate). We evaluated it on 90 new problems.

**Result: 11 of 90.** The model called its tools flawlessly — 603 calls, none refused — and then got
the physics wrong. The obvious conclusion: small models follow protocols, they do not reason. We
wrote it into the plan, retired the expert, and routed that region to a frontier model.

Four days later we wanted to build on that conclusion, and before doing so we read the 79 failures
one by one, looking at **where** each chain broke. It was not the physics.

In 74 of the 79, the model used a number that came from nowhere. It looked up the fluid's density,
the tool returned 882.3 — and in the next step it multiplied by 1359.7. A made-up number that looked
like a density.

Why would it ignore the result it had just asked for? Because **it never saw it where it had learned
to read it.** In its training data, a tool's result appeared written right after the call, in the
same text:

`<calc>3.96 + 0.541/2</calc>= 4.2305`

But we were serving it the standard API way: the call goes out as `tool_calls`, the result comes
back as a separate message with `role: "tool"`. To a large model those are the same thing. To a
small one trained the other way, the result simply was not there.

We served it again the way its training had taught it. **Same adapter. Same 90 problems.**

**90 of 90.**

Paired case by case, 79 to 0. A number that clean is exactly the kind we have learned not to
believe, so we checked before writing it down: none of the 90 statements was in its training data,
no answer recurred, and in 89 of 90 the final answer came from the model's own last calculation. On
those same cases a frontier model had scored 66. (With the caveat it deserves: these are problems we
generated, inside the exact region that expert trained for. A specialist beating a generalist
*there* is what you would expect.)

We had not measured the model. We had measured our harness.

## What it means if you run a fine-tuned model under OpenClaw

It is not a one-off. In twelve days we met it three more times:

- **The system prompt.** Under the runtime's 37 KB prompt, our email expert called a tool on 2 of 32
  turns. Under the prompt it was trained with, 19 of 32.
- **The tool list.** Offered OpenClaw's 54 tools, the expert copied names off the block: 225 of 227
  calls refused. Pruned to its own, 8 of 1160.
- **The result format.** The same email expert: 0.992 with results inline, 0.808 through
  `tool_calls`.

It is one lesson: **a small fine-tuned model is what its corpus taught it — the prompt, the tool
block, the order of the arguments, and the way a result reaches it.** Served any other way it is a
different model, and a worse one. Before concluding that "the model can't do this":

1. Look at where it fails, not only whether it fails. *Did it use what the tool returned?*
2. Serve it once exactly as it was trained. It is a ten-minute run.
3. Take the arithmetic out of the model's head. With a calculator, 40 of 40; without, 4 of 40.

## The big picture: what we are building

It is called **lora-kernel**, it is open source, and it is the runtime of a service: an
OpenAI-compatible API — with OpenClaw instances per task on top — that resolves locally what falls
inside a measured region and sends the rest to a frontier model.

Three ideas hold it up:

**An expert is its corpus.** Each region is a small LoRA over one resident model, served under
exactly what its corpus taught. The story above is why.

**A router that knows how to abstain.** It decides which expert a request looks like, and when it
looks like none, sends it to the frontier. Abstaining is part of the design, not a failure.

**The LoRA is not the textbook; it is the specialist who knows how to use the library.** This is the
centre of version 1.0. Each expert has a library of markdown notes on two shelves: an **operational
harness** (*how is it done?* — steps joined by links: *requires*, *next*, *uses*) and an
**encyclopedic wiki** (*what is it, which formula applies?*). The model does not memorise the notes:
it learns to navigate them with three verbs — search, open, calc. A small program with no AI in it
is the referee: it turns the pages, applies each site's local rules before the note is shown, and
cuts the run if the model skips a required step.

The gain: if a protocol changes tomorrow, **you edit a markdown file in git. Nothing is retrained.**

## What it is not, yet

Better that I say it:

- **Everything measured is on data we generated.** No real traffic has gone through the system.
- **It is not installable yet.** Today it runs on a rented GPU, a tunnel and our proxy.
- **The library is specified, not built.** Its central claim — that it extends an expert to a
  procedure it never trained on — is untested.
- **The learned router failed twice.** Both versions were safe against foreign text, and both sent
  away 100 % of legitimate requests from new senders. It is still a keyword dictionary.
- **We have never measured the saving in money.**

One encouraging signal, on the first real text we have touched — nursing procedures from an open
textbook: an untrained 4B model goes from 29/48 to 45/48 with the right note in front of it, and from
0/12 to 12/12 when the note carries a unit's local rule ("here we cleanse for 8 seconds, not 5"). It
reads well. What it lacks — and what has to be trained — is *acting* under a procedure.

## Roadmap

1. **The pool on a newer base** (Qwen 3.5, 4B). In progress.
2. **The library, piece by piece**, with a test that can kill it early: the expert solving a sibling
   procedure it never saw, only because its notes are in the library.
3. **The first real region:** nursing procedures, as training material — not advice to patients —
   with each site's local adaptations as editable notes.
4. **A router that separates the task from its content**, which is what the two that failed lacked.
5. **The service policy, with the bill measured.**

Every step has, written before it runs, the condition that would prove it false. That is how we
found the harness.

## If you use OpenClaw for repetitive work

We are looking for two or three teams with a task that meets three conditions: it repeats a lot, its
answer can be verified, and today it goes whole to a frontier model. We have no product to sell you.
We have a method for measuring whether part of that work can be resolved locally — and the habit of
publishing the number whichever way it comes out.

Repository: github.com/EvolvingAgentsLabs/lora-kernel
