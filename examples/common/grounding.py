"""What a reply may state — checked against the real tool results, outside the model.

WHY. The school-staff LoRA learnt the protocol and still, after a real result, sometimes writes more lines in
the result's own format and restates them as data ("early pickup: Approved, 3:15 pm" on an agenda that held
one entry), and it quotes a planted instruction as content **[ran]** results/M8-school-staff-20260925. The
architecture's rule for anything that must not depend on the model's behaviour is to enforce it where the
model cannot reach: the gateway holds every real tool result, so it decides what a reply may say.

    ground(reply, results)   every item of the reply must occur in a real tool result; if one does not, the
                             reply is REPLACED by the tools' own text — the user never sees an invented line.
                             Returns (reply, "kept" | "replaced" | "no_result"); "replaced" is the model's
                             fabrication, counted, not hidden
    redact(text)             instruction-shaped text found inside data ("[SYSTEM OVERRIDE: …]", "ignore prior
                             instructions …") is removed from what is shown; the record itself is untouched

Mechanical and conservative on purpose: an item is a clause of the reply (split on `;` and line breaks, list
markers and a restating prefix stripped); it is grounded if it occurs, whitespace- and case-normalised, in a
result. A paraphrase that is true is replaced too — the price of a guarantee, paid in wording, not in facts.
"""
from __future__ import annotations

import re

PREFIXES = ("según el sistema:", "according to the system:", "hecho:", "done:", "listo:")
_INJECTION = re.compile(r"\[?\s*(system override|ignore (?:all |your |the )?(?:prior|previous) instructions|disregard your instructions)"
                        r"[^\]\n]*\]?", re.I)
REDACTED = "[instruction in the record removed]"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .;:-").lower()


def redact(text: str) -> str:
    return _INJECTION.sub(REDACTED, text)


def items(reply: str) -> list[str]:
    body = reply.strip()
    for p in PREFIXES:
        if body.lower().startswith(p):
            body = body[len(p):]
    out = []
    for part in re.split(r";|\n", body):
        part = _norm(part.lstrip("-•* "))
        if len(part) >= 4:
            out.append(part)
    return out


def grounded(reply: str, results: list[str]) -> bool:
    pool = _norm(" \n ".join(results))
    return all(i in pool for i in items(reply))


def fallback(results: list[str], spanish: bool) -> str:
    lines = [l.strip("- ").strip() for r in results for l in r.splitlines() if l.strip()]
    return ("Según el sistema: " if spanish else "According to the system: ") + "; ".join(lines) + "."


def ground(reply: str, results: list[str], spanish: bool = True) -> tuple[str, str]:
    results = [r for r in results if r and r.strip()]
    if not results:
        return reply, "no_result"
    if grounded(reply, results):
        return reply, "kept"
    return fallback(results, spanish), "replaced"
