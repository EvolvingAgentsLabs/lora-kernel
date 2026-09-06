#!/usr/bin/env python3
"""Every document has a Spanish mirror, and the mirror is not behind.

Ported from `ai-os`, which learned it the hard way: two documents had no mirror
at all and five had one that was behind — one was missing three whole
experiments. **A stale mirror is worse than an absent one.** The absent one sends
a reader to the English; the stale one answers confidently and wrongly.

Section count is the proxy, and it is deliberately a weak one. It catches the
failure that actually happens — a section added on one side and not the other —
and it cannot catch a paragraph that drifted. Saying so here rather than letting
the check look stronger than it is.

    python3 scripts/check-mirrors.py

Exit 0 if every English document under docs/ has a mirror at docs/es/ with the
same number of headings, 1 otherwise.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
ES = DOCS / "es"

HEADING = re.compile(r"^#{1,6} ", re.M)


def headings(p: pathlib.Path) -> int:
    # Fenced blocks can contain a `#` at line start — a comment in a code sample
    # counts as a heading otherwise, and the two sides then disagree for a reason
    # that has nothing to do with the prose.
    body = re.sub(r"```.*?```", "", p.read_text(), flags=re.S)
    return len(HEADING.findall(body))


def main() -> int:
    english = sorted(p for p in DOCS.glob("*.md"))
    if not english:
        print("no documents under docs/ — nothing to mirror", file=sys.stderr)
        return 1

    bad = False
    for p in english:
        mirror = ES / p.name
        if not mirror.exists():
            print(f"MISSING  {p.relative_to(ROOT)} has no mirror at {mirror.relative_to(ROOT)}")
            bad = True
            continue
        a, b = headings(p), headings(mirror)
        if a != b:
            print(f"BEHIND   {mirror.relative_to(ROOT)}: {b} sections against {a} in the English")
            bad = True
        else:
            print(f"ok       {p.name} — {a} sections, level")

    orphans = [q for q in ES.glob("*.md") if not (DOCS / q.name).exists()]
    for q in orphans:
        print(f"ORPHAN   {q.relative_to(ROOT)} mirrors nothing")
        bad = True

    if bad:
        print("\nA stale mirror is worse than an absent one.", file=sys.stderr)
        return 1
    print(f"\ndoc mirrors: {len(english)} mirrored and level by section count")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
