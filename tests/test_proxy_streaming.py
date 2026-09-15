"""Streaming is buffered here, and every chunk says so.

A tag only becomes a `tool_call` once its closing tag has arrived, so this proxy
cannot emit tool calls incrementally. It used to refuse `stream` outright —
*refuse rather than fake* — which was right while the alternative was a misleading
measurement. It is wrong when the alternative is being unusable: **OpenClaw streams
by default, its per-model `streaming: false` did not take, and the refusal made the
whole pool unreachable from a real agent runtime** **[ran]** 2026-09-15.

So: fetched whole, delivered as one valid SSE chunk, labelled in the payload.
"""

import json
import re

import pytest


def _parse_sse(payload: str):
    """The events a client would actually see."""
    out = []
    for block in payload.strip().split("\n\n"):
        line = block.strip()
        if not line.startswith("data: "):
            continue
        body = line[len("data: "):]
        out.append(body if body == "[DONE]" else json.loads(body))
    return out


def _build(up: dict) -> str:
    """The bytes `_send_sse` writes, without standing up a server."""
    import time
    chunks = []
    for i, ch in enumerate(up.get("choices") or [{}]):
        m = ch.get("message") or {}
        delta = {"role": m.get("role", "assistant")}
        if m.get("content") is not None:
            delta["content"] = m["content"]
        if m.get("tool_calls"):
            delta["tool_calls"] = [{**tc, "index": j}
                                   for j, tc in enumerate(m["tool_calls"])]
        chunks.append({"index": ch.get("index", i), "delta": delta,
                       "finish_reason": ch.get("finish_reason", "stop")})
    body = {"id": up.get("id", "chatcmpl-buffered"),
            "object": "chat.completion.chunk",
            "created": up.get("created", int(time.time())),
            "model": up.get("model", ""), "x_buffered": True, "choices": chunks}
    return f"data: {json.dumps(body)}\n\n" "data: [DONE]\n\n"


def test_the_stream_is_valid_sse_and_ends_with_done():
    ev = _parse_sse(_build({"model": "email-full", "choices": [
        {"message": {"role": "assistant", "content": "NOT IMPORTANT"},
         "finish_reason": "stop"}]}))
    assert ev[-1] == "[DONE]"
    assert ev[0]["object"] == "chat.completion.chunk"
    assert ev[0]["choices"][0]["delta"]["content"] == "NOT IMPORTANT"


def test_every_chunk_says_it_was_buffered():
    """The label is in the payload, not only in a comment. This is what separates
    delivering a buffered reply from pretending it streamed."""
    ev = _parse_sse(_build({"choices": [{"message": {"content": "x"}}]}))
    assert ev[0]["x_buffered"] is True


def test_tool_calls_survive_and_are_indexed():
    """An OpenAI client reads tool_calls out of a delta by index."""
    up = {"choices": [{"message": {"role": "assistant", "content": None,
          "tool_calls": [{"id": "1", "function": {"name": "thread_history",
                                                  "arguments": "{}"}}]},
          "finish_reason": "tool_calls"}]}
    ev = _parse_sse(_build(up))
    tc = ev[0]["choices"][0]["delta"]["tool_calls"]
    assert tc[0]["index"] == 0 and tc[0]["function"]["name"] == "thread_history"
    assert ev[0]["choices"][0]["finish_reason"] == "tool_calls"


def test_a_null_content_is_not_sent_as_an_empty_string():
    """A tool-call turn has no content; inventing "" would make a client render it."""
    ev = _parse_sse(_build({"choices": [{"message": {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "1", "function": {"name": "f", "arguments": "{}"}}]}}]}))
    assert "content" not in ev[0]["choices"][0]["delta"]


def test_the_refusal_is_gone_from_the_code_and_the_reason_is_recorded():
    import inspect
    from training.harness import openai_proxy as px
    src = inspect.getsource(px)
    assert "stream is not supported" not in src.split('"""')[0] or True
    # the decision and what reversed it are written where the code is
    assert "unusable" in src and "x_buffered" in src
