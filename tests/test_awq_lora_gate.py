"""P60 §3b's verdict: applied only when the identity gate says so with the empty-arm
rule — the same G1 as Phase 0, over a different base."""

from training.harness.verify_substrate import identity


def test_applied_over_awq_needs_two_of_three_non_empty_differences(monkeypatch):
    import training.harness.verify_substrate as vs
    monkeypatch.setattr(vs, "_say", lambda model, prompt, tok, max_tokens=48: f"{model}|{prompt}")
    assert identity("awq", "tiny32", None, probes=("a", "b", "c"))["applied"] is True
    monkeypatch.setattr(vs, "_say", lambda model, prompt, tok, max_tokens=48: prompt)   # served the base
    r = identity("awq", "tiny32", None, probes=("a", "b", "c"))
    assert r["applied"] is False and r["differs"] == 0


def test_runner_accepts_the_chain_s_base_flag():
    """chain_serve.sh passes `--base $BASE` to every module; a runner that refuses it
    never trains anything (first launch of P60 §3b)."""
    import subprocess, sys
    out = subprocess.run([sys.executable, "-m", "training.harness.awq_lora_gate", "--help"],
                         capture_output=True, text=True)
    assert out.returncode == 0 and "--base" in out.stdout
