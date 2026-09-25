"""One agent turn over a domain's tool layer — the loop the gateway and the demos share.

The model writes inline tags (`<agenda_read>1</agenda_read>`, `<billing_charge>membership_id=1;
amount_cents=4500</billing_charge>`) the way `training/harness/openai_proxy.render_tools` teaches it;
`run_chain` stops at each closing tag; this suite executes the call with the SIGNED-IN USER'S CLAIM —
never with anything the model wrote — and writes the result inline. Three outcomes a call can have,
each recorded: a result; a denial raised by the tool layer (another tenant's row); or, for a tool in
`approvals.NEEDS_APPROVAL`, a hold — the call is queued for a person and NOT executed.
"""
from __future__ import annotations

import re
import threading

# ONE WRITER AT A TIME ON A DEMO STORE. sqlite refuses a connection used from a thread other than the one
# that opened it, and the gateway serves each request on its own thread — the fake server caught it on the
# Mac before a card did [ran] 2026-09-25. Only the tool call is serialised, never the model's generation.
DB_LOCK = threading.Lock()


def parse_args(schema: list[dict], name: str, body: str) -> dict:
    """`k=v; k=v` for several parameters; a bare body for a tool with exactly one; nothing for none."""
    body = body.strip()
    if "=" in body:
        out = {}
        for part in body.split(";"):
            k, _, v = part.partition("=")
            if k.strip():
                out[k.strip()] = v.strip()
        return out
    params = next((t["function"]["parameters"].get("properties", {}) for t in schema if t["function"]["name"] == name), {})
    return {next(iter(params)): body} if body and params else {}


class ToolSuite:
    """`run_chain`'s suite: `tools` is a domain module (`examples.school.tools`, `examples.distributor.tools`)."""

    def __init__(self, conn, claim, names: list[str], tools, queue=None):
        self.conn, self.claim, self.names, self.tools, self.queue = conn, claim, names, tools, queue
        self.close = tuple(f"</{n}>" for n in names)
        self.tag = re.compile(r"<(" + "|".join(map(re.escape, names)) + r")>([^<]*)</\1>")
        self.positional: dict = {}
        self.calls: list[dict] = []

    def answer(self, _inbox, name: str, raw: str) -> str:
        from training.email.tools import ToolError
        from .approvals import NEEDS_APPROVAL
        from .permissions import Denied
        args = parse_args(self.tools.SCHEMA, name, raw)
        if self.queue is not None and name in NEEDS_APPROVAL:
            out = self.queue.hold(self.claim, name, args)
            self.calls.append({"tool": name, "args": args, "held": out})
            return out
        try:
            with DB_LOCK:
                out = self.tools.answer(self.conn, self.claim, name, args)
            self.calls.append({"tool": name, "args": args, "result": out})
            return out
        except Denied as e:
            self.calls.append({"tool": name, "args": args, "denied": str(e)})
            raise ToolError(f"permission denied: {e}")
        except (self.tools.ToolError, KeyError, ValueError) as e:
            self.calls.append({"tool": name, "args": args, "error": str(e)})
            raise ToolError(str(e))

    def parse(self, text: str):
        return text.strip() or None

    def wrap(self, gen):
        return gen
