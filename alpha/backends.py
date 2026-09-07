"""Two backends, both greedy, both stdlib.

Greedy is not a detail: at temperature 0 the target's distribution is one-hot, so
speculative decoding's acceptance test reduces to string equality and the whole
instrument becomes available without a sampler, a GPU or vLLM. Any backend added
here MUST be able to run at temperature 0 and MUST support a trailing assistant
message as a prefill, or the surface cannot be measured from mid-answer positions.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


class BackendError(RuntimeError):
    pass


@dataclass
class Reply:
    text: str                    # the ANSWER channel only
    thinking: str = ""           # the reasoning channel, kept apart on purpose
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    truncated: bool = False      # the budget ran out — usually eaten by thinking


def _post(url: str, body: dict, headers: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:  # the body carries the reason; keep it
        raise BackendError(f"{e.code} {e.reason}: {e.read().decode()[:400]}") from e
    except urllib.error.URLError as e:
        raise BackendError(f"unreachable {url}: {e.reason}") from e


class Ollama:
    """Local models.

    EVERY local model in this workspace is a thinking model [ran] 2026-09-07, and
    that is not a detail. The reasoning stream is emitted BEFORE the answer, so a
    generation budget sized for the answer is silently consumed by thinking and
    the call returns an empty `content` with `done_reason == "length"`. Ollama
    hands the two channels back separately, which is what makes the answer
    channel measurable at all — so both are recorded, never concatenated.

    `think=false` works on the qwen family and returns HTTP 500 on gemma, so it
    is attempted once and remembered.
    """

    kind = "ollama"

    def __init__(self, model: str, host: str = "http://localhost:11434", timeout: int = 600):
        self.model, self.host, self.timeout = model, host, timeout
        self.name = f"ollama:{model}"
        self.supports_think_off: bool | None = None

    def _call(self, messages, max_tokens, think_off):
        body = {"model": self.model, "messages": messages, "stream": False,
                "options": {"temperature": 0.0, "top_k": 1,
                            "num_predict": max_tokens, "seed": 0}}
        if think_off:
            body["think"] = False
        return _post(f"{self.host}/api/chat", body, {}, self.timeout)

    def chat(self, messages: list[dict], max_tokens: int = 256) -> Reply:
        t0 = time.time()
        if self.supports_think_off is None:
            try:
                out = self._call(messages, max_tokens, True)
                self.supports_think_off = True
            except BackendError:
                self.supports_think_off = False
                out = self._call(messages, max_tokens, False)
        else:
            out = self._call(messages, max_tokens, self.supports_think_off)
        msg = out.get("message", {})
        return Reply(
            text=msg.get("content") or "",
            thinking=msg.get("thinking") or "",
            prompt_tokens=out.get("prompt_eval_count", 0),
            completion_tokens=out.get("eval_count", 0),
            seconds=time.time() - t0,
            truncated=out.get("done_reason") == "length",
        )


class OpenAICompatible:
    """OpenRouter, vLLM, llama.cpp's server, or a vendor's own endpoint.

    `estimated_cost` is a declared price, not a scraped one: the number has to be
    reconstructible from the run's own config.
    """

    kind = "openai"

    def __init__(self, model: str, base_url: str = "https://openrouter.ai/api/v1",
                 api_key_env: str = "OPENROUTER_API_KEY", timeout: int = 600,
                 usd_per_mtok_in: float = 0.0, usd_per_mtok_out: float = 0.0):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.usd_in, self.usd_out = usd_per_mtok_in, usd_per_mtok_out
        self.name = f"openai:{model}"

    def chat(self, messages: list[dict], max_tokens: int = 256) -> Reply:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise BackendError(
                f"{self.api_key_env} is not set — the frontier arm cannot run. "
                "This is a blocker for a human, not something to work around."
            )
        t0 = time.time()
        out = _post(
            f"{self.base_url}/chat/completions",
            {"model": self.model, "messages": messages, "temperature": 0.0,
             "top_p": 1.0, "max_tokens": max_tokens, "seed": 0},
            {"Authorization": f"Bearer {key}"}, self.timeout,
        )
        usage = out.get("usage") or {}
        choice = out["choices"][0]
        msg = choice.get("message", {})
        return Reply(
            text=(msg.get("content") or ""),
            thinking=(msg.get("reasoning") or ""),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            seconds=time.time() - t0,
            truncated=choice.get("finish_reason") == "length",
        )

    def cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens * self.usd_in + completion_tokens * self.usd_out) / 1e6


def build(tag: str):
    """`ollama:gemma4:12b-mlx` or `openai:anthropic/claude-opus-5`."""
    if tag.startswith("ollama:"):
        return Ollama(tag.split(":", 1)[1])
    if tag.startswith("openai:"):
        return OpenAICompatible(tag.split(":", 1)[1])
    raise ValueError(f"backend tag must start with ollama: or openai: — got {tag!r}")
