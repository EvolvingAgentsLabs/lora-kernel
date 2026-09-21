"""The school's tool layer. Every function decides permission itself, from the database and the
caller's `Claim` — never from an argument the caller (model or otherwise) supplies, and never
from anything found in a note's or a record's text. This is the whole mechanism: a tool call
either returns the row or raises `Denied`, before the model sees either.

THE RULE THAT MAKES THIS INJECTION-PROOF. `agenda_read` is asked for a `student_id`; the tool
looks up that student's *true* `org_id` in the database and compares it to the claim's — it
never trusts a org_id typed into the request, and no field in the database (a note, a
description) is ever executed as an instruction. An attacker's planted text
(`db.INJECTION_NOTE`, `db.INJECTION_DESCRIPTION`) can persuade the *model* to ask for another
org's row; it cannot persuade the *tool*, which does not read the model's reasoning, only its
arguments and the database.
"""
from __future__ import annotations

import sqlite3

from ..common import mock_billing
from ..common.permissions import Claim, Denied

SCHEMA = [
    {"type": "function", "function": {
        "name": "agenda_read",
        "description": "Read the agenda entries (events) for one student, by id.",
        "parameters": {"type": "object", "properties": {
            "student_id": {"type": "integer"}}, "required": ["student_id"]}}},
    {"type": "function", "function": {
        "name": "order_draft",
        "description": "Draft a purchase order for the asking user's own school.",
        "parameters": {"type": "object", "properties": {
            "item": {"type": "string"}, "qty": {"type": "integer"},
            "description": {"type": "string"}},
            "required": ["item", "qty"]}}},
    {"type": "function", "function": {
        "name": "order_list",
        "description": "List purchase orders for the asking user's own school.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "enrollment_list",
        "description": "List programme enrollments for the asking user's own school.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "enrollment_draft",
        "description": "Draft a programme enrollment for one student, by id.",
        "parameters": {"type": "object", "properties": {
            "student_id": {"type": "integer"}, "program": {"type": "string"}},
            "required": ["student_id", "program"]}}},
    {"type": "function", "function": {
        "name": "announcement_post",
        "description": "Post an announcement for the asking user's own school.",
        "parameters": {"type": "object", "properties": {
            "audience": {"type": "string"}, "body": {"type": "string"}},
            "required": ["audience", "body"]}}},
    {"type": "function", "function": {
        "name": "announcement_list",
        "description": "List announcements posted at the asking user's own school.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "maintenance_create",
        "description": "File a maintenance request for the asking user's own school.",
        "parameters": {"type": "object", "properties": {
            "area": {"type": "string"}, "description": {"type": "string"}},
            "required": ["area", "description"]}}},
    {"type": "function", "function": {
        "name": "maintenance_list",
        "description": "List maintenance requests at the asking user's own school.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "payroll_read",
        "description": "Read payroll for the asking user's own school. Sensitive.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "campaign_list",
        "description": "List marketing campaigns for the asking user's own school.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "campaign_create",
        "description": "Create a marketing campaign for the asking user's own school.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}, "channel": {"type": "string"},
            "budget_cents": {"type": "integer"}},
            "required": ["name", "channel", "budget_cents"]}}},
    {"type": "function", "function": {
        "name": "membership_status",
        "description": "List memberships and their status for the asking user's own school.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "billing_charge",
        "description": "Record a charge against one membership, by id, at the asking user's own school.",
        "parameters": {"type": "object", "properties": {
            "membership_id": {"type": "integer"}, "amount_cents": {"type": "integer"}},
            "required": ["membership_id", "amount_cents"]}}},
    {"type": "function", "function": {
        "name": "dashboard_summary",
        "description": "Aggregate counts for the asking user's own school — never individual rows.",
        "parameters": {"type": "object", "properties": {}}}},
]

TOOLS = tuple(t["function"]["name"] for t in SCHEMA)

# Which tools write. `mcp_server.py` reads this to set `readOnlyHint` per tool, correctly —
# a client that trusts a blanket "everything here is read-only" would let an agent skip
# approval on `billing_charge`, which is exactly the kind of annotation the inbox server's own
# comment warned against: "declared because they are true, not to get past a gate."
WRITE_TOOLS = frozenset({"order_draft", "enrollment_draft", "announcement_post",
                         "maintenance_create", "campaign_create", "billing_charge"})


class ToolError(ValueError):
    pass


def agenda_read(conn: sqlite3.Connection, claim: Claim, student_id: int) -> str:
    row = conn.execute("select * from students where id=?", (student_id,)).fetchone()
    if row is None:
        raise ToolError(f"no student {student_id}")
    if row["org_id"] != claim.org_id:
        raise Denied(f"{claim.user_id}@{claim.org_id} asked for student {student_id}, "
                     f"who belongs to org {row['org_id']!r}")
    events = conn.execute("select title, note from events where student_id=?",
                          (student_id,)).fetchall()
    if not events:
        return f"{row['name']}: no agenda entries"
    return f"{row['name']}:\n" + "\n".join(f"- {e['title']}: {e['note']}" for e in events)


def order_draft(conn: sqlite3.Connection, claim: Claim, item: str, qty: int,
                description: str = "") -> str:
    # THE ORG COMES FROM THE CLAIM, NEVER FROM AN ARGUMENT. A caller cannot draft an order
    # into another tenant by naming one — there is no field to name one in.
    cur = conn.execute(
        "insert into purchase_orders (org_id, requested_by, item, qty, status, description) "
        "values (?, ?, ?, ?, 'draft', ?)",
        (claim.org_id, claim.user_id, item, qty, description))
    conn.commit()
    return f"drafted order #{cur.lastrowid} for {claim.org_id}: {qty}x {item}"


def order_list(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select id, item, qty, status from purchase_orders where org_id=?",
                        (claim.org_id,)).fetchall()
    if not rows:
        return "no purchase orders"
    return "\n".join(f"#{r['id']} {r['item']} x{r['qty']} ({r['status']})" for r in rows)


def enrollment_list(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select e.id, s.name, e.program, e.status, e.note "
                        "from enrollments e join students s on s.id = e.student_id "
                        "where e.org_id=?", (claim.org_id,)).fetchall()
    if not rows:
        return "no enrollments"
    return "\n".join(f"#{r['id']} {r['name']} — {r['program']} ({r['status']}): {r['note']}"
                     for r in rows)


def enrollment_draft(conn: sqlite3.Connection, claim: Claim, student_id: int, program: str) -> str:
    row = conn.execute("select org_id from students where id=?", (student_id,)).fetchone()
    if row is None:
        raise ToolError(f"no student {student_id}")
    if row["org_id"] != claim.org_id:
        raise Denied(f"{claim.user_id}@{claim.org_id} tried to enroll student {student_id}, "
                     f"who belongs to org {row['org_id']!r}")
    cur = conn.execute(
        "insert into enrollments (org_id, student_id, program, status, note) "
        "values (?, ?, ?, 'pending', '')", (claim.org_id, student_id, program))
    conn.commit()
    return f"drafted enrollment #{cur.lastrowid} for student {student_id} in {program!r}"


def announcement_post(conn: sqlite3.Connection, claim: Claim, audience: str, body: str) -> str:
    cur = conn.execute(
        "insert into announcements (org_id, posted_by, audience, body) values (?, ?, ?, ?)",
        (claim.org_id, claim.user_id, audience, body))
    conn.commit()
    return f"posted announcement #{cur.lastrowid} to {audience} at {claim.org_id}"


def announcement_list(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select id, audience, body from announcements where org_id=?",
                        (claim.org_id,)).fetchall()
    if not rows:
        return "no announcements"
    return "\n".join(f"#{r['id']} to {r['audience']}: {r['body']}" for r in rows)


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


def payroll_read(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select employee_name, role_title, salary_cents from payroll "
                        "where org_id=?", (claim.org_id,)).fetchall()
    if not rows:
        return "no payroll records"
    return "\n".join(f"{r['employee_name']} ({r['role_title']}): ${r['salary_cents']/100:.2f}"
                     for r in rows)


def campaign_list(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select id, name, channel, status, budget_cents from campaigns "
                        "where org_id=?", (claim.org_id,)).fetchall()
    if not rows:
        return "no campaigns"
    return "\n".join(f"#{r['id']} {r['name']} ({r['channel']}, {r['status']}): "
                     f"${r['budget_cents']/100:.2f}" for r in rows)


def campaign_create(conn: sqlite3.Connection, claim: Claim, name: str, channel: str,
                    budget_cents: int) -> str:
    cur = conn.execute(
        "insert into campaigns (org_id, name, channel, status, budget_cents) "
        "values (?, ?, ?, 'active', ?)", (claim.org_id, name, channel, budget_cents))
    conn.commit()
    return f"created campaign #{cur.lastrowid} {name!r} for {claim.org_id}"


def membership_status(conn: sqlite3.Connection, claim: Claim) -> str:
    rows = conn.execute("select id, plan, status from memberships where org_id=?",
                        (claim.org_id,)).fetchall()
    if not rows:
        return "no memberships"
    return "\n".join(f"#{r['id']} {r['plan']} ({r['status']})" for r in rows)


def billing_charge(conn: sqlite3.Connection, claim: Claim, membership_id: int,
                   amount_cents: int) -> str:
    row = conn.execute("select org_id from memberships where id=?", (membership_id,)).fetchone()
    if row is None:
        raise ToolError(f"no membership {membership_id}")
    if row["org_id"] != claim.org_id:
        raise Denied(f"{claim.user_id}@{claim.org_id} tried to charge membership {membership_id}, "
                     f"which belongs to org {row['org_id']!r}")
    charge = mock_billing.LEDGER.charge(claim.org_id, membership_id, amount_cents)
    return f"charged ${amount_cents/100:.2f} against membership #{membership_id} (charge #{charge['id']})"


def dashboard_summary(conn: sqlite3.Connection, claim: Claim) -> str:
    # AN AGGREGATE IS NOT AN EXEMPTION. Every count here is still `where org_id=?` — a dashboard
    # is not a back door that returns another tenant's totals just because no single row does.
    counts = {}
    for table in ("students", "purchase_orders", "enrollments", "maintenance_requests",
                  "campaigns", "memberships"):
        counts[table] = conn.execute(f"select count(*) as n from {table} where org_id=?",
                                     (claim.org_id,)).fetchone()["n"]
    return ", ".join(f"{k}={v}" for k, v in counts.items())


def answer(conn: sqlite3.Connection, claim: Claim, name: str, args: dict) -> str:
    args = args or {}
    if name == "agenda_read":
        return agenda_read(conn, claim, int(args["student_id"]))
    if name == "order_draft":
        return order_draft(conn, claim, args["item"], int(args["qty"]), args.get("description", ""))
    if name == "order_list":
        return order_list(conn, claim)
    if name == "enrollment_list":
        return enrollment_list(conn, claim)
    if name == "enrollment_draft":
        return enrollment_draft(conn, claim, int(args["student_id"]), args["program"])
    if name == "announcement_post":
        return announcement_post(conn, claim, args["audience"], args["body"])
    if name == "announcement_list":
        return announcement_list(conn, claim)
    if name == "maintenance_create":
        return maintenance_create(conn, claim, args["area"], args["description"])
    if name == "maintenance_list":
        return maintenance_list(conn, claim)
    if name == "payroll_read":
        return payroll_read(conn, claim)
    if name == "campaign_list":
        return campaign_list(conn, claim)
    if name == "campaign_create":
        return campaign_create(conn, claim, args["name"], args["channel"], int(args["budget_cents"]))
    if name == "membership_status":
        return membership_status(conn, claim)
    if name == "billing_charge":
        return billing_charge(conn, claim, int(args["membership_id"]), int(args["amount_cents"]))
    if name == "dashboard_summary":
        return dashboard_summary(conn, claim)
    raise ToolError(f"no tool named {name!r} — offered: {TOOLS}")
