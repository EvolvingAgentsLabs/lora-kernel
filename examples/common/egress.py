r"""The gateway's network egress, closed by construction: an allow-list for this process.

WHY. A member reaches the frontier only if its corpus taught it to abstain and its role's egress is `frontier`
(docs/MECHANISMS.md §6) — that governs what the MODEL decides, not what the PROCESS can do. An organisation holding
sensitive records needs the second guarantee too: whatever a bug or a dependency attempts, the gateway talks to the
hosts its configuration names and to nothing else. The first thing this found was the gateway's own start-up: loading the
tokenizer asks the model hub over the network unless told not to.

THE RULE. `install(hosts, log=...)` replaces `socket.getaddrinfo` and `socket.socket.connect` / `connect_ex` for this
process. A name or address outside the allow-list (the configured hosts plus loopback) is refused BEFORE any packet
leaves — the DNS lookup included — raising `EgressDenied`, and the attempt is appended to `log` as one JSON line.
Nothing is retried, nothing falls back.

WHAT IT IS NOT. A process-level guard: a subprocess, or a C extension opening its own sockets, is outside it. The
operating system's firewall is the deployment's layer (docs/SERVING.md); this is the code's.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import threading
import time
from urllib.parse import urlparse

LOOPBACK = {"localhost", "127.0.0.1", "::1"}


class EgressDenied(PermissionError):
    pass


_state: dict = {}
_lock = threading.Lock()


def hosts_of(*urls: str | None) -> set[str]:
    """The hosts named by the configured URLs (the member's server, the frontier's)."""
    return {urlparse(u).hostname for u in urls if u and urlparse(u).hostname}


def _allowed(host) -> bool:
    h = str(host).strip("[]").lower()
    if h in _state["hosts"]:
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def _deny(host, port, how: str):
    ev = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "egress": "denied", "host": str(host), "port": port, "via": how}
    with _lock:
        _state["denied"].append(ev)
        if _state.get("log"):
            with open(_state["log"], "a") as f:
                f.write(json.dumps(ev) + "\n")
    raise EgressDenied(f"egress to {host}:{port} is not in this gateway's allow-list")


def install(hosts: set[str], log: str | None = None) -> None:
    """Close the process's egress to `hosts` plus loopback. Idempotent; `uninstall()` restores the socket module."""
    if _state:
        uninstall()
    _state.update(hosts={h.lower() for h in hosts} | LOOPBACK, log=log, denied=[],
                  getaddrinfo=socket.getaddrinfo, connect=socket.socket.connect, connect_ex=socket.socket.connect_ex)

    def getaddrinfo(host, port, *a, **k):
        if host is not None and not _allowed(host):
            _deny(host, port, "dns")
        return _state["getaddrinfo"](host, port, *a, **k)

    def _check(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and isinstance(address, tuple) and not _allowed(address[0]):
            _deny(address[0], address[1], "connect")

    def connect(sock, address):
        _check(sock, address)
        return _state["connect"](sock, address)

    def connect_ex(sock, address):
        _check(sock, address)
        return _state["connect_ex"](sock, address)
    socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex = getaddrinfo, connect, connect_ex


def uninstall() -> None:
    if _state:
        socket.getaddrinfo, socket.socket.connect, socket.socket.connect_ex = \
            _state["getaddrinfo"], _state["connect"], _state["connect_ex"]
        _state.clear()


def denied() -> list[dict]:
    return list(_state.get("denied", []))
