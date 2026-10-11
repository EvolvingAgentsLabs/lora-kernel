"""The τ² shim — native tool calls on one side, this repository's inline tags on the other.

WHAT IT IS. An OpenAI-compatible HTTP server between τ²-bench and a vLLM `/v1/completions` endpoint serving
a member. τ² sends `/v1/chat/completions` with `tools=[…]` and `role:"tool"` messages and executes every
call itself — it must, its reward replays the agent's calls on a fresh database (`docs/tau2/RECON.md` §2).
A member reads one running transcript where a call is a tag and its result follows as `= value`, and is
served corpus-mode (generate, stop at the closing tag, the caller supplies the result). Served the other
way, members break: 11/90 against 90/90 (CLAUDE.md §3) **[ran]**. This translates, both directions.

THE SPEC IS `docs/tau2/RECON.md` §3 "Adapter spec", and each point is a function here:

    1 wire          τ² `--agent-llm openai/<member> --agent-llm-args '{"api_base": "http://…:8100/v1"}'`
    2 inbound       τ²'s system prompt KEPT (a member prompt is prepended, never substituted); tools rendered
                    as the repo's block (`tool_calls.tools_to_instruction`, arity on); history folded inline —
                    `fold`
    3 arguments     `k=v; k=v` only when every value is a plain string free of `; , < =` and newlines; a single
                    required argument positionally (the arity convention); otherwise the JSON object; then
                    strings coerced to the type the schema declares — `call_to_tag`, `tag_to_args`, `coerce`
    4 outbound      one call per assistant turn, a conversation-unique id, text after the closing tag cut, a tag
                    nobody offered returned as text and counted — `parse_reply`, `to_openai`
    5 caps          no round-trip cap (τ²'s --max-steps governs); max tokens ≥ 512 per step
    6 log           one line per request, shapes only — `Shim.log`

WHY THE ARGUMENT ENCODING CHANGES AND NOTHING ELSE DOES. The repo's serializer round-trips 1,345 of 1,587
shipped airline calls and loses 220 of 320 writes (nested arrays, integers as strings, values cut at commas,
empty-argument calls dropped); the JSON-body candidate round-trips 1,587/1,587 **[ran]** T0. τ² does not
coerce types at call time (`toolkit.py:138–142`), so a `"50"` for an integer lands in the DB as a string and
the DB hash fails. Coercion reads only τ²'s own schema: this module names no tool, no argument and no domain.

THE FORMULA THE CHECK RESTS ON (G-shim-1). For every shipped call c = (name, args):
    parse(serialize(c)) = c            names, arguments and argument types identical
    serialize(parse(serialize(c))) = serialize(c)
    unfold(fold(conversation)) = conversation   calls, results and user turns identical; assistant text
                                                identical up to surrounding whitespace (the only normalisation)
Pass = 100 %, no tolerance. `examples/tau2/check_shim.py` runs it over every shipped airline trajectory.

`training/harness/openai_proxy.py` is the same idea for OpenClaw and is left untouched: its MAX_ROUNDTRIPS=6,
its `k=v`-only serializer and its `--member-prompt` replacement would each break τ² (RECON §3), and other runs
depend on its behaviour as it is.

    python -m examples.tau2.shim --upstream http://127.0.0.1:8001 --base google/gemma-4-E4B-it --port 8100
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from training.harness import accept_rank
from training.harness.openai_proxy import render_tools
from training.harness.tool_calls import BLOCK_HEADER

MIN_MAX_TOKENS = 512          # a JSON book_reservation does not fit the proxy's 256 (RECON §3.5)
DEFAULT_MAX_TOKENS = 768
PLACEHOLDERS = ("...", "…")   # the block's own placeholder is not a call (tool_calls.to_tool_calls, P63)
TAG = re.compile(r"<([A-Za-z_][\w-]*)>([^<]*)</\1>")
KEY = re.compile(r"^[A-Za-z_][\w.\-]*$")
UNSAFE_KV = re.compile(r"[;,<=\n\r]")
# ONE SENTENCE, NAMING NO DOMAIN. The repo's block shows `k=...`; a member must also be told that a value
# which is not plain text is written as the JSON object — the block is the prompt a corpus has to teach.
JSON_NOTE = ("When a value is a number, a list or an object, or contains ; , = or <, write the whole "
             "argument list as one JSON object instead: <tag>{\"key\": value, …}</tag>.")


class Malformed(ValueError):
    """A tag the model wrote that is not a call the schema can accept."""


# ------------------------------------------------------------------------------------------- the schema
def tool_index(tools: list[dict]) -> dict[str, dict]:
    """`{name: parameters}` from an OpenAI `tools=[…]` list."""
    out = {}
    for t in tools or []:
        fn = t.get("function", t)
        if isinstance(fn.get("name"), str):
            out[fn["name"]] = fn.get("parameters") or {}
    return out


def _resolve(schema: dict, defs: dict) -> dict:
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/$defs/"):
        return defs.get(ref.split("/")[-1], {})
    return schema


def _types(schema: dict, defs: dict) -> tuple[set[str], list[dict]]:
    """Declared JSON types of a schema node, and the alternatives it unions over."""
    schema = _resolve(schema, defs)
    alts = [_resolve(s, defs) for s in (schema.get("anyOf") or schema.get("oneOf") or [])]
    t = schema.get("type")
    types = set([t] if isinstance(t, str) else (t or []))
    for a in alts:
        at = a.get("type")
        types |= set([at] if isinstance(at, str) else (at or []))
    return types, [schema] + alts


INT = re.compile(r"[+-]?\d+")
NUM = re.compile(r"[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?")


def coerce(value, schema: dict, defs: dict):
    """A string put back to the scalar type the schema declares; containers walked.

    Only strings are touched: they are what the `k=v` and positional encodings can turn a number into. A value
    of the right type, or a string where a string is allowed, is returned unchanged — so coercion is the identity
    on every call that already matches its schema, which is what G-shim-1 asserts."""
    types, nodes = _types(schema, defs)
    if isinstance(value, str):
        if not types or "string" in types:
            return value
        v = value.strip()
        if "integer" in types and INT.fullmatch(v):
            return int(v)
        if "number" in types and NUM.fullmatch(v):
            return json.loads(v) if not v.startswith((".", "+")) else float(v)
        if "boolean" in types and v.lower() in ("true", "false"):
            return v.lower() == "true"
        if "null" in types and v.lower() in ("null", "none"):
            return None
        if ("array" in types and v.startswith("[")) or ("object" in types and v.startswith("{")):
            try:
                return coerce(json.loads(v), schema, defs)
            except json.JSONDecodeError:
                return value
        return value
    if isinstance(value, list):
        items = next((n.get("items") for n in nodes if isinstance(n.get("items"), dict)), None)
        return [coerce(x, items, defs) for x in value] if items else value
    if isinstance(value, dict):
        props = {}
        for n in nodes:
            props.update(n.get("properties") or {})
        return {k: coerce(v, props[k], defs) if k in props else v for k, v in value.items()}
    return value


def coerce_args(args: dict, params: dict) -> dict:
    return coerce(args, {"type": "object", "properties": params.get("properties") or {}}, params.get("$defs") or {})


def positional_key(params: dict) -> str | None:
    """The arity convention, as `tools_to_instruction(arity=True)` renders it: exactly one required parameter."""
    props = params.get("properties") or {}
    required = params.get("required") or sorted(props)
    return required[0] if len(required) == 1 else None


# ------------------------------------------------------------------------------------- one call <-> one tag
def _plain(v) -> bool:
    return isinstance(v, str) and v != "" and v == v.strip() and not UNSAFE_KV.search(v)


def call_to_tag(name: str, args: dict, params: dict) -> tuple[str, str]:
    """`(tag, kind)` — the tag a member writes for this call. kind ∈ {empty, positional, kv, json}."""
    if not args:
        return f"<{name}></{name}>", "empty"
    pk = positional_key(params)
    if pk is not None and list(args) == [pk]:
        v = args[pk]
        if (isinstance(v, str) and v and v == v.strip() and "<" not in v and "\n" not in v and "\r" not in v
                and not v.startswith("{") and not re.match(rf"\s*{re.escape(pk)}\s*=", v)):
            return f"<{name}>{v}</{name}>", "positional"
    if all(KEY.match(k) for k in args) and all(_plain(v) for v in args.values()):
        return f"<{name}>{'; '.join(f'{k}={v}' for k, v in args.items())}</{name}>", "kv"
    # `<` escaped so the body stays inside the tag grammar (`[^<]*`); json.loads restores it
    body = json.dumps(args, ensure_ascii=False).replace("<", "\\u003c")
    return f"<{name}>{body}</{name}>", "json"


def tag_to_args(name: str, body: str, params: dict) -> dict:
    """The arguments of a tag body, typed by the schema. Raises Malformed."""
    b = body.strip()
    props = params.get("properties") or {}
    if b in PLACEHOLDERS:
        raise Malformed(f"<{name}> holds the block's placeholder, not arguments")
    if b == "":
        return {}
    if b.startswith("{"):
        try:
            args = json.loads(b)
        except json.JSONDecodeError as e:
            raise Malformed(f"<{name}> JSON body does not parse: {e}") from None
        if not isinstance(args, dict):
            raise Malformed(f"<{name}> JSON body is not an object")
        return coerce_args(args, params)
    pk = positional_key(params)
    if pk is not None and not re.match(rf"{re.escape(pk)}\s*=", b):
        return coerce_args({pk: b}, params)
    args = {}
    for part in b.split(";"):
        k, eq, v = part.partition("=")
        if not eq or not k.strip():
            raise Malformed(f"<{name}> body is neither k=v pairs, JSON nor a positional value")
        args[k.strip()] = v.strip()
    if props and not set(args) <= set(props) and len(props) == 1 and len(args) == 1:
        raise Malformed(f"<{name}> names an argument the schema does not have")
    return coerce_args(args, params)


# ------------------------------------------------------------------------------------- history -> transcript
def _sep(buf: str) -> str:
    return "" if buf == "" or buf.endswith("\n") else "\n"


def _assemble(segs: list[dict]) -> str:
    buf = ""
    for s in segs:
        if s["k"] == "text":
            buf += _sep(buf) + s["text"]
        elif s["k"] == "call":
            buf += _sep(buf) + s["tag"]
            if s.get("result") is not None:
                buf += f"= {s['result']}\n"
        else:                               # a result whose call is not in the history: kept, never dropped
            buf += _sep(buf) + f"= {s['result']}\n"
    return buf


def _call_parts(tc: dict) -> tuple[str, dict]:
    fn = tc.get("function") or tc
    raw = fn.get("arguments")
    args = json.loads(raw) if isinstance(raw, str) else (raw or {})
    return fn["name"], args


def fold(messages: list[dict], tools: list[dict], member_prompt: str | None = None) -> tuple[list[dict], str, dict]:
    """τ²'s OpenAI messages → (chat messages for the template, the open assistant turn's prefix, counts).

    Each agent turn — everything the agent did between two user messages — becomes ONE assistant message: its
    text, each call as its tag, and each result as `= value` on the line after the tag that asked for it, the
    surface `accept_rank.run_chain` trains and serves. A turn still open (the last message is a tool result) is
    returned as `prefix`: the member continues it, exactly as corpus mode continues after `= value`.
    The system prompt is τ²'s (instructions + policy) — a member prompt goes in FRONT of it, never instead."""
    idx = tool_index(tools)
    system = [m.get("content") or "" for m in messages if m.get("role") == "system"]
    chat: list[dict] = []
    sys_text = "\n\n".join(system)
    if sys_text or member_prompt:
        chat.append({"role": "system", "content": f"{member_prompt}\n\n{sys_text}" if member_prompt and sys_text
                     else (member_prompt or sys_text)})
    segs: list[dict] | None = None
    by_id: dict = {}
    counts = {"calls": 0, "json": 0, "kv": 0, "positional": 0, "empty": 0, "orphan_results": 0}
    for m in messages:
        role = m.get("role")
        if role == "system":
            continue
        if role == "user":
            if segs is not None:
                chat.append({"role": "assistant", "content": _assemble(segs)})
                segs = None
            chat.append({"role": "user", "content": m.get("content") or ""})
        elif role == "assistant":
            segs = [] if segs is None else segs
            text = (m.get("content") or "").strip()
            if text:
                segs.append({"k": "text", "text": text})
            for tc in m.get("tool_calls") or []:
                name, args = _call_parts(tc)
                tag, kind = call_to_tag(name, args, idx.get(name, {}))
                counts["calls"] += 1
                counts[kind] += 1
                seg = {"k": "call", "tag": tag, "result": None}
                segs.append(seg)
                by_id[tc.get("id")] = seg
        elif role == "tool":
            segs = [] if segs is None else segs
            seg = by_id.get(m.get("tool_call_id"))
            value = m.get("content")
            value = value if isinstance(value, str) else json.dumps(value)
            if seg is not None and seg["result"] is None:
                seg["result"] = value
            else:
                counts["orphan_results"] += 1
                segs.append({"k": "result", "result": value})
    prefix = ""
    if segs is not None:
        if messages and messages[-1].get("role") == "assistant" and not messages[-1].get("tool_calls"):
            chat.append({"role": "assistant", "content": _assemble(segs)})
        else:
            prefix = _assemble(segs)
    # THE REPO'S BLOCK, PLACED BY THE REPO'S FUNCTION (`openai_proxy.render_tools`: arity on, enums off, on the
    # last user turn), then the one JSON sentence on the same turn when some tool takes keyed arguments.
    if tools:
        before = [m.get("content") for m in chat]
        chat = render_tools(chat, tools)
        if any(positional_key(p) is None and (p.get("properties") or {}) for p in idx.values()):
            i = next(i for i in range(len(chat) - 1, -1, -1)
                     if i >= len(before) or chat[i].get("content") != before[i])
            chat[i] = {**chat[i], "content": chat[i]["content"] + "\n" + JSON_NOTE}
    return chat, prefix, counts


def unfold(chat: list[dict], prefix: str, tools: list[dict]) -> list[tuple]:
    """The inverse of `fold`, for the no-loss check: events (user|text|call|result, …) in order."""
    idx = tool_index(tools)
    names = "|".join(map(re.escape, sorted(idx, key=len, reverse=True)))
    tag = re.compile(rf"<({names})>([^<]*)</\1>") if names else None
    last_user = max((i for i, m in enumerate(chat) if m["role"] == "user"), default=None)
    events: list[tuple] = []

    def assistant(content: str):
        pos = 0
        for m in (tag.finditer(content) if tag else []):
            text = content[pos:m.start()].strip()
            if text:
                events.append(("text", text))
            events.append(("call", m.group(1), tag_to_args(m.group(1), m.group(2), idx[m.group(1)])))
            pos = m.end()
            if content.startswith("= ", pos):
                end = content.find("\n", pos)
                end = len(content) if end < 0 else end
                events.append(("result", content[pos + 2:end]))
                pos = end + 1
        rest_text = content[pos:].strip()
        if rest_text:
            events.append(("text", rest_text))

    for i, m in enumerate(chat):
        if m["role"] == "user":
            c = m["content"]
            if i == last_user and "\n\n" + BLOCK_HEADER in c:
                c = c[:c.rindex("\n\n" + BLOCK_HEADER)]
            elif i == last_user and c.startswith(BLOCK_HEADER):
                continue
            events.append(("user", c))
        elif m["role"] == "assistant":
            assistant(m["content"])
    if prefix:
        assistant(prefix)
    return events


def events_of(messages: list[dict]) -> list[tuple]:
    """The canonical event sequence of τ²'s messages: what `unfold(fold(·))` must give back."""
    events, results = [], {}
    for m in messages:
        if m.get("role") == "tool":
            results.setdefault(m.get("tool_call_id"), []).append(m.get("content"))
    used, called = set(), set()
    for m in messages:
        for tc in (m.get("tool_calls") or []) if m.get("role") == "assistant" else []:
            called.add(tc.get("id"))
    for m in messages:
        role = m.get("role")
        if role == "tool" and m.get("tool_call_id") not in called:
            events.append(("result", m.get("content")))          # an orphan: `fold` keeps it as `= value`
        if role == "user":
            events.append(("user", m.get("content") or ""))
        elif role == "assistant":
            text = (m.get("content") or "").strip()
            if text:
                events.append(("text", text))
            for tc in m.get("tool_calls") or []:
                name, args = _call_parts(tc)
                events.append(("call", name, args))
                r = results.get(tc.get("id"))
                if r and tc.get("id") not in used:
                    used.add(tc.get("id"))
                    events.append(("result", r[0]))
    return events


# ------------------------------------------------------------------------------------- the member's reply
def parse_reply(text: str, tools: list[dict]) -> dict:
    """The member's completion → at most ONE call, the text before it, and what went wrong.

    Generation stops at the first closing tag (`</`), so a reply holds at most one call; anything past a closing
    tag is cut anyway (the model guessing a result it was told to ask for, P43/P55)."""
    idx = tool_index(tools)
    out = {"content": None, "call": None, "kind": None, "unknown": 0, "malformed": 0, "unclosed": 0, "error": None}
    m = TAG.search(text)
    if m is None:
        out["content"] = text.strip() or None
        tail = re.search(r"<([A-Za-z_][\w-]*)>[^<]*$", text)
        out["unclosed"] = int(bool(tail) and tail.group(1) in idx)   # ran out of tokens inside a call
        return out
    name, body = m.group(1), m.group(2)
    before = text[:m.start()].strip() or None
    if name not in idx:
        out["content"], out["unknown"] = text[:m.end()].strip(), 1
        return out
    try:
        args = tag_to_args(name, body, idx[name])
    except Malformed as e:
        out["content"], out["malformed"], out["error"] = text[:m.end()].strip(), 1, str(e)
        return out
    out.update(content=before, call=(name, args), kind=call_to_tag(name, args, idx[name])[1])
    return out


def call_id(messages: list[dict], name: str) -> str:
    """Unique within a conversation: the position (the request grows by ≥ 2 messages per call) and a digest."""
    h = hashlib.sha1(json.dumps(messages, sort_keys=True, default=str).encode()).hexdigest()[:10]
    return f"call_{len(messages):03d}_{h}"


def to_openai(reply: dict, model: str, messages: list[dict], usage: dict) -> dict:
    msg = {"role": "assistant", "content": reply["content"]}
    finish = "stop"
    if reply["call"] is not None:
        name, args = reply["call"]
        msg["tool_calls"] = [{"id": call_id(messages, name), "type": "function",
                              "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}}]
        finish = "tool_calls"
    return {"id": "chatcmpl-" + hashlib.sha1(str(time.time()).encode()).hexdigest()[:12],
            "object": "chat.completion", "created": int(time.time()), "model": model,
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": usage}


# ------------------------------------------------------------------------------------- the server
class Renderer:
    """The member's chat template, thinking off — the same render `examples.school.gateway.vllm_generator` uses."""

    def __init__(self, base: str, empty_thought: bool = False):
        from transformers import AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(base)
        self.empty_thought = empty_thought

    def __call__(self, chat: list[dict]) -> str:
        head = self.tok.apply_chat_template(chat, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        # Gemma 4's larger models open their thought channel with thinking off; an empty one closes it (PAIR0 [ran])
        return head + ("<|channel>thought\n<channel|>" if self.empty_thought else "")


def complete(model: str, prompt: str, max_tokens: int, close: tuple, temperature: float = 0.0,
             seed: int | None = None) -> tuple[str, dict]:
    """`accept_rank.completion`, keeping the usage: stop at `</` (more closing tags than vLLM 0.30 takes) and put
    the tag back with `close_open_tag`, as the corpus-mode loop does."""
    many = len(close) > accept_rank.MAX_STOPS
    r = accept_rank.post("/v1/completions", {
        "model": model, "prompt": prompt, "temperature": temperature, "max_tokens": max_tokens,
        "stop": ["</"] if many else list(close), "include_stop_str_in_output": True,
        **({"seed": seed} if seed is not None else {})})
    ch = r["choices"][0]
    text = ch.get("text") or ""
    if many:
        if text.endswith("</"):
            text = accept_rank.close_open_tag(text[:-2], close)
        elif ch.get("finish_reason") == "stop":
            text = accept_rank.close_open_tag(text, close)
    else:
        reason = ch.get("stop_reason")
        if isinstance(reason, str) and reason in close and not text.endswith(reason):
            text += reason
        elif ch.get("finish_reason") == "stop":
            text = accept_rank.close_open_tag(text, close)
    u = r.get("usage") or {}
    return text, {"prompt_tokens": u.get("prompt_tokens", 0), "completion_tokens": u.get("completion_tokens", 0),
                  "total_tokens": u.get("total_tokens", 0), "finish_reason": ch.get("finish_reason")}


class Shim:
    """The translation, separate from HTTP so a test can drive it with a captured τ² request."""

    def __init__(self, model: str | None, render, generate=complete, member_prompt: str | None = None,
                 max_tokens: int = DEFAULT_MAX_TOKENS, log_path: str | None = None):
        if max_tokens < MIN_MAX_TOKENS:
            raise ValueError(f"max_tokens {max_tokens} < {MIN_MAX_TOKENS}: a JSON book_reservation does not fit")
        self.model, self.render, self.generate = model, render, generate
        self.member_prompt, self.max_tokens, self.log_path = member_prompt, max_tokens, log_path
        self.lock = threading.Lock()

    def prompt_for(self, req: dict) -> tuple[str, list[dict], dict]:
        """Everything the shim forwards is built HERE, from the request's `messages` and `tools` only."""
        tools = req.get("tools") or []
        chat, prefix, counts = fold(req.get("messages") or [], tools, self.member_prompt)
        return self.render(chat) + prefix, tools, counts

    def handle(self, req: dict) -> dict:
        t0 = time.time()
        prompt, tools, counts = self.prompt_for(req)
        names = list(tool_index(tools))
        asked = req.get("max_tokens") or req.get("max_completion_tokens")
        max_tokens = max(MIN_MAX_TOKENS, min(int(asked), self.max_tokens)) if asked else self.max_tokens
        text, usage = self.generate(self.model or req.get("model"), prompt, max_tokens,
                                    tuple(f"</{n}>" for n in names), float(req.get("temperature") or 0.0),
                                    req.get("seed"))
        reply = parse_reply(text, tools)
        finish = usage.pop("finish_reason", None)
        out = to_openai(reply, req.get("model") or self.model, req.get("messages") or [], usage)
        self.log({"t": round(time.time() - t0, 3), "messages": len(req.get("messages") or []),
                  "tools": len(tools), "history_calls": counts["calls"], "history_json": counts["json"],
                  "call": reply["call"][0] if reply["call"] else None, "call_kind": reply["kind"],
                  "unknown": reply["unknown"], "malformed": reply["malformed"], "unclosed": reply["unclosed"],
                  "finish": finish, **usage})
        return out

    def log(self, rec: dict) -> None:
        line = json.dumps(rec)
        print(f"[shim] {line}", flush=True)
        if self.log_path:
            with self.lock, open(self.log_path, "a") as f:
                f.write(line + "\n")


def serve(shim: Shim, port: int) -> ThreadingHTTPServer:
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, code: int, obj: dict):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.rstrip("/").endswith("/models"):
                return self._send(200, {"object": "list", "data": [{"id": shim.model or "member", "object": "model"}]})
            return self._send(200 if self.path.startswith("/health") else 404, {})

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                req = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError as e:
                return self._send(400, {"error": {"message": str(e)}})
            if not self.path.rstrip("/").endswith("/chat/completions"):
                return self._send(404, {"error": {"message": f"the shim serves chat completions, not {self.path}"}})
            if req.get("stream"):
                return self._send(400, {"error": {"message": "the shim does not stream (τ² does not ask it to)"}})
            try:
                return self._send(200, shim.handle(req))
            except Exception as e:           # the server's reason, never a bare status (H2's lesson)
                print(f"[shim] ERROR {e!r}", flush=True)
                return self._send(502, {"error": {"message": repr(e)[:400]}})

    srv = ThreadingHTTPServer(("0.0.0.0", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--upstream", required=True, help="vLLM serving the member (its /v1/completions)")
    ap.add_argument("--base", required=True, help="the member's base, for its chat template")
    ap.add_argument("--model", default=None, help="the served name to ask vLLM for (default: the request's model)")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--member-prompt-file", default=None, help="prepended to τ²'s system prompt, never replacing it")
    ap.add_argument("--empty-thought", action="store_true", help="prefill an empty thought channel (larger Gemma 4)")
    ap.add_argument("--log", default=None)
    a = ap.parse_args()
    accept_rank.HOST = a.upstream.rstrip("/")
    mp = open(a.member_prompt_file).read().strip() if a.member_prompt_file else None
    shim = Shim(a.model, Renderer(a.base, a.empty_thought), member_prompt=mp, max_tokens=a.max_tokens, log_path=a.log)
    serve(shim, a.port)
    print(f"[shim] :{a.port} -> {a.upstream} · base {a.base} · max_tokens {a.max_tokens} · "
          f"member prompt {'prepended' if mp else 'none'} · no round-trip cap", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
