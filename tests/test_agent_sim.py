

# --------------------------------------------------------------------------
# The logprobs seam, added 2026-09-16 for P47. P44 measured the confidence in the
# tool-free configuration; P46 showed that configuration is at its information
# ceiling, so the question moved to the end of a tool chain — where it could not be
# read at all until this existed.
# --------------------------------------------------------------------------

def _final(content, top=None):
    """A server reply with no tool calls: the turn that answers."""
    ch = {"message": {"role": "assistant", "content": content}}
    if top is not None:
        ch["logprobs"] = {"content": [{"top_logprobs": top}]}
    return {"choices": [ch]}


def test_no_logprobs_requested_means_no_confidence_and_no_claim_about_it(monkeypatch):
    from training.harness import agent_sim
    monkeypatch.setattr(agent_sim, "chat",
                        lambda *a, **k: _final("NOT IMPORTANT"))
    r = agent_sim.triage_one("u", None, "m", {"messages": [], "threads": {},
                                              "sent_counts": {}},
                             {"id": "m1", "thread_id": "t1", "from_name": "A",
                              "from": "a@b.c", "subject": "s", "preview": "p"},
                             4, 64)
    assert r["verdict"] is False
    assert r["confidence"] is None
    # Not False: nothing was asked, so nothing is known about where the model began.
    assert r["answered_first"] is None


def test_the_payload_carries_top_logprobs_only_when_asked(monkeypatch):
    from training.harness import agent_sim
    seen = []

    def spy(base_url, key, payload, timeout=300):
        seen.append(payload)
        return _final("IMPORTANT", [{"token": "IMP", "logprob": -0.1}])

    monkeypatch.setattr(agent_sim, "chat", spy)
    args = ("u", None, "m", {"messages": [], "threads": {}, "sent_counts": {}},
            {"id": "m1", "thread_id": "t1", "from_name": "A", "from": "a@b.c",
             "subject": "s", "preview": "p"}, 4, 64)
    agent_sim.triage_one(*args)
    assert "top_logprobs" not in seen[-1]
    agent_sim.triage_one(*args, logprobs=20)
    assert seen[-1]["top_logprobs"] == 20 and seen[-1]["logprobs"] is True


def test_a_preamble_is_reported_as_unread_not_averaged_in(monkeypatch):
    """A model that opens with prose puts a word where the decision should be.

    Reading that as a confidence would measure phrasing. It comes back None, and
    `answered_first` False says which kind of None it is — so the share is
    countable and a run can be declared void on it.
    """
    from training.harness import agent_sim
    monkeypatch.setattr(agent_sim, "chat", lambda *a, **k: _final(
        "Based on the thread history, this is IMPORTANT",
        [{"token": "Based", "logprob": -0.05}]))
    r = agent_sim.triage_one("u", None, "m",
                             {"messages": [], "threads": {}, "sent_counts": {}},
                             {"id": "m1", "thread_id": "t1", "from_name": "A",
                              "from": "a@b.c", "subject": "s", "preview": "p"},
                             4, 64, logprobs=20)
    assert r["verdict"] is True          # the verdict is still readable from the text
    assert r["answered_first"] is False  # but the confidence is not
    assert r["confidence"] is None
