"""The distributor's tool layer — same rule as examples/school/tools.py: permission is decided
from the database and the claim, never from an argument or from text found in a record.
"""
from __future__ import annotations

import sqlite3

from ..common.permissions import Claim, Denied

SCHEMA = [
    {"type": "function", "function": {
        "name": "order_status",
        "description": "Read the status and delivery notes for one order, by id.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "integer"}}, "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "claim_create",
        "description": "File a customer claim for the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {
            "description": {"type": "string"}}, "required": ["description"]}}},
    {"type": "function", "function": {
        "name": "delivery_status",
        "description": "Read the delivery note for one order, by id.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "integer"}}, "required": ["order_id"]}}},
]

TOOLS = tuple(t["function"]["name"] for t in SCHEMA)

# See examples/school/tools.py's WRITE_TOOLS for why this exists: `mcp_server.py` sets
# `readOnlyHint` per tool from this, not a blanket true.
WRITE_TOOLS = frozenset({"claim_create"})


class ToolError(ValueError):
    pass


def _order_row(conn: sqlite3.Connection, claim: Claim, order_id: int):
    row = conn.execute("select * from orders where id=?", (order_id,)).fetchone()
    if row is None:
        raise ToolError(f"no order {order_id}")
    if row["org_id"] != claim.org_id:
        raise Denied(f"{claim.user_id}@{claim.org_id} asked for order {order_id}, "
                     f"which belongs to org {row['org_id']!r}")
    return row


def order_status(conn: sqlite3.Connection, claim: Claim, order_id: int) -> str:
    row = _order_row(conn, claim, order_id)
    return f"order #{order_id}: {row['item']} — {row['status']}"


def delivery_status(conn: sqlite3.Connection, claim: Claim, order_id: int) -> str:
    _order_row(conn, claim, order_id)          # the org check, even though deliveries has its own org_id
    d = conn.execute("select note from deliveries where order_id=?", (order_id,)).fetchone()
    if d is None:
        return f"order #{order_id}: no delivery note yet"
    return f"order #{order_id} delivery: {d['note']}"


def claim_create(conn: sqlite3.Connection, claim: Claim, description: str) -> str:
    cur = conn.execute(
        "insert into claims (org_id, filed_by, description, status) values (?, ?, ?, 'open')",
        (claim.org_id, claim.user_id, description))
    conn.commit()
    return f"filed claim #{cur.lastrowid} for {claim.org_id}"


def answer(conn: sqlite3.Connection, claim: Claim, name: str, args: dict) -> str:
    args = args or {}
    if name == "order_status":
        return order_status(conn, claim, int(args["order_id"]))
    if name == "delivery_status":
        return delivery_status(conn, claim, int(args["order_id"]))
    if name == "claim_create":
        return claim_create(conn, claim, args["description"])
    raise ToolError(f"no tool named {name!r} — offered: {TOOLS}")
