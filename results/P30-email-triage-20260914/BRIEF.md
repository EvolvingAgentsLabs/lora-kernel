# P30 — a region that is somebody's morning, and the first multi-turn run

**Pre-registered 2026-09-14.**

## Why this domain and not another

The architecture only pays where there is a **region**: a narrow task repeated daily.
Triaging one person's mail is that, and it has a property fluid mechanics does not —
**the right answer is mechanically checkable**, so a verifier exists without a judge.
That is what S7's tournament still lacks and why this domain is worth more than a
second physics suite.

## The definition, fixed before anything was generated

A message is important when at least **two** of these hold — and never when it is
automated, whatever else is true:

    it continues a thread I wrote in
    it is addressed to me directly (To:, not Cc:)
    it asks something of me
    the sender is a frequent counterpart

`inbox.important()` is that sentence in one function, used by the generator and by
the scorer, so the truth and the grading cannot drift apart.

## The suite is unanswerable from the listing, and this was checked twice

P15's material could be answered from memory — 27/30 with no tool layer — and the
experiment measured nothing until a handbook made recall impossible. So the test came
first, and **it failed twice before the material was right**:

| draft | best listing-only rule | bar | what leaked |
|---|--:|--:|---|
| 1 | **0.795** | 0.520 | `Re:` was written exactly when the user had replied, and the preview carried the ask |
| 2 | **0.770** | 0.555 | `noreply@` is visible, and automated is never important |
| **3** | **0.680** | **0.680** | nothing — the ceiling *is* the majority class |

The second failure produced the instrument's own correction rather than a change to
the material. **Spotting an automated sender is free and a human does it at a
glance**; leaving those in measures how easy that is. So the ceiling is checked on
the **human** messages, where the tools decide, and there the best rule readable from
the listing scores **exactly the majority class** — 0.680 against 0.680. **The tools
own all 0.320 of the remaining margin.**

## The three tools, and what each withholds from the listing

    thread_history   whether I wrote in this thread — not in the preview
    sender_stats     how much real correspondence exists — not in the preview
    message          the body, and whether I am in To: — the preview is neutral

## What ran (2026-09-14) [ran]

**The multi-turn loop, for the first time.** `docs/SERVING.md` called it *assembled
and not measured*; `training.harness.agent_sim` is an OpenAI client that sends
`tools=[…]`, reads `tool_calls`, executes them, returns `role: "tool"` results and
repeats. Against a stub model through the real proxy:

    24 tool calls · 0 refused · 0 undecided

**The path closes.** Tags become `tool_calls`, results land where the adapter was
trained to read them, and the conversation terminates. That is the plumbing claim and
it is now a test rather than a hope.

**The stub scored 3/8 on the human messages against a bar of 0.625, and the harness
said so.** Its rule uses three of the four signals and never opens the message, so it
*should* be below the bar — a harness that flattered it would be the broken thing
here.

## What is not claimed

**Nothing about the adapters.** No trained model has been run on this suite. The stub
proves the loop, not the pool, and the numbers above are about plumbing. Running the
served kernel against it is the next purchase and it is not made here.
