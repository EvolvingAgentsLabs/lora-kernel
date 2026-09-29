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
