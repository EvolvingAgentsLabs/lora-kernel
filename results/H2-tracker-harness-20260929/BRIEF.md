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

## Result **[ran]** 2026-09-29 — as written **FALSIFIED**, because the comparison arm is void; the harness met the two conditions that can be read (146/160, flat)

Scoring attempt 2, one L4, vLLM 0.30, `tr-s0`. G1 applied. `h2.json`, `S_chain.log`.

| | `base-history` (bare base) | **`harness`** (`tr-s0`) | `harness-noblock` (`tr-s0`) |
|---|--:|--:|--:|
| first turns | 44/60, **void** (< 90 %) | **60/60** | 40/60, **void** (< 90 %) |
| dependent turns | 4/160 | **146/160 (91.3 %)** | 80/160 |
| independent control | 0/60 | 50/60 | 40/60 |
| prompt tokens by turn, $\bar p_1 \ldots \bar p_5$ | 577, 379, 433, 434, 495 | 1613, 1223, 1011, 1149, 1274 | 378, 313, 240, 398, 310 |

**By the conditions written first:**
- `harness`'s dependent turns 146/160 = 91.3 % ≥ 90 %: **met**.
- Flat, $\bar p_5 = 1274 \le 1.1 \times 1613$: **met**.
- "An improvement over `base-history`": **unreadable**, because `base-history` is void by the per-arm first-turns rule (44/60).
- `session_arm.reading` returns **FALSIFIED** when that comparison cannot be made (`beats base-history=None`). The code was not changed after the result; this is recorded as the verdict *as written*.
- `harness-noblock` is void by the same rule (40/60).

**Read where it happens.**
1. **The void comparison is a second instrument error of the same family as H1's.** The first-turns rule was meant to catch
   an arm that the *rendering* broke. `base-history` is not broken by a rendering: it is an untrained base that does not
   know the tracker's protocol, which is exactly the headroom H2 measures. It gets `issue_get` right (40/40) and nearly
   everything else wrong: `issue_create` 4/20, transitions 0/40, pages 0/60. A rule meant to void a broken treatment
   voided the untrained baseline, and with it the comparison. Descriptively, paired on the same 160 dependent turns,
   harness 146 against base 4: **142 : 0, exact sign test $p \lt  10^{-40}$**.
2. **Where the harness fails (14 of 160 dependent, 10 of 60 independent), all in QA:**
   - "Where must tests pass?" → the member reads the whole page `definition-of-done` rather than `#tests` (10/20). The
     statement it needs is in what it read, so the check asks for the exact anchor. **That check can fail while the
     capability works** (CLAUDE.md §3: measuring phrasing). It is recorded, not loosened after the result.
   - QA's final comment (6/20): the member re-reads the issue, or tries a transition the workflow refuses
     (`done → in_review`), instead of commenting. A genuine miss.
3. **Without the tool block (a third of the corpus rendered that way):** 80/160, against H1's 0/60. The member now calls
   tools by name: developer transitions and comments 20/20, the QA lane whole. The lead's lane is still missing
   (`issue_create`/`assign`/`get` 0/20), so it is **learned in part**.
4. **Tokens.** The harness's per-turn prompt is flat over five turns (1,613 → 1,274). The base's is also nearly flat, because
   it barely writes anything to carry. In absolute terms the harness reads ~2.5× the base per turn (more steps, and the
   block).

**Decision for the user:** accept the readable conditions as H2's verdict (the harness met both, with a descriptive 142 : 0
over the base), with the void comparison and the anchor check recorded as instrument errors; or keep "FALSIFIED as written"
and rerun with a baseline that can be read (the per-arm rule applied only to trained members, and the anchor check
counting a page read that contains the statement).

**The user's decision, 2026-09-29: reading 1.** H2's verdict is the readable conditions — **the harness PASSED:** 146/160
dependent (≥ 90 %), flat over five turns, descriptively 142 : 0 over the bare base. "FALSIFIED as written" stays on record,
with its two instrument errors: the per-arm VOID asked of an untrained baseline, and the anchor check that measured
phrasing. Not rerun: no rule could move a baseline at 4/160.

**Two corrections, read afterwards in the records [ran] (no number above changes):**
- *Block-less "learned in part" was the corpus, not the member.* `--harness-corpus` rendered its block-less third by
  `j % 3 == 2`, and the roles rotate by `% 3`: all 400 block-less rows were QA's. The member learned block-less exactly
  the role it was shown (QA 80/80); the lead's lane was never shown (`gate_harness.json`, `rows_without_tool_block_by_kind`).
- *QA's final comment (6/20) is one phrasing:* "Note on it: …" 1/15, "Put a comment on it: …" 5/5.

Both are what H3 trains against ([`../H3-tracker-corpus-v2-20260929/BRIEF.md`](../H3-tracker-corpus-v2-20260929/BRIEF.md)).
