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


# ---------------------------------------------------------------------------
# `set -u` AND AN OPTIONAL SWITCH ARE A DEAD CHAIN.
#
# chain_serve.sh referenced `$TRAINDEPS` inside a heredoc. Launched without it,
# bash exited with `TRAINDEPS: unbound variable` — reported at the heredoc's
# line, not the reference's, so the message points at the wrong place
# **[ran]** 2026-09-14. Same family as the `${ARGS:-}` bug recorded inside
# chain_separate.sh, which cost two sessions of seventy-seven minutes each.
# ---------------------------------------------------------------------------

# `;` SEPARATES ASSIGNMENTS TOO. Anchoring only at the start of a line made
# this report `SESSIONS="${1:-1}"; GPU="${GPU:-L4}"` as an undefaulted read of
# $GPU — a detector that invents findings is as useless as one that misses
# them, and it was caught on its own first run.
ASSIGN = re.compile(r"(?:^|;|\bthen\b|\bdo\b)\s*([A-Z_][A-Z0-9_]*)=", re.M)
REF = re.compile(r"\$\{?([A-Z_][A-Z0-9_]*)\}?")
# Shell and Colab supply these; the script is not expected to define them.
AMBIENT = {"PATH", "HOME", "PWD", "SHELL", "USER", "TMPDIR", "LANG", "PYTHONPATH"}


@pytest.mark.parametrize("path", CHAINS, ids=lambda p: p.name)
def test_every_variable_is_defaulted_before_it_is_read(path):
    """Under `set -u`, reading an unset variable ends the script.

    A reference is safe if the script assigns the name itself, or if that use
    site carries its own `:-` default. Anything else is a switch that works
    only when the caller happens to pass it.
    """
    text = path.read_text()
    if "set -u" not in text and "set -euo" not in text:
        pytest.skip(f"{path.name} does not run under set -u")
    assigned = set(ASSIGN.findall(text)) | AMBIENT
    bad = []
    for i, line in enumerate(text.splitlines(), 1):
        for name in REF.findall(line):
            if name in assigned:
                continue
            if f"${{{name}:-" in line or f"${{{name}-" in line:
                continue          # defaulted right where it is read
            bad.append((i, name, line.strip()))
    assert not bad, (
        f"{path}: read under `set -u` without a default — the chain dies on launch "
        "when the caller omits it:\n"
        + "\n".join(f"  line {n}: ${v}  in  {l[:90]}" for n, v, l in bad))


def test_the_assignment_detector_sees_past_a_semicolon(tmp_path):
    """Its own first run reported `GPU="${GPU:-L4}"` as undefaulted. It is not."""
    p = tmp_path / "chain_semi.sh"
    p.write_text('set -euo pipefail\nSESSIONS="${1:-1}"; GPU="${GPU:-L4}"\necho "$GPU"\n')
    assert "GPU" in set(ASSIGN.findall(p.read_text()))


# ---------------------------------------------------------------------------
# A FILTER THAT DOES NOT KNOW A RUNNER'S PREFIX TURNS ITS RUN INTO SILENCE.
#
# The chain watches a remote log through `grep -E '...'`. Five times a run
# produced exactly the line that explained it and the filter dropped it:
# argparse writes `error:` while the filter had `Error`; a `[tiny]` diagnosis
# printed on the VM was invisible where it was needed; and a 150-case
# `triage_run` scoring pass showed as silence for its whole length because
# `[run]` and `[arm]` were never in the pattern **[ran]** 2026-09-14.
#
# CLAUDE.md: "Never let a long run hide its position." A run whose position is
# invisible cannot be stopped early, and stopping early is where the money is.
# ---------------------------------------------------------------------------

import pathlib

PREFIX = re.compile(r'^\s*print\(f?"\[(\w+)\]', re.M)
RUNNERS = sorted(pathlib.Path("training/harness").glob("*.py"))


def peek_patterns(path: pathlib.Path) -> set[str]:
    """The bracketed tags a chain script's watcher will actually surface."""
    return set(re.findall(r"(\w+)\\\\\]", path.read_text()))


def test_the_watcher_knows_every_prefix_its_runners_print():
    """Anything a runner announces itself with has to reach the watching terminal."""
    watched = set()
    for chain in CHAINS:
        watched |= peek_patterns(chain)
    assert watched, "no bracketed prefixes found in any chain's peek filter"

    # Only the modules a chain can actually launch as MODULE=... matter here.
    launchable = {"serve_openai", "lora_matrix", "native_gate", "triage_run",
                  "multitool_run", "train_pool", "tiny_adapter"}
    missing = {}
    for f in RUNNERS:
        if f.stem not in launchable:
            continue
        for tag in set(PREFIX.findall(f.read_text())):
            if tag not in watched:
                missing.setdefault(f.name, set()).add(tag)
    assert not missing, (
        "these runners print progress under a prefix no chain watcher matches, so "
        "their runs read as silence:\n"
        + "\n".join(f"  {k}: {sorted(v)}" for k, v in sorted(missing.items())))
