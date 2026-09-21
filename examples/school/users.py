"""The school's test identities — one source, used by the MCP server and the adversarial
suite, so a case run through either sees the same claims."""
from __future__ import annotations

from ..common import mock_auth

SEED_USERS = (
    ("educador-north", "educador", "northgate"),
    ("compras-north", "compras", "northgate"),
    ("trainee-north", "trainee", "northgate"),
    ("marketing-north", "marketing", "northgate"),
    ("it-north", "it", "northgate"),
    ("cfo-north", "cfo", "northgate"),
    ("dev-north", "dev", "northgate"),
    ("educador-south", "educador", "southport"),
    ("compras-south", "compras", "southport"),
    ("trainee-south", "trainee", "southport"),
    ("marketing-south", "marketing", "southport"),
    ("it-south", "it", "southport"),
    ("cfo-south", "cfo", "southport"),
    ("dev-south", "dev", "southport"),
)


def register_all() -> None:
    for user_id, role, org_id in SEED_USERS:
        mock_auth.register(user_id, role, org_id)
