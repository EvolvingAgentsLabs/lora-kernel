"""Inside an unquoted heredoc, a backtick is not punctuation. It is a command.

THIS BUG HAS NOW BITTEN FOUR TIMES. The chain scripts write Python to the Colab VM
through heredocs whose delimiter is unquoted, because `$BRANCH` and `$MODULE` have
to interpolate. In that region bash keeps expanding: `#` does not start a comment,
and backticks run whatever is between them. A Python comment reading

    # raised on `import`, so vllm never starts

made bash run `import`, which exited 127, which `set -e` turned into a dead chain
before the GPU had done anything **[ran]** 2026-09-14. `chain_serve.sh` already
carried a comment saying "No backticks in this heredoc — third time today", and the
fourth arrived in a note added underneath it.

A rule a person has to remember is not a rule. This is the gate that replaces it.
"""

import pathlib
import re

import pytest

CHAINS = sorted(pathlib.Path("training/harness").glob("chain_*.sh"))
# `cat > f <<PY` interpolates; `cat > f <<'PY'` does not. Only the first is a hazard.
OPEN = re.compile(r"<<-?\s*(?P<q>['\"]?)(?P<tag>[A-Za-z_]\w*)(?P=q)")


def unquoted_heredoc_lines(path: pathlib.Path):
    """Every (lineno, text) that bash will still expand before writing it out."""
    out, tag = [], None
    for i, line in enumerate(path.read_text().splitlines(), 1):
        if tag is not None:
            if line.strip() == tag:
                tag = None
            else:
                out.append((i, line))
            continue
        m = OPEN.search(line)
        if m and not m.group("q"):
            tag = m.group("tag")
    return out


def test_there_are_chain_scripts_to_check():
    """A guard over an empty set passes forever and guards nothing."""
    assert CHAINS, "no chain scripts found — this test would pass vacuously"


@pytest.mark.parametrize("path", CHAINS, ids=lambda p: p.name)
def test_no_backticks_survive_into_an_unquoted_heredoc(path):
    bad = [(n, l) for n, l in unquoted_heredoc_lines(path) if "`" in l]
    assert not bad, (
        f"{path}: bash will execute what is between the backticks here, and a "
        f"`#` in front of it comments nothing:\n"
        + "\n".join(f"  line {n}: {l.strip()}" for n, l in bad))


@pytest.mark.parametrize("path", CHAINS, ids=lambda p: p.name)
def test_every_unquoted_heredoc_is_closed(path):
    """An unterminated heredoc swallows the rest of the script in silence."""
    text = path.read_text().splitlines()
    tag = None
    for line in text:
        if tag is not None:
            if line.strip() == tag:
                tag = None
            continue
        m = OPEN.search(line)
        if m and not m.group("q"):
            tag = m.group("tag")
    assert tag is None, f"{path}: heredoc <<{tag} is never closed"


def test_the_detector_would_have_caught_the_bug_it_was_written_for(tmp_path):
    """A guard nobody has seen fail is a guard nobody knows works."""
    p = tmp_path / "chain_fake.sh"
    p.write_text("cat > /tmp/x.py <<PY\n# raised on `import`, so vllm never starts\nPY\n")
    assert any("`" in l for _, l in unquoted_heredoc_lines(p))
    # and the quoted form is correctly left alone
    q = tmp_path / "chain_quoted.sh"
    q.write_text("cat > /tmp/x.py <<'PY'\n# `import` is safe here\nPY\n")
    assert not unquoted_heredoc_lines(q)
