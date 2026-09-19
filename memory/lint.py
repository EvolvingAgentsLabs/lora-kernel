"""The library is linted, like code — docs/MEMORY.md §1.5.

    python -m memory.lint knowledge/<subdomain>

exits 1 and names every finding when: a link does not resolve; a `next` chain has a cycle or a
step belongs to no procedure; a body exceeds the token limit; a `{{slot}}` is used and not
declared; a `when:` or `what:` is missing; two notes of one subdomain have the same `when:`.

Beyond §1.5's list, and only what the note format of §1.1–§1.2 already implies **[spec]**: an id
must be the file's path; a shelf admits only its kinds and its link types; a procedure's `steps`
must be the walk its `next` links give (two statements of one order must not disagree); `parent`
and `children` must mirror each other; a site may override only slots that exist.

Every finding is `(rule, note id, message)`. Rules are stable strings: tests and CI key on them.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from memory.notes import BODY_TOKENS, SHELVES, Library, NoteError, count_tokens

Finding = tuple[str, str, str]


def lint(root: str | Path) -> list[Finding]:
    root = Path(root)
    try:
        lib = Library.load(root)
    except NoteError as e:
        return [("parse", str(root), str(e))]
    out: list[Finding] = []
    notes = lib.notes

    for n in notes.values():
        # identity: the id is the path, so a link can be followed by eye and by `open`
        expect = f"{root.name}/{n.path.relative_to(root).with_suffix('')}"
        if n.id != expect:
            out.append(("id-path", n.id, f"id should be `{expect}`"))
        if n.shelf not in SHELVES:
            out.append(("shelf", n.id, f"unknown shelf `{n.shelf}`"))
            continue
        if n.kind not in SHELVES[n.shelf]:
            out.append(("kind", n.id, f"`{n.kind}` is not a kind of the {n.shelf} shelf"))
        if n.id.split("/")[1] != n.shelf:
            out.append(("shelf", n.id, f"a {n.shelf} note outside `{n.shelf}/`"))
        if n.shelf == "wiki" and (n.requires or n.next or n.uses or n.first or n.steps):
            out.append(("link-type", n.id, "a wiki note carries harness links"))
        if n.shelf == "harness" and (n.parent or n.children):
            out.append(("link-type", n.id, "a harness note carries wiki links"))

        for name in ("when", "what"):
            if not getattr(n, name).strip():
                out.append((name, n.id, f"`{name}:` is missing"))

        tokens = count_tokens(n.body)
        if tokens > BODY_TOKENS:
            out.append(("body-tokens", n.id, f"{tokens} tokens > {BODY_TOKENS}"))
        if not n.body.strip():
            out.append(("body-empty", n.id, "a note with no body"))

        for slot in n.used_slots():
            if slot not in n.slots:
                out.append(("slot-undeclared", n.id, f"`{{{{{slot}}}}}` is used and not declared"))
        for slot in n.slots:
            if slot not in n.used_slots():
                out.append(("slot-unused", n.id, f"`{slot}` is declared and never used"))

        for link, target in n.links():
            if target not in notes:
                out.append(("link", n.id, f"{link} → `{target}` does not resolve"))
                continue
            t = notes[target]
            if link in ("requires", "next", "first", "steps") and t.kind not in ("step", "check"):
                out.append(("link-type", n.id, f"{link} → `{target}` is a {t.kind}, not a step"))
            if link in ("parent", "children") and t.shelf != "wiki":
                out.append(("link-type", n.id, f"{link} → `{target}` is not a wiki note"))

    # two notes with one `when:` are one situation with two answers — the radar cannot choose
    for when, k in Counter(n.when.strip().lower() for n in notes.values() if n.when.strip()).items():
        if k > 1:
            ids = sorted(n.id for n in notes.values() if n.when.strip().lower() == when)
            out.append(("when-duplicate", ids[0], f"same `when:` as {ids[1:]}"))

    # procedures: the walk exists, is acyclic, and is the order the skeleton states
    owned: Counter = Counter()
    for p in lib.procedures():
        if not p.first:
            out.append(("procedure-first", p.id, "a procedure with no `first`"))
            continue
        try:
            walk = lib.walk(p.id)
        except NoteError as e:
            out.append(("next-cycle" if "cycles" in str(e) else "link", p.id, str(e)))
            continue
        if walk != p.steps:
            out.append(("procedure-steps", p.id, "`steps` is not the walk `first`/`next` gives"))
        owned.update(walk)
        position = {s: i for i, s in enumerate(walk)}
        for s in walk:
            for r in notes[s].requires:
                if r in position and position[r] >= position[s]:
                    out.append(("requires-order", s, f"requires `{r}`, which comes later"))
                if r not in position and r in notes:
                    out.append(("requires-order", s, f"requires `{r}`, a step of another procedure"))
    for n in notes.values():
        if n.kind in ("step", "check"):
            if owned[n.id] == 0:
                out.append(("step-orphan", n.id, "belongs to no procedure"))
            elif owned[n.id] > 1:
                out.append(("step-shared", n.id, f"walked by {owned[n.id]} procedures"))

    # the wiki is a tree: parent and children mirror each other, one root chain, no cycle
    for n in notes.values():
        if n.shelf != "wiki":
            continue
        for c in n.children:
            if c in notes and notes[c].parent != n.id:
                out.append(("tree", n.id, f"lists `{c}` as a child; its parent is `{notes[c].parent}`"))
        if n.parent in notes and n.id not in notes[n.parent].children:
            out.append(("tree", n.id, f"parent `{n.parent}` does not list it"))
        try:
            lib.path_to_root(n.id)
        except (NoteError, KeyError) as e:
            out.append(("tree", n.id, str(e)))

    # a site overrides what exists, and nothing else
    for s in lib.sites.values():
        for target, slots in s.overrides.items():
            if target not in notes:
                out.append(("site", s.name, f"overrides `{target}`, which does not exist"))
                continue
            for slot in slots or {}:
                if slot not in notes[target].slots:
                    out.append(("site", s.name, f"`{target}` has no slot `{slot}`"))
    return sorted(set(out))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__); return 2
    bad = 0
    for root in argv:
        findings = lint(root)
        lib_n = len(list(Path(root).rglob("*.md")))
        for rule, note_id, msg in findings:
            print(f"[lint] {rule:16s} {note_id}: {msg}")
        print(f"[lint] {root}: {lib_n} file(s), {len(findings)} finding(s)", flush=True)
        bad += len(findings)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
