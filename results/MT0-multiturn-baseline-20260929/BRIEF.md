# MT0 — the multi-turn baseline, before the workflow harness (pre-registered 2026-09-29)

**Why.** Every demo so far is one turn. A real conversation refers back: "move it to dock 5", "file a claim about that
order", "reorder whichever is lowest". The gateway reads only the last request (`runtime_request`), so today "it" has no
referent. The user's proposal is a workflow harness in the member: a domain's state machine, and context values kept
under keys in a cache rather than in the prompt (docs/review/harness-workflow-kv.md). It must be measured against
something. This run sets the two baselines it will face, and says whether there is room for it.

**The suite** (`examples/distributor/generate_sessions.py`, gate passed at zero GPU):
- 60 held-out sessions (124 turns) by one user in one role, each on its own synthetic world.
- **54 dependent turns**: the right call's argument is an id the user named earlier or a value an earlier tool returned
  (the lowest stock item, the order on the open return). The dependent request never contains it (gate S4).
- One session type ends with an independent turn, the control.
- Every turn is checked mechanically by tool and arguments (`call_matches`).
- The oracle, played through the gateway with history, gets every turn right (gate S3).

**Arms.** `out-s0` (M10's member) on `google/gemma-4-E4B-it` bf16, vLLM 0.30, one Colab L4 session:

| arm | what the model reads on turn $i$ |
|---|---|
| `last` | today's gateway: the role's prompt and tools, and the last request only |
| `history` | the same, plus every earlier request and the reply shown for it (`Gateway(history=True)`), the naive way to carry a conversation |

**Reading, written first (`session_arm.reading`).**

| outcome | reading |
|---|---|
| an arm gets under 90 % of its **first** turns right | **VOID**: the rendering broke the member, not the conversation |
| `history` gets under 80 % of the dependent turns | **HEADROOM**: the harness has room on accuracy, beside cost |
| `history` gets 80 % or more | **NO ACCURACY HEADROOM**: the harness's case rests on context cost, reported beside |

Beside the reading: the dependent turns under `last` (expected near 0, since the referent is missing), and the mean prompt
tokens per turn by position, $\bar p_1, \bar p_2, \bar p_3$, for both arms. That is the growth the harness would flatten.

**Stopping condition.** One session; no redesign after the result.

**Not in this run.** The harness itself (it needs the design reviewed and a corpus); concurrency (C1, next); sessions
longer than three turns; OpenClaw's own history (its messages carry the same conversation, plus its context block).

## Result **[ran]** 2026-09-29 — **HEADROOM, at the edge: 43/54 dependent turns with history (79.6 %), 4/54 without**

One L4 session, vLLM 0.30, `out-s0`. G1 applied. `mt0.json`, `chain.log`. First turns 60/60 in both arms and the
independent control 10/10 in both, so neither arm is void.

| session kind (dependent turns) | `last` | `history` |
|---|--:|--:|
| dispatch: "its delivery note", "is it delivered yet?" | 0/14 | 12/14 |
| receiving: "move it to dock 5" | 0/10 | **10/10** |
| claims & returns: "another one on the same order" | 0/10 | **10/10** |
| purchasing: "reorder whichever is lowest" | 4/10 (chance: one of three items) | 9/10 |
| **customer service: "file a claim about that order"** | 0/10 | **2/10** |
| **all dependent** | **4/54** | **43/54** |

Mean prompt tokens by position: `last` 345, 376, 303; `history` 345, 428, 394. The third turn is lower than the second in
both arms because only dispatch sessions reach it, and their prompts are shorter.

**By the table written first: HEADROOM**, since 43/54 is under 80 %, if only just.

**Read where it happens.**
1. **Without the conversation the member cannot resolve a reference at all**: 0/44 outside purchasing, and purchasing's
   4/10 is chance.
2. **With history it resolves a reference it only has to copy into an argument:** an order id into `dock_assign`,
   `return_create` or `delivery_status`, 32/34.
3. **It does not resolve a reference it has to write into free text.** Asked to file a claim about "that order", the
   member copies the user's words ("The seal on that order was broken") and files a claim **with no order number**, in
   8 of 10 cases. In a real system that claim would reach nobody. This is the failure the workflow harness is built for:
   the step's needed value (the `order` key) is fetched and written into the call, rather than left to the model's
   reading of the history.
4. Two dispatch misses write `#28` (copied from an earlier reply's "order #28") where the tool wants `28`.
5. **Context growth is small in two- and three-turn sessions**: +24 % at turn 2 with history. The cost side of the
   harness's case needs longer sessions to show; this suite does not measure it.

**What it sets for H1** (docs/review/harness-workflow-kv.md §5): the harness must match `history`'s 43/54 on the dependent
turns (≤ 3 lost) and should win on customer service's free-text references, which is where history fails. The token bar
applies to sessions long enough to grow, so a longer session type is added to the harness's suite.
