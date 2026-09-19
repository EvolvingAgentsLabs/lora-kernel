"""The pictures: every placeholder has a brief and words for both languages, and every image a
document shows is a file. A document that points at a picture nobody drew is a broken page."""

import importlib.util
import re
from pathlib import Path

spec = importlib.util.spec_from_file_location("place_images", "scripts/place-images.py")
pi = importlib.util.module_from_spec(spec); spec.loader.exec_module(pi)

DOCS = [p for p in Path(".").rglob("*.md")
        if ".git" not in p.parts and p.parts[0] != "results" and p.as_posix() != "docs/img/README.md"]


def _placeholders():
    for p in DOCS:
        for m in re.finditer(r"^>.*(?:PLACEHOLDER|MARCADOR)[^`]*`docs/img/([^`]+)`", p.read_text(), re.M):
            yield p, m.group(1)


def test_every_placeholder_can_be_placed_in_both_languages():
    for doc, name in _placeholders():
        assert name in pi.TEXT, f"{doc} asks for {name}, which place-images.py has no words for"
        assert set(pi.TEXT[name]) == {"en", "es"}


def test_every_placeholder_has_its_brief_in_the_index():
    index = Path("docs/img/README.md").read_text()
    for _, name in _placeholders():
        assert f"### `{name}`" in index, f"no brief for {name} in docs/img/README.md"


def test_a_placeholder_and_its_mirror_ask_for_the_same_pictures():
    asked = {}
    for doc, name in _placeholders():
        asked.setdefault(pi.language(doc), set()).add(name)
    assert asked.get("en") == asked.get("es")


def test_every_image_a_document_shows_is_a_file():
    for p in DOCS + [Path("docs/img/README.md")]:
        for m in re.finditer(r"!\[[^\]]*\]\(([^)\s]+)\)", p.read_text()):
            if not re.match(r"^[a-z]+:", m.group(1)):
                assert (p.parent / m.group(1)).exists(), f"{p} shows {m.group(1)}, which is not there"
