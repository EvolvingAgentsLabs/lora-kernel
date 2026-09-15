"""A stranger's weights, and the ways this could report something it did not test."""

import json
import sys
from pathlib import Path

import pytest

from training.arc import suite
from training.harness import third_party as tp


# --- the suite -------------------------------------------------------------

@pytest.mark.parametrize("written", ["B", "(B)", "Answer: B", "**B**", "B.",
                                     "The answer is B", " b "])
def test_a_letter_is_a_letter_however_it_is_written(written):
    """Scoring the format instead of the answer is measuring phrasing."""
    assert suite.parse(written, ["A", "B", "C", "D"]) == "B"


def test_an_explicit_answer_line_wins_over_thinking_out_loud():
    assert suite.parse("I lean C, but the answer is B", ["A", "B", "C", "D"]) == "B"


def test_no_letter_is_not_a_wrong_letter():
    for t in ("", "hello world", "I don't know"):
        assert suite.parse(t, ["A", "B", "C", "D"]) is None
    assert suite.correct(None, "A") is False


def test_the_bar_is_the_commonest_key():
    items = [{"answer": "A"}, {"answer": "A"}, {"answer": "B"}]
    assert suite.majority_bar(items) == pytest.approx(2 / 3)


def test_the_prompt_lists_every_choice():
    item = {"question": "q?", "choices": [("A", "one"), ("B", "two")], "answer": "A"}
    p = suite.prompt(item)
    assert "A. one" in p and "B. two" in p and "letter" in p


# --- the runner ------------------------------------------------------------

def test_a_pickle_adapter_is_refused_rather_than_loaded(tmp_path):
    """A `.bin` adapter executes whatever is inside it. These are strangers' files."""
    src = tmp_path / "src"; src.mkdir()
    (src / "adapter_config.json").write_text("{}")
    (src / "adapter_model.bin").write_bytes(b"\x80\x04")      # a pickle header
    info = tp.fetch("someone/something", tmp_path / "dest",
                    download=lambda repo: str(src))
    assert "refused" in info and "pickle" in info["refused"]
    assert not (tmp_path / "dest" / "adapter_model.safetensors").exists()


def test_a_safetensors_adapter_is_copied_with_its_shape_recorded(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    (src / "adapter_config.json").write_text(json.dumps(
        {"r": 16, "base_model_name_or_path": "Qwen/Qwen2.5-3B-Instruct",
         "target_modules": ["q_proj", "v_proj"]}))
    (src / "adapter_model.safetensors").write_bytes(b"0" * 64)
    info = tp.fetch("someone/something", tmp_path / "dest",
                    download=lambda repo: str(src))
    assert info["r"] == 16 and info["base"] == "Qwen/Qwen2.5-3B-Instruct"
    assert info["targets"] == ["q_proj", "v_proj"] and info["bytes"] == 64


def test_scoring_counts_an_unparseable_reply_separately(monkeypatch):
    """A model that says nothing has not answered wrongly, and the two must not
    be added together — that is how a broken channel reads as a bad model."""
    items = [{"id": "1", "question": "q", "choices": [("A", "x"), ("B", "y")],
              "answer": "A"}] * 3
    replies = iter(["A", "", "B"])
    monkeypatch.setattr(tp, "ask", lambda *a, **k: next(replies))
    r = tp.score_arc("m", items)
    assert r["correct"] == 1 and r["unparseable"] == 1 and r["n"] == 3
