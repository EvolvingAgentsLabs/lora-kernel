"""What waits for a person survives a restart; the gateway's egress is closed to its configured hosts.

`approvals.Queue(journal=…)` appends `held` → `executing` → `approved` / `rejected` and rebuilds from it: a charge held
before a restart is approved after it and executed exactly once, with the requester's scope; a process that died
mid-execution comes back `interrupted`, never re-run. `egress.install` refuses any host outside the allow-list — the DNS
lookup included — and logs the attempt; loopback stays open.
"""
import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from examples.common import approvals, egress
from examples.common.permissions import Claim, Denied

CFO, DIRECTOR = Claim("cfo-north", "cfo", "northgate"), Claim("director-north", "director", "northgate")


def test_a_held_charge_survives_a_restart_and_runs_once_with_the_requesters_scope(tmp_path):
    j = str(tmp_path / "approvals.jsonl")
    approvals.Queue(journal=j).hold(CFO, "billing_charge", {"membership_id": "1", "amount_cents": "4500"})
    q = approvals.Queue(journal=j)                                  # the gateway restarted
    assert [i["id"] for i in q.pending(DIRECTOR)] == [1] and q.items[0]["requested_by"] == CFO
    ran = []
    with pytest.raises(Denied):
        q.approve(1, CFO, lambda *a: ran.append(a))                 # still not by the account that asked
    assert q.approve(1, DIRECTOR, lambda c, tool, args: ran.append((c, tool, args)) or "charged") == "charged"
    assert ran == [(CFO, "billing_charge", {"membership_id": "1", "amount_cents": "4500"})]
    q2 = approvals.Queue(journal=j)                                 # and restarted again
    assert q2.pending(DIRECTOR) == [] and q2.items[0]["status"] == "approved"
    with pytest.raises(KeyError):
        q2.approve(1, DIRECTOR, lambda *a: ran.append(a))            # once, across restarts
    assert len(ran) == 1


def test_a_process_that_died_mid_execution_comes_back_interrupted_never_rerun(tmp_path):
    j = str(tmp_path / "approvals.jsonl")
    q = approvals.Queue(journal=j)
    q.hold(CFO, "billing_charge", {"membership_id": "2", "amount_cents": "100"})

    def crash(*a):
        raise SystemExit("killed while charging")
    with pytest.raises(SystemExit):
        q.approve(1, DIRECTOR, crash)
    q2 = approvals.Queue(journal=j)
    assert q2.items[0]["status"] == "interrupted" and [i["id"] for i in q2.pending(DIRECTOR)] == [1]
    with pytest.raises(KeyError):
        q2.approve(1, DIRECTOR, lambda *a: "charged again")          # a person checks the ledger; the queue never retries
    q2.reject(1, DIRECTOR)
    assert approvals.Queue(journal=j).items[0]["status"] == "rejected"


def test_the_gateway_keeps_its_handoffs_and_queue_across_a_restart(tmp_path):
    from examples.school.gateway import Gateway
    from examples.school import db, users
    from examples.common import tokens
    users.register_all()

    def generate(system, user, close, history=None):
        steps = iter(["<billing_charge>membership_id=1; amount_cents=4500</billing_charge>", "Held for a director."]
                     if "membresía" in user else ["OUT OF SCOPE"])
        return (lambda prefix: next(steps)), (lambda: {"prompt_tokens": 1, "completion_tokens": 1})
    gw = Gateway(db.build(), generate, org="school", state_dir=str(tmp_path))
    cfo = tokens.issue("cfo-north", "cfo", "northgate")
    gw.turn(cfo, [{"role": "user", "content": "Cobrá la membresía 1"}])
    edu = tokens.issue("educador-north", "educador", "northgate")
    gw.turn(edu, [{"role": "user", "content": "Un alumno se lastimó en el recreo"}])
    before = (len(gw.handoffs), len(gw.queue.items))
    gw2 = Gateway(db.build(), generate, org="school", state_dir=str(tmp_path))      # restart
    assert (len(gw2.handoffs), len(gw2.queue.items)) == before and before[1] == 1
    director = tokens.issue("director-north", "director", "northgate")
    assert [p["id"] for p in gw2.pending(director)] == [1]


@pytest.fixture
def closed():
    yield
    egress.uninstall()


def _local_server():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"ok")

        def log_message(self, *a):
            pass
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def test_egress_is_closed_to_the_configured_hosts_and_every_attempt_is_logged(tmp_path, closed):
    srv = _local_server()
    log = tmp_path / "events.jsonl"
    egress.install(egress.hosts_of(f"http://127.0.0.1:{srv.server_address[1]}", None), log=str(log))
    assert urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/", timeout=5).read() == b"ok"
    with pytest.raises(urllib.error.URLError) as e:
        urllib.request.urlopen("https://huggingface.co/api/models", timeout=5)          # refused at the DNS lookup
    assert isinstance(e.value.reason, egress.EgressDenied)
    with pytest.raises(egress.EgressDenied):
        with socket.socket() as raw:
            raw.connect(("93.184.216.34", 443))                                         # and at connect, by address
    evs = [json.loads(l) for l in log.read_text().splitlines()]
    assert [(e["host"], e["via"]) for e in evs] == [("huggingface.co", "dns"), ("93.184.216.34", "connect")]
    srv.shutdown()


def test_a_configured_frontier_host_is_allowed_and_nothing_else(closed):
    egress.install(egress.hosts_of("http://127.0.0.1:8792", "https://api.anthropic.com/v1"))
    assert egress._allowed("api.anthropic.com") and egress._allowed("127.0.0.1") and egress._allowed("::1")
    assert not egress._allowed("api.openai.com") and not egress._allowed("10.0.0.5")
    egress.uninstall()
    assert socket.getaddrinfo is not None and not egress.denied()
