"""The school's tools as an MCP server, so a real OpenClaw instance can call them.

Mirrors `training/mcp/inbox_server.py` byte for byte in shape — same JSON-RPC handling, same
stderr-only logging (stdout is the protocol channel), same `readOnlyHint`/`destructiveHint`
annotations so a non-interactive OpenClaw turn does not stall waiting for approval. What is new
is the identity: a real deployment attaches a `Claim` per session from a verified token: this
process stands in for that by taking `--user`, resolved once at startup against
`common.mock_auth`, exactly as if a runtime had already checked the token and were now telling
the tool layer who is asking. No model, no adapter, no GPU — a bare frontier model pointed at
this server through OpenClaw already exercises the real boundary: MCP, the tool schema, and the
permission check, all before any LoRA exists for this domain.

    python3 -m examples.school.mcp_server --user compras-north
"""
from __future__ import annotations

import argparse
import json
import sys

from . import db, roles, tools, users
from ..common import mock_auth

PROTOCOL = "2025-06-18"

# The same identities `test_adversarial.py` uses — one source (`users.SEED_USERS`), so a case
# run directly in Python or through a live MCP client such as OpenClaw sees the same claims.
users.register_all()


def handle(msg: dict, conn, claim, role: dict) -> dict | None:
    method, mid = msg.get("method"), msg.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
            "serverInfo": {"name": "lora-kernel-school", "version": "1.0.0"}}}

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "tools/list":
        offered = [t for t in tools.SCHEMA if t["function"]["name"] in role["tools"]]
        listed = []
        for t in offered:
            name = t["function"]["name"]
            write = name in tools.WRITE_TOOLS
            # TRUE PER TOOL, NOT A BLANKET. `billing_charge`, `order_draft`, `enrollment_draft`,
            # `announcement_post`, `maintenance_create`, `campaign_create` write; everything
            # else only reads. A client that trusted one shared annotation would let an agent
            # skip approval on a write — training/mcp/inbox_server.py's own rule: annotations
            # are declared because they are true, not to get past a gate.
            annotations = {"readOnlyHint": not write, "destructiveHint": False,
                           "idempotentHint": not write, "openWorldHint": False,
                           "title": t["function"]["description"]}
            listed.append({"name": name, "description": t["function"]["description"],
                           "inputSchema": t["function"]["parameters"], "annotations": annotations})
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": listed}}

    if method == "tools/call":
        p = msg.get("params") or {}
        name = p.get("name")
        if name not in role["tools"]:
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": f"ERROR: {claim.role} may not call {name}"}],
                "isError": True}}
        try:
            out = tools.answer(conn, claim, name, p.get("arguments") or {})
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": out}], "isError": False}}
        except (tools.ToolError, PermissionError) as e:
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": f"ERROR: {e}"}], "isError": True}}
        except Exception as e:                       # noqa: BLE001
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": repr(e)[:200]}}

    if mid is None:
        return None
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"no method {method!r}"}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", required=True, choices=[u for u, _, _ in users.SEED_USERS])
    args = ap.parse_args()

    claim = mock_auth.issue_claim(args.user)
    role = roles.ROLES[claim.role]
    conn = db.build()
    print(f"[school-mcp] {claim.user_id} as {claim.role}@{claim.org_id}, "
          f"tools: {role['tools']}", file=sys.stderr, flush=True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle(msg, conn, claim, role)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
