"""Two names over one base is not a pool unless both are really there.

P26 showed two adapters producing different text; P36 showed one clearing a gate.
Neither is a pool. These are the ways this runner could report one when there is
not one.
"""

import json
import sys

import pytest

from training.harness import pool_run


def _run(monkeypatch, tmp_path, texts, names=("email-full", "fluids-full")):
    out = tmp_path / "p.json"
    monkeypatch.setattr(pool_run, "OUT", out)
    monkeypatch.setattr(pool_run, "_wait", lambda *a, **k: True)
    monkeypatch.setattr(pool_run, "_probe", lambda m, **k: texts[m])

    class Fake:
        returncode = 0
        def poll(self): return None
        def terminate(self): pass
        def wait(self, timeout=None): pass
        def kill(self): pass

    monkeypatch.setattr(pool_run.subprocess, "Popen", lambda *a, **k: Fake())
    # THE SPY LIVES HERE, not in the caller. A test that installed its own after
    # calling this helper had it overwritten by this line and asserted on an empty
    # list — the test failing, not the runner.
    commands: list[list[str]] = []

    def spy(cmd, *a, **k):
        commands.append(list(cmd))
        return 0, ""

    # THE SEAM IS `run_streaming`, NOT `subprocess.run`. The arms were switched to
    # a streaming child so a twenty-minute scoring pass stops reading as silence;
    # a spy still pointed at `subprocess.run` records nothing and asserts on an
    # empty list — the test failing, not the runner.
    monkeypatch.setattr(pool_run, "run_streaming", spy)
    monkeypatch.chdir(tmp_path)
    argv = ["p", "--base", "B", "--out", str(out)]
    for n in names:
        d = tmp_path / "adapters" / n
        d.mkdir(parents=True, exist_ok=True)
        (d / "adapter_model.safetensors").write_bytes(b"0" * 16)
        argv += ["--adapter", f"{n}=adapters/{n}"]
    monkeypatch.setattr(sys, "argv", argv)
    code = pool_run.main()
    return code, json.loads(out.read_text()), commands


def test_a_member_identical_to_the_base_stops_the_run(monkeypatch, tmp_path):
    code, r, _ = _run(monkeypatch, tmp_path,
                   {"B": "same", "email-full": "same", "fluids-full": "other"})
    assert code == 1 and r["stopped_at_gate"] is True
    assert not r["arms"]


def test_two_names_over_the_same_adapter_is_not_a_pool(monkeypatch, tmp_path):
    """The failure that would look most like success: both differ from the base,
    both are the same expert. Two respectable numbers, one model."""
    code, r, _ = _run(monkeypatch, tmp_path,
                   {"B": "base", "email-full": "twin", "fluids-full": "twin"})
    assert r["members_are_distinct"] is False
    assert code == 1 and r["stopped_at_gate"] is True


def test_distinct_applied_members_are_scored(monkeypatch, tmp_path):
    code, r, _ = _run(monkeypatch, tmp_path,
                   {"B": "base", "email-full": "one", "fluids-full": "two"})
    assert r["members_are_distinct"] is True
    assert all(g["differs_from_base"] for g in r["identity_gate"].values())
    assert r.get("stopped_at_gate") is not True


def test_each_member_is_scored_by_its_own_client(monkeypatch, tmp_path):
    """Sharing a client would measure a suite, not a pool."""
    _, _, seen = _run(monkeypatch, tmp_path,
                      {"B": "base", "email-full": "one", "fluids-full": "two"})
    mods = [c[c.index("-m") + 1] for c in seen if "-m" in c]
    assert "training.harness.agent_sim" in mods
    assert "training.harness.fluids_sim" in mods


def test_a_single_member_is_not_refused_for_being_alone(monkeypatch, tmp_path):
    """The distinctness check must not fire on a one-member run."""
    code, r, _ = _run(monkeypatch, tmp_path, {"B": "base", "email-full": "one"},
                   names=("email-full",))
    assert r["members_are_distinct"] is True and r.get("stopped_at_gate") is not True
