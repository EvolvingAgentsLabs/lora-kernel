"""docs/DEMO.md's zero-GPU parts — the route it shows and the tool layer it calls. No model.

The demo claims three things it does not need a model for: the dictionary keeps the member's own
wording local and sends a paraphrase and a foreign ask out (milestone 2's measured limit, shown
rather than hidden); the tool layer, reached through the demo's own suite, denies another tenant's
order whatever the model wrote; and a write lands at the signed-in user's own centre.
"""
from examples.distributor import db, users
from training.harness import demo_org as d


def _scripted(tag: str):
    def make(system, user):
        n = {"k": 0}

        def gen(prefix):
            n["k"] += 1
            return tag if n["k"] == 1 else "Done."
        return gen, lambda: {"prompt_tokens": 1, "completion_tokens": 1}
    return make


def test_the_route_it_shows_is_the_dictionarys():
    got = [r["decision"] for r in d.routed()]
    assert got == ["local", "out", "out"]


def test_another_tenants_order_is_denied_by_the_tool_not_the_model():
    users.register_all()
    conn = db.build()
    s = d.scene(conn, "customer_service-riverside", "order 2?", _scripted("<order_status>2</order_status>"))
    assert s["denied"] and "harbor" in s["calls"][0]["denied"]
    own = d.scene(conn, "customer_service-riverside", "order 1?", _scripted("<order_status>1</order_status>"))
    assert not own["denied"] and "in transit" in own["calls"][0]["result"]


def test_a_write_lands_at_the_users_own_centre_and_the_bill_prices_what_was_served():
    users.register_all()
    conn = db.build()
    s = d.scene(conn, "it-riverside", "ticket", _scripted("<maintenance_create>area=Dock 2; description=scanner</maintenance_create>"))
    assert "at riverside" in s["calls"][0]["result"]
    b = d.bill([s])
    assert b["turns_served_locally"] == 1 and b["frontier_cost_usd"] > 0 and "GPU" in b["not_priced"]
