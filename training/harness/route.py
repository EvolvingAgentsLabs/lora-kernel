"""Milestone 2 — routing per request: the proxy decides local or frontier, the client
names no model.

WHAT WAS TRUE BEFORE THIS FILE. The route was by model name (`openai_proxy.routes_out`):
an agent asked for `email-full` and got the local expert, asked for anything else and
was forwarded. That is a provider, not a service — the client had to know the pool.

WHAT THIS ADDS, AND HOW LITTLE IT IS. A request for the alias (`--auto`) is classified
by the text it carries — the system prompt and the last user turn — against the
keyword surface each region declares here, and

    exactly one region matches and it is served locally   → the member's name
    the region is one the pool is measured to fail         → the frontier (P40, P41)
    no region, or two                                      → the frontier

The classifier is a dictionary because a dictionary is at **1.000** on the coarse route
over 200 generated cases **[ran]** `tests/test_router_baseline.py`, and a learned
router is priced only once the dictionary fails on real traffic (milestone 4).

THE MATHEMATICS IS THE DELIVERED ACCURACY UNDER A POLICY (FOUNDATIONS §8.4). With
$r(x)$ the route the policy gives case $x$, $L_m(x)$ whether member $m$ answers it
right and $F(x)$ whether the frontier does,

    delivered(policy) = (1/n) Σ_x [ r(x) = (local, m*(x)) ]·L_{m*}(x)
                              + [ r(x) = out ]·F(x)
                              + [ r(x) = (local, m ≠ m*(x)) ]·0

— a case handed to the wrong member counts as wrong by construction, which is the
conservative reading. The by-region policy of P41 is the special case
$r(x) = \\text{region}(x)$ read off a label; per-request replaces the label by the
classifier and can only lose, by exactly the misroutes. `replay` computes both on
P41's records, zero GPU.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


ENVELOPE = re.compile(r"<<<BEGIN_[A-Z_]*INTERNAL_CONTEXT>>>.*?<<<END_[A-Z_]*INTERNAL_CONTEXT>>>", re.S)


@dataclass(frozen=True)
class Region:
    member: str
    keys: tuple[str, ...]
    serve: str              # "local" | "out" — out = measured to fail (P40 / P41)
    # THE MARK IS ONLY AS GOOD AS ITS MEASUREMENT. `fluids-full` is `out` on 11/90, and that was
    # the serving path: through `tool_calls` messages it never saw its results where it had learned
    # to read them. Inline, as its corpus taught, it is 90/90 against the frontier's 66 [ran] M7
    # arm 0b. The mark changes when the member is back through the release gate, not before.
    # IT WENT BACK THROUGH, ON THE POOL'S BASE, AND DID NOT PASS: retrained on Qwen3.5-4B it is 80/90
    # against its own 90/90 (0:10 paired) [ran] M7 arm 0c — ten venturi chains right to the number
    # that end in an `<answer>` tag the corpus never taught. The mark stays `out`.


# The keys are the router baseline's, moved next to the decision they inform. Written
# knowing the generators, which makes them generous — the direction that is
# conservative for "no learned router yet", and the reason milestone 4 re-measures.
# A REGION IS ITS QUESTION, NOT ITS LISTING. Two members can share one inbox: the
# triage expert and the desk expert both read `From: / Subject: / Preview:`, and keyed
# on those the desk's prompts route to triage 15 of 60 times [ran] P64, zero GPU. Keyed
# on what is asked — "is this important" against "did you commit" — the four prompt
# sets separate 60/60, 60/60, 150/150, 140/140.
REGIONS: dict[str, Region] = {
    "email-full": Region("email-full", ("is this important",), "local"),
    "desk-commitment": Region("desk-commitment", ("did you commit", "already established", "promise"), "local"),
    "fluids-full": Region("fluids-full", (
        "head loss", "friction", "roughness", "bore", "pumped",
        "gate", "plate", "thrust", "submerged", "hydrostatic",
        "venturi", "throat", "constriction", "manometer",
        "channel", "manning", "slope", "trapezoid",
        "gauge pressure", "flat base", "flat bottom", "horizontal floor", "tank",
        "what is the", "report the", "state its"), "out"),
}


def text_of(req: dict) -> str:
    """The last user turn, and only that.

    THE SYSTEM PROMPT IS THE RUNTIME'S, NOT THE REQUEST'S SUBJECT. The first live
    OpenClaw turn (P63 **[ran]** 2026-09-18) arrived as 21 messages and 54 tools, and
    its system prompt — OpenClaw's own instructions about channels, gates, tanks and
    slopes of its tooling — out-scored the email listing in the user turn, so `auto`
    routed a triage request out as fluids. The proxy refused it (503) rather than serve
    it wrong, which is what the 503 is for. Tool results and history are not the
    subject either. A content part list (OpenAI's `[{"type": "text", …}]`) is read as
    its text parts."""
    msgs = req.get("messages") or []
    # THE TRAILING RUN OF USER MESSAGES, NOT THE LAST ONE. OpenClaw sends the user's
    # text as one `user` message and then a second `user` message carrying its own
    # `<<<BEGIN_OPENCLAW_INTERNAL_CONTEXT>>>` envelope (P63 [ran]); read alone, that
    # envelope is "no region". So every user message after the last non-user turn is
    # the subject, with any runtime envelope cut out.
    # AND ON A FOLLOW-UP, THE LAST REAL USER TURN ANYWHERE. After a tool call the
    # request ends `assistant(tool_calls) · tool · user(envelope)`: the trailing user
    # run is the envelope alone, "no region", and the turn dies in a 503 loop
    # (P63 attempt 2 [ran]). The subject is the last user message that still says
    # something once the envelope is cut out.
    # AND A RUNTIME'S FINALISATION REQUEST HAS NO LISTING IN ITS LAST USER TURN AT
    # ALL: after the tool round-trip OpenClaw asks for a summary with 0 tools and its
    # own instruction as the user turn — "no region", 503, "finalization failed"
    # [ran]. The subject of a conversation is all of its user text.
    parts = []
    for m in msgs:
        if m.get("role") != "user":
            continue
        c = m.get("content")
        if isinstance(c, list):
            c = "\n".join(str(x.get("text", "")) for x in c if isinstance(x, dict))
        if isinstance(c, str):
            c = ENVELOPE.sub("", c).strip()
            if c:
                parts.append(c)
    return "\n".join(parts)


def classify(text: str, regions: dict[str, Region] = REGIONS) -> str | None:
    """The region whose keys occur most; none on a tie or a miss."""
    t = text.lower()
    scores = sorted(((sum(t.count(k) for k in r.keys), name) for name, r in regions.items()),
                    reverse=True)
    if not scores or scores[0][0] == 0:
        return None
    if len(scores) > 1 and scores[0][0] == scores[1][0]:
        return None
    return scores[0][1]


def decide(req: dict, regions: dict[str, Region] = REGIONS) -> tuple[str, str]:
    """('local', member) or ('out', why)."""
    name = classify(text_of(req), regions)
    if name is None:
        return ("out", "no region")
    r = regions[name]
    return ("local", name) if r.serve == "local" else ("out", f"{name} is served out")


# --- the replay on P41's records (zero GPU) ----------------------------------------

def replay(pool: dict, frontier: dict, inbox_n: int = 150, inbox_seed: int = 717171,
           regions: dict[str, Region] = REGIONS) -> dict:
    """delivered(by request) beside delivered(by region) on the same cases."""
    from training.email.inbox import generate
    from training.harness.generate_email_full import listing

    email = pool["arms"]["email-full"]["records"]
    email = email if isinstance(email, list) else list(email.values())
    fluids = pool["arms"]["fluids-full"]["records"]
    fluids = fluids if isinstance(fluids, list) else list(fluids.values())
    front = {r["id"]: bool(r["passed"]) for r in frontier["records"]}
    inbox = {m["id"]: m for m in generate(inbox_n, inbox_seed)["messages"]}

    cases = []
    for r in email:
        m = inbox.get(r["id"])
        if m is None:
            continue
        cases.append({"id": r["id"], "true": "email-full", "text": listing(m),
                      "local": bool(r["correct"]), "frontier": None})
    for r in fluids:
        cases.append({"id": r["id"], "true": "fluids-full", "text": r["statement"],
                      "local": bool(r["passed"]), "frontier": front.get(r["id"])})

    def deliver(route, c):
        if route[0] == "out":
            return bool(c["frontier"]) if c["frontier"] is not None else False
        return c["local"] if route[1] == c["true"] else False

    by_region = by_request = misrouted = out = 0
    for c in cases:
        rr = regions[c["true"]]
        by_region += deliver(("local", c["true"]) if rr.serve == "local" else ("out", ""), c)
        d = decide({"messages": [{"role": "user", "content": c["text"]}]}, regions)
        if d[0] == "local" and d[1] != c["true"]:
            misrouted += 1
        out += d[0] == "out"
        by_request += deliver(d, c)
    n = len(cases)
    return {"n": n, "email": sum(c["true"] == "email-full" for c in cases),
            "fluids": sum(c["true"] == "fluids-full" for c in cases),
            "by_region": {"delivered": by_region, "accuracy": round(by_region / n, 4)},
            "by_request": {"delivered": by_request, "accuracy": round(by_request / n, 4),
                           "misrouted": misrouted, "out": out, "out_share": round(out / n, 4)},
            "ties_by_region": by_request == by_region and misrouted == 0}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pool", default="results/P41-routing-20260915/pool_results.json")
    ap.add_argument("--frontier", default="results/P41-routing-20260915/frontier_fluids.json")
    ap.add_argument("--out", default="results/P62-route-per-request-20260918/replay.json")
    a = ap.parse_args()
    r = replay(json.loads(Path(a.pool).read_text()), json.loads(Path(a.frontier).read_text()))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(r, indent=1))
    print(f"[route] by region {r['by_region']['accuracy']} · by request {r['by_request']['accuracy']} "
          f"· misrouted {r['by_request']['misrouted']} · out {r['by_request']['out_share']} "
          f"→ {'TIES' if r['ties_by_region'] else 'LOSES'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
