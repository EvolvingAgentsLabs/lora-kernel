"""The tunnel is the piece that lets the user's machine reach a rented card.

What is worth testing here is not that cloudflared works — it is that the URL is
findable by a machine, and that a failure to get one is a failure rather than a
run that quietly serves nothing.
"""

import re
from pathlib import Path

import pytest

from training.harness import serve_tunnel as st


def test_the_url_is_printed_on_one_line_with_a_marker(capsys):
    """A chain greps for this rather than a human reading scrollback, and the URL
    is different on every start so it cannot be hardcoded anywhere."""
    print(f"[tunnel] URL https://weathered-bird-1234.trycloudflare.com")
    out = capsys.readouterr().out
    m = re.search(r"\[tunnel\] URL (https://\S+)", out)
    assert m and m.group(1).endswith(".trycloudflare.com")


def test_the_pattern_finds_a_url_in_cloudflared_noise(tmp_path, monkeypatch):
    noise = (
        "2026-09-15T12:00:00Z INF Thank you for trying Cloudflare Tunnel.\n"
        "2026-09-15T12:00:01Z INF |  https://weathered-bird-1234.trycloudflare.com  |\n"
        "2026-09-15T12:00:02Z INF Registered tunnel connection\n")
    monkeypatch.chdir(tmp_path)
    Path("cloudflared.log").write_text(noise)
    pat = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    assert pat.search(noise).group(0) == "https://weathered-bird-1234.trycloudflare.com"


def test_a_missing_adapter_stops_the_run_before_a_card_is_held(tmp_path, monkeypatch):
    """Holding a rented GPU for hours on a pool that has no weights is the
    expensive version of this mistake."""
    import sys
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv",
                        ["t", "--adapter", "email-full=adapters/nothing-here"])
    assert st.main() == 1


def test_the_result_file_records_what_crosses(tmp_path, monkeypatch):
    """`tunnel.json` is what the local side reads; it must name the pool, so a
    proxy pointed at it cannot be pointed at the wrong server."""
    import json
    monkeypatch.chdir(tmp_path)
    (tmp_path / "adapters" / "e").mkdir(parents=True)
    (tmp_path / "adapters" / "e" / "adapter_model.safetensors").write_bytes(b"0" * 8)
    monkeypatch.setattr(st, "_wait_http", lambda *a, **k: False)

    class Fake:
        returncode = 1
        def poll(self): return None
        def terminate(self): pass
        def wait(self, timeout=None): pass
        def kill(self): pass
    monkeypatch.setattr(st.subprocess, "Popen", lambda *a, **k: Fake())
    import sys
    monkeypatch.setattr(sys, "argv", ["t", "--adapter", "e=adapters/e"])
    st.main()
    d = json.loads((tmp_path / "tunnel.json").read_text())
    assert d["pool"] == ["e"] and d["status"] == "vllm never came up"
