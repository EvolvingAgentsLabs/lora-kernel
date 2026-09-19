"""Textbook → site → case: how a note's slots get their values — docs/MEMORY.md §1.4, §5.2.

    value(slot) = case[slot]  if given  else  site[note][slot]  if given  else  note.slots[slot]

Nearest wins, deterministically, and **before the note reaches the expert**: the model never sees
two values to reconcile, it reads the rule already resolved. A value that came from a site is
marked where it lands — `20 [site] seconds` — so an auditor can see which layer spoke; a case's
value is not marked, because in training and evaluation it stands in for the world.

`resolve` is what the walk log records (slot → value and layer, §5.4); `render` is what is shown.
No model is involved **[spec]** W1, W2.
"""

from __future__ import annotations

import re

from memory.notes import SLOT, Note, NoteError, Site


def resolve(note: Note, site: Site | None = None, case: dict | None = None) -> dict:
    """slot → (value, layer), nearest wins: case → site → textbook. A sentence the site ADDS to the
    note brings its own slots, at the site layer; a case may set those too."""
    out = {k: (v, "textbook") for k, v in note.slots.items()}
    if site:
        for k, v in site.add_for(note.id)[1].items():
            out[k] = (v, "site")
        for k, v in (site.overrides.get(note.id) or {}).items():
            out[k] = (v, "site")
    for k, v in (case or {}).items():
        out[k] = (v, "case")
    return out


def text_of(note: Note, site: Site | None = None) -> str:
    """The note's body with the sentence its site adds, slots still unfilled."""
    add = site.add_for(note.id)[0] if site else ""
    return f"{note.body} {add}" if add else note.body


def shown_slots(note: Note, site: Site | None = None) -> list[str]:
    """Every slot the expert is shown a value for — the note's own and the added sentence's."""
    return SLOT.findall(text_of(note, site))


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

    return SLOT.sub(fill, text_of(note, site))
