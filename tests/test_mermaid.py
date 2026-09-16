"""Every mermaid block in the documentation still renders, and still says what we do.

WHY A TEST. Diagrams rot faster than prose because nobody re-reads them: the stack
diagram carried a frontier in layer 2 being withdrawn for nine days after measurement
said a frontier cannot be a speculative target at all. A broken or stale diagram is
worse than none, because a reader trusts a picture.
"""

import pathlib
import re

import pytest

BLOCKS = [(md, i, m.group(1))
          for md in sorted(pathlib.Path(".").rglob("*.md"))
          if ".git" not in md.parts
          for i, m in enumerate(
              re.finditer(r"```mermaid\n(.*?)```", md.read_text(), re.S), 1)]

KINDS = ("flowchart", "graph", "sequenceDiagram", "stateDiagram", "classDiagram",
         "gantt")


def test_there_are_diagrams_to_check():
    assert len(BLOCKS) >= 10


@pytest.mark.parametrize("md,i,body", BLOCKS,
                         ids=[f"{m.as_posix()}#{i}" for m, i, _ in BLOCKS])
def test_each_block_is_a_diagram_with_balanced_syntax(md, i, body):
    assert body.strip().startswith(KINDS), f"{md}#{i} does not declare a diagram type"
    assert body.count("[") == body.count("]"), f"{md}#{i} has unbalanced brackets"
    assert body.count('"') % 2 == 0, f"{md}#{i} has an unclosed label"
    assert body.count("(") == body.count(")"), f"{md}#{i} has unbalanced parentheses"


@pytest.mark.parametrize("md,i,body", BLOCKS,
                         ids=[f"{m.as_posix()}#{i}" for m, i, _ in BLOCKS])
def test_every_class_has_a_classdef(md, i, body):
    """A `class X foo` with no `classDef foo` renders unstyled and silently."""
    defined = set(re.findall(r"classDef\s+(\w+)", body))
    used = {name for line in re.findall(r"^\s*class\s+[\w,]+\s+(\w+)\s*$", body, re.M)
            for name in [line]}
    assert used <= defined, f"{md}#{i} uses {sorted(used - defined)} with no classDef"


#: Documents that are published artefacts with a date on them. Their diagrams are
#: what was said then, and a header note above each says so. Changing them would be
#: rewriting the record rather than correcting it.
HISTORICAL = {"docs/the-frontier-is-scaffolding.md",
              "docs/es/the-frontier-is-scaffolding.md"}

NODE = re.compile(r'\[\s*"(.*?)"\s*\]', re.S)


def test_no_node_calls_the_frontier_the_target():
    """The correction that took nine days to reach the pictures.

    A frontier API cannot verify a drafted token: no logprobs for a forced
    continuation, a different tokenizer **[ran]** P48. A diagram that draws it as
    the speculative target teaches the thing we measured to be false.

    CHECKED PER NODE, NOT PER BLOCK, and the first version was not. The stack
    diagram legitimately holds a target node *and* a frontier node — they are
    different layers doing different jobs — and a block-level check flagged it while
    missing nothing. A rule that fires on a correct diagram gets switched off.
    """
    offenders = []
    for md, i, body in BLOCKS:
        if md.as_posix() in HISTORICAL:
            continue
        for label in NODE.findall(body):
            low = label.lower()
            if "target" in low and ("frontier" in low or "frontera" in low):
                if not any(k in low for k in ("imposible", "impossible",
                                              "nunca el target", "never the target")):
                    offenders.append(f"{md}#{i}: {label[:70]}")
    assert not offenders, "a node still draws a frontier as the target:\n" + \
        "\n".join(offenders)
