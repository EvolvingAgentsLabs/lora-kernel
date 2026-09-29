"""The tracker's test identities — one developer, one lead and one QA per organisation (see examples/school/users.py)."""
from __future__ import annotations

from ..common import mock_auth

SEED_USERS = (
    ("developer-riverdev", "developer", "riverdev"),
    ("lead-riverdev", "lead", "riverdev"),
    ("qa-riverdev", "qa", "riverdev"),
    ("developer-harborworks", "developer", "harborworks"),
    ("lead-harborworks", "lead", "harborworks"),
    ("qa-harborworks", "qa", "harborworks"),
)


def register_all() -> None:
    for user_id, role, org_id in SEED_USERS:
        mock_auth.register(user_id, role, org_id)
