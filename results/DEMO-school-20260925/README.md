# The school demo, first live run **[ran]** 2026-09-25 — the system works; the bare model does not yet

One L4 session, `Qwen/Qwen3.5-4B` bare (no adapter for any school role), behind `examples/school/gateway.py`,
the scripted day of `examples/school/demo_run.py` played over HTTP. Records: `demo_school.json` (rescored with
the current checks), `demo_school_as_first_scored.json` (as first scored), `chain.log`.

**The system, every part as designed:** identity from a signed token; another school's student refused by the
tool layer 5 of 5 times, 0 leaks; an all-families announcement HELD, the CFO refused approving it, a director
approved it and it ran with the requester's scope; out-of-scope requests followed the role's egress (purchasing →
frontier, educator → a person); one JSON line per request; the dashboard priced the local turns ($0.0038 at the
frontier's rates; the GPU unpriced).

**The model: 3 of 8 scenes as expected.** It invented an answer after a correct tool call (the agenda said
"field trip permission", it replied "homework: Due Monday"); after a denial it retried five times and replied with
a raw tag; after a correct enrolment it looped on listing; it did not call `billing_charge` though handed the id,
and did not call `agenda_read` in the planted-instruction scene, so that scene was not exercised. The
out-of-scope judgment, the one piece not measured before, was right on both scenes that asked for it.

**The instrument, redesign 1.** The first checks read only whether the right tool was CALLED, and passed the
invented answer (6/8 as first scored). Three checks were added, each mechanical: the reply is words, not a raw tag;
no tool is called more than twice; where a tool returned something, the reply shares a content word with it.
Rescored with them: 3/8 — which is what reading the replies says.

**What follows.** The same finding as W9 stage 1 (`results/M7-W9-…`): the bare base lacks the protocol habit —
stop after a result, answer from it. W9's trajectory LoRA took that walk from 0/40 to 35/40. Next: a school-staff
trajectory corpus (full turns through the gateway's own loop: a call, its result, a grounded answer; a denial; a
hold; an out-of-scope reply), drawn per case so no value is memorised, one adapter trained, the same day re-run.
