"""The regenerated suite's own invariants, and the gates it was built against.

`results/P50-suite-audit-20260916/` failed all four previous suites, and the
universal failure was that every region sat at exactly one depth. This suite exists
to not do that, so the grid is asserted rather than intended.
"""

import collections

import pytest

from training.email.desk import (
    DEPTHS,
    REGIONS,
    correct,
    generate,
    listing,
    tools_needed,
)
from training.suite_gates import inspect

WAIVER = {"region_not_in_the_prompt":
          "ranking, not routing — the question names the region by design"}


def _suite(n=240, seed=424242):
    return generate(n, seed)["cases"]


def test_the_region_by_depth_grid_is_full_not_a_diagonal():
    """The failure every previous suite had: 4 of 4, 8 of 8, 2 of 2, 3 of 3 pinned."""
    cells = collections.Counter((c["region"], c["depth"]) for c in _suite())
    assert len(cells) == len(REGIONS) * len(DEPTHS)
    assert min(cells.values()) > 0


def test_every_region_spans_every_depth():
    cases = _suite()
    for r in REGIONS:
        assert {c["depth"] for c in cases if c["region"] == r} == set(DEPTHS)


def test_depth_actually_removes_facts_rather_than_labelling_them():
    """The first version handed over the importance signals whatever was asked.

    Outside `importance` that reduced no work at all — the date needed the same
    lookup at depth 1 as at depth 4 — so depth would have been real in the metadata
    and fake in the cases.
    """
    cases = _suite()
    for r in REGIONS:
        given = {d: min(c["given"].count("\n  ")
                        for c in cases if c["region"] == r and c["depth"] == d)
                 for d in DEPTHS}
        assert given[1] > given[4], f"{r}: depth does not remove facts {given}"
        assert given[4] == 0


def test_the_given_facts_are_the_ones_this_question_is_computed_from():
    cases = _suite()
    commitment = [c for c in cases if c["region"] == "commitment" and c["depth"] == 1]
    assert "promise" in commitment[0]["given"].lower()
    counterpart = [c for c in cases if c["region"] == "counterpart"
                   and c["depth"] == 1]
    # How the count is defined, never who wins it — the first version asserted
    # "this sender is the most frequent one", which was the answer wearing a hint.
    assert "frequency is counted" in counterpart[0]["given"].lower()
    assert "most frequent one" not in counterpart[0]["given"].lower()


def test_the_answer_is_never_given_away_in_the_prompt():
    """P15: a value in the prompt makes the tool decoration.

    `yes_no` is checked differently and deliberately: its answer is the word `yes`,
    which also appears as the VALUE of every given fact, so a substring test would
    fire on every case and measure nothing. What matters there is that the four
    signals are never all supplied — one is always missing, so the verdict is never
    derivable without a tool.
    """
    for c in _suite():
        if c["kind"] == "yes_no":
            assert c["given"].count("\n  ") <= 3, c["case_id"]
            continue
        assert c["answer"].lower() not in c["given"].lower(), c["case_id"]


def test_the_listing_carries_no_decisive_fact():
    for c in _suite():
        if c["kind"] == "yes_no":
            continue
        head = c["prompt"].split("Already established")[0]
        assert c["answer"].lower() not in head.lower(), c["case_id"]


def test_the_focus_message_is_not_the_answer_for_inbox_wide_questions():
    """`owed` and `counterpart` ask about the inbox, so the listing must not be it."""
    for c in _suite():
        if c["region"] in ("owed", "counterpart"):
            assert c["msg"]["id"] != c.get("answer"), c["case_id"]
            assert c["msg"]["from_name"] != c["answer"], c["case_id"]


def test_deeper_cases_need_more_tools():
    cases = _suite()
    for r in REGIONS:
        by_depth = {d: len(tools_needed(next(c for c in cases
                                             if c["region"] == r and c["depth"] == d)))
                    for d in DEPTHS}
        assert by_depth[4] >= by_depth[1]


def test_the_verifier_is_mechanical_and_shared():
    """Ranking needs BOTH acceptance and verified quality on the same cases."""
    c = _suite()[0]
    assert correct(c, f"the answer is {c['answer']}")
    assert not correct(c, "I am not sure")
    assert not correct(c, None)


def test_prompt_is_rendered_by_calling_listing_not_by_copying_it():
    """P38: a corpus must teach the prompt the model will be served."""
    for c in _suite(n=40):
        assert c["prompt"] == listing(c)


def test_the_suite_passes_its_own_gates_with_one_declared_waiver():
    cases = _suite()
    rep = inspect("desk", cases, region_of=lambda c: c["region"],
                  prompt_of=lambda c: c["prompt"], depth_of=lambda c: c["depth"],
                  tools_of=tools_needed, waive=WAIVER)
    assert rep.usable is True
    assert rep.waived == ["region_not_in_the_prompt"]
    # A waiver prints. A gate nobody sees is a gate nobody keeps.
    assert "WAIVED" in rep.table() and "waived for:" in rep.table()


def test_without_the_waiver_the_suite_is_not_usable():
    """The waiver has to be a decision, not a default."""
    rep = inspect("desk", _suite(), region_of=lambda c: c["region"],
                  prompt_of=lambda c: c["prompt"], depth_of=lambda c: c["depth"],
                  tools_of=tools_needed)
    assert rep.usable is False


def test_an_unknown_gate_cannot_be_waived():
    with pytest.raises(ValueError, match="not a gate"):
        inspect("x", _suite(n=16), region_of=lambda c: c["region"],
                prompt_of=lambda c: c["prompt"], depth_of=lambda c: c["depth"],
                tools_of=tools_needed, waive={"base_not_at_the_ceiling": "nope"})


# --- P55b: a date is a date in any shape ----------------------------------------

def test_a_date_in_another_shape_is_the_same_answer():
    """The 32B wrote `2023-01-05` for `January 5` on 5 of its 13 'wrong' cases."""
    from training.email.desk import correct
    case = {"answer": "January 5", "kind": "date"}
    for said in ("January 5", "2023-01-05", "Jan 5", "5 January", "January 5th",
                 "I committed to January 5.", "the 5th of January"):
        assert correct(case, said), said
    for said in ("January 6", "2023-02-05", "no date", "", None):
        assert not correct(case, said), said


def test_non_date_answers_still_match_by_substring():
    from training.email.desk import correct
    assert correct({"answer": "msg-007", "kind": "id"}, "It is msg-007.")
    assert not correct({"answer": "Hugo Duarte", "kind": "name"}, "Ana Costa")
