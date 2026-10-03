"""ROUTE0's rule (training/harness/factored_router.py): local iff exactly one paragraph is not the member's content and
it is the member's task. Synthetic corpora — the measured sets are scored once, in results/ROUTE0-*."""
from training.harness.factored_router import FactoredRouter

HEAD = "Message msg-1 in thread thr-1\nFrom: A B <a@b.com>\nSubject: x\nPreview: y"
CORPORA = {"email": [f"{HEAD}\n\nIs this important?"] * 3,
           "desk": [f"{HEAD}\n\nAlready established:\n  You made a promise in this thread: yes\n\n"
                    "What date did you commit to in this thread?"] * 3}


def test_task_and_content_both_have_to_match():
    r = FactoredRouter(CORPORA)
    other = "Message msg-77 in thread thr-9\nFrom: Aroha Ngata <aroha@wharekai.nz>\nSubject: hui\nPreview: kia ora"
    assert r.decide(f"{other}\n\nIs this important?") == "email"                       # an unseen sender stays
    assert r.decide(f"Is this important?\n\n{other}") == "email"                       # order is free
    assert r.decide(f"{other}\n\nDraft a reply to this.") == "out"                     # another task leaves
    assert r.decide(f"{other}\n\nIs this important?\n\nAlso draft a reply.") == "out"  # two tasks leave
    assert r.decide("A tank holds 30 L of water.\n\nIs this important?") == "out"      # not the member's content
    assert r.decide("Is this important?") == "out"                                     # a task with nothing under it
    assert r.decide(f"{other}\n\nImportant or not?") == "out"                          # a paraphrase leaves (reported)
    desk = f"{other}\n\nAlready established:\n  You made a promise in this thread: yes\n\nWhat date did you commit to in this thread?"
    assert r.decide(desk) == "desk"


def test_openclaws_stamp_is_removed_before_routing():
    r = FactoredRouter(CORPORA)
    assert r.decide(f"[Fri 2026-10-02 10:00 GMT-3] {HEAD}\n\nIs this important?") == "email"


def test_the_proxy_route_keeps_a_region_without_a_corpus_on_its_keys():
    """route.decide_factored: pool members by task and content; fluids (no corpus in the pool) by its keys."""
    from training.harness import route
    msg = lambda t: {"messages": [{"role": "user", "content": t}]}
    # fluids is measured `out` in route.REGIONS: its keys still name it, and the serve table sends it out
    assert route.decide_factored(msg("A pump lifts water; find the head loss in the pipe.")) == ("out", "fluids-full is served out")
    assert route.decide_factored(msg("Write me a haiku."))[0] == "out"
