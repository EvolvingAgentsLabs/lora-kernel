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
    {"type": "function", "function": {
        "name": "dock_assign",
        "description": "Assign one order to a dock at the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "integer"}, "dock_number": {"type": "string"}},
            "required": ["order_id", "dock_number"]}}},
    {"type": "function", "function": {
        "name": "dock_status",
        "description": "Read dock assignments at the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "stock_read",
        "description": "Read stock levels at the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "stock_reorder",
        "description": "Increase stock for one item at the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {
            "item": {"type": "string"}, "qty": {"type": "integer"}},
            "required": ["item", "qty"]}}},
    {"type": "function", "function": {
        "name": "return_create",
        "description": "File a return for one order at the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "integer"}, "reason": {"type": "string"}},
            "required": ["order_id", "reason"]}}},
    {"type": "function", "function": {
        "name": "return_list",
        "description": "List returns filed at the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "maintenance_create",
        "description": "File a maintenance request at the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {
            "area": {"type": "string"}, "description": {"type": "string"}},
            "required": ["area", "description"]}}},
    {"type": "function", "function": {
        "name": "maintenance_list",
        "description": "List maintenance requests at the asking user's own distribution centre.",
        "parameters": {"type": "object", "properties": {}}}},
]

TOOLS = tuple(t["function"]["name"] for t in SCHEMA)

# See examples/school/tools.py's WRITE_TOOLS for why this exists: `mcp_server.py` sets
# `readOnlyHint` per tool from this, not a blanket true.
WRITE_TOOLS = frozenset({"claim_create", "dock_assign", "stock_reorder", "return_create",
                         "maintenance_create"})


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


def dock_assign(conn: sqlite3.Connection, claim: Claim, order_id: int, dock_number: str) -> str:
    row = _order_row(conn, claim, order_id)
    cur = conn.execute(
        "insert into docks (org_id, order_id, dock_number, status, notes) "
        "values (?, ?, ?, 'assigned', '')", (claim.org_id, order_id, dock_number))
    conn.commit()
    return f"assigned order #{order_id} to dock {dock_number} (#{cur.lastrowid})"


def dock_status(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select id, order_id, dock_number, status, notes from docks "
                        "where org_id=?", (claim.org_id,)).fetchall()
    if not rows:
        return "no dock assignments"
    return "\n".join(f"#{r['id']} order {r['order_id']} -> dock {r['dock_number']} "
                     f"({r['status']}): {r['notes']}" for r in rows)


def stock_read(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select item, qty, reorder_threshold from stock where org_id=?",
                        (claim.org_id,)).fetchall()
    if not rows:
        return "no stock records"
    return "\n".join(f"{r['item']}: {r['qty']} (reorder below {r['reorder_threshold']})"
                     for r in rows)


def stock_reorder(conn: sqlite3.Connection, claim: Claim, item: str, qty: int) -> str:
    row = conn.execute("select id, qty from stock where org_id=? and item=?",
                       (claim.org_id, item)).fetchone()
    if row is None:
        raise ToolError(f"no stock record for {item!r} at {claim.org_id}")
    conn.execute("update stock set qty = qty + ? where id=?", (qty, row["id"]))
    conn.commit()
    return f"reordered {qty} of {item!r} for {claim.org_id} (new total {row['qty'] + qty})"


def return_create(conn: sqlite3.Connection, claim: Claim, order_id: int, reason: str) -> str:
    _order_row(conn, claim, order_id)
    cur = conn.execute(
        "insert into returns (org_id, order_id, filed_by, reason, status) "
        "values (?, ?, ?, ?, 'open')", (claim.org_id, order_id, claim.user_id, reason))
    conn.commit()
    return f"filed return #{cur.lastrowid} for order {order_id} at {claim.org_id}"


def return_list(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select id, order_id, reason, status from returns where org_id=?",
                        (claim.org_id,)).fetchall()
    if not rows:
        return "no returns"
    return "\n".join(f"#{r['id']} order {r['order_id']} ({r['status']}): {r['reason']}"
                     for r in rows)


def maintenance_create(conn: sqlite3.Connection, claim: Claim, area: str, description: str) -> str:
    cur = conn.execute(
        "insert into maintenance_requests (org_id, filed_by, area, status, description) "
        "values (?, ?, ?, 'open', ?)", (claim.org_id, claim.user_id, area, description))
    conn.commit()
    return f"filed maintenance request #{cur.lastrowid} for {area} at {claim.org_id}"


def maintenance_list(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select id, area, status, description from maintenance_requests "
                        "where org_id=?", (claim.org_id,)).fetchall()
    if not rows:
        return "no maintenance requests"
    return "\n".join(f"#{r['id']} {r['area']} ({r['status']}): {r['description']}" for r in rows)


def answer(conn: sqlite3.Connection, claim: Claim, name: str, args: dict) -> str:
    args = args or {}
    if name == "order_status":
        return order_status(conn, claim, int(args["order_id"]))
    if name == "delivery_status":
        return delivery_status(conn, claim, int(args["order_id"]))
    if name == "claim_create":
        return claim_create(conn, claim, args["description"])
    if name == "dock_assign":
        return dock_assign(conn, claim, int(args["order_id"]), args["dock_number"])
    if name == "dock_status":
        return dock_status(conn, claim)
    if name == "stock_read":
        return stock_read(conn, claim)
    if name == "stock_reorder":
        return stock_reorder(conn, claim, args["item"], int(args["qty"]))
    if name == "return_create":
        return return_create(conn, claim, int(args["order_id"]), args["reason"])
    if name == "return_list":
        return return_list(conn, claim)
    if name == "maintenance_create":
        return maintenance_create(conn, claim, args["area"], args["description"])
    if name == "maintenance_list":
        return maintenance_list(conn, claim)
    raise ToolError(f"no tool named {name!r} — offered: {TOOLS}")
