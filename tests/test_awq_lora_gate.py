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


def test_the_chain_s_default_pool_adapters_do_not_become_the_toy_adapter():
    """Attempt 1: `MARGS=""` fell back to `--adapter kernel=… --adapter domain=…` and the
    runner served `tiny32=domain=adapters/domain-mt`."""
    import subprocess, sys
    from training.harness.awq_lora_gate import lora_spec
    assert lora_spec("adapters/tiny32") == "tiny32=adapters/tiny32"
    import pytest
    with pytest.raises(SystemExit):
        lora_spec("domain=adapters/domain-mt")
    out = subprocess.run([sys.executable, "-m", "training.harness.awq_lora_gate", "--help"],
                         capture_output=True, text=True)
    assert "--tiny" in out.stdout and "--adapter" in out.stdout


def test_logprob_gate_needs_a_difference_the_base_does_not_make_against_itself():
    """Attempt 2 [ran]: engine loaded the adapter, Punica in use, 1/3 text probes changed
    one word — a toy adapter over a 32B rarely flips an argmax. The logprob gate reads
    the mechanism; the determinism control keeps nondeterminism from reading as a LoRA."""
    from training.harness.awq_lora_gate import logprob_verdict, mean_abs_delta
    nan = float("nan")
    rows = [{"member_vs_base": 0.05, "base_vs_base": 0.0},
            {"member_vs_base": 0.02, "base_vs_base": 0.0001},
            {"member_vs_base": 0.0003, "base_vs_base": 0.0}]
    v = logprob_verdict(rows)
    assert v["applied"] and v["differ"] == 2
    noisy = [{"member_vs_base": 0.05, "base_vs_base": 0.04}] * 3        # the base moves alone
    assert logprob_verdict(noisy)["applied"] is False
    assert logprob_verdict([{"member_vs_base": nan, "base_vs_base": 0.0}] * 3)["applied"] is False
    assert mean_abs_delta([0.0, -1.0, -2.0], [0.0, -1.5, -2.0], 1) == 0.25
    assert mean_abs_delta([nan, -1.0], [0.0, -1.0], 0) == 0.0
