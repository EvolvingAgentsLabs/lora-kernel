"""The 0-leaks gate for the distributor domain — the second instance of
examples/school/test_adversarial.py's matrix, on a different schema, no children in it, no
health-adjacent framing. The tenant boundary is what is under test either way.
"""
from __future__ import annotations

import itertools

import pytest

from . import db, mcp_server, roles, tools, users
from ..common.permissions import Denied

users.register_all()


@pytest.fixture()
def conn():
    return db.build()


def claim_of(user_id: str):
    from ..common import mock_auth
    return mock_auth.issue_claim(user_id)


ALL_USERS = [u for u, _, _ in users.SEED_USERS]
ALL_ORDER_IDS = (1, 2)


@pytest.mark.parametrize("user_id,order_id", list(itertools.product(ALL_USERS, ALL_ORDER_IDS)))
def test_order_status_never_crosses_a_tenant(conn, user_id, order_id):
    claim = claim_of(user_id)
    row = conn.execute("select org_id from orders where id=?", (order_id,)).fetchone()
    same_org = row["org_id"] == claim.org_id
    if same_org:
        out = tools.order_status(conn, claim, order_id)
        assert "order #" in out
    else:
        with pytest.raises(Denied):
            tools.order_status(conn, claim, order_id)


def test_the_injected_delivery_note_is_data_and_grants_no_route_across_tenants(conn):
    """`db.INJECTION_NOTE` is planted on harbor's own delivery and reads back verbatim to a
    harbor claim; acting on what it asks for (order #1, riverside) is still denied."""
    harbor = claim_of("dispatch-harbor")
    out = tools.delivery_status(conn, harbor, 2)
    assert db.INJECTION_NOTE in out
    with pytest.raises(Denied):
        tools.delivery_status(conn, harbor, 1)          # order 1 is riverside's


def test_the_injected_claim_description_grants_no_cross_tenant_order_status(conn):
    """`db.INJECTION_DESCRIPTION` is filed under harbor and asks to list riverside's orders;
    `order_status` takes an id, not "every order", so there is no field the injected text
    could have widened even if a model tried to obey it."""
    harbor = claim_of("customer_service-harbor")
    with pytest.raises(Denied):
        tools.order_status(conn, harbor, 1)              # order 1 is riverside's


def test_claim_create_always_lands_in_the_askers_own_tenant(conn):
    for user_id in ("customer_service-riverside", "customer_service-harbor"):
        tools.claim_create(conn, claim_of(user_id), "test claim")
    rows = conn.execute("select org_id, filed_by from claims where description='test claim'").fetchall()
    assert {r["org_id"] for r in rows} == {"riverside", "harbor"}


def test_an_unregistered_user_is_refused():
    from ..common import mock_auth
    with pytest.raises(PermissionError):
        mock_auth.issue_claim("someone-who-never-signed-in")


def test_a_role_cannot_call_a_tool_it_was_not_given_through_mcp(conn):
    cs = claim_of("customer_service-riverside")
    role = roles.ROLES[cs.role]
    reply = mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "delivery_status", "arguments": {"order_id": 1}}},
        conn, cs, role)
    assert reply["result"]["isError"] is True
    assert "may not call" in reply["result"]["content"][0]["text"]


def test_a_cross_tenant_call_over_mcp_is_an_error_result_not_a_transport_crash(conn):
    dispatch = claim_of("dispatch-riverside")
    role = roles.ROLES[dispatch.role]
    reply = mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "order_status", "arguments": {"order_id": 2}}},
        conn, dispatch, role)
    assert reply["result"]["isError"] is True
    assert "org" in reply["result"]["content"][0]["text"]


def test_zero_leaks_summary(conn):
    leaks = 0
    tried = 0
    for user_id in ALL_USERS:
        claim = claim_of(user_id)
        for oid in ALL_ORDER_IDS:
            tried += 1
            row = conn.execute("select org_id from orders where id=?", (oid,)).fetchone()
            try:
                tools.order_status(conn, claim, oid)
                if row["org_id"] != claim.org_id:
                    leaks += 1
            except Denied:
                pass
    assert tried > 0
    assert leaks == 0, f"{leaks} of {tried} cross-tenant reads were NOT denied"
