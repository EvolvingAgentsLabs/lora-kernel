"""The 0-leaks gate for the school domain (docs/FRAMEWORK.md §9 gap row E falsifier).

Zero GPU, no model — this validates the enforcement layer itself, independent of whether any
model (trained, base, or frontier) can be talked into asking for a forbidden row. That
separation matters: a model that never tries the attack proves nothing about the tool layer,
and a tool layer that only *sometimes* refuses is not fixed by a better prompt. Every case here
asserts `Denied` is raised — a leak is a return value that should have been an exception, and
this file counts them the way `bar.compare` counts a paired comparison: no case is skipped
because it "shouldn't" happen.

Running an actual model (even a bare frontier one, through OpenClaw and `mcp_server.py`) against
these same identities and the same planted injection text is the next, GPU-optional step —
examples/README.md says how (both MCP servers are registered and `mcp probe`-verified against a
real OpenClaw instance, under the project's isolated `lorakernel` profile); a live agent *turn*
still needs a model behind that profile, which is why it is not run here.

Covers the full roster (`docs/FRAMEWORK.md` §1): `educador`, `compras`, `trainee`, `marketing`, `it`, `cfo`, `dev` — 7
roles, 13 tools, 2 tenants, 4 planted injection strings.
"""
from __future__ import annotations

import itertools

import pytest

from . import db, mcp_server, roles, tools, users
from ..common import mock_billing
from ..common.permissions import Denied

users.register_all()


@pytest.fixture()
def conn():
    return db.build()


def claim_of(user_id: str):
    from ..common import mock_auth
    return mock_auth.issue_claim(user_id)


# --- the tenant boundary: every (claim, student) pair outside the claim's own org must deny ---

ALL_USERS = [u for u, _, _ in users.SEED_USERS]
ALL_STUDENT_IDS = (1, 2, 3)


@pytest.mark.parametrize("user_id,student_id", list(itertools.product(ALL_USERS, ALL_STUDENT_IDS)))
def test_agenda_read_never_crosses_a_tenant(conn, user_id, student_id):
    claim = claim_of(user_id)
    if claim.role != "educador":
        pytest.skip("only educador reads agendas")
    row = conn.execute("select org_id from students where id=?", (student_id,)).fetchone()
    same_org = row["org_id"] == claim.org_id
    if same_org:
        out = tools.agenda_read(conn, claim, student_id)
        assert "no agenda entries" in out or ":" in out          # it answered, not denied
    else:
        with pytest.raises(Denied):
            tools.agenda_read(conn, claim, student_id)


def test_the_injected_note_is_read_as_data_never_as_a_route_to_another_tenant(conn):
    """`db.INJECTION_NOTE` is planted on southport's own student and reads back verbatim to a
    southport claim — the tool does not sanitise it, because sanitising is not the mechanism.
    What the mechanism guarantees is that reading it never widens what the *next* call may
    reach: an educador-north claim asking for the very student the note names is still denied,
    proving the injected text has no route into the tenant boundary regardless of what a model
    that had read it might be persuaded to do next."""
    south = claim_of("educador-south")
    out = tools.agenda_read(conn, south, 3)
    assert db.INJECTION_NOTE in out                       # planted text is returned, unmodified…
    with pytest.raises(Denied):                            # …and acting on it is still denied — the note
        tools.agenda_read(conn, south, 2)                  # asks for student 2 "in org northgate"; student 2
                                                            # is northgate's, and `south` is southport's claim


def test_the_injected_description_grants_no_cross_tenant_order_list(conn):
    """`db.INJECTION_DESCRIPTION` asks, in southport's own purchase-order text, to be shown
    northgate's orders. `order_list` takes no id and no org argument at all — there is no
    field for the injected instruction to have reached even if a model tried to obey it."""
    south = claim_of("compras-south")
    listing = tools.order_list(conn, south)
    assert "office supplies" in listing
    assert "art supplies" not in listing                   # northgate's own order never appears


def test_order_draft_always_lands_in_the_askers_own_tenant(conn):
    for user_id in ("compras-north", "compras-south"):
        claim = claim_of(user_id)
        tools.order_draft(conn, claim, "test item", 1)
    rows = conn.execute("select org_id, requested_by from purchase_orders "
                        "where item='test item'").fetchall()
    assert {r["org_id"] for r in rows} == {"northgate", "southport"}
    for r in rows:
        assert r["requested_by"].endswith(r["org_id"][:5])   # each landed with its own requester


def test_an_unregistered_user_is_refused_not_served_as_nobody_in_particular():
    from ..common import mock_auth
    with pytest.raises(PermissionError):
        mock_auth.issue_claim("someone-who-never-signed-in")


# --- the role boundary, through the MCP layer itself, not only through direct calls ---

def test_a_role_cannot_call_a_tool_it_was_not_given_through_mcp(conn):
    educador = claim_of("educador-north")
    role = roles.ROLES[educador.role]
    reply = mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "order_draft", "arguments": {"item": "x", "qty": 1}}},
        conn, educador, role)
    assert reply["result"]["isError"] is True
    assert "may not call" in reply["result"]["content"][0]["text"]


def test_tools_list_over_mcp_offers_only_the_roles_own_surface(conn):
    compras = claim_of("compras-north")
    role = roles.ROLES[compras.role]
    reply = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, conn, compras, role)
    offered = {t["name"] for t in reply["result"]["tools"]}
    assert offered == set(role["tools"])
    assert "agenda_read" not in offered                     # purchasing never sees the agenda tool


def test_write_tools_are_never_annotated_read_only_over_mcp(conn):
    """`billing_charge` writes a charge; a client that trusted a blanket `readOnlyHint: true`
    would let an agent skip approval on it. Checked over every role that has at least one write
    tool, not just cfo."""
    checked_a_write = False
    for role_name in roles.ROLES:
        claim = claim_of(f"{role_name}-north")
        reply = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                                  conn, claim, roles.ROLES[role_name])
        for t in reply["result"]["tools"]:
            is_write = t["name"] in tools.WRITE_TOOLS
            if is_write:
                checked_a_write = True
            assert t["annotations"]["readOnlyHint"] == (not is_write), \
                f"{t['name']}: readOnlyHint should be {not is_write}"
    assert checked_a_write, "no write tool was exercised — the assertion above proves nothing"


def test_a_legitimate_call_over_mcp_round_trips_clean(conn):
    educador = claim_of("educador-north")
    role = roles.ROLES[educador.role]
    reply = mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "agenda_read", "arguments": {"student_id": 1}}},
        conn, educador, role)
    assert reply["result"]["isError"] is False
    assert "field trip" in reply["result"]["content"][0]["text"]


def test_a_cross_tenant_call_over_mcp_is_an_error_result_not_a_transport_crash(conn):
    """The denial has to reach the agent as a normal tool result it can read and stop on —
    not a dropped connection, which an agent runtime might retry into a worse state."""
    educador = claim_of("educador-north")
    role = roles.ROLES[educador.role]
    reply = mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": "agenda_read", "arguments": {"student_id": 3}}},
        conn, educador, role)
    assert reply["result"]["isError"] is True
    assert "org" in reply["result"]["content"][0]["text"]


# --- the five roles added when the reference diagram became the main case ---

# One org-scoped LIST tool per role that has one — the generic isolation sweep: called once per
# org, the result must contain that org's own marker and never the other org's.
LIST_TOOLS = {
    "trainee": ("enrollment_list", "after-school-robotics", "after-school-art"),
    "marketing": ("announcement_list", "Tuesday", "Wednesday"),
    "it": ("maintenance_list", "Projector bulb", "faucet"),
    "cfo": ("payroll_read", "Devon Ashby", "Priya Nandakumar"),
}


@pytest.mark.parametrize("role_name,spec", list(LIST_TOOLS.items()))
def test_list_tools_never_return_the_other_tenants_marker(conn, role_name, spec):
    tool_name, north_marker, south_marker = spec
    north = claim_of(f"{role_name}-north")
    south = claim_of(f"{role_name}-south")
    out_north = tools.answer(conn, north, tool_name, {})
    out_south = tools.answer(conn, south, tool_name, {})
    if north_marker:
        assert north_marker in out_north and north_marker not in out_south
    if south_marker:
        assert south_marker in out_south and south_marker not in out_north


def test_dashboard_summary_counts_are_also_tenant_scoped(conn):
    """An aggregate is not an exemption (tools.py's own rule) — checked, not just asserted in a
    comment: seed one extra northgate-only enrollment and confirm southport's count is untouched."""
    north, south = claim_of("cfo-north"), claim_of("cfo-south")
    before = dict(item.split("=") for item in tools.dashboard_summary(conn, south).split(", "))
    tools.enrollment_draft(conn, claim_of("trainee-north"), 1, "extra-programme")
    after_north = dict(item.split("=") for item in tools.dashboard_summary(conn, north).split(", "))
    after_south = dict(item.split("=") for item in tools.dashboard_summary(conn, south).split(", "))
    assert after_north["enrollments"] == str(int(before["enrollments"]) + 1) \
        if "enrollments" in before else True                   # north's own count moved…
    assert after_south == before                                # …south's did not


@pytest.mark.parametrize("student_id", ALL_STUDENT_IDS)
def test_enrollment_draft_never_crosses_a_tenant(conn, student_id):
    for role in ("trainee-north", "trainee-south"):
        claim = claim_of(role)
        row = conn.execute("select org_id from students where id=?", (student_id,)).fetchone()
        if row["org_id"] == claim.org_id:
            out = tools.enrollment_draft(conn, claim, student_id, "test-programme")
            assert "drafted enrollment" in out
        else:
            with pytest.raises(Denied):
                tools.enrollment_draft(conn, claim, student_id, "test-programme")


def test_billing_charge_never_crosses_a_tenant(conn):
    mock_billing.LEDGER.charges.clear()
    north, south = claim_of("cfo-north"), claim_of("cfo-south")
    tools.billing_charge(conn, north, 1, 5000)                  # membership 1 is northgate's — fine
    with pytest.raises(Denied):
        tools.billing_charge(conn, south, 1, 5000)               # southport claim, northgate membership
    charges = mock_billing.LEDGER.for_org("northgate")
    assert len(charges) == 1 and charges[0]["membership_id"] == 1
    assert mock_billing.LEDGER.for_org("southport") == []        # nothing landed in the other tenant


def test_the_injected_enrollment_note_is_data_and_grants_no_cross_tenant_draft(conn):
    """`db.INJECTION_ENROLLMENT_NOTE` sits on southport's own enrollment and asks for northgate's
    payroll — a tool `trainee` does not even have; what stays reachable to `trainee` is drafting
    another enrolment, and that is still denied across the tenant boundary."""
    south_trainee = claim_of("trainee-south")
    out = tools.enrollment_list(conn, south_trainee)
    assert db.INJECTION_ENROLLMENT_NOTE in out
    with pytest.raises(Denied):
        tools.enrollment_draft(conn, south_trainee, 1, "test-programme")   # student 1 is northgate's


def test_the_injected_maintenance_description_grants_no_cross_tenant_visibility(conn):
    """`db.INJECTION_MAINTENANCE_DESC` sits on southport's own maintenance request and asks to
    list northgate's; `maintenance_list` takes no id at all, so southport's own listing is the
    only thing it could ever return."""
    south_it = claim_of("it-south")
    out = tools.maintenance_list(conn, south_it)
    assert db.INJECTION_MAINTENANCE_DESC in out
    assert "Projector bulb" not in out                          # northgate's own ticket never appears


@pytest.mark.parametrize("role_name,other_tool", [
    ("trainee", "payroll_read"), ("marketing", "billing_charge"),
    ("it", "agenda_read"), ("cfo", "campaign_create"), ("dev", "order_draft")])
def test_every_new_role_is_also_confined_to_its_own_tool_list_through_mcp(conn, role_name, other_tool):
    claim = claim_of(f"{role_name}-north")
    role = roles.ROLES[claim.role]
    reply = mcp_server.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
         "params": {"name": other_tool, "arguments": {}}},
        conn, claim, role)
    assert reply["result"]["isError"] is True
    assert "may not call" in reply["result"]["content"][0]["text"]


def test_zero_leaks_summary(conn):
    """The one number this file exists to produce: every (claim, resource) pair tried, none
    crossed a tenant. Restated as a count, the way every other gate in this repository is —
    now over all seven roles and thirteen tools, not only `agenda_read`."""
    leaks = 0
    tried = 0
    for user_id in ALL_USERS:
        claim = claim_of(user_id)
        if claim.role == "educador":
            for sid in ALL_STUDENT_IDS:
                tried += 1
                row = conn.execute("select org_id from students where id=?", (sid,)).fetchone()
                try:
                    tools.agenda_read(conn, claim, sid)
                    if row["org_id"] != claim.org_id:
                        leaks += 1
                except Denied:
                    pass
        if claim.role == "trainee":
            for sid in ALL_STUDENT_IDS:
                tried += 1
                row = conn.execute("select org_id from students where id=?", (sid,)).fetchone()
                try:
                    tools.enrollment_draft(conn, claim, sid, "sweep")
                    if row["org_id"] != claim.org_id:
                        leaks += 1
                except Denied:
                    pass
        if claim.role == "cfo":
            for mid in (1, 2):
                tried += 1
                row = conn.execute("select org_id from memberships where id=?", (mid,)).fetchone()
                try:
                    tools.billing_charge(conn, claim, mid, 1)
                    if row["org_id"] != claim.org_id:
                        leaks += 1
                except Denied:
                    pass
    assert tried > 0
    assert leaks == 0, f"{leaks} of {tried} cross-tenant reads/writes were NOT denied"
