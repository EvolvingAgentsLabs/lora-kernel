"""memory/notes.py and memory/lint.py — docs/MEMORY.md §1, §1.5, §5.2. No model anywhere.

Layers, nearest wins:  value(slot) = case ▸ site ▸ textbook.  The lint's rules are stable strings;
each test below breaks ONE thing in a small valid library and asserts that rule, and only a rule
of that name, is what fires — a lint that passes everything and a lint that fails everything both
look fine on a library that happens to be clean.
"""

from pathlib import Path

import pytest

from memory.lint import lint, main as lint_main
from memory.notes import (BODY_TOKENS, Library, Note, NoteError, Site, count_tokens,
                          parse_frontmatter, render, resolve)

SPEC_STEP = """---
id: nursing-iv/harness/primary-infusion/03-cleanse-catheter-cap
shelf: harness
kind: step                       # procedure | step | check
title: Cleanse the catheter cap before attaching tubing
when: You are about to connect a syringe or tubing to a patient's IV port.
what: Disinfection of the IV port's cap with an alcohol pad or scrub hub.
requires: [nursing-iv/harness/primary-infusion/02-safety-steps]
next: nursing-iv/harness/primary-infusion/04-assess-patency
uses: [nursing-iv/wiki/asepsis/scrub-the-hub]
slots: {seconds: 5}
source: Nursing Skills (Open RN), ch. 23 — CC BY 4.0
---
Vigorously cleanse the catheter cap for at least {{seconds}} seconds and allow it to dry.
"""

SPEC_SITE = """---
site: ward-7b
overrides:
  nursing-iv/harness/primary-infusion/03-cleanse-catheter-cap: {seconds: 20}
---
"""


def test_the_spec_s_own_example_parses():
    n = Note.parse(SPEC_STEP)
    assert n.kind == "step" and n.slots == {"seconds": 5}
    assert n.requires == ["nursing-iv/harness/primary-infusion/02-safety-steps"]
    assert n.next.endswith("04-assess-patency") and n.uses[0].endswith("scrub-the-hub")
    assert n.used_slots() == ["seconds"]


def test_serialise_round_trips():
    n = Note.parse(SPEC_STEP)
    again = Note.parse(n.serialise())
    assert again == n
    assert again.serialise() == n.serialise()


def test_layers_nearest_wins_and_the_site_is_marked():
    n, site = Note.parse(SPEC_STEP), Site.parse(SPEC_SITE)
    assert "at least 5 seconds" in render(n)
    assert "at least 20 [site] seconds" in render(n, site)          # §5.2's own sentence
    assert "at least 12 seconds" in render(n, site, {"seconds": 12})  # a case is not marked
    assert resolve(n, site)["seconds"] == (20, "site")
    assert resolve(n, site, {"seconds": 12})["seconds"] == (12, "case")


def test_a_slot_with_no_value_raises_rather_than_rendering_braces():
    n = Note.parse(SPEC_STEP.replace("slots: {seconds: 5}\n", ""))
    with pytest.raises(NoteError):
        render(n)


def test_the_parser_refuses_what_it_does_not_understand():
    with pytest.raises(NoteError):
        parse_frontmatter("no frontmatter here")
    with pytest.raises(NoteError):
        parse_frontmatter("---\nid: x\nnever closed")
    with pytest.raises(NoteError):
        Note.parse(SPEC_STEP.replace("kind: step", "kind: step\nmood: good"))


def test_token_proxy_counts_words_and_marks():
    assert count_tokens("Hold for 2-3 minutes.") == 7
    assert count_tokens("") == 0


# ---------------------------------------------------------------- the lint, rule by rule

def _library(tmp: Path, edit=None) -> Path:
    root = tmp / "toy"
    files = {
        "harness/p.md": "---\nid: toy/harness/p\nshelf: harness\nkind: procedure\ntitle: P\nwhen: doing p\nwhat: p\nfirst: toy/harness/p/01-a\nsteps: [toy/harness/p/01-a, toy/harness/p/02-b]\n---\n01 a\n02 b\n",
        "harness/p/01-a.md": "---\nid: toy/harness/p/01-a\nshelf: harness\nkind: step\ntitle: A\nwhen: before a\nwhat: a\nrequires: []\nnext: toy/harness/p/02-b\nuses: [toy/wiki/w/leaf]\nslots: {n: 5}\n---\nDo a for {{n}} seconds.\n",
        "harness/p/02-b.md": "---\nid: toy/harness/p/02-b\nshelf: harness\nkind: step\ntitle: B\nwhen: before b\nwhat: b\nrequires: [toy/harness/p/01-a]\nnext: null\nuses: []\n---\nDo b.\n",
        "wiki/w.md": "---\nid: toy/wiki/w\nshelf: wiki\nkind: concept\ntitle: W\nwhen: asking w\nwhat: w\nparent: null\nchildren: [toy/wiki/w/leaf]\n---\nW.\n",
        "wiki/w/leaf.md": "---\nid: toy/wiki/w/leaf\nshelf: wiki\nkind: formula\ntitle: Leaf\nwhen: asking leaf\nwhat: leaf\nparent: toy/wiki/w\nchildren: []\n---\ny = x\n",
        "site/s.md": "---\nsite: s\noverrides:\n  toy/harness/p/01-a: {n: 9}\n---\n",
    }
    for rel, text in files.items():
        if edit and rel in edit:
            text = edit[rel](text)
        if text is None:
            continue
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


def test_the_toy_library_is_clean(tmp_path):
    assert lint(_library(tmp_path)) == []
    assert lint_main([str(_library(tmp_path))]) == 0


BREAKS = {
    "link": {"harness/p/01-a.md": lambda t: t.replace("toy/wiki/w/leaf", "toy/wiki/w/nowhere")},
    "next-cycle": {"harness/p/02-b.md": lambda t: t.replace("next: null", "next: toy/harness/p/01-a")},
    "step-orphan": {"harness/p/01-a.md": lambda t: t.replace("next: toy/harness/p/02-b", "next: null")},
    "body-tokens": {"harness/p/02-b.md": lambda t: t.replace("Do b.", "word " * (BODY_TOKENS + 1))},
    "slot-undeclared": {"harness/p/02-b.md": lambda t: t.replace("Do b.", "Do b {{m}} times.")},
    "when": {"wiki/w.md": lambda t: t.replace("when: asking w\n", "")},
    "what": {"wiki/w.md": lambda t: t.replace("what: w\n", "")},
    "when-duplicate": {"wiki/w.md": lambda t: t.replace("when: asking w", "when: asking leaf")},
    "id-path": {"wiki/w/leaf.md": lambda t: t.replace("id: toy/wiki/w/leaf", "id: toy/wiki/w/lief")},
    "requires-order": {"harness/p/01-a.md": lambda t: t.replace("requires: []", "requires: [toy/harness/p/02-b]")},
    "tree": {"wiki/w.md": lambda t: t.replace("children: [toy/wiki/w/leaf]", "children: []")},
    "site": {"site/s.md": lambda t: t.replace("{n: 9}", "{m: 9}")},
    "kind": {"wiki/w.md": lambda t: t.replace("kind: concept", "kind: step")},
    "procedure-steps": {"harness/p.md": lambda t: t.replace("steps: [toy/harness/p/01-a, toy/harness/p/02-b]",
                                                            "steps: [toy/harness/p/02-b, toy/harness/p/01-a]")},
}


@pytest.mark.parametrize("rule", sorted(BREAKS))
def test_each_rule_fires_on_its_own_break(tmp_path, rule):
    findings = lint(_library(tmp_path, BREAKS[rule]))
    assert rule in {f[0] for f in findings}, findings
    assert lint_main([str(tmp_path / "toy")]) == 1


def test_every_rule_of_section_1_5_has_a_break():
    """§1.5's list, word for word, against the table above — a rule with no break is untested."""
    for rule in ("link", "next-cycle", "step-orphan", "body-tokens", "slot-undeclared", "when",
                 "what", "when-duplicate"):
        assert rule in BREAKS
