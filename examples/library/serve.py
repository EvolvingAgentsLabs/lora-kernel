r"""The real-document member as an OpenAI-compatible endpoint — what OpenClaw talks to (LIVE-library).

One request is one walk over a library, through the runtime REAL4 measured (`training/wiki/wiki_arm.py`'s `+page` arm):
the question's own words are the first search, over every shelf, with full-text search over the statements; an empty
search falls back to every shelf; a page opens with its statements' text; the member — `real-none-s0`, served by
llama.cpp — searches, opens, follows links and ends with one line: the answer and the statement it cites, or
`Not in my library.` The reply shows that line with the citation rendered as the page's title and anchor, and the
response carries the walk (`x_walk`) so a driver can grade the citation the way the measurement did.

    llama-server -m gemma-4-E4B-it-Q8_0.gguf --lora lora-real-none-s0-f16.gguf --port 8793 -c 12288 -b 512 -ub 512 -ngl 99   # 16,384 ran out of memory on a 16 GB Mac
    python -m examples.library.serve --library knowledge/logistics-regs --upstream http://127.0.0.1:8793 --port 8766
"""
from __future__ import annotations

import argparse
import json
import re
import threading
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CITE = re.compile(r"\[([a-z0-9]{3})§([a-z0-9][a-z0-9-]*)\]")
NO_ANSWER = "The library walk ended without an answer — try again or ask more narrowly."


def walk(lib, searcher, question: str, generate, page_budget: int | None = None) -> dict:
    """One question through the REAL4 runtime. `generate(system, user)` returns `gen(prefix) -> text`."""
    from memory import prompt
    from memory.runtime import ChainSuite, Conversation
    from training.harness.accept_rank import run_chain
    conv = Conversation(lib, seed=zlib.crc32(question.encode()), mode="strict", log_content=True, max_opens=24,
                        searcher=searcher, first_query=question, entry_all_shelves=True, fallback=True, page_text=True,
                        page_budget=page_budget)
    suite = ChainSuite(conv)
    chain = run_chain(suite.wrap(generate(prompt.SYSTEM_WIKI, prompt.user_text_wiki(question))), {}, max_calls=24, suite=suite)          # wiki_arm.MAX_CALLS, as measured
    final = (chain["spans"][-1]["text"] if chain["spans"] else "").strip()
    line = final.splitlines()[-1] if final else ""

    def human(m):
        nid = conv.shown.get(m.group(1))
        return f"[{lib[nid].title.split(' ', 1)[0]} §{m.group(2)}]" if nid else m.group(0)
    # a walk with no final line failed (context overflow, a dead upstream) — it is not a refusal, and the user is told so
    # [ran] LIVE-library: 6 of 51 walks, every one shown as `Not in my library.` until this line
    reply = CITE.sub(human, line) if line else NO_ANSWER
    return {"final": line, "reply": reply, "text": chain["text"],
            "shown": dict(conv.shown), "statements": [list(s) for s in conv.statements], "ended": conv.ended}


def llama_generator(tok, budget: int = 120):              # wiki_arm --max-tokens, as measured
    from training.harness.accept_rank import completion
    from memory.runtime import ChainSuite

    def generate(system: str, user: str):
        head = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                       tokenize=False, add_generation_prompt=True, enable_thinking=False)
        return lambda prefix: completion("member", head + prefix, budget, ChainSuite.close)
    return generate


def serve(lib, searcher, generate, port: int, log: str | None, page_budget: int | None = None):
    lock = threading.Lock()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body):
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"ok": True})
            if self.path == "/v1/models":
                return self._send(200, {"object": "list", "data": [{"id": "auto", "object": "model", "owned_by": "library"}]})
            self._send(404, {"error": "no route"})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                return self._send(404, {"error": "no route"})
            from examples.school.gateway import runtime_request
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            question = runtime_request(body.get("messages") or [])
            t0 = time.time()
            w = walk(lib, searcher, question, generate, page_budget)
            ev = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "question": question, "latency_s": round(time.time() - t0, 2), **w}
            if log:
                with lock, open(log, "a") as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            res = {"object": "chat.completion", "model": "auto", "x_walk": ev,
                   "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": w["reply"]}}]}
            if body.get("stream"):
                chunk = {"id": "chatcmpl-library", "object": "chat.completion.chunk", "created": int(time.time()), "model": "auto",
                         "choices": [{"index": 0, "delta": {"role": "assistant", "content": w["reply"]}, "finish_reason": "stop"}]}
                data = f"data: {json.dumps(chunk, ensure_ascii=False)}\n\ndata: [DONE]\n\n".encode()
                self.send_response(200); self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
                return
            self._send(200, res)

    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


OPENCLAW_PATCH = """{{
  models: {{ providers: {{ library: {{ baseUrl: "http://127.0.0.1:{port}/v1", api: "openai-completions", auth: "api-key",
    apiKey: "local", models: [ {{ id: "auto", name: "regulations library — real-none-s0" }} ] }} }} }},
  agents: {{ defaults: {{ model: "library/auto" }} }}
}}
"""


def main() -> int:
    import os
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--library", default="knowledge/logistics-regs")
    ap.add_argument("--upstream", required=True, help="llama-server serving the member")
    ap.add_argument("--tokenizer", default="google/gemma-4-E4B-it")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--log", default=None)
    ap.add_argument("--page-budget", type=int, default=2500,
                    help="a page over this many tokens opens with the question's best statements (0: whole, as REAL4)")
    ap.add_argument("--openclaw-patch", default=str(Path.home() / ".config/lora-kernel/openclaw/library-reader.json5"))
    a = ap.parse_args()
    os.environ["HF_HUB_OFFLINE"] = os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from examples.common import egress
    egress.install(egress.hosts_of(a.upstream), log=a.log)
    from memory.notes import Library
    from memory.runtime import FullText
    from training.harness import accept_rank
    from transformers import AutoTokenizer
    accept_rank.HOST = a.upstream.rstrip("/")
    lib = Library.load(a.library)
    serve(lib, FullText(lib), llama_generator(AutoTokenizer.from_pretrained(a.tokenizer)), a.port, a.log, a.page_budget or None)
    Path(a.openclaw_patch).parent.mkdir(parents=True, exist_ok=True)
    Path(a.openclaw_patch).write_text(OPENCLAW_PATCH.format(port=a.port))
    print(f"[library] {a.library} · {len(lib.notes)} pages · member at {a.upstream} · :{a.port} · egress closed · "
          f"page budget {a.page_budget or 'none'} · OpenClaw patch {a.openclaw_patch}", flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
