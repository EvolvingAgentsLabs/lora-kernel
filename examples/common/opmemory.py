r"""Short-term operational memory — a cache per session and one per organisation, that a member knows and operates by key
(the user's design, 2026-09-29; docs/review/harness-workflow-kv.md).

WHY. A turn should not have to carry the conversation to know what "it" is (MT0 [ran]: without history 4/54 dependent
turns; with it 43/54, but a reference written into free text is lost 8 of 10 times). The values a workflow needs live
here, under keys; the model reads the key NAMES in a one-line context and fetches or stores a value only in the step that
uses it:

    <get>order</get>= 41                      session scope: this user's conversation
    <put>order=41</put>= stored order
    <get>global.sprint</get>= Sprint 14       organisation scope: every session of the organisation reads it
    <put>global.sprint=Sprint 14</put>= stored global.sprint

THE BOUNDARY IS THE CLAIM'S, AS FOR EVERY TOOL. The session cache is keyed by (organisation, user, session); the global one
by organisation. A key is never looked up across organisations, whatever the model writes; every write is logged with who
made it. Values are text, bounded (`MAX_VALUE`); the store is in memory and dies with the gateway — short-term by design.

WORKFLOWS ARE DECLARED, NOT NEURAL (`Workflow`): a TOML file per workflow — its states, which call moves which state where,
and the keys the workflow uses. The gateway advances the state from the calls the tool layer RAN; the model only reads it.

    [workflow]
    name = "receiving"
    initial = "start"
    keys = ["order", "dock"]
    [states.start]
    on = { dock_assign = "assigned" }
    [states.assigned]
    on = { dock_assign = "assigned" }
"""
from __future__ import annotations

import re
import threading
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

MAX_VALUE = 500
KEY = re.compile(r"^(global\.)?[a-z][a-z0-9_]{0,40}$")
VERBS = ("get", "put")
SCHEMA = [  # rendered like any tool when a member is served with the memory; the corpus teaches the same two lines
    {"type": "function", "function": {"name": "get", "description": "Read a value you stored earlier, by its key (global.<key> for the organisation's).",
                                      "parameters": {"type": "object", "properties": {"key": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "put", "description": "Store a value under a key for later steps: key=value (global.<key> for the organisation's).",
                                      "parameters": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}}}},
]


class MemoryError(ValueError):
    """What the model is told when a key is malformed, missing or its value too long — shown as `ERROR: …`."""


class OpMemory:
    def __init__(self):
        self._session: dict[tuple, dict[str, str]] = {}
        self._global: dict[str, dict[str, str]] = {}
        self.log: list[dict] = []
        self._lock = threading.Lock()

    def _where(self, claim, session: str, key: str) -> tuple[dict, str]:
        if not KEY.match(key or ""):
            raise MemoryError(f"not a key: {key!r} (lowercase letters, digits, _; global.<key> for the organisation)")
        if key.startswith("global."):
            return self._global.setdefault(claim.org_id, {}), key.removeprefix("global.")
        return self._session.setdefault((claim.org_id, claim.user_id, session), {}), key

    def get(self, claim, session: str, key: str) -> str:
        with self._lock:
            store, k = self._where(claim, session, key.strip())
            if k not in store:
                raise MemoryError(f"no key {key.strip()}")
            return store[k]

    def put(self, claim, session: str, key: str, value: str) -> str:
        value = str(value).strip()
        if len(value) > MAX_VALUE:
            raise MemoryError(f"value too long ({len(value)} > {MAX_VALUE})")
        with self._lock:
            store, k = self._where(claim, session, key.strip())
            store[k] = value
            self.log.append({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "org": claim.org_id, "user": claim.user_id,
                             "session": session, "key": key.strip(), "value": value})
        return f"stored {key.strip()}"

    def keys(self, claim, session: str) -> list[str]:
        """The key NAMES a turn may use — the session's, then the organisation's as `global.<key>`. Never the values."""
        with self._lock:
            mine = sorted(k for k in self._session.get((claim.org_id, claim.user_id, session), {}) if not k.startswith("_"))
            org = sorted(f"global.{k}" for k in self._global.get(claim.org_id, {}))
        return mine + org

    def answer(self, claim, session: str, verb: str, body: str) -> str:
        """`get` / `put` as the tool layer serves them: `<get>key</get>`, `<put>key=value</put>`."""
        if verb == "get":
            return self.get(claim, session, body)
        key, sep, value = body.partition("=")
        if not sep:
            raise MemoryError("put needs key=value")
        return self.put(claim, session, key, value)


@dataclass
class Workflow:
    name: str
    initial: str
    states: dict[str, dict[str, str]] = field(default_factory=dict)
    keys: list[str] = field(default_factory=list)
    capture: dict[str, str] = field(default_factory=dict)     # key → regex over the user's request ([capture] in the TOML)

    @classmethod
    def load(cls, path: str | Path) -> "Workflow":
        d = tomllib.loads(Path(path).read_text())
        w = d["workflow"]
        return cls(name=w["name"], initial=w["initial"], keys=list(w.get("keys", [])),
                   states={s: dict(v.get("on", {})) for s, v in d.get("states", {}).items()},
                   capture=dict(d.get("capture", {})))

    def captured(self, memory: OpMemory, claim, session: str, request: str, calls: list[dict]) -> dict[str, str]:
        r"""A key the USER named, kept even when the turn's call went wrong. After the turn, for each `[capture]` key whose
        pattern occurs in the request: if the member did not `put` that key itself this turn, the gateway puts the last
        match. Without it one wrong first call leaves the memory empty and every dependent turn after it finds nothing —
        4 of `s1-noblock`'s 4 misses were one such session [ran] H3. Declared, never inferred; logged like any write."""
        put_now = {str(c.get("args", {}).get("body", "")).split("=", 1)[0].strip() for c in calls if c.get("tool") == "put" and "result" in c}
        out = {}
        for key, pattern in self.capture.items():
            found = re.findall(pattern, request or "")
            if found and key not in put_now:
                memory.put(claim, session, key, found[-1])
                out[key] = found[-1]
        return out

    def state(self, memory: OpMemory, claim, session: str) -> str:
        try:
            return memory.get(claim, session, f"wf_{self.name}")
        except MemoryError:
            return self.initial

    def advance(self, memory: OpMemory, claim, session: str, calls: list[dict]) -> str:
        """Move by every call the tool layer RAN (a result, not a refusal or an error), in order."""
        s = self.state(memory, claim, session)
        for c in calls:
            if "result" in c and c.get("tool") in self.states.get(s, {}):
                s = self.states[s][c["tool"]]
        memory.put(claim, session, f"wf_{self.name}", s)
        return s


def context_line(memory: OpMemory, claim, session: str, workflow: Workflow | None) -> str:
    """The one line a turn reads instead of the conversation: the workflow's state and the key names — no values."""
    state = f"{workflow.name}/{workflow.state(memory, claim, session)}" if workflow else "-"
    keys = [k for k in memory.keys(claim, session) if not k.startswith("wf_")]
    return f"state: {state} · keys: {', '.join(keys) if keys else '(none)'}"
