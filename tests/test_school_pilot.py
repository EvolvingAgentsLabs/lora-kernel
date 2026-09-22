"""training/harness/school_pilot.py's grading — zero GPU, no model. The truth for each case comes
from the case's own `tool`/`entity_id` fields, never from executing a tool, so a live call cannot
leak into what "correct" means (docstring's own claim, held here)."""

from pathlib import Path

from training.harness.school_pilot import evaluate, load_jsonl, parse_call, truth_of

ROOT = Path(__file__).resolve().parent.parent / "examples" / "school" / "data_corpus"


def test_every_educador_row_has_a_recoverable_truth():
    for split in ("train", "eval"):
        rows = load_jsonl(ROOT / f"educador_{split}.jsonl")
        assert rows, split
        for r in rows:
            tool, arg = truth_of(r)
            assert tool == "agenda_read" and isinstance(arg, int)


def test_parse_call_reads_the_corpus_own_tag_shape():
    rows = load_jsonl(ROOT / "educador_eval.jsonl")
    for r in rows:
        got = parse_call(r["messages"][2]["content"])
        assert got == truth_of(r), r["case_id"]


def test_parse_call_is_none_on_no_tag_or_the_wrong_id():
    assert parse_call("I'm not sure what you mean.") is None
    assert parse_call("<agenda_read>7</agenda_read>= ...") == ("agenda_read", 7)


def test_evaluate_grades_by_the_case_truth_not_by_a_live_tool_call():
    rows = load_jsonl(ROOT / "educador_eval.jsonl")[:3]

    def perfect(system, user):
        row = next(r for r in rows if r["messages"][1]["content"] == user)
        return row["messages"][2]["content"]

    result = evaluate(perfect, rows, "test")
    assert result["n"] == 3 and result["correct"] == 3 and result["accuracy"] == 1.0

    def always_wrong(system, user):
        return "<agenda_read>999999</agenda_read>= nothing"

    result = evaluate(always_wrong, rows, "test")
    assert result["correct"] == 0

    def raises(system, user):
        raise RuntimeError("boom")

    result = evaluate(raises, rows, "test")
    assert result["correct"] == 0
    assert all("generation failed" in r["out"] for r in result["records"])
