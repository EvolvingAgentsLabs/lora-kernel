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

WHAT WAITS FOR A PERSON SURVIVES A RESTART. With `journal=<path>` every step is appended to a JSON-lines file — `held`,
`executing`, `approved` / `rejected` — and the queue is rebuilt from it on start. The order is the guarantee: `executing`
is written BEFORE the tool runs, so a process that dies mid-execution comes back with that request `interrupted` — shown
to the approver, never run again on its own. A held charge is executed at most once, with the requester's scope. The
operational memory stays ephemeral on purpose (docs/MECHANISMS.md §8); only what waits for a person persists.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .permissions import Claim, Denied

# tool → the roles whose person may approve it: a director, never the role that asked (the school's two outward-facing writes)
NEEDS_APPROVAL = {"billing_charge": ("director",), "announcement_post": ("director",)}


@dataclass
class Queue:
    items: list[dict] = field(default_factory=list)
    journal: str | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self):
        if self.journal and Path(self.journal).exists():
            for line in Path(self.journal).read_text().splitlines():
                if line.strip():
                    self._replay(json.loads(line))
            for i in self.items:
                if i["status"] == "executing":          # died between `executing` and its outcome: never re-run
                    i["status"] = "interrupted"

    def _write(self, ev: dict) -> None:
        if self.journal:
            Path(self.journal).parent.mkdir(parents=True, exist_ok=True)
            with open(self.journal, "a") as f:
                f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), **ev}, ensure_ascii=False) + "\n")
                f.flush()

    def _replay(self, ev: dict) -> None:
        if ev["ev"] == "held":
            r = ev["requested_by"]
            self.items.append({"id": ev["id"], "tool": ev["tool"], "args": ev["args"],
                               "requested_by": Claim(r["user_id"], r["role"], r["org_id"]),
                               "status": "pending", "result": None, "decided_by": None})
            return
        item = next(i for i in self.items if i["id"] == ev["id"])
        item["status"] = ev["ev"]
        item["decided_by"] = ev.get("decided_by", item["decided_by"])
        item["result"] = ev.get("result", item["result"])

    def hold(self, claim: Claim, tool: str, args: dict) -> str:
        with self._lock:
            item = {"id": len(self.items) + 1, "tool": tool, "args": dict(args), "requested_by": claim,
                    "status": "pending", "result": None, "decided_by": None}
            self.items.append(item)
            self._write({"ev": "held", "id": item["id"], "tool": tool, "args": item["args"],
                         "requested_by": {"user_id": claim.user_id, "role": claim.role, "org_id": claim.org_id}})
        return (f"PENDING APPROVAL #{item['id']}: {tool} {args} is held until a person approves it — "
                f"it has not been executed")

    def pending(self, claim: Claim) -> list[dict]:
        """What waits for this tenant's approver — `interrupted` included, so a person decides what to do with it."""
        return [i for i in self.items if i["status"] in ("pending", "interrupted") and i["requested_by"].org_id == claim.org_id]

    def _item(self, item_id: int, approver: Claim, allow_interrupted: bool = False) -> dict:
        item = next((i for i in self.items if i["id"] == item_id), None)
        ok = ("pending", "interrupted") if allow_interrupted else ("pending",)
        if item is None or item["status"] not in ok:
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
        with self._lock:
            item = self._item(item_id, approver)
            item["status"] = "executing"
            self._write({"ev": "executing", "id": item_id, "decided_by": approver.user_id})
        result = execute(item["requested_by"], item["tool"], item["args"])
        with self._lock:
            item["result"], item["status"], item["decided_by"] = result, "approved", approver.user_id
            self._write({"ev": "approved", "id": item_id, "decided_by": approver.user_id, "result": str(result)[:500]})
        return result

    def reject(self, item_id: int, approver: Claim) -> None:
        with self._lock:
            item = self._item(item_id, approver, allow_interrupted=True)
            item["status"], item["decided_by"] = "rejected", approver.user_id
            self._write({"ev": "rejected", "id": item_id, "decided_by": approver.user_id})
