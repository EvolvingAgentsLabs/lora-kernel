r"""The grader of W9 — the answer, and the citation that makes it verifiable (docs/MEMORY.md §1.6).

The final line is `answer [id§anchor]`. Three readings, each mechanical:

    value right   every token of the expected value (a number, a time, a name) is on the line,
                  outside the citation, and no other number is: a line that lists 18 and 40 hedges
    verified      the citation names a statement that (a) this conversation showed — the id is one
                  a result displayed, mapped back through the referee's own table — (b) the walk
                  OPENED, and (c) whose text, as the referee rendered it, holds every value token
    state         right = value right AND verified · unverified = value right, citation fails ·
                  wrong = otherwise.  `Not in my library.` is right on a question the wiki cannot answer

CREDIT IS `right` ONLY. A right number the walk cannot show it read is `unverified` and is reported
apart — the memory is verifiable only if the check is on the statement, not on the number
(the lesson of W4's grader: a reader that got lucky over the wrong note is invisible to a final score).
The closed-book arm has no conversation, so it can only ever be `unverified`: its gate reads
`value_right`, because what it measures is whether the value is in the weights.
"""
from __future__ import annotations

import re

CITE = re.compile(r"\[([a-z0-9]{3})§([a-z0-9][a-z0-9-]*)\]")
_NUM = re.compile(r"\d+(?::\d+)?")
NONE = "not in my library"


def final_line(reply: str) -> str:
    lines = [l.strip() for l in (reply or "").strip().splitlines() if l.strip()]
    return lines[-1] if lines else ""


def _norm(n: str) -> str:
    """`06:00` and `6:00` are one time; `018` and `18` one number."""
    h, _, m = n.partition(":")
    return f"{int(h)}:{m}" if m else str(int(h))


def _has(text: str, token: str) -> bool:
    if _NUM.fullmatch(token):
        return _norm(token) in {_norm(n) for n in _NUM.findall(text)}
    return token.lower() in text.lower()


def value_right(row: dict, line: str) -> bool:
    plain = CITE.sub(" ", line)
    if row["check"]["kind"] == "none":
        return NONE in plain.lower()
    toks = row["check"]["tokens"]
    if not toks or not all(_has(plain, t) for t in toks):
        return False
    if any(_has(plain, t) for t in row["check"].get("never", [])):
        return False
    wanted = {_norm(t) for t in toks if _NUM.fullmatch(t)}
    if not wanted:                       # a name: a restated "Brisk-40" is not a second answer
        return True
    # a number the question itself states (a product's "-40", an invoice's amount) is not a hedge
    asked = {_norm(n) for n in _NUM.findall(row.get("question", ""))}
    extra = {_norm(n) for n in _NUM.findall(plain)} - wanted - asked
    return not extra


def citation(conv, line: str) -> dict:
    """What the line cites and whether it holds — against the referee's own record of the walk."""
    m = None
    for m in CITE.finditer(line):
        pass
    if m is None:
        return {"cited": None, "verified": False, "why": "no citation"}
    shown, anchor = m.group(1), m.group(2)
    if conv is None or shown not in conv.shown:
        return {"cited": f"{shown}§{anchor}", "verified": False, "why": "an id this conversation never showed"}
    nid = conv.shown[shown]
    if (nid, anchor) not in conv.statements:
        return {"cited": [nid, anchor], "verified": False, "why": "a statement the walk did not open"}
    return {"cited": [nid, anchor], "verified": True, "text": conv._statement_text(conv.lib[nid], anchor)}


def grade(row: dict, reply: str, conv=None) -> dict:
    line = final_line(reply)
    ok = value_right(row, line)
    if row["check"]["kind"] == "none":
        return {"state": "right" if ok else "wrong", "value_right": ok, "verified": ok, "line": line[-200:]}
    c = citation(conv, line)
    holds = c["verified"] and all(_has(c.get("text", ""), t) for t in row["check"]["tokens"])
    if c["verified"] and not holds:
        c["why"] = "the cited statement does not hold the value"
    state = "right" if (ok and holds) else ("unverified" if ok else "wrong")
    return {"state": state, "value_right": ok, "verified": bool(holds), "cited": c["cited"],
            "why": None if holds else c.get("why"), "supporting": list(row["support"]) if row.get("support") else None,
            "cited_the_supporting": bool(row.get("support")) and c["cited"] == list(row["support"]), "line": line[-200:]}
