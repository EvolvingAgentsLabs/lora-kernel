"""Three tools over one inbox. They answer; they never guess.

EACH ONE SUPPLIES A FACT THAT IS NOT IN THE LISTING, which is what makes asking a
decision rather than a copy — the property P21 had to rebuild the fluid suite to get.

    thread_history   who wrote what in this thread, including whether I did
    sender_stats     how much real correspondence exists with this address
    message          the full text, headers included

A TOOL THAT QUIETLY RETURNS SOMETHING PLAUSIBLE turns a model's mistake into a number
nobody can see, so an unknown id is an error rather than an empty result.
"""

from __future__ import annotations

import json

TOOLS = ("thread_history", "sender_stats", "message")


class ToolError(ValueError):
    pass


def _args(text: str) -> dict[str, str]:
    out = {}
    for part in text.replace("\n", " ").split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            raise ToolError(f"argument {part.strip()!r} is not key=value")
        k, _, v = part.partition("=")
        out[k.strip().lower()] = v.strip()
    if not out:
        raise ToolError("no arguments")
    return out


def thread_history(inbox: dict, text: str) -> str:
    a = _args(text)
    tid = a.get("thread_id") or a.get("thread") or a.get("id")
    if not tid:
        raise ToolError("thread_history needs thread_id")
    hist = inbox["threads"].get(tid)
    if hist is None:
        raise ToolError(f"no thread {tid!r}; ids look like thr-000")
    me = inbox["me"]
    return json.dumps({
        "turns": len(hist),
        "i_wrote_in_thread": any(h["from"] == me for h in hist),
        "participants": sorted({h["from"] for h in hist}),
    })


def sender_stats(inbox: dict, text: str) -> str:
    a = _args(text)
    who = a.get("address") or a.get("sender") or a.get("from")
    if not who:
        raise ToolError("sender_stats needs address")
    n = inbox["sent_counts"].get(who)
    if n is None:
        # AN ADDRESS WE HAVE NEVER WRITTEN TO IS A FACT, not an error: zero is the
        # answer. An address that is not in this inbox at all is the error.
        if not any(m["from"] == who for m in inbox["messages"]):
            raise ToolError(f"no sender {who!r} in this inbox")
        n = 0
    return json.dumps({"messages_i_sent_them": n, "frequent": n >= 5})


def message(inbox: dict, text: str) -> str:
    a = _args(text)
    mid = a.get("id") or a.get("message_id")
    if not mid:
        raise ToolError("message needs id")
    m = next((x for x in inbox["messages"] if x["id"] == mid), None)
    if m is None:
        raise ToolError(f"no message {mid!r}; ids look like msg-000")
    hist = inbox["threads"][m["thread_id"]]
    last = hist[-1]
    return json.dumps({
        "from": m["from"], "subject": m["subject"],
        "to": last.get("to", []), "cc": last.get("cc", []),
        "body": last["preview"],
        "addressed_directly": inbox["me"] in last.get("to", []),
    })


HANDLERS = {"thread_history": thread_history, "sender_stats": sender_stats,
            "message": message}


def answer(inbox: dict, name: str, body: str) -> str:
    if name not in HANDLERS:
        raise ToolError(f"no tool named {name!r}; this inbox has {sorted(HANDLERS)}")
    return HANDLERS[name](inbox, body)


# The same three, as an OpenAI client would declare them. The `enum` on `property`
# is absent on purpose: P28 measured enums as harmful and they are not carried.
SCHEMA = [
    {"type": "function", "function": {
        "name": "thread_history",
        "description": "who has written in a thread, and whether I did",
        "parameters": {"type": "object",
                       "properties": {"thread_id": {"type": "string"}},
                       "required": ["thread_id"]}}},
    {"type": "function", "function": {
        "name": "sender_stats",
        "description": "how much I have written to an address",
        "parameters": {"type": "object",
                       "properties": {"address": {"type": "string"}},
                       "required": ["address"]}}},
    {"type": "function", "function": {
        "name": "message",
        "description": "the full message, with headers",
        "parameters": {"type": "object",
                       "properties": {"id": {"type": "string"}},
                       "required": ["id"]}}},
]
