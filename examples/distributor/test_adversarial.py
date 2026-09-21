"""The 0-leaks gate for the distributor domain — the second instance of
examples/school/test_adversarial.py's matrix, on a different schema, no children in it, no
health-adjacent framing. The tenant boundary is what is under test either way.

Covers the full roster the reference diagram names (`docs/img/solution-architecture.png`):
`customer_service`, `dispatch`, `receiving`, `purchasing`, `claims_returns`, `it` — 6 roles, 11
tools, two tenants, 4 planted injection strings.
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


# --- the four roles added when the distributor was brought to the school's depth ---

LIST_TOOLS = {
    "receiving": ("dock_status", "Forklift", None),
    "purchasing": ("stock_read", "canned goods", "bottled water"),
    "claims_returns": ("return_list", None, "Wrong item received"),   # only harbor has a seeded return
    "it": ("maintenance_list", "Scanner battery", "jammed"),
}


@pytest.mark.parametrize("role_name,spec", list(LIST_TOOLS.items()))
def test_list_tools_never_return_the_other_tenants_marker(conn, role_name, spec):
    tool_name, riverside_marker, harbor_marker = spec
    riverside = claim_of(f"{role_name}-riverside")
    harbor = claim_of(f"{role_name}-harbor")
    out_riverside = tools.answer(conn, riverside, tool_name, {})
    out_harbor = tools.answer(conn, harbor, tool_name, {})
    if riverside_marker:
        assert riverside_marker in out_riverside and riverside_marker not in out_harbor
    if harbor_marker:
        assert harbor_marker in out_harbor and harbor_marker not in out_riverside


def test_dock_assign_never_crosses_a_tenant(conn):
    for role in ("receiving-riverside", "receiving-harbor"):
        claim = claim_of(role)
        row = conn.execute("select org_id from orders where id=1").fetchone()
        if row["org_id"] == claim.org_id:
            assert "assigned order" in tools.dock_assign(conn, claim, 1, "9")
        else:
            with pytest.raises(Denied):
                tools.dock_assign(conn, claim, 1, "9")


def test_stock_reorder_can_never_reach_another_tenants_item(conn):
    """`stock_reorder` looks the item up scoped to the claim's own org — there is no field a
    caller could use to name another tenant's stock row, the same rule as `order_draft`."""
    riverside = claim_of("purchasing-riverside")
    with pytest.raises(tools.ToolError):
        tools.stock_reorder(conn, riverside, "bottled water", 10)   # bottled water is harbor's only


def test_return_create_never_crosses_a_tenant(conn):
    for role in ("claims_returns-riverside", "claims_returns-harbor"):
        claim = claim_of(role)
        row = conn.execute("select org_id from orders where id=2").fetchone()
        if row["org_id"] == claim.org_id:
            assert "filed return" in tools.return_create(conn, claim, 2, "test reason")
        else:
            with pytest.raises(Denied):
                tools.return_create(conn, claim, 2, "test reason")


def test_the_injected_return_reason_is_data_and_grants_no_cross_tenant_listing(conn):
    """`db.INJECTION_RETURN_REASON` sits on harbor's own return and asks to list riverside's
    returns; `return_list` takes no id at all, so harbor's own listing is the only thing it
    could ever return."""
    harbor = claim_of("claims_returns-harbor")
    out = tools.return_list(conn, harbor)
    assert db.INJECTION_RETURN_REASON in out


def test_the_injected_maintenance_description_grants_no_cross_tenant_visibility(conn):
    """`db.INJECTION_MAINTENANCE_DESC` sits on harbor's own maintenance request and asks to
    list riverside's."""
    harbor = claim_of("it-harbor")
    out = tools.maintenance_list(conn, harbor)
    assert db.INJECTION_MAINTENANCE_DESC in out
    assert "Scanner battery" not in out                       # riverside's own ticket never appears


@pytest.mark.parametrize("role_name,other_tool", [
    ("receiving", "stock_reorder"), ("purchasing", "return_create"),
    ("claims_returns", "maintenance_create"), ("it", "dock_assign")])
def test_every_new_role_is_also_confined_to_its_own_tool_list_through_mcp(conn, role_name, other_tool):
    claim = claim_of(f"{role_name}-riverside")
    role = roles.ROLES[claim.role]
    reply = mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": other_tool, "arguments": {}}},
        conn, claim, role)
    assert reply["result"]["isError"] is True
    assert "may not call" in reply["result"]["content"][0]["text"]


def test_write_tools_are_never_annotated_read_only_over_mcp(conn):
    checked_a_write = False
    for role_name in roles.ROLES:
        claim = claim_of(f"{role_name}-riverside")
        reply = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                  conn, claim, roles.ROLES[role_name])
        for t in reply["result"]["tools"]:
            is_write = t["name"] in tools.WRITE_TOOLS
            if is_write:
                checked_a_write = True
            assert t["annotations"]["readOnlyHint"] == (not is_write), \
                f"{t['name']}: readOnlyHint should be {not is_write}"
    assert checked_a_write, "no write tool was exercised — the assertion above proves nothing"


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
        if claim.role == "receiving":
            tried += 1
            row = conn.execute("select org_id from orders where id=1").fetchone()
            try:
                tools.dock_assign(conn, claim, 1, "9")
                if row["org_id"] != claim.org_id:
                    leaks += 1
            except Denied:
                pass
    assert tried > 0
    assert leaks == 0, f"{leaks} of {tried} cross-tenant reads/writes were NOT denied"
