

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


# --------------------------------------------------------------------------
# Resumability. P47 was lost twice on the same measurement: to a KeyError after
# all 475 cases had been scored, and to a Colab session that stopped answering at
# 260 of 475 **[ran]** 2026-09-16. The first fix did not help the second, because
# the loop still wrote once, at the end.
# --------------------------------------------------------------------------

def _stub(monkeypatch, seen):
    from training.harness import agent_sim

    def one(base_url, key, model, inbox, msg, *a, **k):
        seen.append(msg["id"])
        return {"verdict": msg["_truth"], "calls": 1, "refused": 0, "turns": 2,
                "confidence": 0.8, "answered_first": True, "asked": [],
                "text": "IMPORTANT"}

    monkeypatch.setattr(agent_sim, "triage_one", one)
    return agent_sim


def test_a_run_checkpoints_before_it_finishes(tmp_path, monkeypatch):
    import json
    import sys

    seen = []
    agent_sim = _stub(monkeypatch, seen)
    out = tmp_path / "r.json"

    # Die after the first checkpoint, the way a reclaimed session does.
    real = agent_sim.triage_one

    def explode(*a, **k):
        if len(seen) >= 30:
            raise RuntimeError("session stopped answering")
        return real(*a, **k)

    monkeypatch.setattr(agent_sim, "triage_one", explode)
    monkeypatch.setattr(sys, "argv", ["p", "--n", "60", "--out", str(out)])
    try:
        agent_sim.main()
    except RuntimeError:
        pass
    saved = json.loads(out.read_text())
    assert saved["partial"] is True
    assert len(saved["records"]) == 25, "nothing was persisted before the death"


def test_a_second_attempt_resumes_instead_of_rescoring(tmp_path, monkeypatch,
                                                       capsys):
    import sys

    seen = []
    agent_sim = _stub(monkeypatch, seen)
    out = tmp_path / "r.json"
    monkeypatch.setattr(sys, "argv", ["p", "--n", "40", "--out", str(out)])
    agent_sim.main()
    first = len(seen)
    assert first == 40

    seen.clear()
    agent_sim.main()
    # THE POINT: the second attempt pays for nothing it already has.
    assert seen == [], f"rescored {len(seen)} cases that were already on disk"
    assert "resuming" in capsys.readouterr().out


def test_an_unreadable_checkpoint_is_reported_and_does_not_stop_the_run(
        tmp_path, monkeypatch, capsys):
    import sys

    seen = []
    agent_sim = _stub(monkeypatch, seen)
    out = tmp_path / "r.json"
    out.write_text("{ this is not json")
    monkeypatch.setattr(sys, "argv", ["p", "--n", "8", "--out", str(out)])
    assert agent_sim.main() == 0
    assert "could not reuse" in capsys.readouterr().out
    assert len(seen) == 8
