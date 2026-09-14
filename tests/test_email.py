"""The email suite has to be unanswerable from the listing, or it measures nothing.

P15's material could be answered from memory — 27/30 with no tool layer at all — and
the experiment measured nothing until a per-case handbook made recall impossible.
These are the checks that would have caught it there.
"""

import itertools

from training.email.inbox import generate, important
from training.email.tools import SCHEMA, ToolError, answer


def test_the_listing_alone_cannot_beat_the_majority_class():
    """A reader of the listing is guessing — measured where the tools decide.

    SPOTTING AN AUTOMATED MESSAGE IS FREE AND SHOULD BE. `noreply@` is visible in
    the listing and a human tells it at a glance, so leaving those in measures how
    easy that is rather than whether the tools are needed: the first version of this
    test read 0.77 against a 0.555 bar almost entirely on that. **The question the
    tools exist for is which of the HUMAN messages matters**, and that is where the
    ceiling is checked. The automated ones stay in the suite, because filtering them
    is part of the job — they are simply not where the difficulty is.
    """
    inbox = generate(200, 11)
    msgs = [m for m in inbox["messages"] if not m["_facts"]["automated"]]
    truth = [m["_truth"] for m in msgs]
    bar = max(sum(truth), len(truth) - sum(truth)) / len(truth)

    # Every predicate a model could apply to the listing, and every combination.
    feats = {
        "re": lambda m: m["subject"].startswith("Re:"),
        "question": lambda m: "?" in m["preview"],
        "automated_addr": lambda m: any(p in m["from"] for p in
                                        ("noreply", "notifications", "digest",
                                         "billing")),
        "long_subject": lambda m: len(m["subject"]) > 18,
    }
    best = 0.0
    for r in range(1, len(feats) + 1):
        for combo in itertools.combinations(feats, r):
            for signs in itertools.product([True, False], repeat=r):
                hit = sum((all(feats[c](m) is s for c, s in zip(combo, signs))
                           == m["_truth"]) for m in msgs)
                best = max(best, hit / len(msgs))
    assert best <= bar + 0.08, (
        f"a listing-only rule reaches {best:.3f} against a bar of {bar:.3f}; "
        "the tools are decoration and this suite measures nothing")


def test_the_tools_supply_what_the_listing_withholds():
    inbox = generate(30, 5)
    m = next(x for x in inbox["messages"] if not x["_facts"]["automated"])
    assert "i_wrote_in_thread" not in m and "frequent_sender" not in m
    hist = answer(inbox, "thread_history", f"thread_id={m['thread_id']}")
    assert "i_wrote_in_thread" in hist
    stats = answer(inbox, "sender_stats", f"address={m['from']}")
    assert "frequent" in stats


def test_the_definition_is_one_function_used_by_both_sides():
    facts = {"automated": False, "i_wrote_in_thread": True,
             "addressed_directly": True, "asks_something": False,
             "frequent_sender": False}
    assert important(facts) is True
    facts["i_wrote_in_thread"] = False
    assert important(facts) is False
    facts.update({"automated": True, "i_wrote_in_thread": True,
                  "addressed_directly": True, "asks_something": True})
    assert important(facts) is False, "automated is never important, whatever else"


def test_a_tool_refuses_rather_than_inventing():
    inbox = generate(10, 2)
    for call in ("thread_history", "thr-999"), ("message", "id=msg-999"), \
                ("sender_stats", "address=nobody@nowhere.com"):
        try:
            answer(inbox, call[0], call[1] if "=" in call[1]
                   else f"thread_id={call[1]}")
            assert False, f"{call} should have raised"
        except ToolError:
            pass


def test_the_schema_declares_one_required_parameter_each():
    """P28's arity convention renders these positionally; the client maps the value
    back onto the parameter name. That only works if there is exactly one."""
    for t in SCHEMA:
        assert len(t["function"]["parameters"]["required"]) == 1


def test_the_multi_turn_loop_runs_end_to_end():
    """THE PIECE docs/SERVING.md CALLED ASSEMBLED AND NOT MEASURED.

    Every earlier measurement was a single turn. This drives the real path — an
    OpenAI client with `tools=[…]`, the proxy, a model that answers with tags, tool
    results returned as `role: "tool"` — and asserts the loop closes: calls are made,
    none are refused, and every message gets a verdict.
    """
    import json as _json
    import subprocess
    import sys
    import time
    import urllib.request
    from pathlib import Path
    import tempfile

    up = subprocess.Popen([sys.executable, "tests/fixtures/fake_upstream.py"])
    px = subprocess.Popen([sys.executable, "-m", "training.harness.openai_proxy",
                           "--upstream", "http://127.0.0.1:8099", "--port", "8098"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen("http://127.0.0.1:8098/v1/models", timeout=1)
                break
            except Exception:
                time.sleep(0.25)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.json"
            subprocess.run([sys.executable, "-m", "training.harness.agent_sim",
                            "--base-url", "http://127.0.0.1:8098/v1",
                            "--model", "kernel", "--n", "8", "--out", str(out)],
                           capture_output=True, text=True, timeout=120)
            r = _json.loads(out.read_text())
    finally:
        px.terminate(); up.terminate()

    assert r["calls"] > 0, "the model was never asked for a tool"
    assert r["refused"] == 0, f"tools refused {r['refused']} calls the loop produced"
    assert r["undecided"] == 0, "a message never got a verdict"
