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


# NAMESPACE PUNCTUATION, which is the only thing this module knows about how agent
# runtimes rename a tool. OpenClaw offers an MCP tool as `mcp__<server>__<tool>`;
# other runtimes use a dot, a slash or a colon. Keying on the punctuation rather
# than on a prefix list keeps this a serializer: it recognises *that* a name is
# namespaced, never *which* namespace it came from.
NAMESPACE = re.compile(r"__|[./:]")


def _tail(name: str) -> str:
    return NAMESPACE.split(name)[-1]


def _keys(t: dict) -> set[str]:
    fn = t.get("function", t)
    return set((fn.get("parameters") or {}).get("properties") or {})


def prune(tools: list[dict], surface: list[str],
          args: dict | None = None) -> tuple[list[dict], dict, dict]:
    """Keep only the offered tools the member has a tag for, under the tag's name.

    WHY THIS EXISTS. P43 ran the end-to-end and the agent turn made **no tool calls
    at all** — OpenClaw offers its own toolbox, and `email-full` was trained on three
    tags **[ran]** `results/P43-openclaw-e2e-20260915/`. Two separate things were
    wrong with what it saw, and they have to be fixed separately because they are
    separately measurable:

        VOLUME     dozens of tag names the weights have never seen. P25 measured the
                   cost of an unknown surface at 27 of 63 — it knows a step needs a
                   lookup and gets the name wrong **[ran]**.
        RENAMING   even a tool it does know arrives as `mcp__lora-inbox__message`,
                   which is not the tag `<message>` it writes.

    Returns `(kept, forward, back)`. `kept` is the offered schemas rewritten to the
    member's own tag names, `forward` maps tag -> the caller's name, and `back` is
    its inverse, so a call this adapter writes leaves under the name the caller
    offered. **Without the rename back, pruning would produce calls the agent
    cannot route** — it asked for `mcp__lora-inbox__message` and a `<message>` means
    nothing to it.

    THE MATCH IS BY NAME — EXACT OR THE LAST NAMESPACE SEGMENT — AND THEN BY THE KEYS
    THE MEMBER WRITES. P59 recorded a runtime offering its own `message` tool
    (`action`, `channel`, `target`, …) beside the member's `lora-inbox__message`
    (`id`) **[ran]**; a rule that let the exact name win handed the member's
    `<message>id=…</message>` to a messaging tool. So when `args` names the keys a
    tag is written with, a candidate whose parameters carry all of them beats one
    that does not, whatever its name. With no `args`, an exact name wins as before.
    An ambiguity that survives both rules is **dropped**, because calling the wrong
    one of two tools is worse than calling neither.

    AN EMPTY RESULT IS A RESULT. A member that recognises none of the offered tools
    gets no tools, and the caller sees that in the record rather than in a fallback
    that quietly re-offers the surface P25 already priced.
    """
    args = args or {}
    cands: dict[str, list[dict]] = {t: [] for t in surface}
    for t in tools or []:
        fn = t.get("function", t)
        name = fn.get("name")
        if not isinstance(name, str):
            continue
        tail = name if name in cands else _tail(name)
        if tail in cands:
            cands[tail].append(t)

    def pick(tag: str, hits: list[dict]) -> dict | None:
        if not hits:
            return None
        want = set(args.get(tag) or [])
        if want:
            fitting = [t for t in hits if want <= _keys(t)]
            if len(fitting) == 1:
                return fitting[0]
            if len(fitting) > 1:
                hits = fitting
        exact = [t for t in hits if (t.get("function", t)).get("name") == tag]
        if len(exact) == 1 and not want:
            return exact[0]
        return hits[0] if len(hits) == 1 else None

    kept, forward = [], {}
    for tag in surface:
        t = pick(tag, cands.get(tag) or [])
        if t is None:
            continue                     # absent, or ambiguous and therefore refused
        fn = dict(t.get("function", t))
        forward[tag] = fn["name"]
        fn["name"] = tag
        kept.append({**t, "function": fn} if "function" in t else fn)
    return kept, forward, {v: k for k, v in forward.items()}


def rename_calls(calls: list[dict], forward: dict) -> list[dict]:
    """Put the caller's own names back on the calls the adapter wrote."""
    out = []
    for c in calls:
        fn = dict(c["function"])
        fn["name"] = forward.get(fn["name"], fn["name"])
        out.append({**c, "function": fn})
    return out
