"""EDIT0, the operational memory's half: a `put` on an existing key replaces its value — the next `get` returns the new
value and only it (Spotlight's overwrite property, read [read] percepta.ai/blog/spotlight-memory, on our memory)."""
from types import SimpleNamespace

from examples.common.opmemory import OpMemory


def test_a_put_on_an_existing_key_replaces_its_value():
    m, claim = OpMemory(), SimpleNamespace(org_id="o", user_id="u")
    m.answer(claim, "s", "put", "issue=RD-1")
    m.answer(claim, "s", "put", "issue=RD-2")
    assert m.answer(claim, "s", "get", "issue") == "RD-2"
    m.answer(claim, "s", "put", "global.sprint=12")
    m.answer(claim, "s", "put", "global.sprint=13")
    assert m.get(claim, "other-session", "global.sprint") == "13"
    assert m.keys(claim, "s") == ["issue", "global.sprint"]          # one key each, never a stale duplicate
