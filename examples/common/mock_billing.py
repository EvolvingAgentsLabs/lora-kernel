"""Stands in for Stripe: records a charge against a membership, opens no network connection.

Same principle as `mock_auth.py` for identity: the *mechanism* under test is that a tool
decides permission and scope itself, never a payments provider's dashboard or a model's word
for it. A real deployment swaps this module for a Stripe client without touching `tools.py`'s
call sites — `charge()` and `status()` are the whole surface either one has to provide.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Ledger:
    charges: list[dict] = field(default_factory=list)

    def charge(self, org_id: str, membership_id: int, amount_cents: int) -> dict:
        row = {"org_id": org_id, "membership_id": membership_id, "amount_cents": amount_cents,
              "id": len(self.charges) + 1}
        self.charges.append(row)
        return row

    def for_org(self, org_id: str) -> list[dict]:
        return [c for c in self.charges if c["org_id"] == org_id]


LEDGER = Ledger()
