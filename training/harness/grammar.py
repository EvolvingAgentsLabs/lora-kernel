"""A grammar mask for tool calls: malformed becomes impossible, not unlikely.

WHY. P21 measured a learned protocol tying a hand-written rule on coverage —
94/96 against 93/96 — and losing on cleanliness: **20 of its 116 calls were refused
by the tools, against the rule's 0** [ran] `results/P21-handbook-20260911/`. The
adapter is not worse at knowing what to ask. It is worse at saying it, because a
rule assembles characters and a model emits them.

A sampler can close that. This is the same move `capability-kernel` and `llm_os`
made with a token trie, pointed at the tool-call surface: at each step, compute the
set of characters that can still begin a valid call, and mask everything else.

IT IS A RUNTIME PRIMITIVE, NOT A SECOND MODEL. No weights, no extra forward pass,
nothing learned. The protocol's intelligence stays in the adapter; this only makes
the adapter unable to mistype it.

WHAT IT CANNOT DO, and the brief says so before the run: a well-formed query for
the wrong thing passes every grammar. `fluid=glycerin` on a problem about water is
valid syntax. The mask removes rejections; it cannot remove wrong arguments.

    from training.harness.grammar import CallGrammar
    g = CallGrammar()
    g.allowed("<look")          # the characters that can come next
"""

from __future__ import annotations

import re

from training.physics.tools import TOOLS, UNITS

# The keys each tool accepts, in the order the corpus writes them. Order is not
# enforced — a model that writes `property=` before `fluid=` has made a formatting
# choice, and `_args` accepts it, so the grammar does too.
KEYS: dict[str, set[str]] = {
    "lookup": {"fluid", "property", "t"},
    "convert": {"value", "from", "to"},
    "calc": set(),          # a free expression, checked by the evaluator not here
}
VALUES: dict[tuple[str, str], set[str] | None] = {
    ("lookup", "property"): {"density", "viscosity"},
    ("convert", "from"): set(UNITS),
    ("convert", "to"): set(UNITS),
}

OPEN = re.compile(r"<(%s)>" % "|".join(TOOLS))


class CallGrammar:
    """Which characters may follow a partial call. Never which are likely."""

    def __init__(self, tools: tuple[str, ...] = TOOLS):
        self.tools = tools

    # -- the states a partial call can be in -------------------------------
    def state(self, text: str) -> tuple[str, str]:
        """(state, payload) for the tail of `text` after the last complete call."""
        m = None
        for m in OPEN.finditer(text):
            pass
        if m is None:
            return ("tag", text[text.rfind("<") + 1:] if "<" in text else "")
        tool = m.group(1)
        body = text[m.end():]
        if f"</{tool}>" in body:
            return ("done", tool)
        return ("body", tool + "\x00" + body)

    def allowed(self, text: str) -> set[str] | None:
        """The characters that may come next, or None for "anything".

        None is returned for a `calc` body and for prose outside a call, because
        this grammar constrains the *protocol*, not the physics. Masking an
        arithmetic expression would be masking the expert's work.
        """
        kind, payload = self.state(text)
        if kind == "tag":
            return self._tag_chars(payload)
        if kind == "done":
            return None
        tool, body = payload.split("\x00", 1)
        if tool == "calc":
            return None
        return self._body_chars(tool, body)

    def _tag_chars(self, partial: str) -> set[str] | None:
        """Inside `<…>`: only prefixes of a real tool name can continue."""
        if "<" not in partial and partial == "":
            return None                       # not in a tag at all
        names = [t for t in self.tools if t.startswith(partial)]
        if not names:
            return set()                      # dead end: nothing is valid
        out = {n[len(partial)] for n in names if len(n) > len(partial)}
        if partial in self.tools:
            out.add(">")
        return out

    def _close_chars(self, tool: str, partial: str) -> set[str]:
        want = f"</{tool}>"
        if not want.startswith(partial):
            return set()
        return {want[len(partial)]} if len(want) > len(partial) else set()

    def _body_chars(self, tool: str, body: str) -> set[str] | None:
        """THE CHECKER FOUND BOTH OF THIS FUNCTION'S BUGS BEFORE A GPU DID.

        `T=20` was blocked because `_args` lowercases keys and this did too, so the
        only continuation offered for `t` was lowercase. And `to=m</convert>` was
        blocked because the tail was split on separators but not on the closing
        tag, so the value being completed was `m</convert>`, which prefixes no unit.
        Both are the same mistake: comparing what the model writes against a
        normalised form of what the tool accepts.
        """
        # ONCE `<` IS WRITTEN THE CALL IS CLOSING, and only `/tool>` completes it.
        # Without this the mask allowed `<` and then refused the `/` after it — a
        # dead end it had opened itself, and the third bug the checker caught.
        if "<" in body:
            return self._close_chars(tool, body[body.rfind("<"):])
        keys = KEYS[tool]
        seen = {k.lower() for k, _ in re.findall(r"(\w+)\s*=\s*([^;,<]*)", body)}
        tail = re.split(r"[;,]", body)[-1]
        if "=" not in tail:
            key = tail.strip().lower()
            live = [k for k in keys if k.startswith(key) and
                    (k == key or k not in seen)]
            if not live:
                return set()
            out = set()
            for k in live:
                if len(k) > len(key):
                    out |= {k[len(key)], k[len(key)].upper()}
            if key in keys:
                out.add("=")
            out.add(" ")
            return out
        key, val = tail.split("=", 1)
        allowed = VALUES.get((tool, key.strip().lower()))
        if allowed is None:
            return None                       # free value: a number or a name
        val = val.strip()
        live = [v for v in allowed if v.lower().startswith(val.lower())]
        if not live:
            return set()
        out = set()
        for v in live:
            if len(v) > len(val):
                out |= {v[len(val)], v[len(val)].upper(), v[len(val)].lower()}
        if any(v.lower() == val.lower() for v in allowed):
            out |= {";", ",", "<", " "}
        return out
