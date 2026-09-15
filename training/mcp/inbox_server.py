"""The inbox tools as an MCP server, so a real agent can actually use the expert.

WHY THIS EXISTS. P43 ran the end-to-end and found the honest limit of it: the
OpenClaw turn made **no tool calls at all**. OpenClaw sends its *own* tools, not the
inbox's, so `email-full` answered from the listing alone — which is what the base
does and what P31 measured at 0.345 **[ran]**. The 0.741 comes from `agent_sim`,
which supplies the three tools and executes them. **The agent turn demonstrated the
transport; the suite demonstrated the expert; nothing demonstrated both.**

This closes that gap: OpenClaw speaks MCP (`mcp.servers.<name>` in its own config
schema **[read]**), so the same three tools the suite uses become tools the agent
owns.

IT SERVES THE SYNTHETIC INBOX, ON PURPOSE. `training/email/inbox.generate` draws a
deterministic inbox from a seed. **No real correspondence is read, opened or
forwarded by this server** — the demo is reproducible and costs the user nothing.
Pointing it at real mail would be a different program with a different review.

    python3 -m training.mcp.inbox_server --seed 717171 --n 150
"""

from __future__ import annotations

import argparse
import json
import sys

from training.email.inbox import generate
from training.email.tools import SCHEMA, ToolError, answer

PROTOCOL = "2025-06-18"


def _args_to_body(name: str, args: dict) -> str:
    """MCP hands structured arguments; the tools read `key=value; key=value`."""
    return "; ".join(f"{k}={v}" for k, v in (args or {}).items())


def handle(msg: dict, inbox: dict) -> dict | None:
    """One JSON-RPC message. `None` means a notification with no reply."""
    method, mid = msg.get("method"), msg.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "lora-kernel-inbox", "version": "1.0.0"}}}

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "tools/list":
        # ANNOTATIONS, BECAUSE THEIR ABSENCE IS WHAT BLOCKED THE FIRST DEMO.
        # `openclaw mcp probe` reported *"tools have no safety annotations; calls
        # require approval in prompting session postures"*, so a non-interactive
        # turn had nobody to approve and the agent answered from the listing with
        # zero tool calls — the very failure this server exists to remove
        # **[ran]** 2026-09-15.
        #
        # These are declared because they are TRUE, not to get past a gate: all
        # three are lookups over an in-memory synthetic inbox. They read, they do
        # not write, the same arguments give the same answer, and nothing outside
        # this process is touched. A tool that wrote anything would not carry
        # `readOnlyHint` and would deserve the approval prompt.
        annotations = {"readOnlyHint": True, "destructiveHint": False,
                       "idempotentHint": True, "openWorldHint": False}
        tools = [{"name": t["function"]["name"],
                  "description": t["function"]["description"],
                  "inputSchema": t["function"]["parameters"],
                  "annotations": {**annotations,
                                  "title": t["function"]["description"]}}
                 for t in SCHEMA]
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": tools}}

    if method == "tools/call":
        p = msg.get("params") or {}
        name = p.get("name")
        try:
            out = answer(inbox, name, _args_to_body(name, p.get("arguments")))
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": out}], "isError": False}}
        except ToolError as e:
            # A TOOL ERROR IS A RESULT, NOT A TRANSPORT FAILURE. The agent should
            # see what it did wrong and ask again, which is exactly what the suite
            # measures — `agent_sim` counts these as `refused` and carries on.
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": f"ERROR: {e}"}],
                "isError": True}}
        except Exception as e:                       # noqa: BLE001
            return {"jsonrpc": "2.0", "id": mid, "error": {
                "code": -32603, "message": repr(e)[:200]}}

    if mid is None:
        return None
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": f"no method {method!r}"}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=717171,
                    help="the suite's own seed, so the demo matches what was scored")
    ap.add_argument("--n", type=int, default=150)
    args = ap.parse_args()

    inbox = generate(args.n, args.seed)
    # stderr, never stdout: stdout is the protocol channel and a stray print on it
    # corrupts the stream in a way the client reports as a parse error.
    print(f"[inbox-mcp] synthetic inbox: {args.n} messages, seed {args.seed}",
          file=sys.stderr, flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle(msg, inbox)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
