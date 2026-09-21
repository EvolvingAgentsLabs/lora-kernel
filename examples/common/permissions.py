"""The tool layer's permission check — outside the model, per docs/FRAMEWORK.md §9 gap row E.

WHY THIS FILE EXISTS AND IS THIS SHORT. The pasted architecture that started this (see
docs/FRAMEWORK.md §9, docs/PLAN.md §0 addendum 2026-09-20) named Auth0 and Postgres row-level
security. Those are one *implementation* of one *principle*: a tool call carries who is asking,
and checks it before a row crosses the boundary, in code the model never sees and cannot argue
with. This module is that principle, minimal enough to read in one sitting and to run with
sqlite and zero external services — the falsifier this repository can actually afford today.
Standing up Auth0 and Postgres RLS is deferred until this version is shown insufficient
(docs/FRAMEWORK.md §7 step 4).

A tool always calls `enforce_org` first (the tenant boundary — the biggest, cheapest-to-get-
wrong leak: one customer's data reaching another customer's agent) and `enforce_owner` when a
row also has a narrower owner within the tenant. Both raise `Denied`, never return a flag a
caller could forget to check.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Claim:
    """What a verified identity token's claims collapse to, for one tool call.

    In a real deployment this is attached by the agent runtime after checking a JWT (Auth0,
    Keycloak, whatever an org already runs); `mock_auth.py` stands in for that check. The
    model is never shown this object and cannot construct one: it is attached by the harness
    that drives the request, before the model's turn begins.
    """
    user_id: str
    role: str
    org_id: str


class Denied(PermissionError):
    """Raised by a tool, before a row is read or written — never a text refusal a model wrote.
    An adversarial suite counts these; a row that reaches the model without one raising is a
    leak, however politely the model then declines to repeat it."""


def enforce_org(claim: Claim, org_id: str) -> None:
    """The tenant boundary. No role, however senior, crosses it — a school district's own
    finance officer still may not read a different district's students."""
    if org_id != claim.org_id:
        raise Denied(f"{claim.user_id} ({claim.role}@{claim.org_id}) asked for a row in "
                     f"org {org_id!r} — different tenant, refused before it was read")


def enforce_owner(claim: Claim, owner_ids: tuple[str, ...]) -> None:
    """A narrower boundary inside one tenant: the claim's own user must be among the row's
    permitted owners (e.g. a guardian and their own children). `owner_ids` is resolved by the
    tool from the database, never guessed from the claim or trusted from the caller's text."""
    if claim.user_id not in owner_ids:
        raise Denied(f"{claim.user_id} is not among the permitted owners {owner_ids!r}")
