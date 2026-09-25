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

    POST /v1/chat/completions            the agent's request (Authorization: Bearer <token>)
    GET  /admin/approvals                a director's queue      POST /admin/approvals/<id>/approve|reject
    GET  /admin/handoffs                 requests queued for a person
    GET  /admin/dashboard                turns served locally / forwarded / handed off, tokens, the bill
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
from examples.school import roles as school_roles
from examples.school import tools as school_tools

SCOPE = ("Answer in the user's language, in one or two sentences, from what your tools returned. If a tool "
         "result says PENDING APPROVAL, tell the user it is waiting for a director. If the request is not "
         "something your tools cover, reply with exactly: OUT OF SCOPE")
OUT = "OUT OF SCOPE"
APPROVERS = {"director"}


class Gateway:
    def __init__(self, conn, generate, frontier=None, log_path=None, max_calls: int = 4):
        """`generate(system, user) -> (gen(prefix) -> text, used() -> {prompt_tokens, completion_tokens})`."""
        self.conn, self.generate, self.frontier, self.log_path, self.max_calls = conn, generate, frontier, log_path, max_calls
        self.queue, self.handoffs, self.events, self.lock = approvals.Queue(), [], [], threading.Lock()

    # ------------------------------------------------------------------ one request
    def turn(self, token: str, messages: list[dict], model: str = "auto") -> dict:
        from training.harness.accept_rank import run_chain
        from training.harness.openai_proxy import render_tools
        t0 = time.time()
        claim = tokens.verify(token)
        asked = model.split(":", 1)[1] if model.startswith("auto:") else None
        if asked and asked != claim.role:
            raise Denied(f"the token is a {claim.role}'s; the request asked to be served as {asked}")
        role = school_roles.ROLES.get(claim.role)
        if role is None:
            raise Denied(f"no agent role {claim.role!r} in this school")
        request = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        schema = [t for t in school_tools.SCHEMA if t["function"]["name"] in role["tools"]]
        user = render_tools([{"role": "user", "content": request}], schema)[-1]["content"]
        suite = ToolSuite(self.conn, claim, role["tools"], school_tools, self.queue)
        gen, used = self.generate(f"{role['system_prompt']} {SCOPE}", user, suite.close)
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
                return school_tools.answer(self.conn, c, tool, args)
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


def frontier_client(url: str, key: str, model: str):
    """A forwarded request, OpenAI-compatible. Only built when the operator configures one."""
    def ask(messages: list[dict]) -> str:
        req = urllib.request.Request(url.rstrip("/") + "/chat/completions", method="POST",
                                     data=json.dumps({"model": model, "messages": messages}).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
        return json.loads(urllib.request.urlopen(req, timeout=120).read())["choices"][0]["message"]["content"]
    return ask


# ------------------------------------------------------------------ HTTP
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

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"ok": True})
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
                    return self._send(200, {"object": "chat.completion", "model": body.get("model"),
                                            "choices": [{"index": 0, "finish_reason": "stop",
                                                         "message": {"role": "assistant", "content": out["reply"]}}],
                                            "x_route": out["route"], "x_calls": out["event"]["calls"]})
                return self._guard(run)
            self._send(404, {"error": "no route"})

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
