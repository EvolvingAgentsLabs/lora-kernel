r"""Grading a reply to a walk — what W4's gate and W5's arms both read.

REDESIGN 2 OF THIS INSTRUMENT [ran] 2026-09-19, after an adversarial review of the first grader:

* its `body` rule was an exact substring of the rendered line, `[site]` marker included — a check
  that fails while the capability works, on 57 of the 80 held-out rows. An expert that opened the
  right note and wrote "hold pressure 9 minutes" scored as one that never found the note;
* its number rule accepted any number anywhere in the reply — a check that passes while the
  capability is absent: *"The patient is 15 years old and the nurse waits 8 seconds"* passed a check
  for 15 seconds.

WHAT IS GRADED, AND WHERE.

1. **The walk, where it happens** (the with-library arm only — it is the only arm that has one). The
   referee's own log says which notes were opened. `walk_ok` is: the task was answered, the guard
   never spoke, every step the task asks for was opened in order, the last step of the procedure
   opened is the target (not one short, not one past) — or, for a quantity, the note that supplies
   it was opened; for a rate, the formula note was opened and the calculator was used.
2. **The answer, at the place the corpus teaches it**: the final span, i.e. what the expert wrote
   after the last inline result. Every one of the 600 training rows ends in ONE line of one of four
   forms — `6 mL`, `400 mL/hr`, `Last step carried out: <the line>`, `Not in my library.`
   Content is read off the LAST non-empty line only:
     value  the numbers written *immediately before the unit* on that line — at least one, and all of
            them the right one (within the tolerance for a computed rate). A number that is not
            attached to the unit is not an answer, so a decoy cannot pass;
     body   ATTRIBUTION, not string equality: among every step note of the library, rendered under
            this case's site and case values, the target is (one of) the closest to the line by
            content-word overlap, $s(n) = |W(\text{line}) \cap W(n)| / |W(n)|$, with
            $s(\text{target}) \ge 0.5$ — and every number the target line carries (what the note
            SUPPLIES: a site's seconds, a case's minutes) is on the line;
     none   the line says *not in my library*.

THE STATES. `right` — content holds and the reply is the taught one-line form. `format` — content
holds in another form (a sentence, a different prefix): its own bucket, NOT wrong and NOT right —
fluids on the 4B lost 10 of 90 to a final-line format with every number correct [ran] M7 arm 0c.
`unread` — content holds but the walk shows the supplying note was never opened: for an arm that
claims to read a library, a right answer it did not read is not evidence of reading. `wrong`.
**Credit for a capability claim is `right` or `format`; the contract a client receives is `right`.**
`verbatim` — the first grader's rule — is kept as a reported column named for what it is.

WHAT THIS CANNOT DETECT. An expert that opens the right notes and then writes the right step's words
without having *carried anything out* — there is nothing to carry out in a text task; the walk is the
evidence. Two steps in different procedures that state the same line attribute to each other: those
rows carry `final_is_a_shared_line` and are reported apart. A paraphrase that shares under half the
target's content words scores wrong.
"""
from __future__ import annotations

import re

from memory.layers import render
from memory.notes import Library, Site
from memory.runtime import _words

NUM = r"-?\d+(?:\.\d+)?"
CARRY_PREFIX = "Last step carried out:"
_MARK = re.compile(r"\s*\[(?:site|case)\]")
STATES = ("right", "format", "unread", "wrong")


def final_line(reply: str) -> str:
    lines = [l.strip() for l in (reply or "").splitlines() if l.strip()]
    return lines[-1] if lines else ""


def one_line(reply: str) -> bool:
    return len([l for l in (reply or "").splitlines() if l.strip()]) == 1


def _range(text: str) -> str:
    return re.sub(r"\s*(?:-|to)\s*", "-", text.strip())


def _unit_re(unit: str) -> str:
    return re.escape(unit) + r"(?![\w/])"


def claims(line: str, unit: str) -> list[str]:
    """Numbers (or ranges) written immediately before the unit."""
    return [m.group(1) for m in re.finditer(rf"({NUM}(?:\s*(?:-|to)\s*{NUM})?)\s*{_unit_re(unit)}", line, re.I)]


def _is(check: dict, claim: str) -> bool:
    if "tolerance" in check:
        if re.search(r"(?:-|to)", claim.lstrip("-")):
            return False
        return abs(float(claim) - float(check["value"])) <= check["tolerance"]
    return _range(claim) == _range(str(check["value"]))


def _value(check: dict, reply: str) -> tuple[bool, bool]:
    line = final_line(reply)
    said = claims(line, check["unit"])
    content = bool(said) and all(_is(check, c) for c in said)
    canonical = one_line(reply) and bool(re.fullmatch(
        rf"{NUM}(?:\s*(?:-|to)\s*{NUM})?\s*{_unit_re(check['unit'])}\.?", line, re.I))
    return content, canonical


def _none(reply: str) -> tuple[bool, bool]:
    line = final_line(reply).lower()
    return "not in my library" in line, one_line(reply) and line.rstrip(".") == "not in my library"


def clean(body: str) -> str:
    return " ".join(_MARK.sub("", body).split())


def _content_words(text: str) -> set[str]:
    return {w for w in _words(clean(text)) if not re.fullmatch(NUM, w)}


def step_bodies(lib: Library, row: dict) -> dict[str, str]:
    """Every step note of the library as this case's conversation would show it."""
    p = row.get("replay") or {}
    site = Site(name="case-site", overrides=p["site"]) if p.get("site") else None
    case = p.get("case") or {}
    return {n.id: clean(render(n, site, case.get(n.id))) for n in lib.notes.values() if n.kind == "step"}


def attribute(line: str, bodies: dict[str, str]) -> tuple[list[str], dict[str, float]]:
    w = _content_words(line)
    score = {i: (len(w & _content_words(b)) / len(_content_words(b)) if _content_words(b) else 0.0)
             for i, b in bodies.items()}
    top = max(score.values(), default=0.0)
    return [i for i, s in score.items() if s == top and top > 0], score


def target_of(lib: Library, row: dict) -> str | None:
    """The step a carry task ends on."""
    if row["family"] != "carry":
        return None
    steps = lib.walk(row["procedure"])
    k, m = row["meta"]["k"], row["meta"]["m"]
    return steps[k + m - 1]


def _body(lib: Library, row: dict, reply: str) -> tuple[bool, bool]:
    line = final_line(reply)
    canonical = one_line(reply) and line.startswith(CARRY_PREFIX)
    said = line[len(CARRY_PREFIX):] if line.startswith(CARRY_PREFIX) else line
    bodies = step_bodies(lib, row)
    target = target_of(lib, row)
    closest, score = attribute(said, bodies)
    # Two notes that render to the same line are one line: a tie with the target is the target.
    attributed = target in closest and score[target] >= 0.5
    supplied = set(re.findall(NUM, bodies[target]))
    return attributed and supplied <= set(re.findall(NUM, said)), canonical


def walk_evidence(conv, carried: int, chain: dict | None = None) -> dict:
    """What the referee's record says about one served conversation. `carried` = steps resumed."""
    return {"opened": list(conv.opened[carried:]), "answered": bool(conv.answered),
            "violations": [v["kind"] for v in conv.guard.violations],
            "calcs": sum(1 for l in conv.log if l["verb"] == "calc" and not l.get("error")),
            "errors": dict(conv.errors), "ended": conv.ended,
            "ran_out": bool(chain and chain.get("ran_out"))}


def walk_ok(lib: Library, row: dict, walk: dict) -> bool:
    if not walk["answered"] or walk["violations"] or walk.get("ran_out"):
        return False
    opened = walk["opened"]
    if row["family"] == "none":
        return True
    if row["family"] == "carry":
        steps = lib.walk(row["procedure"])
        k, m = row["meta"]["k"], row["meta"]["m"]
        mine = [i for i in opened if i in set(steps)]
        return mine == steps[k:k + m]            # in order, none skipped, not one past
    supplying = row["walk"][-1]
    if row["family"] == "rate":
        return supplying in opened and walk["calcs"] > 0
    return supplying in opened


def grade(lib: Library, row: dict, reply: str, walk: dict | None = None) -> dict:
    """`reply` is the FINAL SPAN — what was written after the last inline result (the whole reply
    for an arm with no verbs). `walk` is `walk_evidence(...)` for the arm that has a walk."""
    kind = row["check"]["kind"]
    if kind == "none":
        content, canonical = _none(reply)
    elif kind == "body":
        content, canonical = _body(lib, row, reply)
    else:
        content, canonical = _value(row["check"], reply)
    read = walk_ok(lib, row, walk) if walk is not None else None
    if not content:
        state = "wrong"
    elif read is False:
        state = "unread"
    else:
        state = "right" if canonical else "format"
    out = {"state": state, "content": content, "canonical": canonical, "walk_ok": read,
           "credit": state in ("right", "format")}
    if kind == "body":
        out["verbatim"] = " ".join(row["check"]["body"].split()).lower() in " ".join((reply or "").split()).lower()
    return out
