"""Why a case failed: the tool layer, or the physics.

WHY THIS EXISTS. P21's rule arm writes **93 of 96** tool calls correctly and still
scores 5 of 30 [ran] `results/P21-handbook-20260911/`. A single accuracy number
cannot tell those two facts apart, so it cannot say whether the next thing to fix
is the protocol or the expert — and those are different projects.

HOW THE VERDICT IS REACHED, and why not by exception type. The obvious taxonomy is
`SyntaxError` against `LogicError`: did the call parse. That is the wrong cut. A
malformed call that the tool happens to accept is not a protocol success, and a
perfectly-formed `lookup` with the wrong fluid is not a physics failure. So the
oracle decides instead: **did this arm obtain the values the oracle obtained?**

    rejected > 0            malformed   the tool refused the call
    accepted < wanted       missing     it did not ask where the oracle asked
    matched  < wanted       wrong args  it asked, and got a different value
    otherwise               physics     it held every value and still answered wrong

The first three are the tool layer's. The last one is the expert's, and no amount
of protocol work will move it.

THIS IS COMPUTED FROM WHAT THE RUNNER ALREADY RECORDS, so it applies to runs that
are already finished — including the two P21 arms that reported before it existed.
"""

from __future__ import annotations

MODES = ("malformed", "missing", "wrong args", "physics")


def classify(rec: dict) -> str | None:
    """The failure mode of one scored case, or None if it passed."""
    if rec["passed"]:
        return None
    accepted = rec["queries"] - rec["rejected"]
    if rec["rejected"] > 0:
        return "malformed"
    if accepted < rec["wanted"]:
        return "missing"
    if rec["matched"] < rec["wanted"]:
        return "wrong args"
    return "physics"


def tally(records: list[dict]) -> dict:
    """Counts per mode, plus the one number the taxonomy exists to produce."""
    counts = {m: 0 for m in MODES}
    for r in records:
        m = classify(r)
        if m:
            counts[m] += 1
    failed = sum(counts.values())
    protocol = failed - counts["physics"]
    return {"failed": failed, "by_mode": counts,
            "protocol": protocol, "physics": counts["physics"],
            "share_physics": round(counts["physics"] / failed, 3) if failed else None}
