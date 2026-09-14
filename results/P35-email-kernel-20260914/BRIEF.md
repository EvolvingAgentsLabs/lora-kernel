# P35 — teach the kernel the names, and see whether the margin moves

**Pre-registered 2026-09-14, before the adapter was trained.**

## Exactly what P34 left open

P34 measured a protocol adapter taking this base from **0 tool calls to 127** on the
email suite — and **all 127 refused**, because it asked in the vocabulary it had
learned **[ran]**. The disposition to ask transfers across domains; the names do not.

So this trains a kernel on the email tool names and nothing else, and asks whether
the 0.320 of margin that P31 showed sitting with the tools can be reached.

## What the corpus is, and what it must not be

`training/harness/generate_email_protocol.py`. Four questions about an inbox that
**cannot be answered from the listing** — how many turns a thread has, whether I
wrote in it, how much I have written to an address, who sent the last message. Each
one is solved by asking, which is the whole of what is taught.

**It states nothing about what makes a message important.** No replies, no being
addressed directly, no frequent correspondents, no two-of-four rule — none of
`training/email/inbox.important`. That is asserted at generation time and again in
`tests/test_email_protocol_corpus.py`. If the judgement leaked in, the adapter would
be a triage expert wearing a kernel's name and this step would measure nothing.

**A fresh inbox every five examples**, so no id, address or count survives to be
recalled. P15 lost an entire experiment to a fixed table of fourteen numbers.

## The gate, and it is the one P31 fixed

The **exact one-sided binomial test** against the majority class at α = 0.05 on the
human messages, computed on the sample actually scored. On P31's draw that is
**83/113**. *Accuracy above the bar is not a pass*, and a score that lands there is
reported as "above the bar, inside what the bar itself produces".

## Falsification, all four outcomes named in advance

| what comes back | reading |
|---|---|
| **calls accepted, gate cleared** | the kernel/domain split works end to end: a protocol adapter reaches a margin the base cannot |
| **calls accepted, gate not cleared** | the protocol is learnable and **the judgement is the missing half** — the next purchase is a domain adapter, not more protocol |
| **calls still refused** | the corpus taught names the served surface does not use; a corpus/serving drift, and `tests/test_email_protocol_corpus.py` should have caught it |
| **calls fall back toward zero** | training on this vocabulary cost the disposition P34 measured — the most surprising outcome, and the one that would most change the plan |

**The second row is the expected one** and it is not a failure: P31 showed the
base cannot judge, and nothing here teaches judging. Reporting a cleared protocol
with an unmoved score is the honest result if that is what happens, and saying so
now is what stops it being dressed up later.

## A confound named before the number, not chosen after it

**The corpus teaches the model to invent its own tool result.** Its assistant turns
read `<tool>args</tool>= {…}` followed by the answer, because that is the shape the
physics corpora use and the shape a stop-string harness expects. **The proxy sets no
stop sequence** — it extracts tags from the finished text — so at serving time the
model writes the tag, fabricates a result, answers from the fabrication, and *only
then* receives the real result as a `role: "tool"` message.

That is how P34's 127 calls were extracted too, so the two runs stay comparable. But
it means **"calls accepted, score unmoved" has two explanations**, and they are not
the same finding:

| explanation | what it would mean |
|---|---|
| the judgement is the missing half | expected; buy a domain adapter next |
| the model answered from its own fabrication and ignored the real result | the serving shape is wrong, and no domain adapter would fix it |

**How they are told apart**, decided now: `strip_calls` removes the tags but leaves
the fabricated `= {…}` in the assistant content. If the final verdicts track the
fabricated values rather than the real ones, it is the second. That is readable from
the records without another GPU run.

**The fix, if it is needed**, is a `stop` list of the closing tags with
`include_stop_str_in_output` so `CALL` still matches — deliberately **not** applied
now, because changing the serving shape mid-experiment would make P35's call count
incomparable with P34's.

## Headroom, checked rather than assumed

- **Floor**: base alone, 0 tool calls, 39/113 **[ran]** P31.
- **Ceiling**: a listing-only rule reaches the majority class exactly **[ran]**
  `tests/test_email.py`, so 0.320 of margin is unclaimed and reachable only by
  asking.
- **The adapter applies**: `triage_run` now runs the identity gate before scoring,
  so a null result cannot be confused with an adapter that was never served.

## What it is not

Not a comparison with `kernel-mt`. P34 already measured that arm, and re-running it
would buy a number this brief can cite.
