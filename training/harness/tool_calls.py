"""Between the tags the adapter writes and the `tool_calls` a client expects.

THE QUESTION THIS SETTLES. P26 ended with an endpoint an agent can call and an agent
that would see nothing usable — the adapters emit `<lookup>material=X; property=Y
</lookup>` in the message body, and OpenAI clients read a `tool_calls` array. That
brief said bridging it "reintroduces the hand-written harness the weights were meant
to replace", and that sentence conflates two things:

    deciding which tool and what arguments   the protocol — 144 lines of rule
                                             transfer 0 of 63 to a new subject,
                                             the adapter 27 of 63 [ran] P25
    serialising a decided call into JSON     a format converter

THIS FILE IS THE SECOND ONE AND ONLY THE SECOND ONE. It contains no tool names, no
argument lists, no unit table, no fluid names, no label vocabulary and no phrasings.
It reads whatever tag it is given and whatever `key=value` pairs are inside it. That
is what makes it a serializer rather than a harness: a new domain costs it nothing,
where the rule costs 38 of its 109 lines.

IT DOES NOT PARSE VALUES INTO TYPES. `value=3.4` becomes the string `"3.4"`, because
the tool on the other side takes text and typing it here would be this module
deciding what a domain's arguments mean — the exact thing it must not do.
"""

from __future__ import annotations

import json
import re

# Any tag whose body has no angle brackets. The tool names are not listed anywhere
# in this module, on purpose: listing them is the first line of a harness.
CALL = re.compile(r"<([A-Za-z_][\w-]*)>([^<]*)</\1>")
PAIR = re.compile(r"([\w.\-]+)\s*=\s*([^;,]*)")


def to_tool_calls(text: str) -> list[dict]:
    """Every call in a message body, as OpenAI `tool_calls` entries."""
    out = []
    for i, m in enumerate(CALL.finditer(text)):
        name, body = m.group(1), m.group(2)
        args = {k.strip(): v.strip() for k, v in PAIR.findall(body)}
        # A body with no `key=value` in it is a positional argument — `<calc>` takes
        # an expression, not a keyed list. It is handed over under a reserved key
        # rather than dropped, because dropping it would lose the call.
        if not args and body.strip():
            args = {"_": body.strip()}
        out.append({
            "id": f"call_{i}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        })
    return out


def from_tool_call(call: dict) -> str:
    """Back to the tag the harness answers. The round trip has to be exact."""
    fn = call["function"]
    args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
    if list(args) == ["_"]:
        body = args["_"]
    else:
        body = "; ".join(f"{k}={v}" for k, v in args.items())
    return f"<{fn['name']}>{body}</{fn['name']}>"


def strip_calls(text: str) -> str:
    """The message body with its calls removed — what `content` becomes."""
    return CALL.sub("", text).strip()


def tools_to_instruction(tools: list[dict], arity: bool = False,
                        enums: bool = False) -> str:
    """An OpenAI `tools=[…]` schema, rendered as the tag surface the adapter knows.

    THIS IS THE HALF THAT IS NOT FREE, and it is named rather than hidden. The
    adapter was trained on three tag names; a client offering `search_flights` gets
    a line telling the model that tag exists, and nothing in the weights knows what
    it means. P25 measured what that costs: on a subject it had never seen, the
    adapter reached 27 of 63 — it knows *that* a step needs a query and gets the
    names wrong. **A claim that the adapter does function-calling would be a claim
    about this function.**
    """
    lines = []
    for t in tools:
        fn = t.get("function", t)
        params = (fn.get("parameters") or {})
        props = params.get("properties") or {}
        keys = sorted(props)
        required = params.get("required") or keys

        # CONVENTION A — ARITY. A function with exactly one required parameter is
        # rendered positionally. This keys on a COUNT, not on a name: nothing here
        # knows which tool it is looking at. P27 measured what its absence costs —
        # 33 of 93 refusals were `<calc>expression=...</calc>` against a model
        # trained on `<calc>1.2 * 3</calc>` [ran].
        if arity and len(required) == 1:
            shape = "..."
        else:
            def one(k):
                # CONVENTION B — ENUMS. A parameter that declares its allowed values
                # shows them. The names are schema, written by whoever declared the
                # tool; the values behind them stay data, so the adapter still has to
                # call the tool to learn what a modulus is.
                vals = (props.get(k) or {}).get("enum") if enums else None
                return f"{k}={'|'.join(map(str, vals))}" if vals else f"{k}=..."
            shape = "; ".join(one(k) for k in keys) or "..."

        lines.append(f"<{fn['name']}>{shape}</{fn['name']}>"
                     + (f"  — {fn['description']}" if fn.get("description") else ""))
    return ("The following tools are available. Ask for one by writing its tag on "
            "the line that needs it:\n" + "\n".join(lines)) if lines else ""
