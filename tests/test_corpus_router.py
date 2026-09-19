"""Milestone 2, arm 1 — the router as an n-gram model of the members' corpora.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §8.4, §8.5). A router is scored on the term
it can change — a request served by a member whose corpus it does not belong to counts as
wrong — and on abstention. These protect the measured verdict
(results/M2-corpus-router-20260919/BRIEF.md) in BOTH directions: what the arm buys, and the
limit that keeps it out of the proxy. If the last test here starts failing, the record is
stale and has to be rewritten, not the test.
"""

import pytest

from training.harness import route, router_sets
from training.harness.corpus_router import CorpusRouter, request_text, tokens


@pytest.fixture(scope="module")
def router():
    return CorpusRouter.from_pool()


@pytest.fixture(scope="module")
def sets():
    return {**router_sets.build(), **router_sets.build_fresh()}


def _dictionary(text):
    d = route.decide({"messages": [{"role": "user", "content": text}]})
    return d[1] if d[0] == "local" else "out"


def test_the_router_sees_the_request_before_the_proxy_renders_tools_into_it():
    assert request_text("Is this important?\n\nThe following tools are available. x") == "Is this important?"


def test_ids_are_one_symbol_and_a_request_has_an_end():
    assert tokens("msg-029")[1:] == ["msg", "-", "#", "</s>"]


def test_in_distribution_nothing_is_lost_and_nothing_is_misrouted(router, sets):
    s = router_sets.score(router.decide, {"A": sets["A"]})["A"]
    assert (s["local_right_member"], s["misrouted_to_local"], s["lost_local"]) == (715, 0, 0)


@pytest.mark.parametrize("name", ["C", "D", "E", "C2", "E2"])
def test_foreign_text_is_never_served_by_a_member(router, sets, name):
    assert router_sets.score(router.decide, {name: sets[name]})[name]["misrouted_to_local"] == 0


def test_the_headroom_is_real_the_dictionary_serves_foreign_text_locally(sets):
    got = router_sets.score(_dictionary, {k: sets[k] for k in ("C2", "E2")})
    assert got["C2"]["misrouted_to_local"] == 8 and got["E2"]["misrouted_to_local"] == 51


def test_a_request_two_members_could_claim_goes_out(router):
    both = ("Message msg-003 in thread thr-003\nFrom: A B <a.b@x.com>\nSubject: s\nPreview: p.\n\n"
            "Is this important?\n\nWhat date did you commit to in this thread?")
    assert router.decide(both) == "out"


def test_KNOWN_LIMIT_every_request_from_an_unseen_sender_is_lost(router, sets):
    """Why this arm is not in the proxy. Every generated address ends `.com`, so `. com >` is
    frame, and a real sender leaves the distribution [ran] M2. The dictionary keeps all 120."""
    assert router_sets.score(router.decide, {"F": sets["F"]})["F"]["lost_local"] == 120
    assert router_sets.score(_dictionary, {"F": sets["F"]})["F"]["lost_local"] == 0
