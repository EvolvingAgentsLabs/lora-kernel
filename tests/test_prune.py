"""The tool surface, pruned to what a member declares — and renamed back.

WHAT THESE GUARD. P43's agent turn made zero tool calls **[ran]**, and two separate
things were wrong with what the expert saw: the *volume* of unknown tags, and the
*renaming* of the three it knew. A prune that fixed only the first would produce
calls the agent cannot route, and would look like it worked from the model's side.
"""

from __future__ import annotations

import json
import re

import pytest

from training.harness import contract
from training.harness.openai_proxy import rebuild_transcript
from training.harness.tool_calls import prune, rename_calls, tools_to_instruction
from training.harness.train_pool import POOL

CALL = re.compile(r"<([A-Za-z_][\w-]*)>([^<]*)</\1>")


def fn(name, **props):
    return {"type": "function", "function": {
        "name": name,
        "parameters": {"type": "object", "properties": props,
                       "required": sorted(props)}}}


INBOX = ["thread_history", "sender_stats", "message"]


# --- the surfaces are read off the corpora, not asserted --------------------

HEAD = "The following tools are available"
# THE SAME PATTERN THE SERIALIZER USES. A narrower one — matching only
# `<tag>...</tag>` — read the physics block as a single tool, because its
# other two render their keyed arguments instead **[ran]** 2026-09-16.
OFFERED = CALL


def _taught(corpus: str) -> tuple[list[str], bool]:
    """The tags this corpus teaches, and whether it teaches an order.

    A corpus carrying an offered block is read from the block, because that is the
    text the model sees, and its order is a fact. The physics corpora carry **no
    listing at all** and their call order varies row to row — so there is an order
    in the file and it is not a fact about anything. Returning the distinction is
    what keeps the test from enforcing an accident.
    """
    block, first = None, []
    with open(corpus) as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            for m in row["messages"]:
                t = m.get("content") or ""
                if HEAD in t and block is None:
                    block = [x.group(1) for x in OFFERED.finditer(t[t.index(HEAD):])]
            for m in CALL.finditer(json.dumps(row)):
                if m.group(1) not in first:
                    first.append(m.group(1))
    return (block, True) if block else (sorted(set(first)), False)


@pytest.mark.parametrize("path,record", sorted(POOL.items()))
def test_the_declared_surface_is_what_the_corpus_teaches(path, record):
    """The band's rule, applied to the new field: re-read, never trust.

    Doing exactly this to the bands caught three of five wrong on the first pass,
    and doing it to the surface caught the order wrong on all four non-empty ones.
    """
    taught, ordered = _taught(record["corpus"])
    if ordered:
        assert taught == record["surface"], (
            f"{path} declares {record['surface']} and its block lists {taught}")
    else:
        assert sorted(record["surface"]) == taught, (
            f"{path} declares {record['surface']} and its corpus calls {taught}")


@pytest.mark.parametrize("path,record", sorted(POOL.items()))
def test_where_an_order_was_taught_it_is_not_alphabetised(path, record):
    """The check that would have caught the first version of `surface`.

    It sorted, and the rendered block then matched the corpus in every character
    except the order of its three lines. Only a corpus that carries a block can fail
    this — the others are sorted on purpose, to say no order was taught.
    """
    _, ordered = _taught(record["corpus"])
    if ordered:
        assert record["surface"] != sorted(record["surface"])


def test_an_empty_surface_is_declared_and_not_omitted():
    """`domain-mt` calls nothing in 600 of 600; `[]` is the true statement."""
    assert POOL["adapters/domain-mt"]["surface"] == []
    assert contract.offers(POOL["adapters/domain-mt"], "calc") is False


def test_a_member_that_says_nothing_is_not_read_as_a_denial():
    assert contract.offers({"band": contract.band(0, 1)}, "anything") is True


def test_a_surface_the_serializer_could_not_parse_is_refused():
    with pytest.raises(contract.ContractError, match="tool_calls.CALL"):
        contract.validate("m", contract.text("c", contract.band(0, 1),
                                             tags=["mcp::message"]))


def test_a_tag_declared_twice_is_refused():
    r = contract.text("c", contract.band(0, 1))
    r["surface"] = ["message", "message"]
    with pytest.raises(contract.ContractError, match="twice"):
        contract.validate("m", r)


# --- pruning ---------------------------------------------------------------

def test_the_pruned_surface_is_byte_for_byte_the_trained_one():
    """The decisive check, and the one that caught the sort.

    Take the tools the MCP server really offers, rename them the way an agent
    runtime really does, prune, render — and require the result to equal the block
    `email-full` read in 598 of 598 training prompts, character for character.
    Anything less than equality is a shorter surface, not the trained one.
    """
    from training.email.tools import SCHEMA
    renamed = [{"type": "function",
                "function": {**t["function"],
                             "name": f"mcp__lora-inbox__{t['function']['name']}"}}
               for t in SCHEMA]
    kept, _, _ = prune(renamed, POOL["adapters/email-full"]["surface"])
    got = tools_to_instruction(kept, arity=True, enums=False)

    with open(POOL["adapters/email-full"]["corpus"]) as f:
        row = json.loads(f.readline())
    user = [m for m in row["messages"] if m["role"] == "user"][0]["content"]
    assert got == user[user.index(HEAD):]


def test_the_volume_goes_away():
    tools = [fn(f"Tool{i}") for i in range(50)] + [fn("message", id="")]
    kept, fwd, back = prune(tools, INBOX)
    assert [k["function"]["name"] for k in kept] == ["message"]


def test_a_namespaced_name_is_matched_on_its_last_segment():
    for offered in ("mcp__lora-inbox__message", "lora-inbox.message",
                    "lora-inbox/message", "lora-inbox:message"):
        kept, fwd, _ = prune([fn(offered)], INBOX)
        assert [k["function"]["name"] for k in kept] == ["message"], offered
        assert fwd["message"] == offered


def test_an_exact_name_wins_over_a_namespaced_one():
    kept, fwd, _ = prune([fn("mcp__other__message"), fn("message")], INBOX)
    assert fwd["message"] == "message"


def test_two_servers_offering_the_same_tail_are_refused_rather_than_guessed():
    """Calling the wrong one of two tools is worse than calling neither."""
    kept, fwd, _ = prune([fn("mcp__a__message"), fn("mcp__b__message")], INBOX)
    assert kept == [] and fwd == {}


def test_the_schema_survives_the_rename():
    """The arity convention reads `required`; losing it would cost P28's 55%."""
    kept, _, _ = prune([fn("mcp__x__message", id="")], INBOX)
    assert kept[0]["function"]["parameters"]["required"] == ["id"]
    assert "<message>...</message>" in tools_to_instruction(kept, arity=True)


def test_recognising_none_of_them_yields_none_rather_than_a_fallback():
    """P25 priced an unknown surface at 27/63. Re-offering it is not a repair."""
    kept, fwd, _ = prune([fn("Bash"), fn("Read")], INBOX)
    assert kept == [] and fwd == {}


def test_pruning_against_an_empty_surface_offers_nothing():
    assert prune([fn("calc")], []) == ([], {}, {})


# --- the rename back, which is the half that makes it usable ---------------

def test_a_call_leaves_under_the_name_the_caller_offered():
    tools = [fn("mcp__lora-inbox__thread_history", id="")]
    _, fwd, _ = prune(tools, INBOX)
    calls = [{"id": "call_0", "type": "function",
              "function": {"name": "thread_history", "arguments": '{"id": "7"}'}}]
    assert rename_calls(calls, fwd)[0]["function"]["name"] == \
        "mcp__lora-inbox__thread_history"


def test_a_tag_outside_the_surface_leaves_unchanged():
    assert rename_calls(
        [{"function": {"name": "calc", "arguments": "{}"}}], {"message": "x"}
    )[0]["function"]["name"] == "calc"


def test_the_history_is_folded_in_the_vocabulary_the_model_reads():
    """Its own past work must not come back in a vocabulary it does not have."""
    tools = [fn("mcp__lora-inbox__message", id="")]
    _, _, back = prune(tools, INBOX)
    out = rebuild_transcript([
        {"role": "assistant", "tool_calls": [
            {"id": "c1", "type": "function",
             "function": {"name": "mcp__lora-inbox__message",
                          "arguments": '{"id": "7"}'}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "hello"},
    ], back)
    assert "<message>id=7</message>= hello" in out[0]["content"]
    assert "mcp__" not in out[0]["content"]


def test_without_the_map_the_history_keeps_the_callers_names():
    """The unpruned path is untouched — every measurement before today used it."""
    out = rebuild_transcript([
        {"role": "assistant", "tool_calls": [
            {"id": "c1", "type": "function",
             "function": {"name": "calc", "arguments": '{"_": "2 * 3"}'}}]},
    ])
    assert "<calc>2 * 3</calc>" in out[0]["content"]


# --- the wiring, driven through a real server ------------------------------
#
# THE UNIT TESTS ABOVE WOULD PASS WITH THE PROXY NEVER CALLING ANY OF THEM. The flag,
# the surface lookup and the `forward` map crossing from the request path to the
# response path are the parts a stub cannot reach, and they are where a filter that
# silently does nothing would live. So this drives an actual socket.

import threading
import urllib.request
from http.server import ThreadingHTTPServer

import training.harness.openai_proxy as px


class _Serving:
    def __init__(self, reply, **flags):
        self.reply = reply
        self.flags = flags
        self.seen = {}

    def __enter__(self):
        self._old = {k: getattr(px, k) for k in
                     ("PRUNE", "POOL_SURFACE", "_fetch", "LOG", "KEY", "FALLBACK")}
        px.PRUNE = self.flags.get("prune", True)
        px.POOL_SURFACE = self.flags.get("surfaces", {"email-full": INBOX})
        px.LOG = px.KEY = px.FALLBACK = None

        def fake_fetch(path, payload, timeout=600, base=None, key=None):
            self.seen = payload
            return json.loads(json.dumps(self.reply))

        px._fetch = fake_fetch
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), px.Handler)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}/v1/chat/completions"
        return self

    def __exit__(self, *a):
        self.srv.shutdown()
        self.srv.server_close()
        for k, v in self._old.items():
            setattr(px, k, v)

    def post(self, body):
        req = urllib.request.Request(
            self.url, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())


def _reply(text):
    return {"choices": [{"message": {"role": "assistant", "content": text},
                         "finish_reason": "stop"}]}


FIFTY_PLUS_THREE = [fn(f"Tool{i}") for i in range(50)] + [
    fn("mcp__lora-inbox__message", id=""),
    fn("mcp__lora-inbox__sender_stats", sender=""),
    fn("mcp__lora-inbox__thread_history", id="")]


def test_the_expert_is_shown_three_tags_and_not_fifty_three():
    with _Serving(_reply("ok")) as s:
        s.post({"model": "email-full", "messages": [{"role": "user", "content": "hi"}],
                "tools": FIFTY_PLUS_THREE})
        block = s.seen["messages"][-1]["content"]
    assert block.count("<") - block.count("</") == 3
    for tag in INBOX:
        assert f"<{tag}>" in block
    assert "Tool0" not in block and "mcp__" not in block


def test_a_call_comes_back_under_the_name_the_agent_offered():
    with _Serving(_reply("checking <message>id=7</message>")) as s:
        out = s.post({"model": "email-full",
                      "messages": [{"role": "user", "content": "hi"}],
                      "tools": FIFTY_PLUS_THREE})
    call = out["choices"][0]["message"]["tool_calls"][0]
    assert call["function"]["name"] == "mcp__lora-inbox__message"
    assert json.loads(call["function"]["arguments"]) == {"id": "7"}
    assert out["choices"][0]["finish_reason"] == "tool_calls"


def test_with_the_flag_off_nothing_is_filtered():
    """Every measurement before today ran this way and has to keep meaning it."""
    with _Serving(_reply("ok"), prune=False) as s:
        s.post({"model": "email-full", "messages": [{"role": "user", "content": "hi"}],
                "tools": FIFTY_PLUS_THREE})
        block = s.seen["messages"][-1]["content"]
    assert "Tool0" in block and "mcp__lora-inbox__message" in block


def test_a_model_the_pool_does_not_declare_is_offered_everything():
    with _Serving(_reply("ok")) as s:
        s.post({"model": "some-frontier-model",
                "messages": [{"role": "user", "content": "hi"}],
                "tools": FIFTY_PLUS_THREE})
        block = s.seen["messages"][-1]["content"]
    assert "Tool0" in block


def test_the_record_keeps_both_counts_and_no_prompt(tmp_path):
    log = tmp_path / "t.jsonl"
    with _Serving(_reply("ok")) as s:
        px.LOG = str(log)
        s.post({"model": "email-full",
                "messages": [{"role": "user", "content": "SECRET PROSE"}],
                "tools": FIFTY_PLUS_THREE})
    row = json.loads(log.read_text().splitlines()[0])
    assert row["tools_offered"] == 53 and len(row["tools"]) == 3
    assert "SECRET PROSE" not in log.read_text()


# --- P59: a runtime's own tool with the member's bare name --------------------------

def test_the_members_keys_beat_a_colliding_bare_name():
    """OpenClaw offers `message` (action, channel, target, …) beside
    `lora-inbox__message` (id) **[ran]** P59. The corpus writes `<message>id=…`."""
    tools = [fn("message", action="", channel="", target=""), fn("lora-inbox__message", id="")]
    kept, fwd, _ = prune(tools, ["message"], {"message": ["id"]})
    assert fwd == {"message": "lora-inbox__message"}
    assert kept[0]["function"]["parameters"]["required"] == ["id"]


def test_without_declared_keys_the_exact_name_still_wins():
    tools = [fn("mcp__other__message"), fn("message")]
    _, fwd, _ = prune(tools, ["message"])
    assert fwd["message"] == "message"


def test_the_real_openclaw_surface_prunes_to_the_three_inbox_tools():
    """The recording P59 made of one OpenClaw turn: 54 tools, streaming."""
    import pathlib
    rec = pathlib.Path("results/P59-prune-attribution-20260917/openclaw_tools.json")
    tools = json.loads(rec.read_text())
    assert len(tools) == 54
    member = POOL["adapters/email-full"]
    kept, fwd, _ = prune(tools, member["surface"], member["surface_args"])
    assert fwd == {"thread_history": "lora-inbox__thread_history",
                   "sender_stats": "lora-inbox__sender_stats",
                   "message": "lora-inbox__message"}


@pytest.mark.parametrize("path,record", sorted(POOL.items()))
def test_the_declared_keys_are_what_the_corpus_writes(path, record):
    """Read off the corpus, like the band and the surface."""
    seen = {}
    with open(record["corpus"]) as f:
        for line in f:
            if not line.strip():
                continue
            for m in CALL.finditer(json.dumps(json.loads(line))):
                body = m.group(2)
                if "=" in body:
                    seen.setdefault(m.group(1), set()).update(
                        k.strip() for k in re.findall(r"([\w.\-]+)\s*=", body))
    for tag, keys in (record.get("surface_args") or {}).items():
        assert set(keys) <= seen.get(tag, set()), (path, tag, keys, seen.get(tag))
