"""The deep commitment band — a difficulty axis for a *trained* expert.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §8.2, §8.3). The ordering test needs
Q(T) ≥ max Q(E) AND graded experts that do not saturate; on the shallow band
g75 ≡ g600 = 1.000 because the promise is the last message and one call copies it.
Here the answer is my LATEST promise in a thread whose last message, at depth ≥ 2, is
the sender's, with the sender's own dates as distractors — so the chain has to read
history and discriminate. The verifier accepts exactly one named date. And the shallow
suite P51/P55b scored is pinned by hash: adding a region must not move a byte of it.
"""

import hashlib
import json

from training.email.desk import DEEP, correct, dates_in, generate
from training.email.desk_tools import answer

GUARD = {"commitment": "c73d5fb0af6297f8", "all": "5fe8bfde795ed75d"}


def _hash(cases):
    return hashlib.sha256("\n".join(c["prompt"] + "|" + c["answer"] for c in cases).encode()).hexdigest()[:16]


def test_the_shallow_suite_did_not_move_a_byte():
    """P51 and P55b scored these; a deep band that changed them would void both."""
    cs = generate(960, 424242)["cases"]
    assert _hash([c for c in cs if c["region"] == "commitment"]) == GUARD["commitment"]
    assert _hash(cs) == GUARD["all"]


def test_the_deep_band_fills_every_depth_and_only_when_asked():
    cs = generate(960, 424242, regions=(DEEP,))["cases"]
    assert len(cs) == 960 and {c["depth"] for c in cs} == {1, 2, 3, 4}
    assert all(c["region"] == DEEP for c in cs)
    assert not any(c["region"] == DEEP for c in generate(40, 1)["cases"])


def test_at_depth_two_and_up_the_last_message_is_not_mine():
    """So `message(id)` alone cannot answer — the history has to be read."""
    for c in generate(200, 7, regions=(DEEP,))["cases"]:
        hist = c["desk"]["threads"][c["msg"]["thread_id"]]
        if c["depth"] >= 2:
            assert hist[-1]["from"] != c["desk"]["me"]
        assert c["answer"] in " ".join(h["preview"] for h in hist if h["from"] == c["desk"]["me"])


def test_the_answer_is_the_latest_promise_and_distractors_are_real_dates():
    for c in generate(200, 7, regions=(DEEP,))["cases"]:
        f = c["msg"]["_facts"]
        assert c["answer"] == f["promises"][-1]
        if c["depth"] >= 3:
            assert len(f["promises"]) == c["depth"] - 1 and len(c["distractors"]) == 2 * (c["depth"] - 2)
            for d in c["distractors"]:
                assert dates_in(d)


def test_the_desk_thread_history_carries_the_previews():
    c = generate(8, 3, regions=(DEEP,))["cases"][0]
    out = json.loads(answer(c["desk"], "thread_history", f"thread_id={c['msg']['thread_id']}"))
    assert "messages" in out and out["messages"][0]["preview"]
    assert out["turns"] == len(out["messages"])


def test_the_verifier_accepts_exactly_one_named_date():
    case = {"answer": "September 6", "kind": "date"}
    assert correct(case, "September 6")
    assert correct(case, "I committed to 2023-09-06.")
    assert not correct(case, "June 12 or September 6")        # two dates: decided nothing
    assert not correct(case, "June 12")
    assert not correct(case, "no date")


def test_the_answer_is_never_in_the_prompt():
    for c in generate(120, 11, regions=(DEEP,))["cases"]:
        assert c["answer"] not in c["prompt"]
        for d in c["distractors"]:
            assert d not in c["prompt"]


# --- Phase 2's entry condition: the static suite gates, on the deep band ---------------

def test_the_deep_band_passes_the_static_suite_gates():
    """The seven lessons as gates (P50). `region_not_in_the_prompt` is declared to
    fail for the desk — ranking was chosen over routing — so the three structural
    gates a single-region suite can pass are the ones asserted."""
    from training.suite_gates import (depth_is_not_the_region, has_a_difficulty_axis,
                                      the_answer_is_not_a_copy)
    cs = generate(240, 424242, regions=(DEEP,))["cases"]
    axis = has_a_difficulty_axis(cs, depth_of=lambda c: c["depth"])
    sep = depth_is_not_the_region(cs, region_of=lambda c: c["region"], depth_of=lambda c: c["depth"])
    copy = the_answer_is_not_a_copy(cs, prompt_of=lambda c: c["prompt"], answer_of=lambda c: c["answer"])
    for f in (axis, sep, copy):
        assert f.passed, f"{f.name}: {f.detail}"
