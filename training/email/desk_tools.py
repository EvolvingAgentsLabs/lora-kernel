"""The desk's tool surface: the inbox three, plus the one they were missing.

WHY A SEPARATE MODULE AND NOT AN EDIT. `training/email/tools.py` is the surface the
triage corpus was generated against, and P38 measured what happens when a corpus and
a served surface drift apart: **71 refusals of 606 calls that looked like physics**,
and a whole run void. Adding a fourth tool there would silently change the prompt
every existing adapter was trained on. So the desk gets its own surface and the
triage one is left exactly as it was.

THE MISSING TOOL, AND IT WOULD HAVE VOIDED THE RUN. `desk.py` asks two questions
about the **whole inbox** — *which message am I most overdue to answer* and *who do I
correspond with most* — while the listing shows exactly one message. With only
`thread_history`, `sender_stats` and `message`, a model cannot even enumerate what it
is being asked about: it has no way to learn that `msg-007` exists. Both regions would
have scored near zero for every arm, and the failure would have read as *the models
cannot do this* rather than *the suite forgot to make it answerable*.

`inbox` is that enumeration, and it is deliberately thin — ids, senders and subjects,
which is what a mail client's list pane shows. **It carries no fact any answer depends
on**: not whether you wrote in the thread, not how often you write to someone, not
what was promised. Those stay behind the other three, so asking remains a decision.
"""

from __future__ import annotations

import json

from training.email.tools import (  # noqa: F401  (re-exported on purpose)
    ToolError,
    message,
    sender_stats,
    thread_history,
)
from training.email.tools import SCHEMA as _INBOX_SCHEMA

TOOLS = ("inbox", "thread_history", "sender_stats", "message")


def inbox(desk: dict, text: str = "") -> str:
    """Every message id with its sender and subject. The list pane, nothing more."""
    return json.dumps([{"id": m["id"], "thread_id": m["thread_id"],
                        "from": m["from"], "from_name": m["from_name"],
                        "subject": m["subject"]}
                       for m in desk["messages"]])


HANDLERS = {"inbox": inbox, "thread_history": thread_history,
            "sender_stats": sender_stats, "message": message}


def answer(desk: dict, name: str, body: str) -> str:
    if name not in HANDLERS:
        raise ToolError(f"no tool named {name!r}; this desk has {sorted(HANDLERS)}")
    return HANDLERS[name](desk, body)


SCHEMA = [
    {"type": "function", "function": {
        "name": "inbox",
        "description": "list every message in the inbox with its sender and subject",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    *_INBOX_SCHEMA,
]
