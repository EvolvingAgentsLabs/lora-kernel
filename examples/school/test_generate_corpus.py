"""Zero-GPU checks for the school's training corpus generator — no model, nothing trained.

Two regressions this file exists to hold, both found by running the generator twice and reading
its output, not by inspecting the code and assuming it was fine:

1. A write task (`order_draft`) and a read task (`order_list`) share one connection so entity ids
   stay stable across the corpus; the first version let that same connection let write tasks grow
   what a later read task saw, so `order_list`'s completion drifted from ~1 KB to ~7 KB over one
   run — an instrument bug in the same family `../../CLAUDE.md` §3 already names.
2. `ORDER BY random()` is SQLite's own PRNG, seeded from system entropy, not from this file's
   `random.Random(seed)` — and Python's builtin `hash()` is randomised per process, the exact bug
   `../../evolving-memory`'s central test already failed 6 of 30 seeds on. Both were in this file's
   first version; `../../CLAUDE.md` §7 promises a formula tied to a run, and a generator that is
   not reproducible from its own seed cannot keep that promise.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import generate_corpus as gc
from . import tools as tools_mod


def test_every_used_write_tool_has_a_rollback_table():
    """The module-level assertion already enforces this at import time; re-asserted here so a
    change that removed the assertion would still be caught."""
    used = {tool for tasks in gc._TASKS.values() for tool in tasks}
    missing = (used & tools_mod.WRITE_TOOLS) - set(gc._WRITE_TABLE)
    assert not missing


def test_a_write_task_does_not_leak_into_a_later_read_tasks_answer():
    """The regression test for the bug this file's docstring names: generate order_draft and
    order_list many times, interleaved, on one shared connection, and confirm every order_list
    completion is byte-identical — not growing with how many order_draft rows came before it."""
    import random
    conn = gc.build_training_db(n_students=30, seed=1)
    claim = gc._claim_for("compras")
    completions = []
    rng = random.Random(2)
    for i in range(30):
        if i % 2 == 0:
            row = gc._t_order_draft(conn, rng)
        else:
            row = gc._t_order_list(conn, rng)
        _, _, tool_name, args = row
        write_table = gc._WRITE_TABLE.get(tool_name)
        before = (conn.execute(f"select max(id) from {write_table}").fetchone()[0]
                 if write_table else None)
        result = tools_mod.answer(conn, claim, tool_name, args)
        if write_table is not None:
            conn.execute(f"delete from {write_table} where id > ?", (before or 0,))
            conn.commit()
        if tool_name == "order_list":
            completions.append(result)
    assert len(completions) > 1
    assert len(set(completions)) == 1, "order_list drifted across interleaved order_draft calls"


def test_generated_rows_are_shaped_like_a_training_row():
    report = gc.generate("educador", n=20, seed=99)
    rows = [json.loads(l) for l in open(report["train_path"])]
    assert rows, "no rows written"
    for r in rows:
        roles_seen = [m["role"] for m in r["messages"]]
        assert roles_seen == ["system", "user", "assistant"]
        assert "<agenda_read>" in r["messages"][2]["content"]
        assert "=" in r["messages"][2]["content"]                   # the call, then its own result


def test_no_completion_repeats_within_a_role():
    report = gc.generate("trainee", n=60, seed=100)
    rows = [json.loads(l) for l in open(report["train_path"])] + \
        [json.loads(l) for l in open(report["eval_path"])]
    completions = [r["messages"][2]["content"] for r in rows]
    assert len(completions) == len(set(completions))


def test_held_out_entities_never_appear_in_the_train_file():
    report = gc.generate("educador", n=40, seed=101)
    train = [json.loads(l) for l in open(report["train_path"])]
    eva = [json.loads(l) for l in open(report["eval_path"])]
    train_students = {r["entity_id"] for r in train}
    eval_students = {r["entity_id"] for r in eva}
    assert not (train_students & eval_students), "an entity leaked across the held-out split"


def test_every_role_produces_at_least_one_row():
    """A pure zero-argument aggregate read (cfo's payroll_read, dashboard_summary,
    membership_status) has exactly one correct answer per world snapshot — this asserts the
    generator still produces that one example rather than silently writing nothing, the same
    "fixed knowledge prices nothing" shape ../../CLAUDE.md §3 already names (P15, P21), now for
    an aggregate read instead of a lookup table."""
    for role in gc._TASKS:
        report = gc.generate(role, n=30, seed=102)
        assert report["train"] + report["eval"] > 0, f"{role} produced no rows at all"


def test_generation_is_reproducible_from_its_own_seed():
    """Regression test for both bugs this file's docstring names: run the two roles that used
    them (`educador`/`_random_student`'s old `ORDER BY random()`, `marketing`/`it`'s old
    `hash()`) twice, same seed, and confirm the files are byte-identical."""
    for role in ("educador", "marketing", "it", "trainee"):
        r1 = gc.generate(role, n=60, seed=777)
        content1 = [Path(r1["train_path"]).read_text(), Path(r1["eval_path"]).read_text()]
        r2 = gc.generate(role, n=60, seed=777)
        content2 = [Path(r2["train_path"]).read_text(), Path(r2["eval_path"]).read_text()]
        assert content1 == content2, f"{role}'s corpus is not reproducible from seed 777"
