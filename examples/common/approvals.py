"""Writes that wait for a person — enforced in the tool layer, never by what a model says.

WHY. A cheap local model that can call `billing_charge` is only safe if the charge cannot happen
because the model asked: the tool must hold it until a person with the authority to approve it
says so. Before this module the school's `billing_charge` executed on the call — the demo document
promised an approval step the code did not have **[ran]** 2026-09-25, read in `examples/school/tools.py`.

THE RULE. A tool in `NEEDS_APPROVAL` is not executed on the model's call: the call is recorded as a
pending request and the model is told so in the tool result. `approve(id, claim)` executes it, with
the REQUESTER's claim (the scope is the requester's tenant, never the approver's), only if the
approver's role is one of that tool's approvers, the approver is in the same tenant, and the
approver is not the requester. `reject` closes it. Nothing a model writes reaches `approve`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .permissions import Claim, Denied

# tool → the roles whose person may approve it: a director, never the role that asked (the school's two outward-facing writes)
NEEDS_APPROVAL = {"billing_charge": ("director",), "announcement_post": ("director",)}


@dataclass
class Queue:
    items: list[dict] = field(default_factory=list)

    def hold(self, claim: Claim, tool: str, args: dict) -> str:
        item = {"id": len(self.items) + 1, "tool": tool, "args": dict(args), "requested_by": claim,
                "status": "pending", "result": None, "decided_by": None}
        self.items.append(item)
        return (f"PENDING APPROVAL #{item['id']}: {tool} {args} is held until a person approves it — "
                f"it has not been executed")

    def pending(self, claim: Claim) -> list[dict]:
        return [i for i in self.items if i["status"] == "pending" and i["requested_by"].org_id == claim.org_id]

    def _item(self, item_id: int, approver: Claim) -> dict:
        item = next((i for i in self.items if i["id"] == item_id), None)
        if item is None or item["status"] != "pending":
            raise KeyError(f"no pending request #{item_id}")
        req = item["requested_by"]
        if approver.org_id != req.org_id:
            raise Denied(f"{approver.user_id}@{approver.org_id} may not decide a request of org {req.org_id!r}")
        if approver.role not in NEEDS_APPROVAL[item["tool"]]:
            raise Denied(f"a {approver.role} may not approve {item['tool']}")
        if approver.user_id == req.user_id:
            raise Denied("a request is not approved by the account that made it")
        return item

    def approve(self, item_id: int, approver: Claim, execute) -> str:
        """`execute(claim, tool, args)` runs the tool — with the requester's claim."""
        item = self._item(item_id, approver)
        item["result"] = execute(item["requested_by"], item["tool"], item["args"])
        item["status"], item["decided_by"] = "approved", approver.user_id
        return item["result"]

    def reject(self, item_id: int, approver: Claim) -> None:
        item = self._item(item_id, approver)
        item["status"], item["decided_by"] = "rejected", approver.user_id
