r"""A training corpus for the school's role packs — the first step of `docs/PLAN.md` §1
milestone 7 arm 4's pattern (`training/nursing/generate_walks.py`) applied to `examples/school/`:
drive the real tool layer, render the real tag surface, and hold out enough data that a trained
adapter could not simply recall this file.

WHY THIS IS THE NEXT STEP, NAMED IN `examples/README.md`. Everything under `examples/school/` so
far is code and a three-row fixture sized for an adversarial test, not for training: `db.py`'s
`SEED` exists to plant two injection strings and prove 0 leaks, not to teach a role its job. This
file is a *different* generator, over a *larger*, separately-seeded synthetic school
(`build_training_db`, not `db.build`), because a corpus drawn from the same three rows the
adversarial suite checks would be a corpus an adapter could memorise its way through — the same
mistake P15 made once already (CLAUDE.md §3: "a control with no lookup tool scored 27/30").

WHAT IS TAUGHT IS THE CALL, NEVER THE DATA. Every row renders through
`training.harness.tool_calls.tools_to_instruction` (`ARITY=True`, the pool's own default) and the
role's own `system_prompt` from `roles.py` — the same functions a served member's block comes
from, so a copy cannot drift from what is actually shown (CLAUDE.md §3: "a corpus must teach the
prompt the model will be served"). The assistant turn is corpus mode: the call, then `=`, then the
tool's own real return text, exactly as `accept_rank.py`'s loop would inject it — never a
`tool_calls` message, which P55 measured costs 0.808 against 0.992.

HELD OUT BY STUDENT/ORDER/ETC., NOT BY ROW. `--eval-share` reserves whole entities (a student, an
order id, a membership) for the held-out set, never rows — an adapter that memorised entity #7's
agenda cannot get credit by seeing entity #7 phrased a different way at evaluation time.

    python3 -m examples.school.generate_corpus --role educador --n 400
    python3 -m examples.school.generate_corpus --role all --n 400   # every role, one file each
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sqlite3
from collections import Counter
from pathlib import Path

from training.harness.tool_calls import tools_to_instruction

from . import db as db_mod
from . import roles as roles_mod
from . import tools as tools_mod

OUT = Path(__file__).parent / "data_corpus"
ARITY = True   # matches training/harness/openai_proxy.py's ARITY — the pool's own default


# --- a training-scale synthetic school, separate from the adversarial fixture's 3 rows ---------

FIRST_NAMES = ["Jamie", "Rowan", "Kavi", "Priya", "Devon", "Ashby", "Noor", "Theo", "Mabel",
              "Ines", "Yusuf", "Callum", "Wren", "Soraya", "Lucian", "Mira", "Idris", "Zuri"]
LAST_NAMES = ["Ashby", "Nandakumar", "Okafor", "Lindqvist", "Petrov", "Hassan", "Costa", "Reyes",
             "Dubois", "Kowalski", "Marchetti", "Solano", "Ibarra", "Fenwick", "Osei"]
CLASSROOMS = ["Room 1", "Room 2", "Room 3", "Room 4", "Room 5", "Room 6"]
PROGRAMS = ["after-school-robotics", "after-school-art", "after-school-choir", "swim-club",
           "chess-club", "coding-club", "drama-club"]
AREAS = ["Room 1", "Room 2", "Room 3", "Room 4", "Gym", "Cafeteria", "Library", "Front office"]
CHANNELS = ["email", "sms", "flyer", "app-push"]

EVENT_TITLES = [
    ("field trip permission", "Signed, returning {day}."),
    ("early pickup", "Approved, guardian arriving at {time}."),
    ("lunch account", "Balance is ${amt}, auto-reload is {onoff}."),
    ("allergy note", "No changes since last term; kitchen has the current list."),
    ("photo consent", "{consent} for the yearbook and the school site."),
]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def build_training_db(n_students: int, seed: int, path: str = ":memory:") -> sqlite3.Connection:
    """A school ~40x the size of the adversarial fixture, one tenant, so a corpus this size does
    not just re-teach the three rows `test_adversarial.py` already owns."""
    rng = random.Random(seed)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(db_mod.SCHEMA)
    conn.execute("insert into orgs values (?, ?)", ("northgate", "Northgate Elementary"))

    guardians = []
    for i in range(max(1, n_students // 2)):
        gid = f"g-corpus-{i:03d}"
        conn.execute("insert into guardians values (?, ?, ?)",
                    (gid, "northgate", f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"))
        guardians.append(gid)

    students = []
    for sid in range(1, n_students + 1):
        name = f"{rng.choice(LAST_NAMES)}, {rng.choice(FIRST_NAMES)}"
        gid = rng.choice(guardians)
        room = rng.choice(CLASSROOMS)
        conn.execute("insert into students values (?, ?, ?, ?, ?)", (sid, "northgate", gid, name, room))
        students.append(sid)
        n_events = rng.randint(1, 3)
        for _ in range(n_events):
            title, note_t = rng.choice(EVENT_TITLES)
            note = note_t.format(day=rng.choice(DAYS), time=f"{rng.randint(1,5)}:{rng.choice(['00','15','30','45'])} pm",
                                 amt=rng.randint(5, 60), onoff=rng.choice(["on", "off"]),
                                 consent=rng.choice(["Consent given", "Consent withheld"]))
            conn.execute("insert into events values (?, ?, ?, ?, ?)",
                        (None, "northgate", sid, title, note))

    for i in range(max(1, n_students // 3)):
        conn.execute(
            "insert into purchase_orders (org_id, requested_by, item, qty, status, description) "
            "values (?, ?, ?, ?, 'draft', ?)",
            ("northgate", "compras-north", rng.choice(["art supplies", "office supplies", "sports kit"]),
             rng.randint(1, 50), ""))
        conn.execute("insert into enrollments (org_id, student_id, program, status, note) "
                    "values (?, ?, ?, 'confirmed', '')",
                    ("northgate", rng.choice(students), rng.choice(PROGRAMS)))
        conn.execute("insert into announcements (org_id, posted_by, audience, body) values (?, ?, ?, ?)",
                    ("northgate", "marketing-north", "guardians",
                     f"{rng.choice(['Picture day', 'Book fair', 'Assembly'])} is next {rng.choice(DAYS)}."))
        conn.execute("insert into maintenance_requests (org_id, filed_by, area, status, description) "
                    "values (?, ?, ?, 'open', ?)",
                    ("northgate", "it-north", rng.choice(AREAS), "Routine ticket."))
        conn.execute("insert into campaigns (org_id, name, channel, status, budget_cents) "
                    "values (?, ?, ?, 'active', ?)",
                    ("northgate", f"campaign-{i}", rng.choice(CHANNELS), rng.randint(10000, 100000)))
        conn.execute("insert into memberships (org_id, guardian_id, plan, status) values (?, ?, 'family-annual', 'active')",
                    ("northgate", rng.choice(guardians)))
        conn.execute("insert into payroll (org_id, employee_name, role_title, salary_cents) values (?, ?, 'staff', ?)",
                    ("northgate", f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}", rng.randint(350000, 500000)))
    conn.commit()
    return conn


def _stable_id(text: str) -> str:
    """`blake2b`, never Python's `hash()` — randomised per process, the exact bug
    `../../evolving-memory`'s central test failed on 6 of 30 seeds for, and the one this file's
    own determinism check (`test_generate_corpus.py`) caught here, in a new codebase, the same
    day this generator was first run."""
    return hashlib.blake2b(text.encode(), digest_size=4).hexdigest()


# --- rendering the call the way the pool renders it, never a hand-rolled copy ------------------

def render_call(schema_entry: dict, args: dict) -> str:
    """`<tool>value</tool>` for a one-required-arg tool (ARITY), `<tool>k=v; k2=v2</tool>`
    otherwise — the same convention `tools_to_instruction` documents and the served pool uses."""
    fn = schema_entry["function"]
    name = fn["name"]
    params = fn.get("parameters") or {}
    required = params.get("required") or sorted((params.get("properties") or {}))
    if ARITY and len(required) == 1:
        body = str(args[required[0]])
    else:
        body = "; ".join(f"{k}={args[k]}" for k in sorted(args))
    return f"<{name}>{body}</{name}>"


# --- one example per (role, task) -----------------------------------------------------------

def _claim_for(role: str):
    from ..common.permissions import Claim
    return Claim(user_id=f"{role}-north-corpus", role=role, org_id="northgate")


def examples_for_role(conn: sqlite3.Connection, role: str, n: int, rng: random.Random,
                      eval_ids: set) -> tuple[list[dict], list[dict]]:
    """Returns (train_rows, eval_rows). `eval_ids` names the entities (student/order/etc. ids)
    reserved for evaluation — an adapter is trained on every row about every OTHER entity."""
    schema_by_name = {t["function"]["name"]: t for t in tools_mod.SCHEMA}
    role_tools = [schema_by_name[t] for t in roles_mod.ROLES[role]["tools"]]
    system = roles_mod.ROLES[role]["system_prompt"] + "\n\n" + tools_to_instruction(role_tools, arity=ARITY)
    claim = _claim_for(role)

    tasks = _TASKS[role]
    train, eva = [], []
    seen_completions = set()
    tries = 0
    while len(train) + len(eva) < n and tries < n * 20:
        tries += 1
        kind = rng.choice(list(tasks))
        row = tasks[kind](conn, rng)
        if row is None:
            continue
        entity_id, user_text, tool_name, args = row
        # A WRITE TASK MUST NOT LEAK INTO WHAT A LATER READ TASK SEES. Both share `conn`
        # (entities have to stay stable for the held-out split), so an `order_draft` example
        # generated before an `order_list` one would otherwise make `order_list`'s answer a
        # function of *how much of the corpus had already been generated* — a moving target
        # no real query result is, and an instrument bug the same shape as the ones
        # `../CLAUDE.md` §3 already names. Caught by inspecting the file, not assumed away:
        # `order_list` completions grew from ~1 KB to ~7 KB over one run before this fix.
        write_table = _WRITE_TABLE.get(tool_name)
        before_max = (conn.execute(f"select max(id) from {write_table}").fetchone()[0]
                     if write_table else None)
        try:
            result = tools_mod.answer(conn, claim, tool_name, args)
        except tools_mod.ToolError:
            continue
        if write_table is not None:
            conn.execute(f"delete from {write_table} where id > ?", (before_max or 0,))
            conn.commit()
        call = render_call(schema_by_name[tool_name], args)
        assistant = f"{call}= {result}\n{_final_line(kind, result)}"
        if assistant in seen_completions:
            continue                       # dedupe on what is WRITTEN, not on what is asked
        seen_completions.add(assistant)
        record = {"case_id": f"{role}-{len(train) + len(eva):04d}", "role": role, "kind": kind,
                  "tool": tool_name, "entity_id": entity_id,
                  "messages": [{"role": "system", "content": system},
                              {"role": "user", "content": user_text},
                              {"role": "assistant", "content": assistant}]}
        (eva if entity_id in eval_ids else train).append(record)
    return train, eva


def _final_line(kind: str, result: str) -> str:
    first = result.splitlines()[0] if result else result
    return f"Here's what I found: {first}" if len(result) < 200 else "Here's what I found — see above."


def _random_student(conn, rng):
    """`ORDER BY random()` is SQLite's own PRNG, seeded from system entropy — not `rng`, so a
    corpus built from it cannot be reproduced from a seed. Every draw goes through `rng` instead;
    `../../CLAUDE.md` §7's determinism promise is worth a query more than an `ORDER BY` clause."""
    rows = conn.execute("select id, name from students").fetchall()
    return rng.choice(rows) if rows else None


def _t_agenda(conn, rng):
    row = _random_student(conn, rng)
    if row is None:
        return None
    phr = rng.choice([f"Can you check {row['name'].split(', ')[-1]}'s agenda (student {row['id']})?",
                      f"What's on the agenda for student {row['id']}?",
                      f"Any updates for {row['name']} (id {row['id']})?"])
    return row["id"], phr, "agenda_read", {"student_id": row["id"]}


def _t_order_list(conn, rng):
    return "orders", rng.choice(["What purchase orders are open?", "List our purchase orders.",
                                 "Show me the current orders."]), "order_list", {}


def _t_order_draft(conn, rng):
    item = rng.choice(["crayons", "printer paper", "soccer balls", "whiteboard markers"])
    qty = rng.randint(1, 40)
    return f"draft-{item}-{qty}", f"Please order {qty} {item}.", "order_draft", {"item": item, "qty": qty}


def _t_enrollment_list(conn, rng):
    return "enrollments", rng.choice(["What enrollments do we have open?", "List current enrollments."]), \
        "enrollment_list", {}


def _t_enrollment_draft(conn, rng):
    row = _random_student(conn, rng)
    if row is None:
        return None
    program = rng.choice(PROGRAMS)
    return row["id"], f"Enroll student {row['id']} in {program}.", "enrollment_draft", \
        {"student_id": row["id"], "program": program}


def _t_announcement_list(conn, rng):
    return "announcements", rng.choice(["What announcements have gone out?", "List recent announcements."]), \
        "announcement_list", {}


def _t_announcement_post(conn, rng):
    body = rng.choice(["Picture day is next week.", "Book fair starts Monday.", "Early dismissal Friday."])
    return f"post-{_stable_id(body)}", f"Please post this to guardians: {body}", "announcement_post", \
        {"audience": "guardians", "body": body}


def _t_maintenance_list(conn, rng):
    return "maintenance", rng.choice(["What maintenance tickets are open?", "List the maintenance queue."]), \
        "maintenance_list", {}


def _t_maintenance_create(conn, rng):
    area = rng.choice(AREAS)
    desc = rng.choice(["Light flickering.", "Door won't lock.", "AC not cooling."])
    return f"maint-{area}-{_stable_id(desc)}", f"Please file a ticket: {desc} ({area}).", \
        "maintenance_create", {"area": area, "description": desc}


def _t_payroll_read(conn, rng):
    return "payroll", "What's payroll looking like this month?", "payroll_read", {}


def _t_campaign_list(conn, rng):
    return "campaigns", rng.choice(["What campaigns are running?", "List active campaigns."]), \
        "campaign_list", {}


def _t_campaign_create(conn, rng):
    name = f"campaign-{rng.randint(1000,9999)}"
    channel = rng.choice(CHANNELS)
    budget = rng.randint(10000, 100000)
    return name, f"Start a {channel} campaign called {name!r} with a ${budget/100:.0f} budget.", \
        "campaign_create", {"name": name, "channel": channel, "budget_cents": budget}


def _t_membership_status(conn, rng):
    return "memberships", "What's the status of our memberships?", "membership_status", {}


def _t_dashboard(conn, rng):
    return "dashboard", rng.choice(["Give me the dashboard summary.", "What do the numbers look like?"]), \
        "dashboard_summary", {}


# WHICH TABLE A WRITE TOOL GROWS, so its example can be rolled back after — see the comment at
# the call site. Every `WRITE_TOOLS` entry from `tools.py` is named here or the roll-back cannot
# find what to undo; a tool that writes and is missing from this map is a silent hole, so
# `test_generate_corpus.py` asserts the two sets agree.
_WRITE_TABLE = {
    "order_draft": "purchase_orders", "enrollment_draft": "enrollments",
    "announcement_post": "announcements", "maintenance_create": "maintenance_requests",
    "campaign_create": "campaigns",
}

_TASKS = {
    "educador": {"agenda": _t_agenda},
    "compras": {"order_list": _t_order_list, "order_draft": _t_order_draft},
    "trainee": {"enrollment_list": _t_enrollment_list, "enrollment_draft": _t_enrollment_draft},
    "marketing": {"announcement_list": _t_announcement_list, "announcement_post": _t_announcement_post,
                 "campaign_list": _t_campaign_list, "campaign_create": _t_campaign_create},
    "it": {"maintenance_list": _t_maintenance_list, "maintenance_create": _t_maintenance_create},
    "cfo": {"payroll_read": _t_payroll_read, "membership_status": _t_membership_status,
           "dashboard_summary": _t_dashboard},
    "dev": {"dashboard_summary": _t_dashboard, "maintenance_list": _t_maintenance_list},
}

# A GUARD THAT READS THE CODE, not a comment promising it — every write tool this file actually
# drives has a rollback table, checked here rather than assumed, at import time so a test or a
# run both trip it.
_used_tools = {tool for tasks in _TASKS.values() for tool in tasks}
_missing_rollback = (_used_tools & tools_mod.WRITE_TOOLS) - set(_WRITE_TABLE)
assert not _missing_rollback, (
    f"these write tools are used in _TASKS with no rollback table named: {_missing_rollback} "
    "— a read task later in the same role would see their leftovers")


def generate(role: str, n: int, seed: int, eval_share: float = 0.15) -> dict:
    rng = random.Random(seed)
    conn = build_training_db(n_students=max(60, n // 3), seed=seed)
    all_students = [r["id"] for r in conn.execute("select id from students").fetchall()]
    eval_ids = set(rng.sample(all_students, max(1, int(len(all_students) * eval_share))))
    # non-student entities ("orders", "enrollments", ...) are shared markers, not held out —
    # they name a TASK KIND, not one row; only per-student tasks (agenda, enrollment) get a
    # real held-out split.
    train, eva = examples_for_role(conn, role, n, rng, eval_ids)

    OUT.mkdir(parents=True, exist_ok=True)
    train_p, eval_p = OUT / f"{role}_train.jsonl", OUT / f"{role}_eval.jsonl"
    train_p.write_text("\n".join(json.dumps(r) for r in train) + ("\n" if train else ""))
    eval_p.write_text("\n".join(json.dumps(r) for r in eva) + ("\n" if eva else ""))
    return {"role": role, "train": len(train), "eval": len(eva),
            "by_kind": dict(Counter(r["kind"] for r in train)),
            "held_out_students": len(eval_ids), "train_path": str(train_p), "eval_path": str(eval_p)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", default="all", choices=["all"] + list(_TASKS))
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20260921)
    a = ap.parse_args()

    roles = list(_TASKS) if a.role == "all" else [a.role]
    reports = {r: generate(r, a.n, a.seed + i) for i, r in enumerate(roles)}
    print(json.dumps(reports, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
