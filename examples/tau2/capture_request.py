"""Capture what τ² actually sends an agent model — the real HTTP body, no model anywhere.

WHY. G-shim-3 asks whether anything from a task's grading criteria can reach the shim. τ² builds the
agent's request in `LLMAgent` (`src/tau2/agent/llm_agent.py`) and hands it to litellm, which writes the
HTTP body; reading that code says the body is the system prompt (instructions + policy), the
conversation and the tools, and nothing else **[read]**. This turns the reading into a recording: it
runs τ²'s own `LLMAgent.generate_next_message` over shipped airline conversations, with litellm pointed
(`openai/<name>`, `api_base`) at a local server that records each POST body and answers a canned
reply. What the server records is byte for byte what the shim would receive.

RUN UNDER τ²'S OWN VENV (it imports tau2; this repository's venvs do not have it):

    ~/evolvingagents/tau2-bench/.venv/bin/python examples/tau2/capture_request.py \
        --tau2 ~/evolvingagents/tau2-bench --out examples/tau2/fixtures

It writes, for the test-split tasks it captures:
    tau2_requests.json   [{task_id, cut, body}] — the recorded POST bodies (the shim's input)
    tau2_gold.json       {task_id: evaluation_criteria + user_scenario} — read ONLY by the leak test
    airline_tools.json   the 14 tool schemas, `Tool.openai_schema`, as τ² offers them
Zero model calls, zero spend: the "model" is the local recorder.
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CAPTURED: list[dict] = []


class Recorder(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        CAPTURED.append({"path": self.path, "body": body})
        out = json.dumps({"id": "chatcmpl-rec", "object": "chat.completion", "created": 0, "model": body.get("model"),
                          "choices": [{"index": 0, "finish_reason": "stop",
                                       "message": {"role": "assistant", "content": "recorded"}}],
                          "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tau2", default=str(Path.home() / "evolvingagents/tau2-bench"))
    ap.add_argument("--out", default="examples/tau2/fixtures")
    ap.add_argument("--traj", default="data/tau2/results/final/gpt-4.1-2025-04-14_airline_default_gpt-4.1-2025-04-14_4trials.json")
    ap.add_argument("--tasks", default="2,13,24", help="test-split task ids to capture")
    a = ap.parse_args()

    from tau2.agent.llm_agent import LLMAgent
    from tau2.data_model.message import AssistantMessage, ToolMessage, UserMessage
    from tau2.domains.airline.environment import get_environment, get_tasks

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Recorder)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/v1"

    env = get_environment()
    tools, policy = env.get_tools(), env.get_policy()
    test = {t.id: t for t in get_tasks("test")}
    sims = json.load(open(Path(a.tau2) / a.traj))["simulations"]
    keep = ("role", "content", "tool_calls", "id", "requestor", "error")

    def to_msg(m):
        d = {k: v for k, v in m.items() if k in keep}
        return {"assistant": AssistantMessage, "user": UserMessage, "tool": ToolMessage}[m["role"]](**d)

    requests, gold = [], {}
    for tid in a.tasks.split(","):
        assert tid in test, f"task {tid} is not in the airline test split"
        sim = next(s for s in sims if s["task_id"] == tid and s["trial"] == 0)
        msgs = [to_msg(m) for m in sim["messages"]]
        # two cut points: right after the user's first message, and right after the last tool result
        # (mid-turn: the agent continues after reading a result — the shape the shim folds inline)
        first_user = next(i for i, m in enumerate(msgs) if isinstance(m, UserMessage))
        last_tool = max((i for i, m in enumerate(msgs) if isinstance(m, ToolMessage)), default=None)
        for cut, i in (("first_user", first_user), ("after_last_tool", last_tool)):
            if i is None:
                continue
            agent = LLMAgent(tools=tools, domain_policy=policy, llm="openai/member-under-test",
                             llm_args={"temperature": 0.0, "api_base": base, "api_key": "x"})
            state = agent.get_init_state(message_history=msgs[:i])
            before = len(CAPTURED)
            agent.generate_next_message(msgs[i], state)
            assert len(CAPTURED) == before + 1, "τ² made no request, or more than one"
            requests.append({"task_id": tid, "cut": cut, "n_history": i + 1, **CAPTURED[-1]})
        t = test[tid]
        gold[tid] = {"evaluation_criteria": t.evaluation_criteria.model_dump(mode="json"),
                     "user_scenario": t.user_scenario.model_dump(mode="json"),
                     "description": t.description.model_dump(mode="json") if t.description else None}
    srv.shutdown()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "tau2_requests.json").write_text(json.dumps(requests, indent=1, ensure_ascii=False))
    (out / "tau2_gold.json").write_text(json.dumps(gold, indent=1, ensure_ascii=False))
    (out / "airline_tools.json").write_text(json.dumps([t.openai_schema for t in tools], indent=1))
    print(f"[tau2] captured {len(requests)} request(s) over tasks {a.tasks}; {len(tools)} tools; 0 model calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
