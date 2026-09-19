"""Milestone 5: verifiable questions over a real procedure, and a runner that stays off the laptop.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §9.4). Headroom is only readable if the checker
scores the capability and not the phrasing, and if the unmemorisable item really is not answerable
from the question."""

import re
from pathlib import Path

from training.nursing import questions as Q
from training.nursing.source import ATTRIBUTION, CHECKLISTS, note


def test_the_suite_is_fixed_and_has_four_kinds():
    a, b = Q.build(), Q.build()
    assert a == b and len(a) == 72
    assert {q["kind"] for q in a} == {"order", "next", "rate", "site"}


def test_a_letter_is_scored_however_it_is_phrased_and_two_letters_are_not_an_answer():
    q = next(x for x in Q.build() if x["kind"] == "order")
    right, wrong = q["answer"], ("A" if q["answer"] == "B" else "B")
    assert Q.check(q, right) and Q.check(q, f"{right}.") and Q.check(q, f"The answer is {right}")
    assert not Q.check(q, wrong) and not Q.check(q, f"{right} or {wrong}") and not Q.check(q, "")


def test_every_keyed_answer_is_the_step_that_really_follows():
    for q in Q.build():
        if q["kind"] != "next":
            continue
        steps = CHECKLISTS[q["checklist"]]
        done = re.search(r'completed this step:\n"(.*)"\nWhich', q["question"], re.S).group(1)
        opts = dict(re.findall(r"^([A-D])\. (.*)$", q["question"], re.M))
        assert opts[q["answer"]] == steps[steps.index(done) + 1]


def test_the_site_value_is_not_the_textbooks_and_is_not_in_the_question():
    """P21 on real content: the channel has to be needed, or an open book measures nothing."""
    for q in Q.build():
        if q["kind"] == "site":
            assert q["answer"] != q["textbook"]
            assert str(q["answer"]) not in q["question"] and str(q["answer"]) in q["site_note"]


def test_a_note_carries_its_attribution():
    assert ATTRIBUTION in note("discontinuing an IV") and "CC BY 4.0" in ATTRIBUTION


def test_no_runner_in_this_package_reaches_for_a_local_model():
    """The user's instruction, 2026-09-19: no model on local resources — Colab for everything."""
    for f in Path("training/nursing").glob("*.py"):
        code = "\n".join(l for l in f.read_text().split("\n") if not l.lstrip().startswith("#"))
        code = re.sub(r'"""(.*?)"""', "", code, flags=re.S)          # prose may name what it replaced
        assert "ollama" not in code.lower() and "11434" not in code, f.name
