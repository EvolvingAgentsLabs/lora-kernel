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
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from training.harness.contract import validate
from training.harness.tool_calls import (
    CALL, from_tool_call, keep_offered, prune, rename_calls, stop_for,
                                         strip_calls, to_tool_calls,
                                         tools_to_instruction)

UPSTREAM = "http://127.0.0.1:8000"
ARITY = True          # P28: recovers 55% of the schema's cost, 0 domain lines
ENUMS = False         # P28: made it worse — not carried forward
LOG = None            # --log <path> records traffic for the null arm
KEY = None            # --api-key: required once this is reachable from outside
PASSTHROUGH = False   # --passthrough: forward untouched, log shapes only
UP_KEY = None         # --upstream-key: the credential the upstream itself wants
PRUNE = False         # --prune: offer a member only the tools it declares a tag for
# THE CORPUS-MODE LOOP HAS A CAP AND THE LIVE PATH HAD NONE. `accept_rank.run_chain`
# stops after `max_calls=6`; an agent runtime executes every call the model writes,
# and on the live turn for msg-014 the expert wrote `<thread_history>turns=2</…>`
# after its verdict, got an error back, and wrote it again — 30 round-trips, 71
# messages, until the turn was killed [ran] P63 attempt 5. Past the cap a call is
# returned as text and the agent finalises with what the model last said.
MAX_ROUNDTRIPS = 6
# AND A STEP IS SHORT. The corpus-mode loop asks for 160 tokens per completion
# (`accept_rank --max-tokens`): a member's step is a call or a verdict, never an
# essay. Unbounded, a 3B on an L4 spent three minutes per turn writing past its
# answer with nothing to stop at (P63 attempt 6 [ran]). A member is served with at
# most this many tokens per step; the agent's own limit applies when it is smaller.
MEMBER_MAX_TOKENS = 256
MEMBER_PROMPT = False # --member-prompt: serve a member under the system prompt its corpus taught
POOL_SYSTEM: dict[str, str] = {}

# --- the tool surface ------------------------------------------------------
#
# WHAT THIS DOES NOT DO, STILL. This module names no tool, no argument and no unit.
# The surface it prunes to is **the member's own declaration**, read out of
# `contract.py` — the same place the band it was trained on lives. The proxy learns
# which tags exist the way a router learns which depths are safe: by asking the
# adapter, not by knowing the domain.
#
# WHY IT IS OFF BY DEFAULT. Every measurement before today ran without it, and P27's
# 604/604 round trips used exact names where pruning is a no-op — but *this path has
# never been run against an agent*, and a behaviour change hidden inside an
# instrument is how a suite stops comparing to itself. `--prune` on and off is
# exactly the pair of arms the question needs.
POOL_SURFACE: dict[str, list[str]] = {}
POOL_ARGS: dict[str, dict] = {}


def _load_surfaces() -> dict[str, list[str]]:
    """`{served model name: its declared tags}`, from the pool registry.

    The registry keys adapters by directory (`adapters/email-full`) and vLLM serves
    them by basename (`email-full`), which is the name a client puts in `model`.
    A member that declares no surface is left out: silence is not a denial.
    """
    from training.harness.train_pool import POOL
    out = {}
    for path, record in POOL.items():
        rec = validate(path, record)
        sf = rec.get("surface")
        if sf is not None:
            name = path.rsplit("/", 1)[-1]
            out[name] = sf
            POOL_ARGS[name] = rec.get("surface_args") or {}
        if rec.get("system"):
            POOL_SYSTEM[path.rsplit("/", 1)[-1]] = rec["system"]
    return out


def under_member_prompt(messages: list[dict], system: str) -> list[dict]:
    """The runtime's system messages replaced by the member's released prompt.

    THE TOOL BLOCK IS PRUNED TO WHAT THE MEMBER TRAINED ON; THE PROMPT IS THE SAME
    PRINCIPLE ONE MESSAGE UP. What reaches the model is what its corpus taught — the
    runtime's instructions about its own channels, sandboxes and sub-agents are for a
    general agent, and a member routed a request in its region is not one."""
    rest = [m for m in messages if m.get("role") != "system"]
    return [{"role": "system", "content": system}] + rest

# --- routing ---------------------------------------------------------------
#
# WHAT THIS IS FOR. P41 measured that sending one failing subdomain to a frontier
# takes delivered accuracy from **0.546 to 0.775** **[ran]**, and P40 measured which
# subdomain fails. So the frontier stops being scaffolding and becomes the fallback
# for what the local pool is measured not to do.
#
# THE ROUTE IS BY MODEL NAME, WHICH IS THE CALLER'S OWN CHOICE. Nothing here infers
# a region: an agent asks for `email-full` and gets the local expert, asks for
# `gpt-...` and is forwarded. Per-case escalation is a different and unsolved
# problem — P41 measured both available rules delivering *less* than routing by
# region, because they look for a chain that is inconsistent and this expert's
# chains are consistent and wrong.
AUTO = None           # --auto: the alias a client asks for when it names no model
AUTO_OUT = None       # --auto-out: the frontier model an `auto` request becomes when it leaves
FALLBACK = None       # --fallback: where anything not served locally goes
FALLBACK_KEY = None   # read from an env var, never from the command line
LOCAL: set[str] = set()   # --local: the model names that must never leave


def resolve_auto(req: dict) -> tuple[str, str] | None:
    """Milestone 2: a request for the alias is routed by its text (`route.decide`).
    Returns the decision, and rewrites `model` in place — to the member if local, to
    `--auto-out` if it leaves. None when the request did not ask for the alias."""
    if not AUTO or req.get("model") != AUTO:
        return None
    from training.harness.route import decide
    d = decide(req)
    req["model"] = d[1] if d[0] == "local" else (AUTO_OUT or AUTO)
    print(f"[route] auto -> {d[0]} ({d[1]}) · {len(req.get('messages') or [])} messages · "
          f"{len(req.get('tools') or [])} tools", flush=True)
    return d


def routes_out(model: str | None) -> bool:
    """Does this request leave the machine? Local names never do."""
    if not FALLBACK or not model:
        return False
    return model not in LOCAL


def _join(base: str, path: str) -> str:
    """`base` + `path` with exactly one `/v1`.

    AN OPENAI-COMPATIBLE BASE URL IS CONVENTIONALLY WRITTEN WITH `/v1` — every
    client expects `https://api.openai.com/v1` — while the path the caller sends
    already carries `/v1/chat/completions`. Concatenating gave
    `…/api/v1/v1/chat/completions`, which OpenRouter answers with an HTML 404 page,
    and `docs/OPENCLAW.md` had been written with the doubled form in it
    **[ran]** 2026-09-15. The base keeps its own convention and this absorbs it.
    """
    base = base.rstrip("/")
    if base.endswith("/v1") and path.startswith("/v1/"):
        return base + path[len("/v1"):]
    return base + path


def _fetch(path: str, payload: dict | None, timeout: int = 600,
           base: str | None = None, key: str | None = None):
    headers = {"Content-Type": "application/json"}
    tok = key if base else UP_KEY
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(
        _join(base or UPSTREAM, path),
        method="POST" if payload is not None else "GET",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    return json.loads(body) if body.strip() else {}


def _announce(model: str, payload: dict) -> None:
    """One line per request that leaves, naming SHAPES and never content.

    A deployment routing real mail to a third party should be able to see what
    left without the transcript being printed into a log. `openclaw_traffic.py`
    holds the same line: shapes survive, content does not.
    """
    msgs = payload.get("messages") or []
    print(f"[route] OUT -> {model} · {len(msgs)} messages · "
          f"{sum(len(str(m.get('content') or '')) for m in msgs)} chars · "
          f"{len(payload.get('tools') or [])} tools", flush=True)


def rebuild_transcript(messages: list[dict], back: dict | None = None) -> list[dict]:
    """Fold an agent's `tool_calls` / `tool` results back into the tag transcript.

    THIS IS THE MULTI-TURN PATH AND IT IS UNMEASURED. An OpenAI client keeps the
    conversation as structured turns; the adapter was trained on one running
    transcript where a call is immediately followed by `= value`. So an assistant
    turn carrying `tool_calls` becomes its tags again, and each `role: "tool"` result
    becomes the `= value` that answers the tag above it.

    A result whose `tool_call_id` matches nothing is appended rather than dropped:
    losing a value the agent computed is worse than a transcript in an odd order.

    `back` maps the caller's tool names to the member's own tags. When the surface
    has been pruned, an earlier turn in the agent's history calls
    `mcp__lora-inbox__message` and the adapter is reading a transcript of
    `<message>` — folding the history under the caller's name would show the model
    its own past work in a vocabulary it does not have.
    """
    out, pending = [], {}
    for m in messages:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            text = m.get("content") or ""
            for tc in rename_calls(m["tool_calls"], back or {}):
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


def _record(req: dict, tools, up: dict, offered: int | None = None,
            prompt: str | None = None) -> None:
    """One line per request, for `training.harness.null_arm`.

    WHAT AN AGENT ACTUALLY ASKS FOR CANNOT BE GUESSED FROM A SUITE. Only the shapes
    are kept — which tools were offered, how deep the conversation was, and the
    reply's text, which is what the null arm reads to count well-formed calls. The
    prompt is not written down: it is the user's, and the measurement does not need
    it.
    """
    msg = ((up.get("choices") or [{}])[0].get("message") or {})
    with open(LOG, "a") as f:
        f.write(json.dumps({
            "model": req.get("model"),
            "tools": [((x.get("function") or x).get("name")) for x in (tools or [])],
            # HOW MANY WERE OFFERED AND HOW MANY SURVIVED. Two counts, because the
            # two failures they separate are different: an agent offering nothing
            # this member knows, and an agent offering fifty of which three landed.
            # P43 could not tell them apart from the outside.
            "tools_offered": len(tools or []) if offered is None else offered,
            "prompt": prompt,
            "turns": len(req.get("messages") or []),
            "reply": msg.get("content") or "",
            "upstream_tool_calls": len(msg.get("tool_calls") or []),
        }) + "\n")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_sse(self, up: dict):
        """One `chat.completion.chunk` carrying the whole reply, then `[DONE]`.

        The shape is what an OpenAI client parses; the content arrived all at once.
        `x_buffered` says so in the payload rather than only in a comment.
        """
        chunks = []
        for i, ch in enumerate(up.get("choices") or [{}]):
            m = ch.get("message") or {}
            delta = {"role": m.get("role", "assistant")}
            if m.get("content") is not None:
                delta["content"] = m["content"]
            if m.get("tool_calls"):
                delta["tool_calls"] = [
                    {**tc, "index": j} for j, tc in enumerate(m["tool_calls"])]
            chunks.append({"index": ch.get("index", i), "delta": delta,
                           "finish_reason": ch.get("finish_reason", "stop")})
        body = {"id": up.get("id", "chatcmpl-buffered"),
                "object": "chat.completion.chunk",
                "created": up.get("created", int(time.time())),
                "model": up.get("model", ""),
                "x_buffered": True,
                "choices": chunks}
        payload = (f"data: {json.dumps(body)}\n\n" "data: [DONE]\n\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

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
        if not self._authorised():
            return self._send(401, {"error": {"message": "unauthorised"}})
        try:
            self._send(200, _fetch(self.path, None, timeout=30))
        except Exception as e:
            self._send(502, {"error": {"message": repr(e)}})

    def _authorised(self) -> bool:
        """ONCE THIS IS REACHABLE FROM OUTSIDE, IT NEEDS A DOOR. A tunnel turns a
        localhost proxy into a public inference endpoint, and an open one is
        somebody else's free GPU. The key is compared in constant time so the
        comparison itself does not leak its length."""
        if not KEY:
            return True
        import hmac
        got = (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
        return hmac.compare_digest(got, KEY)

    def do_POST(self):
        if not self._authorised():
            return self._send(401, {"error": {"message": "unauthorised"}})
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

        # ROUTED OUT BEFORE ANY TRANSLATION. The tag surface exists because the
        # local adapters were trained on it; a frontier model speaks `tools=[…]`
        # natively and rendering tags at it would hand it our convention to learn.
        auto = resolve_auto(req)
        if auto and auto[0] == "out" and not FALLBACK:
            # WOULD LEAVE, AND THERE IS NOWHERE TO GO. Said in the reply and in the
            # log, shapes only — never silently served by a member outside its region.
            return self._send(503, {"error": {"message": f"routed out ({auto[1]}) and no "
                                              "--fallback is configured"}})
        if routes_out(req.get("model")) or (auto and auto[0] == "out"):
            _announce(req.get("model"), req)
            try:
                return self._send(200, _fetch(self.path, req, base=FALLBACK,
                                              key=FALLBACK_KEY))
            except urllib.error.HTTPError as e:
                return self._send(e.code, {"error": {"message": e.read()[:400].decode(
                    "utf-8", "replace")}})
            except Exception as e:
                return self._send(502, {"error": {"message": repr(e)}})

        if PASSTHROUGH:
            # MEASURE BEFORE BUILDING. In this mode nothing is translated: the
            # request goes upstream exactly as it arrived and the reply comes back
            # untouched. What it buys is the traffic — the shapes an agent actually
            # sends — which is the input the null arm needs and which no suite can
            # guess. It lets a deployment be measured while it keeps working.
            try:
                up = _fetch(self.path, req)
            except urllib.error.HTTPError as e:
                return self._send(e.code, {"error": {"message": e.read()[:400].decode(
                    "utf-8", "replace")}})
            except Exception as e:
                return self._send(502, {"error": {"message": repr(e)}})
            if LOG:
                _record(req, req.get("tools"), up)
            return self._send(200, up)

        tools = req.pop("tools", None)
        req.pop("tool_choice", None)
        # PRUNE BEFORE RENDERING, so the block the adapter reads carries its own tag
        # names and nothing else. `forward` puts the caller's names back on the way
        # out; `back` rewrites the history on the way in.
        offered, forward, back = len(tools or []), {}, {}
        surface = POOL_SURFACE.get(req.get("model")) if PRUNE else None
        if surface is not None and tools:
            tools, forward, back = prune(tools, surface, POOL_ARGS.get(req.get("model")))
        # STREAMING IS BUFFERED, AND SAYING SO IS WHAT KEEPS IT HONEST.
        #
        # A tag only becomes a `tool_call` once its closing tag has arrived, so this
        # proxy cannot emit tool calls incrementally. It used to refuse `stream`
        # outright — "refuse rather than fake" — and that was right while the
        # alternative was a misleading measurement. It is wrong here: **OpenClaw
        # streams by default and its per-model `streaming: false` did not take**, so
        # refusing made the whole pool unusable by a real agent runtime **[ran]**
        # 2026-09-15. Being unusable is the worse failure.
        #
        # So the reply is fetched whole and delivered as one SSE chunk. A client
        # that asked for a stream gets valid SSE and a correct answer; what it does
        # not get is incremental delivery, which is a latency property and not a
        # correctness one. Every chunk carries `x_buffered: true` so nobody reads
        # token-by-token streaming into a reply that arrived all at once.
        streaming = bool(req.pop("stream", False))
        req.pop("stream_options", None)
        msgs = rebuild_transcript(req.get("messages") or [], back)
        prompt_kind = "runtime"
        if MEMBER_PROMPT and POOL_SYSTEM.get(req.get("model")):
            msgs = under_member_prompt(msgs, POOL_SYSTEM[req["model"]])
            prompt_kind = "member"
        req["messages"] = render_tools(msgs, tools) if tools else msgs
        if surface is not None:
            asked = req.get("max_tokens") or req.get("max_completion_tokens")
            req["max_tokens"] = min(int(asked), MEMBER_MAX_TOKENS) if asked else MEMBER_MAX_TOKENS
            req.pop("max_completion_tokens", None)
        if tools:
            # THE BLOCK'S HEADER IS A STOP SEQUENCE (tool_calls.stop_for): a model
            # that starts reproducing the block it was shown has finished answering.
            stop = req.get("stop")
            stop = [stop] if isinstance(stop, str) else list(stop or [])
            kept_names = [((x.get("function") or x).get("name")) for x in tools]
            req["stop"] = stop + [s_ for s_ in stop_for(tools, kept_names) if s_ not in stop]
            req["include_stop_str_in_output"] = True

        try:
            up = _fetch("/v1/chat/completions", req)
        except urllib.error.HTTPError as e:
            return self._send(e.code, {"error": {"message": e.read()[:400].decode(
                "utf-8", "replace")}})
        except Exception as e:
            return self._send(502, {"error": {"message": repr(e)}})

        if LOG:
            _record(req, tools, up, offered=offered, prompt=prompt_kind)

        roundtrips = sum(1 for m in (req.get("messages") or []) if m.get("role") == "tool")
        for choice in up.get("choices", []):
            msg = choice.get("message") or {}
            text = msg.get("content") or ""
            if tools and CALL.search(text) and roundtrips >= MAX_ROUNDTRIPS:
                print(f"[prune] round-trip cap {MAX_ROUNDTRIPS} reached; the call is returned as text", flush=True)
                msg["content"] = strip_calls(text) or text
                continue
            if tools and CALL.search(text):
                calls, dropped = keep_offered(
                    to_tool_calls(text), {((x.get("function") or x).get("name")) for x in tools})
                if dropped:
                    print(f"[prune] {dropped} call(s) to names not offered left as text", flush=True)
                calls = rename_calls(calls, forward)
                if not calls:
                    continue
                msg["tool_calls"] = calls
                msg["content"] = strip_calls(text) or None
                choice["finish_reason"] = "tool_calls"
        if streaming:
            return self._send_sse(up)
        return self._send(200, up)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream", default=UPSTREAM)
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--api-key", dest="api_key", default=None,
                    help="require this bearer token; set it whenever the proxy is "
                         "reachable from outside localhost")
    ap.add_argument("--upstream-key", dest="upstream_key", default=None,
                    help="bearer token the upstream itself requires")
    ap.add_argument("--passthrough", action="store_true",
                    help="translate nothing; forward and log shapes. Use this to "
                         "measure a deployment while it keeps working")
    ap.add_argument("--log", default=None,
                    help="append one line per request, for training.harness.null_arm")
    ap.add_argument("--enums", action="store_true",
                    help="P28 measured this as harmful; off unless asked")
    ap.add_argument("--prune", action="store_true",
                    help="offer each pool member only the tools it declares a tag "
                         "for, matching an exact name or the last namespace segment "
                         "of one. P43's agent turn made zero tool calls because it "
                         "was offered a toolbox this expert had never seen")
    ap.add_argument("--member-prompt", dest="member_prompt", action="store_true",
                    help="serve a member under the system prompt its corpus taught (contract `system`)")
    ap.add_argument("--auto", default=None,
                    help="model alias routed per request by its text (milestone 2)")
    ap.add_argument("--auto-out", dest="auto_out", default=None,
                    help="the frontier model an `auto` request becomes when it leaves")
    ap.add_argument("--fallback", default=None,
                    help="where a model this pool does not serve is forwarded, "
                         "e.g. https://api.openai.com/v1. Requests routed here "
                         "LEAVE THE MACHINE")
    ap.add_argument("--fallback-key-env", dest="fallback_key_env",
                    default="OPENAI_API_KEY",
                    help="env var holding the fallback credential. Never pass a key "
                         "on the command line: it lands in `ps` and in shell history")
    ap.add_argument("--local", default=None,
                    help="comma-separated model names that must never leave; "
                         "defaults to whatever the upstream lists at /v1/models")
    args = ap.parse_args()
    globals()["UPSTREAM"] = args.upstream
    globals()["FALLBACK"] = args.fallback
    globals()["AUTO"], globals()["AUTO_OUT"] = args.auto, args.auto_out
    globals()["MEMBER_PROMPT"] = args.member_prompt
    if args.auto:
        from training.harness.route import REGIONS
        print(f"[route] `{args.auto}` is routed per request: "
              + ", ".join(f"{n} -> {r.serve}" for n, r in REGIONS.items())
              + (f"; out becomes {args.auto_out}" if args.auto_out else ""), flush=True)
    if args.fallback:
        import os
        key = os.environ.get(args.fallback_key_env)
        if not key:
            # A FALLBACK WITHOUT A CREDENTIAL FAILS ON THE FIRST ESCALATION, which
            # is the worst moment to find out. It fails here instead.
            print(f"--fallback is set but ${args.fallback_key_env} is empty; "
                  "refusing to start with a route that cannot work")
            return 2
        globals()["FALLBACK_KEY"] = key
        if args.local:
            local = {n.strip() for n in args.local.split(",") if n.strip()}
        else:
            # WHAT THE POOL SERVES IS WHAT STAYS. Asking the upstream is better than
            # a hand-kept list, which drifts the moment an adapter is added.
            try:
                local = {m["id"] for m in
                         _fetch("/v1/models", None, timeout=30).get("data", [])}
            except Exception as e:
                print(f"cannot list the local models ({e!r}); "
                      "pass --local explicitly rather than guessing what stays")
                return 2
        globals()["LOCAL"] = local
        print(f"[proxy] local, never leaves: {sorted(local)}")
        print(f"[proxy] everything else -> {args.fallback} "
              f"(key from ${args.fallback_key_env})")
    globals()["ENUMS"] = args.enums
    globals()["PRUNE"] = args.prune
    if args.prune:
        globals()["POOL_SURFACE"] = _load_surfaces()
    if args.member_prompt:
        if not PRUNE:
            _load_surfaces()          # the contract is read on the same pass
        print(("[prompt] members served under their released prompt: " + ", ".join(sorted(POOL_SYSTEM)))
              if POOL_SYSTEM else "[prompt] --member-prompt set but no member declares a system prompt", flush=True)
        # ANNOUNCED, BECAUSE IT CHANGES WHAT THE MODEL SEES. A filter nobody can see
        # from outside is the kind that gets blamed on the weights later.
        for name, sf in sorted(POOL_SURFACE.items()):
            print(f"[prune] {name}: {sf or 'no tools — declares none'}")
        print("[prune] a model not listed above is offered every tool, unpruned")
    globals()["LOG"] = args.log
    globals()["KEY"] = args.api_key
    globals()["UP_KEY"] = args.upstream_key
    globals()["PASSTHROUGH"] = args.passthrough
    if args.api_key is None and args.passthrough:
        print("[proxy] WARNING: no --api-key. Do not expose this.", flush=True)

    print(f"[proxy] :{args.port} -> {args.upstream}  "
          f"{'passthrough' if args.passthrough else f'arity={ARITY} enums={args.enums}'}"
          f"  auth={'on' if args.api_key else 'OFF'}  log={args.log or 'off'}",
          flush=True)
    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
