"""The tools an agent actually owns, and the ways this server could lie about them.

P43 ran the end-to-end and found its honest limit: the OpenClaw turn made **no tool
calls**, because OpenClaw sends its own tools and not the inbox's. The expert
answered from the listing alone — what the base does, 0.345 **[ran]** P31. This
server closes that gap, so these check the gap is really closed.
"""

import json

import pytest

from training.email.inbox import generate
from training.mcp.inbox_server import handle


@pytest.fixture
def inbox():
    return generate(30, 717171)


def _call(method, inbox, mid=1, **params):
    return handle({"jsonrpc": "2.0", "id": mid, "method": method,
                   "params": params or {}}, inbox)


def test_it_offers_exactly_the_tools_the_suite_scores(inbox):
    """If the agent's tools and the suite's tools drift, the demo and the number
    stop being about the same system."""
    from training.email.tools import TOOLS
    r = _call("tools/list", inbox)
    assert {t["name"] for t in r["result"]["tools"]} == set(TOOLS)


def test_every_tool_carries_the_schema_a_client_needs(inbox):
    for t in _call("tools/list", inbox)["result"]["tools"]:
        s = t["inputSchema"]
        assert s["type"] == "object" and s.get("required") and t["description"]


def test_a_real_lookup_returns_the_fact_the_listing_withholds(inbox):
    tid = inbox["messages"][0]["thread_id"]
    r = _call("tools/call", inbox, name="thread_history", arguments={"thread_id": tid})
    body = json.loads(r["result"]["content"][0]["text"])
    assert "i_wrote_in_thread" in body and r["result"]["isError"] is False


def test_a_tool_error_is_a_result_not_a_transport_failure(inbox):
    """The agent should see what it did wrong and ask again — which is what
    `agent_sim` counts as `refused` and carries on from."""
    r = _call("tools/call", inbox, name="thread_history", arguments={"thread_id": "nope"})
    assert "error" not in r
    assert r["result"]["isError"] is True
    assert "ids look like" in r["result"]["content"][0]["text"]


def test_a_notification_gets_no_reply(inbox):
    """Answering a notification corrupts the stream for a strict client."""
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}, inbox) is None


def test_an_unknown_method_with_an_id_gets_an_error_not_silence(inbox):
    r = handle({"jsonrpc": "2.0", "id": 9, "method": "nope/nope"}, inbox)
    assert r["error"]["code"] == -32601


def test_initialize_announces_tools(inbox):
    r = _call("initialize", inbox)
    assert "tools" in r["result"]["capabilities"]
    assert r["result"]["serverInfo"]["name"] == "lora-kernel-inbox"


def test_it_serves_the_synthetic_inbox_and_says_so_in_its_own_docstring():
    """Nobody should be able to point this at real mail by accident."""
    import inspect
    from training.mcp import inbox_server
    src = inspect.getsource(inbox_server)
    assert "No real correspondence" in src
    assert "inbox.generate" in src or "from training.email.inbox import generate" in src


def test_the_seed_makes_the_demo_match_what_was_scored():
    """The suite scores seed 717171; a demo on another draw is a different inbox."""
    import inspect
    from training.mcp.inbox_server import main
    assert "717171" in inspect.getsource(main)
