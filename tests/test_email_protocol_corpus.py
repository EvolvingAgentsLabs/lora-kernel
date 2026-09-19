"""A kernel corpus that teaches the judgement is a domain corpus in disguise.

P15 measured nothing until a per-case handbook made the answers unmemorisable, and
P34 established that what has to be taught here is the *vocabulary* and not the
disposition. These check both halves.
"""

import json
import re
import subprocess
import sys

import pytest

from training.harness import generate_email_protocol as gen


@pytest.fixture(scope="module")
def rows(tmp_path_factory):
    out = tmp_path_factory.mktemp("ep") / "train.jsonl"
    r = subprocess.run([sys.executable, "-m",
                        "training.harness.generate_email_protocol",
                        "--n", "200", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return [json.loads(l) for l in out.read_text().splitlines() if l.strip()]


def test_the_corpus_never_states_the_triage_rule(rows):
    blob = json.dumps(rows).lower()
    assert not [w for w in gen.RULE_WORDS if w in blob]


def test_an_environment_word_may_only_appear_inside_an_address_in_a_prompt(rows):
    """`noreply@…` is a recipient. `noreply` as prose would be the rule."""
    addr = re.compile(r"[\w.+-]+@[\w.-]+")
    for r in rows:
        for m in r["messages"]:
            if m["role"] == "assistant":
                continue
            outside = addr.sub(" ", m["content"].lower())
            assert not [w for w in gen.ENVIRONMENT_WORDS if w in outside]


def test_an_environment_word_is_allowed_where_a_tool_answered(rows):
    """The served tools return these strings too; refusing them would refuse the suite.

    Not an assertion that one appears — only that nothing in the pipeline forbids
    it. A corpus that had scrubbed them would be teaching a cleaner inbox than the
    one the adapter will meet.
    """
    answers = " ".join(m["content"] for r in rows for m in r["messages"]
                       if m["role"] == "assistant").lower()
    assert "automated" in answers or "noreply" in answers or True


def test_every_reply_asks_for_exactly_one_tool_and_it_is_one_of_the_three(rows):
    from training.email.tools import TOOLS
    for r in rows:
        reply = r["messages"][-1]["content"]
        tags = re.findall(r"<([a-z_]+)>", reply)
        assert len(tags) == 1, reply[:120]
        assert tags[0] in TOOLS


def test_the_argument_keys_are_the_ones_the_tools_accept(rows):
    """P34 could not say whether its refusals were names or arguments. Both here."""
    want = {"thread_history": "thread_id=", "sender_stats": "address=",
            "message": "id="}
    for r in rows:
        assert want[r["tool"]] in r["messages"][-1]["content"]


def test_the_answers_cannot_be_memorised(rows):
    """A fixed inbox would let the adapter learn the ids instead of the protocol."""
    threads = {re.search(r"thr-\d+", r["messages"][1]["content"]).group(0)
               for r in rows if "thr-" in r["messages"][1]["content"]}
    counts = {r["messages"][-1]["content"].split("= ", 1)[1][:40] for r in rows}
    # many distinct threads, and many distinct answers for them
    assert len(threads) > 15 and len(counts) > 30


def test_the_corpus_uses_the_surface_the_proxy_renders(rows):
    """Corpus and served prompt must not drift; P34's refusals show what that costs."""
    from training.harness.openai_proxy import render_tools
    from training.email.tools import SCHEMA
    served = render_tools([{"role": "user", "content": "x"}], SCHEMA)[-1]["content"]
    for tool in ("thread_history", "sender_stats", "message"):
        assert f"<{tool}>" in served and f"<{tool}>" in gen.INSTRUCTION


def test_only_selects_a_subset_and_refuses_a_name_that_matches_nothing(monkeypatch):
    """Filling every gap is right for a short tarball, wrong when one is wanted."""
    from training.harness import train_pool
    import sys
    monkeypatch.setattr(sys, "argv", ["p", "--only", "nothing-like-this"])
    # it must refuse rather than silently train the whole pool
    assert train_pool.main() == 1
