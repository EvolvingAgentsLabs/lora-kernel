"""The school's gateway — one OpenAI-compatible endpoint in front of a small local model (docs/DEMO.md).

Where it sits in an agent system like the reference one: the agent runtime (OpenClaw, one agent per
role) points its model setting here; identity, the tenant database, payments and monitoring stay what
they are. What happens to one request:

    1  WHO    the bearer token is verified (examples/common/tokens.py, standing in for the identity
              provider) → a Claim: user, role, tenant. The role in `model: auto:<role>` must match it
    2  TURN   the role's own prompt and tools (examples/school/roles.py) on the LOCAL model; tools run
              in the tool layer with the Claim — another tenant's row is refused there, whatever the
              model wrote; `billing_charge` and `announcement_post` are HELD for a director
    3  SCOPE  a request the role's tools do not cover is answered `OUT OF SCOPE` by the model, and
              then the role's own egress policy decides: `frontier` forwards it (if one is configured),
              `person` queues it for staff. **The model's scope judgment is not a measured router** —
              the demo records how often it is right, and says so
    4  LOG    one JSON line per request (examples/school/events.jsonl), the monitoring feed: who, role,
              route, tools, denials, holds, tokens, latency — and the frontier price those tokens would
              have cost (training/harness/bill.py rates); the local GPU's cost is not priced

    POST /v1/chat/completions            the agent's request (Authorization: Bearer <token>); `stream: true` gets
                                         valid SSE, buffered — a runtime that streams by default (OpenClaw) is served
    GET  /v1/models                      one model, `auto`: the role is the token's, never the model id's
    GET  /admin/approvals                a director's queue      POST /admin/approvals/<id>/approve|reject
    GET  /admin/handoffs                 requests queued for a person
    GET  /admin/dashboard                turns served locally / forwarded / handed off, tokens, the bill

LIVE (2026-09-26): `python -m examples.school.gateway --upstream <vLLM URL> --member school-s0` serves this over HTTP
for a real agent runtime — the model on a rented card (training/harness/serve_tunnel.py), the gateway, the tools and
the store here; `--frontier-url/--frontier-model/--frontier-key-env` make the `frontier` egress real (the key is read
from the environment, never from a flag). It writes one OpenClaw config patch per role, each carrying that role's
signed token as the provider key (`--openclaw-dir`).
"""
from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from examples.common import approvals, tokens
from examples.common import grounding as grounding_mod
from examples.common.agent_loop import ToolSuite
from examples.common.permissions import Denied

# ONE GATEWAY, ONE ORGANISATION PER PROCESS (2026-09-28). The school and the distributor share the shape — roles, tools,
# a store, seed users — but not the prompt their members were trained on: the school's corpus ends the role's prompt
# with SCOPE and teaches `OUT OF SCOPE`; the distributor's (examples/distributor/generate_turns.py) is the role's prompt
# alone and never abstains, and runs its writes without a director's approval, as training/harness/demo_org.scene does.
# A member is served the way its corpus taught it (CLAUDE.md §3), so the organisation carries those two switches.
ORGS = {"school": {"package": "examples.school", "scope": True, "approvals": True, "provider": "schoolgw"},
        "distributor": {"package": "examples.distributor", "scope": False, "approvals": False, "provider": "distgw"}}


def org_modules(org: str) -> dict:
    import importlib
    pkg = ORGS[org]["package"]
    return {m: importlib.import_module(f"{pkg}.{m}") for m in ("roles", "tools", "db", "users")}

SCOPE = ("Answer in the user's language, in one or two sentences, from what your tools returned. If a tool "
         "result says PENDING APPROVAL, tell the user it is waiting for a director. If the request is not "
         "something your tools cover, reply with exactly: OUT OF SCOPE")
OUT = "OUT OF SCOPE"
APPROVERS = {"director"}


def _text(content) -> str:
    """A message's text, whether a string or a list of parts ({"type": "text", "text": ...}) as runtimes send it."""
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") in ("text", "input_text"))
    return content or ""


_RUNTIME_CONTEXT = re.compile(r"<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>.*?<<<END_OPENCLAW_INTERNAL_CONTEXT>>>", re.S)
_STAMP = re.compile(r"^\[[A-Z][a-z]{2} \d{4}-\d{2}-\d{2} \d{2}:\d{2}[^\]]*\]\s*")
_RUNTIME_FOOTER = re.compile(r"\n+Runtime: agent=.*\Z", re.S)


def runtime_request(messages: list[dict]) -> str:
    """The person's request, out of what a live runtime sends. OpenClaw [ran] 2026-09-26 appends a user message of its
    own internal context AFTER the request, stamps the request `[Sat 2026-09-26 20:41 GMT-3] …` and may add a
    `Runtime: agent=…` footer; the first version of this gateway took the last user message and read the context."""
    for m in reversed(messages):
        if m.get("role") != "user":
            continue
        text = _RUNTIME_FOOTER.sub("", _STAMP.sub("", _RUNTIME_CONTEXT.sub("", _text(m.get("content"))).strip())).strip()
        if text:
            return text
    return ""


class Gateway:
    def __init__(self, conn, generate, frontier=None, log_path=None, max_calls: int = 4, org: str = "school"):
        """`generate(system, user) -> (gen(prefix) -> text, used() -> {prompt_tokens, completion_tokens})`."""
        self.conn, self.generate, self.frontier, self.log_path, self.max_calls = conn, generate, frontier, log_path, max_calls
        self.org, mods = org, org_modules(org)
        self.roles, self.tools = mods["roles"], mods["tools"]
        self.queue = approvals.Queue() if ORGS[org]["approvals"] else None
        self.handoffs, self.events, self.lock = [], [], threading.Lock()

    # ------------------------------------------------------------------ one request
    def turn(self, token: str, messages: list[dict], model: str = "auto") -> dict:
        from training.harness.accept_rank import run_chain
        from training.harness.openai_proxy import render_tools
        t0 = time.time()
        claim = tokens.verify(token)
        asked = model.split(":", 1)[1] if model.startswith("auto:") else None
        if asked and asked != claim.role:
            raise Denied(f"the token is a {claim.role}'s; the request asked to be served as {asked}")
        role = self.roles.ROLES.get(claim.role)
        if role is None:
            raise Denied(f"no agent role {claim.role!r} in this {self.org}")
        request = runtime_request(messages)
        schema = [t for t in self.tools.SCHEMA if t["function"]["name"] in role["tools"]]
        user = render_tools([{"role": "user", "content": request}], schema)[-1]["content"]
        suite = ToolSuite(self.conn, claim, role["tools"], self.tools, self.queue)
        system = f"{role['system_prompt']} {SCOPE}" if ORGS[self.org]["scope"] else role["system_prompt"]
        gen, used = self.generate(system, user, suite.close)
        chain = run_chain(gen, {}, max_calls=self.max_calls, suite=suite)
        final = (chain["spans"][-1]["text"] if chain["spans"] else "").strip()
        route, reply = "local", final
        if OUT in final.upper():
            if role["egress"] == "frontier":
                route = "frontier"
                reply = self.frontier(messages) if self.frontier else \
                    "Forwarded to the frontier model (not configured in this demo, so nothing left the building)."
            else:
                route = "person"
                with self.lock:
                    self.handoffs.append({"id": len(self.handoffs) + 1, "user": claim.user_id, "org": claim.org_id, "request": request})
                reply = "This needs a member of staff; it has been passed to a person."
        grounding = "no_result"
        if route == "local":
            # WHAT THE REPLY MAY STATE IS DECIDED HERE, NOT BY THE MODEL (examples/common/grounding.py): an item
            # that is in no real tool result replaces the reply with the tools' own text; instruction-shaped
            # text found in a record is removed from what is shown.
            spanish = bool(re.search(r"[¿¡áéíóúñ]", request)) or request.split(" ", 1)[0].lower().endswith(("á", "ame", "é"))
            reply, grounding = grounding_mod.ground(reply, [c["result"] for c in suite.calls if "result" in c], spanish)
            reply = grounding_mod.redact(reply)
        ev = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "user": claim.user_id, "role": claim.role, "org": claim.org_id,
              "route": route, "grounding": grounding, "calls": suite.calls, "denied": sum("denied" in c for c in suite.calls),
              "held": sum("held" in c for c in suite.calls), "latency_s": round(time.time() - t0, 2), **used()}
        with self.lock:
            self.events.append(ev)
            if self.log_path:
                with open(self.log_path, "a") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        return {"reply": reply, "route": route, "walk": chain["text"], "event": ev}

    # ------------------------------------------------------------------ a person's side
    def _director(self, token: str):
        claim = tokens.verify(token)
        if claim.role not in APPROVERS:
            raise Denied(f"a {claim.role} does not decide approvals")
        return claim

    def approve(self, token: str, item_id: int) -> str:
        claim = self._director(token)
        from examples.common.agent_loop import DB_LOCK

        def execute(c, tool, args):
            with DB_LOCK:
                return self.tools.answer(self.conn, c, tool, args)
        return self.queue.approve(item_id, claim, execute)

    def reject(self, token: str, item_id: int) -> None:
        self.queue.reject(item_id, self._director(token))

    def pending(self, token: str) -> list[dict]:
        claim = self._director(token)
        return [{"id": i["id"], "tool": i["tool"], "args": i["args"], "requested_by": i["requested_by"].user_id}
                for i in self.queue.pending(claim)]

    def dashboard(self, token: str) -> dict:
        from training.harness.bill import INPUT_RATE, OUTPUT_RATE
        claim = self._director(token)
        evs = [e for e in self.events if e["org"] == claim.org_id]
        local = [e for e in evs if e["route"] == "local"]
        p, c = sum(e.get("prompt_tokens", 0) for e in local), sum(e.get("completion_tokens", 0) for e in local)
        return {"org": claim.org_id, "turns": len(evs), "served_locally": len(local),
                "to_frontier": sum(e["route"] == "frontier" for e in evs), "to_a_person": sum(e["route"] == "person" for e in evs),
                "denied_calls": sum(e["denied"] for e in evs), "held_for_approval": sum(e["held"] for e in evs),
                "replies_replaced_by_the_tools_text": sum(e.get("grounding") == "replaced" for e in evs),
                "local_tokens": {"prompt": p, "completion": c},
                "frontier_cost_avoided_usd": round(p * INPUT_RATE + c * OUTPUT_RATE, 6),
                "not_priced": "the local GPU's own cost"}


def vllm_generator(model: str, tok, max_tokens: int = 160):
    """`Gateway`'s `generate`, over an OpenAI-compatible completions server (vLLM, or the fake)."""
    from training.harness.accept_rank import completion

    def generate(system: str, user: str, close: tuple):
        head = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)
        used = {"prompt_tokens": 0, "completion_tokens": 0}

        def gen(prefix: str) -> str:
            text = completion(model, head + prefix, max_tokens, close)
            used["prompt_tokens"] += len(tok(head + prefix)["input_ids"])
            used["completion_tokens"] += len(tok(text)["input_ids"])
            return text
        return gen, lambda: dict(used)
    return generate


def frontier_client(url: str, key: str, model: str, budget_usd: float | None = None, rates: tuple = (0.0, 0.0)):
    """A forwarded request, OpenAI-compatible. Only built when the operator configures one. With `budget_usd`, each
    call's real usage is priced at `rates` ($ per million input, output tokens) and nothing more is forwarded once the
    spend reaches the budget — the reply says so instead."""
    spent = {"usd": 0.0, "calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def ask(messages: list[dict]) -> str:
        if budget_usd is not None and spent["usd"] >= budget_usd:
            return f"The frontier budget (${budget_usd:.2f}) is spent; this request was not forwarded."
        req = urllib.request.Request(url.rstrip("/") + "/chat/completions", method="POST",
                                     data=json.dumps({"model": model, "messages": messages}).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        out = json.loads(urllib.request.urlopen(req, timeout=120).read())
        u = out.get("usage") or {}
        spent["calls"] += 1
        spent["prompt_tokens"] += u.get("prompt_tokens", 0)
        spent["completion_tokens"] += u.get("completion_tokens", 0)
        spent["usd"] = round((spent["prompt_tokens"] * rates[0] + spent["completion_tokens"] * rates[1]) / 1e6, 6)
        print(f"[frontier] call {spent['calls']} · {u.get('prompt_tokens')}+{u.get('completion_tokens')} tokens · "
              f"${spent['usd']:.4f} spent" + (f" of ${budget_usd:.2f}" if budget_usd is not None else ""), flush=True)
        return out["choices"][0]["message"]["content"]
    ask.spent = spent
    return ask


def serve(gw: Gateway, port: int = 8765) -> ThreadingHTTPServer:
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code: int, body) -> None:
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        def _token(self) -> str:
            return (self.headers.get("Authorization") or "").removeprefix("Bearer ").strip()

        def _guard(self, fn):
            try:
                return fn()
            except (tokens.InvalidToken,) as e:
                return self._send(401, {"error": str(e)})
            except Denied as e:
                return self._send(403, {"error": str(e)})
            except KeyError as e:
                return self._send(404, {"error": str(e)})

        def _sse(self, body: dict) -> None:
            # BUFFERED SSE, as training/harness/openai_proxy.py serves it [ran] P63: the reply is decided whole — the
            # grounding filter needs all of it — so one chunk carries it, then [DONE].
            ch = body["choices"][0]
            chunk = {"id": "chatcmpl-gateway", "object": "chat.completion.chunk", "created": int(time.time()),
                     "model": body.get("model") or "auto", "x_route": body.get("x_route"),
                     "choices": [{"index": 0, "delta": {"role": "assistant", "content": ch["message"]["content"]},
                                  "finish_reason": "stop"}]}
            data = (f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n" "data: [DONE]\n\n").encode()
            self.send_response(200); self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache"); self.send_header("Content-Length", str(len(data)))
            self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"ok": True})
            if self.path == "/v1/models":
                return self._send(200, {"object": "list", "data": [{"id": "auto", "object": "model", "owned_by": "gateway"}]})
            if self.path == "/admin/approvals":
                return self._guard(lambda: self._send(200, gw.pending(self._token())))
            if self.path == "/admin/handoffs":
                return self._guard(lambda: (gw._director(self._token()), self._send(200, gw.handoffs))[1])
            if self.path == "/admin/dashboard":
                return self._guard(lambda: self._send(200, gw.dashboard(self._token())))
            self._send(404, {"error": "no route"})

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            m = re.fullmatch(r"/admin/approvals/(\d+)/(approve|reject)", self.path)
            if m:
                i = int(m.group(1))
                if m.group(2) == "approve":
                    return self._guard(lambda: self._send(200, {"result": gw.approve(self._token(), i)}))
                return self._guard(lambda: (gw.reject(self._token(), i), self._send(200, {"rejected": i}))[1])
            if self.path == "/v1/chat/completions":
                def run():
                    out = gw.turn(self._token(), body.get("messages") or [], body.get("model") or "auto")
                    res = {"object": "chat.completion", "model": body.get("model"),
                           "choices": [{"index": 0, "finish_reason": "stop",
                                        "message": {"role": "assistant", "content": out["reply"]}}],
                           "x_route": out["route"], "x_calls": out["event"]["calls"]}
                    return self._sse(res) if body.get("stream") else self._send(200, res)
                return self._guard(run)
            self._send(404, {"error": "no route"})

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


OPENCLAW_PATCH = """{{
  models: {{ providers: {{ {prov}: {{ baseUrl: "http://127.0.0.1:{port}/v1", api: "openai-completions", auth: "api-key",
    apiKey: "{token}", models: [ {{ id: "auto", name: "{org} gateway — {user}" }} ] }} }} }},
  agents: {{ defaults: {{ model: "{prov}/auto" }} }}
}}
"""


def main() -> int:
    import argparse
    import os
    from pathlib import Path
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--upstream", required=True, help="an OpenAI-compatible completions server serving the member (vLLM)")
    ap.add_argument("--org", default="school", choices=sorted(ORGS), help="which organisation this gateway serves")
    ap.add_argument("--member", default="school-s0", help="the served name of the organisation's staff adapter")
    ap.add_argument("--tokenizer", default=None, help="the base's tokenizer (defaults to family.SMALL); only its chat template")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--frontier-url", default=None, help="e.g. https://api.openai.com/v1 — the `frontier` egress, made real")
    ap.add_argument("--frontier-model", default=None)
    ap.add_argument("--frontier-key-env", default="FRONTIER_API_KEY", help="the env var holding the frontier key")
    ap.add_argument("--frontier-budget-usd", type=float, default=None, help="stop forwarding once this much is spent")
    ap.add_argument("--frontier-rates", default="0,0", help="$ per million input,output tokens, to price each call")
    ap.add_argument("--log", default=None, help="default: examples/<org>/events.jsonl")
    ap.add_argument("--openclaw-dir", default=str(Path.home() / ".config/lora-kernel/openclaw"))
    a = ap.parse_args()
    from training.harness import accept_rank
    from training.harness.family import SMALL
    from transformers import AutoTokenizer
    accept_rank.HOST = a.upstream.rstrip("/")
    tok = AutoTokenizer.from_pretrained(a.tokenizer or SMALL)
    frontier = None
    if a.frontier_url:
        key = os.environ.get(a.frontier_key_env)
        if not key or not a.frontier_model:
            print(f"[gateway] --frontier-url needs --frontier-model and ${a.frontier_key_env} set", flush=True)
            return 2
        frontier = frontier_client(a.frontier_url, key, a.frontier_model, a.frontier_budget_usd,
                                   tuple(float(x) for x in a.frontier_rates.split(",")))
    mods = org_modules(a.org)
    db, users = mods["db"], mods["users"]
    users.register_all()
    gw = Gateway(db.build(), vllm_generator(a.member, tok), frontier=frontier, log_path=a.log or f"examples/{a.org}/events.jsonl",
                 org=a.org)
    serve(gw, a.port)
    out = Path(a.openclaw_dir); out.mkdir(parents=True, exist_ok=True)
    for user_id, role, org in users.SEED_USERS:
        (out / f"{user_id}.json5").write_text(OPENCLAW_PATCH.format(port=a.port, token=tokens.issue(user_id, role, org, ttl=12 * 3600),
                                                                    user=user_id, prov=ORGS[a.org]["provider"], org=a.org))
    if a.org == "school":
        (out / "director-north.token").write_text(tokens.issue("director-north", "director", "northgate", ttl=12 * 3600))
    print(f"[gateway] {a.org} :{a.port} · model {a.member} at {a.upstream} · frontier "
          f"{a.frontier_model + ' at ' + a.frontier_url if frontier else 'NOT configured (frontier-egress roles say so)'}", flush=True)
    print(f"[gateway] one OpenClaw patch per user in {out} (each carries that user's signed token)", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
