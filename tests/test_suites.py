"""The suite record: what the runner reads, and that `email` did not move.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §4.4, §8.1). The drafter is served the
prefix its corpus taught — SYSTEM, listing, tool block — so the record for a suite must
reproduce that prefix byte for byte; for the desk the block is the same function
(`tools_to_instruction`, arity on) over the desk surface that `generate_desk.py`
rendered into the corpus. And the corpus-mode recursion
s_j = s_{j-1} || s̃_j || "= tool(s̃_j)\\n" has to run unchanged over the new surface:
four tags, a positional shim by parameter count, a free-text answer verified by
substring.
"""

from __future__ import annotations

import json

from training.harness import suites
from training.harness.accept_rank import CLOSE, POSITIONAL, run_chain, user_text
from training.harness.generate_desk import INSTRUCTION as DESK_BLOCK
from training.email.inbox import generate as gen_inbox


def scripted(*chunks):
    it = iter(chunks)
    return lambda prefix: next(it)


def test_the_email_suite_is_the_runner_before_the_refactor_byte_for_byte():
    s = suites.load("email")
    inbox = gen_inbox(12, 717171)
    cases = s.cases(12, 717171)
    m = inbox["messages"][0]
    assert s.user_text(cases[0]) == user_text(m)
    assert s.close == CLOSE and s.positional == POSITIONAL
    assert s.eval_n == 475 and s.eval_seed == 717171
    assert [c.human for c in cases] == [not x["_facts"]["automated"] for x in inbox["messages"]]
    assert s.parse("NOT IMPORTANT") is False and s.parse("IMPORTANT") is True


def test_the_desk_suite_is_commitment_only_and_the_size_the_brief_names():
    s = suites.load("desk")
    cases = s.cases(960, 424242)
    assert len(cases) == 240
    assert {c.meta["depth"] for c in cases} == {1, 2, 3, 4}
    assert all(c.meta["region"] == "commitment" and c.human for c in cases)
    assert s.bar(cases) == 0.0


def test_the_desk_block_is_the_one_the_corpus_taught():
    s = suites.load("desk")
    assert s.block == DESK_BLOCK
    row = json.loads(open("training/harness/data_desk/train.jsonl").readline())
    assert row["messages"][0]["content"] == s.system
    assert row["messages"][1]["content"].endswith("\n\n" + s.block)


def test_the_desk_positional_map_keys_on_count_and_skips_the_zero_parameter_tool():
    s = suites.load("desk")
    assert set(s.positional) == {"thread_history", "sender_stats", "message"}
    assert "inbox" not in s.positional


def test_the_loop_runs_over_the_desk_surface_and_verifies_a_date():
    s = suites.load("desk")
    case = s.cases(960, 424242)[0]
    gen = scripted(f"<message>{case.user.split()[1]}</message>", case.truth)   # positional id
    out = run_chain(gen, case.ctx, suite=s)
    assert out["calls"] == 1 and out["refused"] == 0
    assert '"body":' in out["text"]
    assert case.verify(out["verdict"]) is True


def test_the_desk_loop_stops_at_all_four_tags():
    s = suites.load("desk")
    case = s.cases(960, 424242)[0]
    gen = scripted("<inbox></inbox>", "nothing")
    out = run_chain(gen, case.ctx, suite=s)
    assert out["calls"] == 1 and out["refused"] == 0 and out["text"].startswith("<inbox></inbox>= [")


def test_an_unknown_suite_is_refused():
    import pytest
    with pytest.raises(ValueError):
        suites.load("physics")
