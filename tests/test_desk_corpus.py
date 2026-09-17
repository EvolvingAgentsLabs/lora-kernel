"""The desk `commitment` corpus: the target's chain, served the way it will be scored.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §4.4, §8.3). An adapter learns
p(x_t | x_<t) for the prefixes its corpus contains, so the corpus must be, byte for
byte, the prompt the runner will serve: the same SYSTEM, the same listing, the same tool
block, and the chain rendered as `<tag>body</tag>= {result}` followed by the answer.
The grades are nested prefixes of one seeded shuffle, D_25 ⊂ D_75 ⊂ D_600, so that
*how much* is the only variable between them; and every evaluation prompt is excluded
by content, so nothing the verifier scores was ever in training.
"""

from __future__ import annotations

import json
import re

import pytest

from training.email.desk import correct, generate
from training.harness import graded
from training.harness.desk_sim import SYSTEM
from training.harness.generate_desk import EVAL_N, EVAL_SEED, INSTRUCTION, OUT, chain_for

CALL = re.compile(r"<([A-Za-z_][\w-]*)>([^<]*)</\1>")
ROWS = [json.loads(l) for l in open(OUT) if l.strip()]


def test_the_corpus_is_the_size_and_shape_the_brief_names():
    assert len(ROWS) == 600
    assert {r["depth"] for r in ROWS} == {1, 2, 3, 4}
    assert all(r["region"] == "commitment" for r in ROWS)


def test_no_evaluation_prompt_is_in_the_corpus():
    """Excluded by content, not by seed: a different draw can reproduce a listing."""
    held = {c["prompt"] for c in generate(EVAL_N, EVAL_SEED)["cases"]}
    user = {r["messages"][1]["content"].split("\n\nThe following tools")[0] for r in ROWS}
    assert not (user & held)


def test_every_oracle_answer_verifies_and_is_read_off_the_message_body():
    for r in ROWS:
        asst = r["messages"][2]["content"]
        calls = CALL.findall(asst)
        assert [c[0] for c in calls] == ["message"], "the chain is the target's: one `message`"
        assert calls[0][1].startswith("id=msg-")
        # the injected result carries the date the answer copies
        body = asst.split("= ", 1)[1].split("\n")[0]
        assert r["answer"] in json.loads(body)["body"]
        assert correct({"answer": r["answer"]}, asst.splitlines()[-1])


def test_the_user_turn_is_system_listing_and_the_desk_block():
    r = ROWS[0]
    assert r["messages"][0] == {"role": "system", "content": SYSTEM}
    assert r["messages"][1]["content"].endswith("\n\n" + INSTRUCTION)
    for tag in ("inbox", "thread_history", "sender_stats", "message"):
        assert f"<{tag}>" in INSTRUCTION


def test_the_chain_is_declared_once_and_used_everywhere():
    case = generate(4, EVAL_SEED)["cases"][0]
    assert [t for t, _ in chain_for(case)] == ["message"]


def test_the_grades_are_nested_cover_every_depth_and_reproduce(tmp_path):
    subs = graded.nested_subsets(ROWS, graded.DESK_SIZES)
    ids = {k: {r["case_id"] for r in v} for k, v in subs.items()}
    assert ids[25] < ids[75]
    for k, v in subs.items():
        assert {r["depth"] for r in v} == {1, 2, 3, 4}
        on_disk = [json.loads(l) for l in open(graded.path_for(k, graded.DESK)) if l.strip()]
        assert on_disk == v, f"train_g{k}.jsonl is not what nested_subsets() produces"


def test_a_grade_missing_a_depth_is_refused():
    rows = [{"case_id": f"x{i}", "depth": 1 + (i % 3)} for i in range(30)]
    assert graded.balanced(rows) is not None
