"""The library endpoint (examples/library/serve.py) runs one question through REAL4's runtime and the live driver grades
the walk the way the measurement did: a scripted member that searches, opens the supporting page and cites its statement
is `right`; one that cites a statement it never opened is not."""
import json
import re
from pathlib import Path


def _rows():
    return [json.loads(l) for l in Path("results/REAL4-refusal-20260930/questions.jsonl").read_text().splitlines()]


def _scripted(row, cite_anchor):
    def generate(system, user):
        def gen(prefix):
            if "<search" not in prefix:
                return "<search shelf=wiki>x</search>"
            if "<open>" not in prefix:
                title = row["support"][0].rsplit("/", 1)[1].replace("-", ".")
                m = re.search(r"\[([a-z0-9]{3})\] page · " + re.escape(title) + r" ", prefix)
                return f"<open>{m.group(1)}</open>" if m else "Not in my library."
            sid = re.search(r"<open>([a-z0-9]{3})</open>", prefix).group(1)
            return f"{row['answer']} [{sid}§{cite_anchor}]"
        return gen
    return generate


def test_the_endpoint_walk_is_graded_like_the_measurement():
    from examples.library import serve
    from examples.library.live_library import grade_walk
    from memory.notes import Library
    from memory.runtime import FullText
    lib = Library.load("knowledge/logistics-regs")
    row = next(r for r in _rows() if r["support"] and r["hops"] == 1 and r["support"][1] == "h-2-i")
    ev = serve.walk(lib, FullText(lib), row["question"], _scripted(row, row["support"][1]))
    assert grade_walk(lib, row, ev)["state"] == "right", ev["final"]
    assert "§" in ev["reply"] and "[1910.178 §h-2-i]" in ev["reply"]
    wrong = serve.walk(lib, FullText(lib), row["question"], _scripted(row, "zz"))
    assert grade_walk(lib, row, wrong)["state"] != "right"


def test_a_dropped_stop_string_is_put_back_on_a_tag_with_attributes():
    """llama.cpp drops the stop string; `close_open_tag` puts the closing tag back — also on `<search shelf=wiki>`, which the
    first live smoke test returned unclosed (no search ran)."""
    from training.harness.accept_rank import close_open_tag
    from memory.runtime import ChainSuite
    assert close_open_tag("<search shelf=wiki>How long must a carrier keep its training records?", ChainSuite.close) \
        == "<search shelf=wiki>How long must a carrier keep its training records?</search>"
    assert close_open_tag("<open>k3f§pack", ChainSuite.close) == "<open>k3f§pack</open>"
    assert close_open_tag("The answer is 12 months [k3f§c]", ChainSuite.close) == "The answer is 12 months [k3f§c]"


def test_a_walk_with_no_answer_is_not_shown_as_a_refusal():
    """A walk that ends with no line (LIVE-library: the context overflowed on a long page) is a failure, not a refusal —
    the reply says so, and the grade (on the final line) does not count it as `Not in my library.`"""
    from examples.library import serve
    from examples.library.live_library import grade_walk
    from memory.notes import Library
    from memory.runtime import FullText
    lib = Library.load("knowledge/logistics-regs")
    row = next(r for r in _rows() if r["check"]["kind"] == "none")
    ev = serve.walk(lib, FullText(lib), row["question"], lambda system, user: (lambda prefix: ""))
    assert ev["final"] == "" and ev["reply"] == serve.NO_ANSWER
    assert grade_walk(lib, row, ev)["state"] != "right"


def test_a_long_page_opens_with_the_questions_statements_within_budget():
    """`page_budget`: 1910.178 (~6,900 tokens whole) opens under the budget with the supporting statement among the shown
    ones, the rest listed by anchor; a short page opens whole, as REAL4 measured it."""
    from memory.notes import Library, count_tokens
    from memory.runtime import Conversation
    lib = Library.load("knowledge/logistics-regs")
    row = next(r for r in _rows() if r["support"] and r["support"][0].endswith("1910-178"))
    page = lib[row["support"][0]]
    conv = Conversation(lib, page_text=True, page_budget=2500, first_query=row["question"])
    text = conv._render(page, None)
    assert count_tokens(text) <= 2600 and f"§{row['support'][1]} " in text and "more sections, not shown" in text
    whole = Conversation(lib, page_text=True, first_query=row["question"])._render(page, None)
    assert count_tokens(whole) > 6000
    short = lib["logistics-regs/wiki/1-906"]
    assert conv._render(short, None) == Conversation(lib, page_text=True)._render(short, None)
