"""The team tracker's tool layer — same rule as the school's and the distributor's: permission is decided from the store
and the claim, never from an argument or from text found in a record. And, as a tracker's workflow scheme does, a move
an issue's declared workflow does not allow is refused here, whatever the model asked (`issue_workflows/*.toml`).
"""
from __future__ import annotations

import re
import sqlite3
import tomllib
from functools import lru_cache
from pathlib import Path

from ..common.permissions import Claim, Denied

WORKFLOWS = Path(__file__).parent / "issue_workflows"


def _fn(name, description, props=None, required=None):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {
        "type": "object", "properties": props or {}, **({"required": required} if required else {})}}}


SCHEMA = [
    _fn("issue_get", "Read one issue of your team by key: type, summary, status, assignee, sprint, points, comments.",
        {"key": {"type": "string"}}, ["key"]),
    _fn("issue_search", "Search your team's issues: filters status=, assignee=, type=, sprint=current, component= separated by ';'.",
        {"query": {"type": "string"}}, ["query"]),
    _fn("issue_create", "Create an issue in your team's project and the active sprint.",
        {"type": {"type": "string"}, "summary": {"type": "string"}}, ["type", "summary"]),
    _fn("issue_transition", "Move an issue to another status, as its workflow allows.",
        {"key": {"type": "string"}, "status": {"type": "string"}}, ["key", "status"]),
    _fn("issue_assign", "Assign an issue to a person of your team, by name.",
        {"key": {"type": "string"}, "person": {"type": "string"}}, ["key", "person"]),
    _fn("issue_comment", "Add a comment to an issue.", {"key": {"type": "string"}, "text": {"type": "string"}}, ["key", "text"]),
    _fn("worklog_add", "Log hours of work on an issue.", {"key": {"type": "string"}, "hours": {"type": "number"}}, ["key", "hours"]),
    _fn("sprint_board", "The active sprint's issues, grouped by status, with points."),
    _fn("page_read", "Read the team space: a page (e.g. definition-of-done) or one statement of it (page#anchor).",
        {"ref": {"type": "string"}}, ["ref"]),
]
TOOLS = tuple(t["function"]["name"] for t in SCHEMA)
WRITE_TOOLS = frozenset({"issue_create", "issue_transition", "issue_assign", "issue_comment", "worklog_add"})


class ToolError(ValueError):
    pass


@lru_cache(maxsize=None)
def transitions(kind: str) -> dict[str, list[str]]:
    return tomllib.loads((WORKFLOWS / f"{kind}.toml").read_text())["transitions"]


def _key(k: str) -> str:
    k = str(k).strip().strip("'\"").upper().lstrip("#")
    if not re.fullmatch(r"[A-Z]{2,5}-\d+", k):
        raise ToolError(f"not an issue key: {k!r} (e.g. RD-12)")
    return k


def _issue(conn: sqlite3.Connection, claim: Claim, key: str):
    k = _key(key)
    row = conn.execute("select * from issues where key=?", (k,)).fetchone()
    if row is None:
        raise ToolError(f"no issue {k}")
    if row["org_id"] != claim.org_id:
        raise Denied(f"{claim.user_id}@{claim.org_id} asked for {k}, which belongs to org {row['org_id']!r}")
    return row


def _line(conn, r) -> str:
    sprint = conn.execute("select name from sprints where id=?", (r["sprint_id"],)).fetchone() if r["sprint_id"] else None
    return (f"{r['key']} [{r['type']}] {r['summary']} — status {r['status']} · assignee {r['assignee'] or 'unassigned'} · "
            f"{sprint['name'] if sprint else 'backlog'} · {r['points']} pts · {r['priority']} · {r['component']}")


def issue_get(conn, claim, key: str) -> str:
    r = _issue(conn, claim, key)
    notes = conn.execute("select author, body from comments where issue_key=? and org_id=?", (r["key"], claim.org_id)).fetchall()
    hours = conn.execute("select coalesce(sum(hours), 0) h from worklogs where issue_key=? and org_id=?", (r["key"], claim.org_id)).fetchone()["h"]
    return "\n".join([_line(conn, r), f"logged {hours:g}h"] + [f"- {n['author']}: {n['body']}" for n in notes])


def issue_search(conn, claim, query: str) -> str:
    where, vals = ["org_id=?"], [claim.org_id]
    for part in re.split(r"[;,]", query or ""):
        k, _, v = part.partition("=")
        k, v = k.strip().lower(), v.strip()
        if not k or not v:
            continue
        if k == "sprint" and v.lower() == "current":
            where.append("sprint_id=(select id from sprints where org_id=? and active=1)")
            vals.append(claim.org_id)
        elif k in ("status", "type", "component", "priority"):
            where.append(f"{k}=?"); vals.append(v.lower())
        elif k == "assignee":
            if v.lower() in ("none", "unassigned"):
                where.append("assignee is null")
            else:
                where.append("lower(assignee) like ?"); vals.append(f"%{v.lower()}%")
        else:
            raise ToolError(f"unknown filter {k!r} (status, assignee, type, sprint, component, priority)")
    rows = conn.execute(f"select * from issues where {' and '.join(where)} order by key limit 12", vals).fetchall()
    return "\n".join(_line(conn, r) for r in rows) if rows else "no issues match"


def issue_create(conn, claim, type: str, summary: str) -> str:
    kind = type.strip().lower()
    if kind not in ("story", "bug"):
        raise ToolError("type is story or bug")
    prefix = conn.execute("select prefix from orgs where id=?", (claim.org_id,)).fetchone()["prefix"]
    n = 1 + max([int(r["key"].split("-")[1]) for r in conn.execute("select key from issues where org_id=?", (claim.org_id,))] or [0])
    sprint = conn.execute("select id from sprints where org_id=? and active=1", (claim.org_id,)).fetchone()
    key = f"{prefix}-{n}"
    conn.execute("insert into issues values (?, ?, ?, ?, ?, null, ?, 1, 'medium', null)",
                 (key, claim.org_id, kind, summary.strip(), "todo" if kind == "story" else "triage", sprint["id"] if sprint else None))
    conn.commit()
    return f"created {key} [{kind}] {summary.strip()}"


def issue_transition(conn, claim, key: str, status: str) -> str:
    r = _issue(conn, claim, key)
    to = status.strip().lower().replace(" ", "_").replace("-", "_")
    allowed = transitions(r["type"]).get(r["status"], [])
    if to not in allowed:
        raise ToolError(f"cannot move {r['key']} from {r['status']} to {to} (allowed: {', '.join(allowed) or 'none'})")
    conn.execute("update issues set status=? where key=?", (to, r["key"]))
    conn.commit()
    return f"moved {r['key']} from {r['status']} to {to}"


def issue_assign(conn, claim, key: str, person: str) -> str:
    r = _issue(conn, claim, key)
    who = conn.execute("select name from people where org_id=? and lower(name) like ?",
                       (claim.org_id, f"%{person.strip().lower()}%")).fetchall()
    if len(who) != 1:
        raise ToolError(f"no single person matching {person!r} in your team" + (f" ({', '.join(w['name'] for w in who)})" if who else ""))
    conn.execute("update issues set assignee=? where key=?", (who[0]["name"], r["key"]))
    conn.commit()
    return f"assigned {r['key']} to {who[0]['name']}"


def issue_comment(conn, claim, key: str, text: str) -> str:
    r = _issue(conn, claim, key)
    cur = conn.execute("insert into comments (org_id, issue_key, author, body) values (?, ?, ?, ?)",
                       (claim.org_id, r["key"], claim.user_id, text.strip()))
    conn.commit()
    return f"commented on {r['key']} (#{cur.lastrowid})"


def worklog_add(conn, claim, key: str, hours) -> str:
    r = _issue(conn, claim, key)
    h = float(str(hours).lower().rstrip("h").strip())
    if not 0 < h <= 24:
        raise ToolError("hours must be between 0 and 24")
    conn.execute("insert into worklogs (org_id, issue_key, author, hours) values (?, ?, ?, ?)", (claim.org_id, r["key"], claim.user_id, h))
    conn.commit()
    total = conn.execute("select sum(hours) h from worklogs where issue_key=? and org_id=?", (r["key"], claim.org_id)).fetchone()["h"]
    return f"logged {h:g}h on {r['key']} (total {total:g}h)"


def sprint_board(conn, claim) -> str:
    s = conn.execute("select id, name from sprints where org_id=? and active=1", (claim.org_id,)).fetchone()
    if s is None:
        return "no active sprint"
    rows = conn.execute("select status, count(*) n, sum(points) p from issues where sprint_id=? group by status order by status", (s["id"],)).fetchall()
    return f"{s['name']}: " + "; ".join(f"{r['status']} {r['n']} issues ({r['p']} pts)" for r in rows)


def page_read(conn, claim, ref: str) -> str:
    page, _, anchor = ref.strip().lower().partition("#")
    rows = conn.execute("select anchor, text from pages where org_id=? and page=?" + (" and anchor=?" if anchor else ""),
                        (claim.org_id, page, anchor) if anchor else (claim.org_id, page)).fetchall()
    if not rows:
        pages = sorted({r["page"] for r in conn.execute("select page from pages where org_id=?", (claim.org_id,))})
        raise ToolError(f"no page {ref!r} (pages: {', '.join(pages)})")
    return "\n".join(f"[{page}#{r['anchor']}] {r['text']}" for r in rows)


def answer(conn: sqlite3.Connection, claim: Claim, name: str, args: dict) -> str:
    a = args or {}
    fns = {"issue_get": lambda: issue_get(conn, claim, a["key"]), "issue_search": lambda: issue_search(conn, claim, a.get("query", "")),
           "issue_create": lambda: issue_create(conn, claim, a["type"], a["summary"]),
           "issue_transition": lambda: issue_transition(conn, claim, a["key"], a["status"]),
           "issue_assign": lambda: issue_assign(conn, claim, a["key"], a["person"]),
           "issue_comment": lambda: issue_comment(conn, claim, a["key"], a["text"]),
           "worklog_add": lambda: worklog_add(conn, claim, a["key"], a["hours"]), "sprint_board": lambda: sprint_board(conn, claim),
           "page_read": lambda: page_read(conn, claim, a["ref"])}
    if name not in fns:
        raise ToolError(f"no tool {name}")
    return fns[name]()
