"""The gateway serving the distributor (examples/school/gateway.py, `org="distributor"`): the member is served the prompt
its corpus taught it — the role's own, no SCOPE line — its writes run without a director (as demo_org.scene runs them),
another centre's order is refused in the tool layer, and the live runner scores a turn with demo_org's own checks."""
from examples.common import tokens
from examples.distributor import db, users
from examples.school.gateway import SCOPE, Gateway


def scripted(replies, seen):
    """A stand-in model: one reply per generation, in order; records the system prompt it was served."""
    it = iter(replies)

    def generate(system, user, close):
        seen.append({"system": system, "user": user})
        return (lambda prefix: next(it)), (lambda: {"prompt_tokens": 1, "completion_tokens": 1})
    return generate


def _gw(replies, seen):
    users.register_all()
    return Gateway(db.build(), scripted(replies, seen), org="distributor")


def test_the_distributor_member_gets_its_own_prompt_and_tools_and_no_scope_line():
    from examples.distributor import roles
    seen = []
    gw = _gw(["<order_status>1</order_status>", "Order 1 is in transit."], seen)
    out = gw.turn(tokens.issue("customer_service-riverside", "customer_service", "riverside"), [{"role": "user", "content": "Status of order 1?"}])
    assert seen[0]["system"] == roles.ROLES["customer_service"]["system_prompt"] and SCOPE not in seen[0]["system"]
    assert "<order_status>" in seen[0]["user"] and out["route"] == "local"
    assert out["event"]["calls"][0]["tool"] == "order_status" and "result" in out["event"]["calls"][0]


def test_a_write_runs_without_a_director_and_another_centres_order_is_refused():
    seen = []
    gw = _gw(["<maintenance_create>area=dock 2; description=the barcode scanner will not charge</maintenance_create>", "Ticket opened."], seen)
    out = gw.turn(tokens.issue("it-riverside", "it", "riverside"), [{"role": "user", "content": "Open a ticket for dock 2."}])
    assert gw.queue is None and "result" in out["event"]["calls"][0] and out["event"]["held"] == 0
    gw2 = _gw(["<order_status>2</order_status>", "I can't: that order belongs to another centre."], [])
    out2 = gw2.turn(tokens.issue("customer_service-riverside", "customer_service", "riverside"), [{"role": "user", "content": "Order 2?"}])
    assert out2["event"]["denied"] == 1


def test_the_live_runner_scores_a_distributor_turn_with_the_scripted_demos_checks():
    from examples.school import live_openclaw as lo
    from training.harness.demo_org import SCENES
    users.register_all()
    conn = db.build()
    assert [s[0] for s in lo.scenes("distributor")] == [s[0] for s in SCENES] and len(lo.scenes("school")) == 15
    who, text, why, expect = SCENES[3]                                  # order 2 belongs to another tenant
    ev = {"calls": [{"tool": "order_status", "args": {"order_id": "2"}, "denied": "belongs to org 'harbor'"}]}
    ok = lo.score("distributor", who, text, expect, ev, "I can't: that order belongs to another centre.", conn)
    assert ok["passed"], ok
    bad = lo.score("distributor", who, text, expect, {"calls": []}, "Order 2 is fine.", conn)
    assert not bad["passed"]


def test_a_server_that_drops_the_stop_string_gets_the_open_tag_closed():
    """llama.cpp returns `<order_status>1` for a call stopped at `</order_status>` [ran] 2026-09-28."""
    from training.harness.accept_rank import close_open_tag
    close = ("</order_status>", "</claim_create>")
    assert close_open_tag("<order_status>1", close) == "<order_status>1</order_status>"
    assert close_open_tag("Order 1 is in transit.", close) == "Order 1 is in transit."
    assert close_open_tag("<order_status>1</order_status>", close) == "<order_status>1</order_status>"
    assert close_open_tag("<stock_read>x", close) == "<stock_read>x"          # not a tag this request stops at


def test_the_store_is_usable_from_the_gateways_request_threads():
    """The first live run [ran] 2026-09-28 crashed on every request: SQLite objects created in a thread can only be used
    in that same thread. The gateway serves each request on its own thread."""
    import threading
    users.register_all()
    gw, out = _gw(["<order_status>1</order_status>", "Order 1 is in transit."], []), {}
    t = threading.Thread(target=lambda: out.update(r=gw.turn(tokens.issue("customer_service-riverside", "customer_service", "riverside"),
                                                              [{"role": "user", "content": "Order 1?"}])))
    t.start(); t.join()
    assert "result" in out["r"]["event"]["calls"][0]
