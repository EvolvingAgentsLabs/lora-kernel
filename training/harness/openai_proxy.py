"""An OpenAI-compatible front end for the adapter pool, assembled from measured parts.

WHAT IT IS. A proxy between an agent runtime — OpenClaw, Hermes, anything that speaks
OpenAI — and a vLLM server holding the pool. The agent sends `tools=[…]` and reads
`tool_calls`; the adapters read a tag surface and write tags. This translates, in both
directions, and forwards everything else untouched.

EVERY PIECE IT USES WAS MEASURED SEPARATELY.

    /v1/models with one name per adapter, verified applied     P26  [ran]
    tags -> tool_calls, 0 domain lines, 604/604 round trips    P27  [ran]
    tools=[…] -> tag surface                                   P27  [ran] costs 0.188
    the arity convention                                       P28  [ran] recovers 55%

WHAT IS ASSEMBLED HERE AND NOT YET MEASURED: **the multi-turn path.** An agent sends
back `role: "tool"` results, and this renders them into the transcript as `= value`
so the adapter continues where it left off. Every measurement so far has been a
single turn — P27 arm 3 explicitly so. **This code is the first time the loop exists,
and running it is a different step from writing it.** It is marked here rather than
discovered later.

WHAT IT DOES NOT DO. It does not choose the adapter: the client's `model` field does,
because S3 measured a router tying a lookup table and there is nothing better to
offer. And it adds no domain knowledge — it names no tool, no argument and no unit.

    python3 -m training.harness.openai_proxy --upstream http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from training.harness.tool_calls import (CALL, from_tool_call, strip_calls,
                                         to_tool_calls, tools_to_instruction)

UPSTREAM = "http://127.0.0.1:8000"
ARITY = True          # P28: recovers 55% of the schema's cost, 0 domain lines
ENUMS = False         # P28: made it worse — not carried forward
LOG = None            # --log <path> records traffic for the null arm


def _fetch(path: str, payload: dict | None, timeout: int = 600):
    req = urllib.request.Request(
        UPSTREAM + path, method="POST" if payload is not None else "GET",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    return json.loads(body) if body.strip() else {}


def rebuild_transcript(messages: list[dict]) -> list[dict]:
    """Fold an agent's `tool_calls` / `tool` results back into the tag transcript.

    THIS IS THE MULTI-TURN PATH AND IT IS UNMEASURED. An OpenAI client keeps the
    conversation as structured turns; the adapter was trained on one running
    transcript where a call is immediately followed by `= value`. So an assistant
    turn carrying `tool_calls` becomes its tags again, and each `role: "tool"` result
    becomes the `= value` that answers the tag above it.

    A result whose `tool_call_id` matches nothing is appended rather than dropped:
    losing a value the agent computed is worse than a transcript in an odd order.
    """
    out, pending = [], {}
    for m in messages:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            text = m.get("content") or ""
            for tc in m["tool_calls"]:
                text += ("\n" if text and not text.endswith("\n") else "")
                text += from_tool_call(tc)
                pending[tc.get("id")] = len(out)
            out.append({"role": "assistant", "content": text})
        elif role == "tool":
            value = m.get("content", "")
            i = pending.get(m.get("tool_call_id"))
            if i is None:
                out.append({"role": "assistant", "content": f"= {value}"})
            else:
                out[i]["content"] += f"= {value}"
        else:
            out.append({k: v for k, v in m.items() if k in ("role", "content")})
    return out


def render_tools(messages: list[dict], tools: list[dict]) -> list[dict]:
    """Put the tag surface where the adapter expects to read it."""
    block = tools_to_instruction(tools, arity=ARITY, enums=ENUMS)
    if not block:
        return messages
    out = list(messages)
    for i in range(len(out) - 1, -1, -1):
        if out[i].get("role") == "user":
            out[i] = {**out[i], "content": f"{out[i]['content']}\n\n{block}"}
            return out
    return out + [{"role": "user", "content": block}]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_GET(self):
        try:
            self._send(200, _fetch(self.path, None, timeout=30))
        except Exception as e:
            self._send(502, {"error": {"message": repr(e)}})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError as e:
            return self._send(400, {"error": {"message": str(e)}})
        if not self.path.startswith("/v1/chat/completions"):
            try:
                return self._send(200, _fetch(self.path, req))
            except Exception as e:
                return self._send(502, {"error": {"message": repr(e)}})

        tools = req.pop("tools", None)
        req.pop("tool_choice", None)
        # STREAMING IS REFUSED RATHER THAN FAKED. A tag only becomes a tool_call once
        # its closing tag has arrived, so a streamed reply cannot carry tool_calls
        # incrementally without buffering the whole thing — which is not streaming.
        if req.pop("stream", False):
            return self._send(400, {"error": {
                "message": "stream is not supported: a tag is only a tool call once "
                           "it is closed, so this proxy would have to buffer the "
                           "whole reply and call it a stream"}})
        msgs = rebuild_transcript(req.get("messages") or [])
        req["messages"] = render_tools(msgs, tools) if tools else msgs

        try:
            up = _fetch("/v1/chat/completions", req)
        except urllib.error.HTTPError as e:
            return self._send(e.code, {"error": {"message": e.read()[:400].decode(
                "utf-8", "replace")}})
        except Exception as e:
            return self._send(502, {"error": {"message": repr(e)}})

        if LOG:
            # TRAFFIC IS RECORDED SO THE NULL ARM HAS SOMETHING TO MEASURE. What an
            # agent actually asks for cannot be guessed from a suite, and the first
            # question about a new deployment is whether the base can do the job at
            # all — which needs its traffic, not ours.
            with open(LOG, "a") as f:
                f.write(json.dumps({
                    "model": req.get("model"),
                    "tools": [((x.get("function") or x).get("name"))
                              for x in (tools or [])],
                    "turns": len(req.get("messages") or []),
                    "reply": ((up.get("choices") or [{}])[0].get("message") or {}
                              ).get("content") or "",
                }) + "\n")

        for choice in up.get("choices", []):
            msg = choice.get("message") or {}
            text = msg.get("content") or ""
            if tools and CALL.search(text):
                calls = to_tool_calls(text)
                msg["tool_calls"] = calls
                msg["content"] = strip_calls(text) or None
                choice["finish_reason"] = "tool_calls"
        return self._send(200, up)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream", default=UPSTREAM)
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--log", default=None,
                    help="append one line per request, for training.harness.null_arm")
    ap.add_argument("--enums", action="store_true",
                    help="P28 measured this as harmful; off unless asked")
    args = ap.parse_args()
    globals()["UPSTREAM"] = args.upstream
    globals()["ENUMS"] = args.enums
    globals()["LOG"] = args.log

    print(f"[proxy] :{args.port} -> {UPSTREAM}  arity={ARITY} enums={ENUMS}",
          flush=True)
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
