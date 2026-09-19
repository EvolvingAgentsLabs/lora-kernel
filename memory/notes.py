"""A note, a library of notes, and the layers that fill a note's slots — docs/MEMORY.md §1, §5.2.

WHAT A NOTE IS. One markdown file: a frontmatter block and a body of at most `BODY_TOKENS`
tokens. Two shelves. The **harness** shelf holds procedures, steps and checks, joined by the typed
links `requires` / `next` / `uses` — those links are the control flow. The **wiki** shelf holds
concepts, formulas and tables, joined by `parent` → `children`. Every note carries `when:` and
`what:`; those two lines, not the body, are what the radar will index (§2, W3).

SLOTS AND LAYERS (§1.4, §5.2). A body says `{{seconds}}`; the value is resolved nearest-wins,

    value(slot) = case[slot]  if given  else  site[note][slot]  if given  else  note.slots[slot]

and a value that did not come from the textbook is marked where it lands — `20 [site]` — so the
reader meets the rule already resolved and an auditor can see which layer spoke.

WHY THE PARSER IS HERE AND NOT PyYAML. CI installs pytest and nothing else, and the frontmatter
this library uses is a small, closed subset: scalars, `[a, b]`, `{k: v}`, and one nested map (a
site's `overrides:`). Anything outside that subset raises — a note the parser half-understands is
worse than one it refuses.

No model is involved anywhere in this module **[spec]** W1.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

BODY_TOKENS = 150                      # §1: the hard limit on a note's body
SHELVES = {"harness": ("procedure", "step", "check"), "wiki": ("concept", "formula", "table")}
SLOT = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")
_PIECE = re.compile(r"\w+|[^\w\s]")
_ORDER = ("id", "shelf", "kind", "title", "when", "what", "requires", "next", "uses",
          "parent", "children", "first", "steps", "slots", "source")


class NoteError(ValueError):
    """A file that is not a note. Carries the path so a lint line can name it."""


def count_tokens(text: str) -> int:
    """Words plus punctuation marks — a tokenizer-free proxy for the §1 limit.

    n(text) = |{ maximal runs of \\w } ∪ { single non-space, non-word characters }|. On English
    prose a BPE tokenizer lands within roughly ±20 % of it (rare clinical words split further,
    punctuation runs merge). The limit is a budget on attention, not a contract with one
    vocabulary, and CI has no tokenizer to ask; W2's runtime owns the exact cap per note.
    """
    return len(_PIECE.findall(text))


# ---------------------------------------------------------------- frontmatter

def _scalar(text: str):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text in ("", "null", "~"):
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def _split(text: str) -> list[str]:
    """Split on commas that sit outside quotes and brackets."""
    parts, depth, quote, cur = [], 0, "", ""
    for ch in text:
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(cur); cur = ""
            continue
        cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def _value(text: str):
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return [_scalar(p) for p in _split(text[1:-1])]
    if text.startswith("{") and text.endswith("}"):
        out = {}
        for p in _split(text[1:-1]):
            k, _, v = p.partition(":")
            out[k.strip()] = _scalar(v)
        return out
    return _scalar(text)


def _strip_comment(line: str) -> str:
    # `kind: step      # procedure | step | check` — a comment needs a space before its hash
    return re.sub(r"\s+#\s.*$", "", line)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """`---\\nkey: value\\n---\\nbody` → (fields, body). One level of nesting, by indentation."""
    if not text.startswith("---\n"):
        raise NoteError("no frontmatter")
    m = re.match(r"---\n(.*?)\n---[ \t]*(?:\n(.*))?$", text, flags=re.S)
    if not m:
        raise NoteError("frontmatter is not closed")
    head, body = m.group(1), m.group(2) or ""
    fields: dict = {}
    nested = None
    for raw in head.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        key, colon, rest = line.strip().partition(":")
        if not colon:
            raise NoteError(f"not a `key: value` line: {raw!r}")
        if line[0] in " \t":
            if nested is None:
                raise NoteError(f"indented line under no key: {raw!r}")
            fields[nested][key.strip()] = _value(rest)
        elif rest.strip() == "":
            nested = key.strip(); fields[nested] = {}
        else:
            nested = None; fields[key.strip()] = _value(rest)
    return fields, body.strip("\n")


def _dump(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(_dump(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {_dump(v)}" for k, v in value.items()) + "}"
    return "null" if value is None else str(value)


# ---------------------------------------------------------------- the note

@dataclass
class Note:
    id: str
    shelf: str
    kind: str
    title: str
    when: str = ""
    what: str = ""
    body: str = ""
    requires: list[str] = field(default_factory=list)   # harness
    next: str | None = None                             # harness
    uses: list[str] = field(default_factory=list)       # harness
    first: str | None = None                            # a procedure's first step
    steps: list[str] = field(default_factory=list)      # a procedure's ordered step ids
    parent: str | None = None                           # wiki
    children: list[str] = field(default_factory=list)   # wiki
    slots: dict = field(default_factory=dict)
    source: str = ""
    path: Path | None = None

    @classmethod
    def parse(cls, text: str, path: Path | None = None) -> "Note":
        try:
            f, body = parse_frontmatter(text)
        except NoteError as e:
            raise NoteError(f"{path}: {e}") from None
        known = set(_ORDER)
        extra = set(f) - known
        if extra:
            raise NoteError(f"{path}: unknown field(s) {sorted(extra)}")
        for need in ("id", "shelf", "kind", "title"):
            if not f.get(need):
                raise NoteError(f"{path}: missing `{need}`")
        return cls(id=f["id"], shelf=f["shelf"], kind=f["kind"], title=str(f["title"]),
                   when=str(f.get("when") or ""), what=str(f.get("what") or ""), body=body,
                   requires=list(f.get("requires") or []), next=f.get("next"),
                   uses=list(f.get("uses") or []), first=f.get("first"),
                   steps=list(f.get("steps") or []), parent=f.get("parent"),
                   children=list(f.get("children") or []), slots=dict(f.get("slots") or {}),
                   source=str(f.get("source") or ""), path=path)

    def serialise(self) -> str:
        """The file this note is. `parse(serialise(n)) == n` field for field (tests hold it)."""
        f = {"id": self.id, "shelf": self.shelf, "kind": self.kind, "title": self.title,
             "when": self.when, "what": self.what}
        if self.shelf == "harness":
            if self.kind == "procedure":
                f.update(first=self.first, steps=self.steps)
            else:
                f.update(requires=self.requires, next=self.next, uses=self.uses)
        else:
            f.update(parent=self.parent, children=self.children)
        if self.slots:
            f["slots"] = self.slots
        if self.source:
            f["source"] = self.source
        lines = [f"{k}: {_dump(f[k])}" for k in _ORDER if k in f]
        return "---\n" + "\n".join(lines) + "\n---\n" + self.body + "\n"

    def links(self) -> list[tuple[str, str]]:
        """Every (link type, target id) this note declares."""
        out = [("requires", t) for t in self.requires] + [("uses", t) for t in self.uses]
        out += [("steps", t) for t in self.steps] + [("children", t) for t in self.children]
        out += [(k, v) for k, v in (("next", self.next), ("first", self.first),
                                    ("parent", self.parent)) if v]
        return out

    def used_slots(self) -> list[str]:
        return SLOT.findall(self.body)


# ---------------------------------------------------------------- layers

@dataclass
class Site:
    """A ward's adaptations — overrides only (§5.2). `overrides[note id] = {slot: value}`."""
    name: str
    overrides: dict[str, dict]
    path: Path | None = None

    @classmethod
    def parse(cls, text: str, path: Path | None = None) -> "Site":
        f, _ = parse_frontmatter(text)
        if not f.get("site"):
            raise NoteError(f"{path}: a site file needs `site:`")
        return cls(name=str(f["site"]), overrides=dict(f.get("overrides") or {}), path=path)


def resolve(note: Note, site: Site | None = None, case: dict | None = None) -> dict:
    """slot → (value, layer), nearest wins: case → site → textbook."""
    out = {k: (v, "textbook") for k, v in note.slots.items()}
    for k, v in ((site.overrides.get(note.id) or {}) if site else {}).items():
        out[k] = (v, "site")
    for k, v in (case or {}).items():
        out[k] = (v, "case")
    return out


def render(note: Note, site: Site | None = None, case: dict | None = None,
           mark: bool = True) -> str:
    """The body as the expert reads it: slots filled, a site's value marked `[site]`.

    A case's value is NOT marked: in training and evaluation it stands in for the world, and a
    mark the served text never carries would be a feature only the corpus has.
    """
    values = resolve(note, site, case)

    def fill(m: re.Match) -> str:
        name = m.group(1)
        if name not in values:
            raise NoteError(f"{note.id}: slot `{name}` has no value in any layer")
        value, layer = values[name]
        return f"{value} [site]" if (mark and layer == "site") else str(value)

    return SLOT.sub(fill, note.body)


# ---------------------------------------------------------------- the library

@dataclass
class Library:
    root: Path
    notes: dict[str, Note]
    sites: dict[str, Site]

    @classmethod
    def load(cls, root: str | Path) -> "Library":
        root = Path(root)
        notes: dict[str, Note] = {}
        sites: dict[str, Site] = {}
        for p in sorted(root.rglob("*.md")):
            rel = p.relative_to(root)
            if len(rel.parts) == 1:               # README, ATTRIBUTION — not notes
                continue
            if rel.parts[0] == "site":
                s = Site.parse(p.read_text(), p); sites[s.name] = s
                continue
            n = Note.parse(p.read_text(), p)
            if n.id in notes:
                raise NoteError(f"{p}: id `{n.id}` is already {notes[n.id].path}")
            notes[n.id] = n
        return cls(root=root, notes=notes, sites=sites)

    def __getitem__(self, note_id: str) -> Note:
        return self.notes[note_id]

    def procedures(self) -> list[Note]:
        return [n for n in self.notes.values() if n.kind == "procedure"]

    def walk(self, procedure_id: str) -> list[str]:
        """The oracle's walk: from `first`, following `next`, until a step has none.

        Raises on a cycle or a dangling link rather than returning a short walk — a walk that
        silently stops early is a procedure with its last steps missing.
        """
        proc = self.notes[procedure_id]
        seen: list[str] = []
        cur = proc.first
        while cur:
            if cur in seen:
                raise NoteError(f"{procedure_id}: `next` cycles at {cur}")
            if cur not in self.notes:
                raise NoteError(f"{procedure_id}: `{cur}` does not exist")
            seen.append(cur)
            cur = self.notes[cur].next
        return seen

    def path_to_root(self, wiki_id: str) -> list[str]:
        """A wiki note's ancestors, nearest first — the classification it sits under."""
        out, cur = [], self.notes[wiki_id].parent
        while cur:
            if cur in out:
                raise NoteError(f"{wiki_id}: `parent` cycles at {cur}")
            out.append(cur)
            cur = self.notes[cur].parent
        return out
