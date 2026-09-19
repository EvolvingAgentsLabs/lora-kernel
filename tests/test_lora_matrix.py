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


# --- D2: the renaming arm (results/D2-rekey-20260918/BRIEF.md) -----------------------

def _rekey_run(monkeypatch, tmp_path, subject_g2, renamed_g2):
    """main() with `--rekey`, every GPU step faked; returns the file and what was asked."""
    asked = []
    monkeypatch.setattr(lora_matrix, "g1",
                        lambda base, tag, steps: {"passed": True, "adapter": f"adapters/tiny-{tag}"})

    def fake_g2(base, adapter, tag, debug=False):
        asked.append((tag, adapter, debug))
        ok = {"control": True, "subject": subject_g2, "rekeyed": renamed_g2}[tag]
        return {"passed": ok, "verdict": "applied" if ok else "not applied"}

    import training.harness.rekey as rekey
    monkeypatch.setattr(lora_matrix, "g2", fake_g2)
    monkeypatch.setattr(rekey, "rekey_adapter", lambda src, dst: {"src": src, "dst": dst, "moved": 4})
    out = tmp_path / "m.json"
    monkeypatch.setattr(sys, "argv", ["m", "--rekey", "--out", str(out)])
    lora_matrix.main()
    return json.loads(out.read_text()), asked


def test_the_renaming_arm_is_bought_only_when_the_subject_fails(monkeypatch, tmp_path):
    """Arms in sequence: a subject that already serves its adapter has no C18 to explain."""
    res, asked = _rekey_run(monkeypatch, tmp_path, subject_g2=True, renamed_g2=True)
    assert [a[0] for a in asked] == ["control", "subject"]
    assert "G2r" not in res["arms"]["subject"]


def test_renamed_and_applied_reads_as_a_naming_mismatch(monkeypatch, tmp_path):
    res, asked = _rekey_run(monkeypatch, tmp_path, subject_g2=False, renamed_g2=True)
    assert asked[-1] == ("rekeyed", "adapters/tiny-rekeyed", True)
    assert res["reading"].startswith("C18 is a naming mismatch")


def test_renamed_and_still_the_base_does_not_close_d2(monkeypatch, tmp_path):
    res, _ = _rekey_run(monkeypatch, tmp_path, subject_g2=False, renamed_g2=False)
    assert res["reading"].startswith("renaming was not enough")
    assert "Qwen2.5 stays" in res["decision"]


def test_the_control_is_never_served_at_debug(monkeypatch, tmp_path):
    """The control is the arm whose answer is known; it is asked exactly as P33 asked it."""
    _, asked = _rekey_run(monkeypatch, tmp_path, subject_g2=False, renamed_g2=True)
    assert asked[0] == ("control", "adapters/tiny-control", False)


def test_nothing_renamed_is_void_not_falsified(monkeypatch, tmp_path):
    """If PEFT did not write the names the brief assumed, G2r would repeat G2."""
    import training.harness.rekey as rekey
    asked = []
    monkeypatch.setattr(lora_matrix, "g1",
                        lambda base, tag, steps: {"passed": True, "adapter": "a"})
    def fake_g2(base, adapter, tag, debug=False):
        asked.append(tag)
        return {"passed": tag == "control", "verdict": "applied" if tag == "control" else "not applied"}
    monkeypatch.setattr(lora_matrix, "g2", fake_g2)
    monkeypatch.setattr(rekey, "rekey_adapter", lambda src, dst: {"moved": 0})
    out = tmp_path / "m.json"
    monkeypatch.setattr(sys, "argv", ["m", "--rekey", "--out", str(out)])
    lora_matrix.main()
    assert asked == ["control", "subject"]
    assert json.loads(out.read_text())["reading"].startswith("VOID for D2")


def test_warmup_dummies_are_not_the_adapter():
    """D2 [ran] 2026-09-19: vLLM activates dummy LoRAs while profiling; summed with the
    real activation they read an adapter that landed nowhere as 531 modules with weights."""
    ok, miss = lora_matrix.FOUND, lora_matrix.MISSING
    dummy = [f"DEBUG {ok} m.layers.{i}.q_proj." for i in range(3)] + [f"DEBUG {miss} m.lm_head, skipping."]
    real = [f"DEBUG {miss} m.layers.{i}.q_proj, skipping." for i in range(3)] + [f"DEBUG {miss} m.lm_head, skipping."]
    acts = lora_matrix.split_activations("\n".join(dummy * 3 + real))
    assert len(acts) == 4
    assert acts[-1] == {"with": 0, "without": 4}
    assert sum(a["with"] for a in acts) == 9          # what the first counter reported


def test_the_recorded_rekeyed_log_splits_as_the_record_says():
    from pathlib import Path
    log = Path("results/D2-rekey-20260918/vllm.log")
    acts = lora_matrix.split_activations(log.read_text(errors="replace"))
    assert [(a["with"], a["without"]) for a in acts] == [(177, 1)] * 3 + [(152, 26)]
