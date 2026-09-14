"""The control arm has to be able to void the run, or it is decoration.

Every one of these asserts a reading the four Qwen3.5 runs could not make. They are
about the decision table, not about any model: the table is the part that was
missing when `IDENTICAL TO BASE` came back four times and meant four things.
"""

import json
import subprocess
import sys

import pytest

from training.harness import lora_matrix


def _decide(monkeypatch, tmp_path, control, subject):
    """Run main() with both gates faked, and read the verdict it wrote."""
    plan = {"control": control, "subject": subject}

    def fake_g1(base, tag, steps):
        return {"passed": plan[tag][0], "adapter": f"adapters/tiny-{tag}"}

    def fake_g2(base, adapter, tag):
        ok = plan[tag][1]
        return {"passed": ok, "verdict": "applied" if ok else "not applied"}

    monkeypatch.setattr(lora_matrix, "g1", fake_g1)
    monkeypatch.setattr(lora_matrix, "g2", fake_g2)
    out = tmp_path / "m.json"
    monkeypatch.setattr(sys, "argv", ["m", "--out", str(out)])
    lora_matrix.main()
    return json.loads(out.read_text())


def test_a_broken_procedure_voids_the_run(monkeypatch, tmp_path):
    """The control failing means nothing was learned about the subject.

    This is the row that did not exist today. Without it, a harness bug and an
    unsupported model produce the same output, and the transcript records the
    second.
    """
    r = _decide(monkeypatch, tmp_path, control=(True, False), subject=(True, False))
    assert r["control_valid"] is False
    assert "VOID" in r["reading"]
    assert "Qwen3.5" in r["reading"] or "no model" in r["decision"]


def test_a_working_control_makes_the_subject_readable(monkeypatch, tmp_path):
    r = _decide(monkeypatch, tmp_path, control=(True, True), subject=(True, False))
    assert r["control_valid"] is True
    assert "serving-stack limit" in r["reading"]
    assert "Qwen2.5" in r["decision"]


def test_training_failure_and_serving_failure_read_differently(monkeypatch, tmp_path):
    """G1 failing is about the model; G2 failing is about vLLM. Not the same fact."""
    train = _decide(monkeypatch, tmp_path, (True, True), (False, False))
    serve = _decide(monkeypatch, tmp_path, (True, True), (True, False))
    assert train["reading"] != serve["reading"]
    assert "cannot be trained" in train["reading"]


def test_a_no_op_adapter_is_never_handed_to_the_serving_gate(monkeypatch, tmp_path):
    r = _decide(monkeypatch, tmp_path, (True, True), (False, False))
    assert r["arms"]["subject"]["G2"]["verdict"] == "not asked: G1 failed"


def test_both_passing_does_not_by_itself_authorise_a_switch(monkeypatch, tmp_path):
    """A usable family is not a reason to pay for retraining. The decision says so."""
    r = _decide(monkeypatch, tmp_path, (True, True), (True, True))
    assert "separate call" in r["decision"]


def test_the_exit_code_is_not_the_gate_verdict(monkeypatch, tmp_path):
    """`serve_openai` exits 0 on a clean run whose gate said `not applied`.

    Reading the return code instead of the file would report every subject as a
    pass — the exact shape of error that made two Qwen3.5 diagnoses wrong.
    """
    dest = tmp_path / "gate_subject.json"
    dest.write_text(json.dumps({"gate_verdict": "not applied: served text is "
                                                "identical to the base"}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lora_matrix, "run", lambda *a: 0)          # clean exit
    assert lora_matrix.g2("b", "a", "subject")["passed"] is False


def test_results_are_on_disk_before_the_second_arm_starts(monkeypatch, tmp_path):
    """A GPU run that reports only at the end makes an abort cost everything."""
    seen = []

    monkeypatch.setattr(lora_matrix, "g1",
                        lambda base, tag, steps: {"passed": True, "adapter": "a"})

    def fake_g2(base, adapter, tag):
        seen.append(json.loads((tmp_path / "m.json").read_text())
                    if (tmp_path / "m.json").exists() else None)
        return {"passed": True, "verdict": "applied"}

    monkeypatch.setattr(lora_matrix, "g2", fake_g2)
    monkeypatch.setattr(sys, "argv", ["m", "--out", str(tmp_path / "m.json")])
    lora_matrix.main()
    # by the time the SUBJECT is gated, the CONTROL's result is already durable
    assert seen[1] is not None and "control" in seen[1]["arms"]


def test_the_brief_was_written_before_the_run():
    from pathlib import Path
    brief = Path("results/P33-lora-matrix-20260914/BRIEF.md")
    assert brief.exists()
    text = brief.read_text()
    assert "positive control" in text and "void" in text.lower()
