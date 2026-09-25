r"""A fake `vllm serve` — the serving path's integration test, zero GPU, no model, no download.

WHY IT EXISTS. On 2026-09-24/25 three scoring sessions of W9 were lost, none to the model: a repeated
`--lora-modules` flag that vLLM 0.30 reads as a duplicate key (only the last adapter loaded); arms that
asked for an adapter's PATH where vLLM serves its NAME (134 × 404 behind a G1 that had passed); and a
chain that kept polling after the runner died **[ran]** results/M7-W9-atomic-statements-20260924. Each
is an integration bug a server that behaves like vLLM at its edges would have caught on the Mac, before
a card was bought. This is that server — and nothing more: it models vLLM's *interface*, never a
model's behaviour.

WHAT IT REPRODUCES, each observed on a real vLLM 0.30 log, never assumed:

    the command line     `vllm serve MODEL --port P [--enable-lora --lora-modules a=x b=y ...]`; a
                         SECOND `--lora-modules` REPLACES the first (vLLM: "Found duplicate keys
                         --lora-modules" — the last list wins)
    /health              200 once up
    /v1/models           the base and every LoRA NAME it registered
    /v1/completions      404 for a model it does not serve (a path is not a name); `stop` honoured,
                         the stop string kept when `include_stop_str_in_output`
    a member's text      differs from the base's on the same prompt, so G1 has something to see; an
                         adapter that was NOT registered can never be asked for, which is the point

    with fake_vllm.patched(responder):      # accept_rank.serve/HOST now point at the fake
        runner_main()

`responder(model, prompt) -> text` is the test's scripted model; the default answers
`Not in my library.`, which drives every walking runner to a clean, graded, wrong answer.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def parse_serve(cmd: list[str]) -> dict:
    """`vllm serve …` → {"base", "port", "loras": {name: path}}, with vLLM 0.30's duplicate-key rule."""
    if cmd[:2] != ["vllm", "serve"]:
        raise ValueError(f"not a vllm serve command: {cmd[:3]}")
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("model")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--enable-lora", action="store_true")
    # nargs="+" with the default "store" action: a repeated flag REPLACES the earlier list — the
    # behaviour vLLM 0.30 logged as "Found duplicate keys --lora-modules" and served accordingly
    ap.add_argument("--lora-modules", nargs="+", default=[])
    a, _ = ap.parse_known_args(cmd[2:])
    loras = {}
    for spec in a.lora_modules:
        name, eq, path = spec.partition("=")
        if not eq:
            raise ValueError(f"a --lora-modules entry is name=path, got {spec!r}")
        loras[name] = path
    if loras and not a.enable_lora:
        raise ValueError("--lora-modules without --enable-lora")
    return {"base": a.model, "port": a.port, "loras": loras}


def default_responder(model: str, prompt: str) -> str:
    return "Not in my library."


class _Handler(BaseHTTPRequestHandler):
    server_version = "fake-vllm/0.30"

    def log_message(self, *args):          # quiet: a test reads records, not an access log
        pass

    def _send(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        s = self.server.spec
        if self.path == "/health":
            return self._send(200, {})
        if self.path == "/v1/models":
            return self._send(200, {"data": [{"id": m} for m in [s["base"], *s["loras"]]]})
        self._send(404, {"error": "no route"})

    def do_POST(self):
        s = self.server.spec
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path != "/v1/completions":
            return self._send(404, {"error": "no route"})
        model = body.get("model")
        if model != s["base"] and model not in s["loras"]:
            self.server.refused.append(model)
            return self._send(404, {"error": {"message": f"The model `{model}` does not exist."}})
        text = self.server.responder(model, body.get("prompt", ""))
        # G1'S PROBES CARRY NO STOP LIST. A registered adapter changes the text there — the one thing G1
        # asks — so what G1 checks against this fake is that the member EXISTS under that name.
        if model != s["base"] and not body.get("stop"):
            text = f"{text} (as {model})"
        stop_reason = None
        for st in body.get("stop") or []:
            if st in text:
                cut = text.index(st)
                text, stop_reason = text[:cut] + (st if body.get("include_stop_str_in_output") else ""), st
                break
        self.server.served.append(model)
        self._send(200, {"choices": [{"text": text, "stop_reason": stop_reason, "finish_reason": "stop"}]})


class FakeProc:
    """What `accept_rank.serve` returns: the three methods `wait_ready` and `stop` call."""

    def __init__(self, server: ThreadingHTTPServer):
        self.server, self.returncode = server, None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.server.shutdown(); self.server.server_close(); self.returncode = 0

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        self.terminate()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def patched(responder=default_responder):
    """Point `accept_rank.serve` at a fake server built from the SAME command line the runner writes.
    Yields a dict that fills in with the server (its `refused` and `served` lists) once one starts."""
    from training.harness import accept_rank as ar
    seen: dict = {}
    port = _free_port()
    old_serve, old_host = ar.serve, ar.HOST

    def serve(model: str, extra: list[str]):
        cmd = ["vllm", "serve", model, "--port", str(port), *extra]
        spec = parse_serve(cmd)
        server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
        server.spec, server.responder, server.refused, server.served = spec, responder, [], []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        seen.update(spec=spec, server=server)
        return FakeProc(server)

    ar.serve, ar.HOST = serve, f"http://127.0.0.1:{port}"
    try:
        yield seen
    finally:
        ar.serve, ar.HOST = old_serve, old_host


class FakeTokenizer:
    """`AutoTokenizer.from_pretrained` for tests: a chat template that joins, words as ids."""

    @classmethod
    def from_pretrained(cls, *_a, **_k):
        return cls()

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, **_k):
        return "".join(f"<|{m['role']}|>{m['content']}\n" for m in messages) + ("<|assistant|>" if add_generation_prompt else "")

    def __call__(self, text):
        return {"input_ids": text.split()}
