"""Stands in for Auth0/Keycloak: issues a `Claim`, opens no network connection, calls no API.

docs/FRAMEWORK.md §9 gap row E: "identity must flow runtime -> proxy -> tool; the model never
holds a credential." Here the claim is registered once per test user, exactly as a real agent
runtime attaches a verified token's claims to each call before a tool ever runs — this file is
the fake identity provider, not a shortcut around checking one. An id nobody registered is
refused, never served as if it were nobody in particular.
"""
from __future__ import annotations

from .permissions import Claim

_DIRECTORY: dict[str, Claim] = {}


def register(user_id: str, role: str, org_id: str) -> Claim:
    """Called once, when a test user (or a real one, later, off a real token) is set up."""
    claim = Claim(user_id=user_id, role=role, org_id=org_id)
    _DIRECTORY[user_id] = claim
    return claim


def issue_claim(user_id: str) -> Claim:
    """The one call a tool layer trusts. `KeyError` becomes `PermissionError`: an unknown
    caller is a denial, not a guess at who they might be."""
    try:
        return _DIRECTORY[user_id]
    except KeyError:
        raise PermissionError(f"no claim for {user_id!r} — not signed in") from None
