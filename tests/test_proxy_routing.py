"""What leaves the machine, and what must not.

P41 measured that sending one failing subdomain to a frontier takes delivered
accuracy from 0.546 to 0.775. This is the route that does it — and the thing worth
testing is not that it forwards, but that it forwards **only** what it should.
"""

import io
import json

import pytest

from training.harness import openai_proxy as px


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(px, "FALLBACK", None)
    monkeypatch.setattr(px, "FALLBACK_KEY", None)
    monkeypatch.setattr(px, "LOCAL", set())


def test_nothing_leaves_when_no_fallback_is_configured(monkeypatch):
    monkeypatch.setattr(px, "LOCAL", {"email-full"})
    assert px.routes_out("gpt-5") is False
    assert px.routes_out("email-full") is False


def test_a_local_model_never_leaves_even_with_a_fallback(monkeypatch):
    monkeypatch.setattr(px, "FALLBACK", "https://api.openai.com/v1")
    monkeypatch.setattr(px, "LOCAL", {"email-full", "fluids-full"})
    assert px.routes_out("email-full") is False
    assert px.routes_out("fluids-full") is False


def test_anything_the_pool_does_not_serve_goes_out(monkeypatch):
    monkeypatch.setattr(px, "FALLBACK", "https://api.openai.com/v1")
    monkeypatch.setattr(px, "LOCAL", {"email-full"})
    assert px.routes_out("gpt-5") is True


def test_a_request_with_no_model_does_not_leave(monkeypatch):
    """Absence of a name is not permission to send it away."""
    monkeypatch.setattr(px, "FALLBACK", "https://api.openai.com/v1")
    monkeypatch.setattr(px, "LOCAL", {"email-full"})
    assert px.routes_out(None) is False
    assert px.routes_out("") is False


def test_the_announcement_names_shapes_and_never_content(capsys, monkeypatch):
    """A deployment routing real mail should see what left without its transcript
    being printed into a log. openclaw_traffic.py holds the same line."""
    secret = "the merger closes on Tuesday and the number is 4.2M"
    px._announce("gpt-5", {"messages": [{"role": "user", "content": secret}],
                           "tools": [{"type": "function"}]})
    out = capsys.readouterr().out
    assert "gpt-5" in out and "1 messages" in out and "1 tools" in out
    assert secret not in out
    for word in ("merger", "Tuesday", "4.2M"):
        assert word not in out


def test_a_fallback_without_a_credential_refuses_to_start(monkeypatch):
    """Failing on the first escalation is the worst moment to find out."""
    import sys
    monkeypatch.delenv("NOPE_KEY", raising=False)
    monkeypatch.setattr(sys, "argv",
                        ["p", "--fallback", "https://api.openai.com/v1",
                         "--fallback-key-env", "NOPE_KEY"])
    assert px.main() == 2


def test_the_key_is_read_from_the_environment_not_an_argument():
    """A key on the command line lands in `ps` and in shell history."""
    import inspect
    src = inspect.getsource(px.main)
    assert "--fallback-key-env" in src
    assert '"--fallback-key"' not in src, "no flag may take the key itself"
