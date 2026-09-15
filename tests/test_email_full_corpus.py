"""The ceiling arm has to be a ceiling, not a memory test.

P15 scored 27/30 from recall alone before a per-case handbook made that
impossible. These are the checks that would have caught it there.
"""

import json
import subprocess
import sys

import pytest

from training.harness import generate_email_full as gen


@pytest.fixture(scope="module")
def rows(tmp_path_factory):
    out = tmp_path_factory.mktemp("ef") / "train.jsonl"
    r = subprocess.run([sys.executable, "-m",
                        "training.harness.generate_email_full",
                        "--n", "300", "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return [json.loads(l) for l in out.read_text().splitlines() if l.strip()]


def test_no_listing_the_run_will_be_scored_on_is_in_the_corpus(rows):
    """Excluding seed 717171 is not enough, and the first version of this test
    only proved it was not enough by accident.

    Message ids run msg-000..msg-029 and subjects come from a fixed list, so a
    different draw reproduces a listing by chance. That first version matched id
    and subject anywhere in the corpus and reported 16 hits — most of them not
    exploitable at all. The number that matters is **the same listing carrying the
    same verdict**, and it was 2 of 150. Small enough to sit inside the gate's
    noise; cheap enough to remove outright, which the generator now does.
    """
    from training.email.inbox import generate
    seen = {r["messages"][1]["content"].split("\n\nThe following")[0] for r in rows}
    overlap = [m for m in generate(150, gen.EVAL_SEED)["messages"]
               if gen.listing(m) in seen]
    assert not overlap, (
        f"{len(overlap)} listings this run will be scored on are in its own "
        "training data")


def test_the_corpus_is_not_lopsided(rows):
    """The base already answers NOT IMPORTANT to everything; a lopsided corpus
    would reinforce the exact failure this adapter exists to fix."""
    share = sum(r["truth"] for r in rows) / len(rows)
    assert 0.3 <= share <= 0.7, share


def test_an_automated_message_is_settled_without_spending_a_call(rows):
    """Asking three tools for something visible in the listing is its own error."""
    auto = [r for r in rows if r["automated"]]
    assert auto, "no automated messages in the corpus"
    assert all(r["calls"] == 0 for r in auto)
    assert all(r["truth"] is False for r in auto)


def test_a_human_message_is_never_decided_without_asking(rows):
    """The listing withholds every signal but one; deciding from it is guessing."""
    human = [r for r in rows if not r["automated"]]
    assert human and all(r["calls"] == 3 for r in human)


def test_the_verdict_is_the_scorer_s_own_definition(rows):
    """Corpus and scorer must not drift; both read inbox.important."""
    for r in rows[:40]:
        last = r["messages"][-1]["content"].strip().splitlines()[-1]
        assert last == ("IMPORTANT" if r["truth"] else "NOT IMPORTANT")


def test_it_teaches_the_surface_the_proxy_renders(rows):
    from training.harness.openai_proxy import render_tools
    from training.email.tools import SCHEMA
    served = render_tools([{"role": "user", "content": "x"}], SCHEMA)[-1]["content"]
    for tool in ("thread_history", "sender_stats", "message"):
        assert f"<{tool}>" in served and f"<{tool}>" in gen.INSTRUCTION
