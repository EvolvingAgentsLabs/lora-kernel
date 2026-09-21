"""The distributor's test identities — see examples/school/users.py for why this is one
source shared by the MCP server and the adversarial suite."""
from __future__ import annotations

from ..common import mock_auth

SEED_USERS = (
    ("customer_service-riverside", "customer_service", "riverside"),
    ("dispatch-riverside", "dispatch", "riverside"),
    ("receiving-riverside", "receiving", "riverside"),
    ("purchasing-riverside", "purchasing", "riverside"),
    ("claims_returns-riverside", "claims_returns", "riverside"),
    ("it-riverside", "it", "riverside"),
    ("customer_service-harbor", "customer_service", "harbor"),
    ("dispatch-harbor", "dispatch", "harbor"),
    ("receiving-harbor", "receiving", "harbor"),
    ("purchasing-harbor", "purchasing", "harbor"),
    ("claims_returns-harbor", "claims_returns", "harbor"),
    ("it-harbor", "it", "harbor"),
)


def register_all() -> None:
    for user_id, role, org_id in SEED_USERS:
        mock_auth.register(user_id, role, org_id)
