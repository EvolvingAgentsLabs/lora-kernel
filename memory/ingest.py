r"""Real documents into the library, mechanically — no one writes or rewords a statement.

WHY. Every walk the memory has been measured on (W9, B5, the tracker) crossed a library a generator wrote. The thesis —
the LoRA holds the navigation, the library holds the content — has never met content nobody designed for the member.
This turns an official document into pages of the library's own shape (docs/MEMORY.md §1.6) so a trained member can be
measured on it unchanged: the content moves, the member does not.

THE SOURCE: the U.S. Code of Federal Regulations as the eCFR serves it (XML, public domain). One SECTION → one page
`<root>/wiki/<part>-<section>`. One PARAGRAPH → one statement, anchored by its own label path — `(b)(3)(ii)` is
`§b-3-ii`, a definition in a definitions section is anchored by its term — and its text kept verbatim. A cross-reference
to a section in the same ingest (`§ 1.908(b)(3)`) becomes a link `[[<root>/wiki/1-908]](b)(3)` inside the statement,
where the regulation put it; a reference outside the ingest stays text. `source:` names the document and the sha256 of
the file read, so what the member saw is auditable.

WHAT IT DOES NOT DO. Split a long paragraph: a regulation's paragraph runs 40–90 words where W9's generator kept a
statement under 40 tokens. The linter reports it (`statement-tokens`); the ingest keeps the paragraph whole, because
cutting it is rewriting it — and that difference is part of what "real documents" means.

    python -m memory.ingest --root logistics-regs --out knowledge/logistics-regs cfr/*.xml
"""
from __future__ import annotations

import argparse
import hashlib
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from memory.notes import Note

ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv"}
LABEL = re.compile(r"^\(([a-z]{1,4}|\d{1,2}|[A-Z])\)\s*")
XREF = re.compile(r"§\s*(\d+)\.(\d+)")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def _text(el) -> str:
    return re.sub(r"\s+", " ", html.unescape("".join(el.itertext()))).strip()


def _level(label: str, path: list[str]) -> int:
    """The eCFR's paragraph levels: (a) · (1) · (i) · (A). `(i)` is a letter after `(h)` at the top level, else roman."""
    if label.isdigit():
        return 2
    if label.isupper():
        return 4
    if label in ROMAN and not (len(path) == 1 and path[0] == chr(ord(label[0]) - 1) and len(label) == 1):
        if len(path) >= 2:
            return 3
    return 1


def sections(xml_text: str):
    root = ET.fromstring(xml_text)
    for div in root.iter():
        if div.tag.startswith("DIV") and div.get("TYPE") == "SECTION":
            head = div.find("HEAD")
            yield div.get("N"), _text(head) if head is not None else div.get("N"), [_text(p) for p in div.findall("P")]


def page(root: str, number: str, heading: str, paras: list[str], ids: set[str], source: str) -> Note:
    title = re.sub(r"^§?\s*[\d.]+\s*", "", heading).strip()
    definitions = "definitions" in heading.lower()
    path: list[str] = []
    used: set[str] = set()
    lines = []
    for para in paras:
        m = LABEL.match(para)
        anchor = None
        if m and not definitions:
            lab = m.group(1)
            lvl = _level(lab, path)
            path = path[:lvl - 1] + [lab.lower()]
            anchor = "-".join(path)
        elif definitions:
            term = re.match(r"^([A-Z][A-Za-z ,\-]{1,60}?) (?:means|includes|has the meaning)", para)
            anchor = slug(term.group(1)) if term else None
        anchor = anchor or "text"
        base, k = anchor, 2
        while anchor in used:
            anchor, k = f"{base}-{k}", k + 1
        used.add(anchor)

        def link(m):
            target = f"{root}/wiki/{m.group(1)}-{m.group(2)}"
            return f"[[{target}]]" if target in ids else m.group(0)
        lines.append(f"§{anchor} {XREF.sub(link, para)}")
    pid = f"{root}/wiki/{number.replace('.', '-')}"
    return Note(id=pid, shelf="wiki", kind="page", title=f"{number} {title}",
                when=f"You need what section {number} requires: {title}",
                what=f"Section {number} of the regulation — {title}", body="\n".join(lines), source=source)


def ingest(files: list[Path], root: str) -> list[Note]:
    secs = []
    for f in files:
        raw = f.read_bytes()
        src = f"{f.name}#sha256:{hashlib.sha256(raw).hexdigest()[:16]} (eCFR, public domain)"
        secs += [(n, h, p, src) for n, h, p in sections(raw.decode())]
    ids = {f"{root}/wiki/{n.replace('.', '-')}" for n, _, _, _ in secs}
    return [page(root, n, h, p, ids, src) for n, h, p, src in secs]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    notes = ingest([Path(f) for f in a.files], a.root)
    for n in notes:
        p = Path(a.out) / (n.id.split("/", 1)[1] + ".md")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(n.serialise())
    print(f"[ingest] {len(notes)} pages, {sum(n.body.count(chr(10)) + 1 for n in notes)} statements → {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
