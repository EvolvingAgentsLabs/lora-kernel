# H2 — the workflow harness on long sessions: a team tracker (Jira + Confluence-like) (pre-registered 2026-09-29)

**Why.** H1 **[ran]** showed the harness on two- and three-turn sessions: per arm, `harness` resolved 53/54 dependent
turns against the conversation-in-the-prompt's 43/54, keeping the per-turn prompt flat. Two things were left open:
- the **token** case, which needs sessions long enough for a carried conversation to grow;
- the **no-block** failure: 0/60, because the member never saw its tools undescribed.

The user chose the domain (2026-09-29): a development team's Jira + Confluence. It has explicit workflows, natural keys
and long sessions.

**The domain** (`examples/tracker/`, synthetic, gated):
- two organisations with issues `RD-12` / `HW-7` (stories and bugs), people, sprints, comments (some with a planted
  instruction), worklogs, and a Confluence-like space of atomic statements: the definition of done, component owners, the
  release process, the bug policy;
- the tool layer decides tenancy from the claim and **enforces each issue type's declared workflow** (TOML), as Jira's
  workflow scheme does;
- three roles, developer, lead and QA, each with a session workflow for the harness.

**The suite** (`examples/tracker/generate_sessions.py`, gate passed at zero GPU): 60 held-out sessions of four and five
turns, **280 turns, 160 dependent**. A dependent turn's argument is:
- a key named earlier ("move it to review");
- a key an earlier tool **created** ("show me the bug you just created");
- or a value an earlier result showed, whose meaning a page states ("who owns its component?").

The harness oracle solves every session through the gateway, with and without the tool block.

**The corpus.** `train_harness.jsonl`, 1,400 rows from 300 training sessions: 800 with `get`, 300 with `put`. **A third of
the sessions are rendered without the tool block** (400 rows), H1's lesson, so the member learns its tools by name. The
member is `tr-s0`, `google/gemma-4-E4B-it` + LoRA, the unchanged recipe, one L4 (`session_arm --train-seed 0`).

**Arms**, on the 60 held-out sessions, one L4, vLLM 0.30:

| arm | model | what it reads on a turn |
|---|---|---|
| `base-history` | the bare base | the conversation in the prompt + the tool block: serving a new domain today, with no member |
| `harness` | `tr-s0` | the context line (state · key names) + the request + the tool block |
| `harness-noblock` | `tr-s0` | the context line + the request, no tool block |

**Verdict, written first (`session_arm.reading`). A VOID is per arm**, H1's lesson: an arm whose first turns fall under
90 % is void, not the run.

| condition | bar |
|---|---|
| `harness`'s dependent turns | ≥ 90 % (an absolute standard, CLAUDE.md §3) |
| `harness` against `base-history` on the dependent turns | an improvement: exact paired sign test, $p \lt  0.05$ |
| `harness`'s prompt tokens on the last turn against the first | $\bar p_5 \le 1.1\ \bar p_1$ |
| `harness-noblock` against `harness` | loses no more than 8 of the 160 dependent turns (5 %) |

The first three → **PASSED**; the no-block condition is read beside it. Reported beside: `base-history`'s token growth
over five turns, which is the cost the harness removes.

**Stopping condition.** One seed, one scoring session. There is no redesign after the result.

**Not in this run.** A member trained on the same sessions in history format, the attribution arm, to be bought only if
H2 passes and the question becomes *memory or training*; OpenClaw live; the global cache across sessions.

**Scoring attempt 1 [ran] 2026-09-29: void, a transport fault; nothing was measured.** Every request of every arm, 420
turns, came back `HTTP 400` (`h2_attempt1_void_http400.json`, `S_attempt1_void_http400.log`). Every configuration that had
worked sent at most four stop sequences: the school's largest role has 4 tools, the distributor's harness 2 + `get`/`put`.
A tracker role sends 5 to 8. `accept_rank.completion` now stops at the generic `</` when a role has more than four closing
tags and puts the tag back (`close_open_tag`, as for llama.cpp); the error now carries the server's reason; a session with
a transport error is played again on resume. The member (`tr-s0`) and the verdict are unchanged; scoring reruns.
