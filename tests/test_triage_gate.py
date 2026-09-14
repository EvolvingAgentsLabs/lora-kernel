"""A score over an adapter that was never applied is a score about the base.

P33 measured vLLM accepting a LoRA, logging that it loaded it, and serving the base
anyway. `triage_run` serves a pool and scores it; without a gate a null result is
ambiguous between "the adapter did not help" and "there was no adapter", and that
ambiguity has already cost this project four runs.
"""

import json
import sys

from training.harness import triage_run


def _run(monkeypatch, tmp_path, texts, pool=("kernel",)):
    """main() with the servers faked, returning (exit code, results on disk)."""
    out = tmp_path / "t.json"
    monkeypatch.setattr(triage_run, "OUT", out)
    monkeypatch.setattr(triage_run, "_wait", lambda *a, **k: True)
    monkeypatch.setattr(triage_run, "_probe", lambda model, **k: texts[model])

    class Fake:
        returncode = 0
        def poll(self): return None
        def terminate(self): pass
        def wait(self, timeout=None): pass
        def kill(self): pass

    monkeypatch.setattr(triage_run.subprocess, "Popen", lambda *a, **k: Fake())
    monkeypatch.setattr(triage_run.subprocess, "run",
                        lambda *a, **k: type("R", (), {"stdout": "", "stderr": ""})())
    # REAL FILES RATHER THAN A PATCHED `Path.exists`. Patching it silently did
    # not take, main() returned on its missing-weights check before the gate ran,
    # and three tests failed for a reason that had nothing to do with the gate.
    monkeypatch.chdir(tmp_path)
    for name in pool:
        d = tmp_path / "adapters" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "adapter_model.safetensors").write_bytes(b"0" * 16)
    argv = ["t", "--base", "B", "--arms", ",".join(pool), "--out", str(out)]
    for name in pool:
        argv += ["--adapter", f"{name}=adapters/{name}"]
    monkeypatch.setattr(sys, "argv", argv)
    code = triage_run.main()
    return code, json.loads(out.read_text())


def test_an_adapter_identical_to_the_base_stops_the_run(monkeypatch, tmp_path):
    code, res = _run(monkeypatch, tmp_path,
                     {"B": "I am a model.", "kernel": "I am a model."})
    assert code == 1
    assert res["stopped_at_gate"] is True
    assert res["identity_gate"]["kernel"]["differs_from_base"] is False
    assert "arms" not in res or not res["arms"]


def test_an_applied_adapter_is_recorded_and_the_run_continues(monkeypatch, tmp_path):
    _, res = _run(monkeypatch, tmp_path,
                  {"B": "I am a model.", "kernel": "<thread_history>id=1</thread_history>"})
    assert res["identity_gate"]["kernel"]["differs_from_base"] is True
    assert res.get("stopped_at_gate") is not True


def test_one_applied_adapter_does_not_excuse_another(monkeypatch, tmp_path):
    """A pool is only served if every member of it is."""
    code, res = _run(monkeypatch, tmp_path,
                     {"B": "same", "kernel": "different", "domain": "same"},
                     pool=("kernel", "domain"))
    assert code == 1 and res["stopped_at_gate"] is True


def test_the_base_only_arm_needs_no_gate(monkeypatch, tmp_path):
    """P31 serves no adapter; gating it would compare the base with itself."""
    out = tmp_path / "t.json"
    monkeypatch.setattr(triage_run, "OUT", out)
    monkeypatch.setattr(triage_run, "_wait", lambda *a, **k: True)
    called = []
    monkeypatch.setattr(triage_run, "_probe",
                        lambda model, **k: called.append(model) or "x")

    class Fake:
        returncode = 0
        def poll(self): return None
        def terminate(self): pass
        def wait(self, timeout=None): pass
        def kill(self): pass

    monkeypatch.setattr(triage_run.subprocess, "Popen", lambda *a, **k: Fake())
    monkeypatch.setattr(triage_run.subprocess, "run",
                        lambda *a, **k: type("R", (), {"stdout": "", "stderr": ""})())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv",
                        ["t", "--base", "B", "--arms", "base", "--out", str(out)])
    triage_run.main()
    assert called == [], "the base-only arm probed something it should not have"
