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
import sys
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
# THE NAME HAS TO END WHERE THE DETECTOR SAYS IT DOES. Without the lookahead
# this reads `$_self` — an ordinary lowercase local — as a reference to `$_`,
# and reports it as an undefaulted environment variable. Second false positive
# this guard has produced, and both were about where a token stops.
REF = re.compile(r"\$\{?([A-Z_][A-Z0-9_]*)\}?(?![A-Za-z0-9_])")
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
    """The bracketed tags a chain script's watcher will actually surface.

    Both shapes: one tag per alternative (`run\\]|arm\\]`) and a single
    alternation group (`(run|arm)\\]`), which is what the filters became when
    they had to hold two dozen prefixes.
    """
    body = path.read_text()
    tags = set(re.findall(r"(\w+)\\\\\]", body))
    for group in re.findall(r"\(([\w|]+)\)\\\\\]", body):
        tags |= set(group.split("|"))
    return tags


def test_the_watcher_knows_every_prefix_its_runners_print():
    """Anything a runner announces itself with has to reach the watching terminal."""
    watched = set()
    for chain in CHAINS:
        watched |= peek_patterns(chain)
    assert watched, "no bracketed prefixes found in any chain's peek filter"

    # WHICH MODULES A CHAIN CAN LAUNCH, DERIVED. This was a hand-kept list, and a
    # hand-kept list always lags the newest runner — which is exactly the one whose
    # position nobody can see yet. `ladder_sweep` printed `[sweep]`, no filter
    # matched it, and this guard passed because the module was not on the list
    # **[ran]** 2026-09-15. A chain launches `python -m MODULE --out NAME`, so a
    # module with a `--out` flag and a `__main__` is one a chain can launch.
    launchable = {f.stem for f in RUNNERS
                  if '"--out"' in f.read_text() and "__main__" in f.read_text()}
    assert len(launchable) > 10, f"the derivation stopped finding runners: {launchable}"
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


# ---------------------------------------------------------------------------
# EDITING A RUNNING SCRIPT MOVES THE GROUND UNDER IT.
#
# Bash reads a script incrementally, by byte offset. A patch that landed while a
# chain was running killed the live instance with `line 184: syntax error near
# unexpected token 'done'` — after its run had finished but before its trap could
# stop the Colab session, which is where that afternoon's orphans came from
# **[ran]** 2026-09-14. Running from a copy makes it impossible rather than
# forbidden.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", CHAINS, ids=lambda p: p.name)
def test_a_chain_runs_from_a_copy_of_itself(path):
    text = path.read_text()
    assert "CHAIN_REEXEC" in text, (
        f"{path} runs from its own file; editing it mid-run corrupts the running "
        "instance")
    # the guard has to come before anything that takes time, or it guards nothing
    body = text.splitlines()
    i = next(n for n, l in enumerate(body) if "CHAIN_REEXEC" in l)
    before = "\n".join(body[:i])
    assert "colab " not in before, f"{path} talks to Colab before re-execing"


@pytest.mark.parametrize("path", CHAINS, ids=lambda p: p.name)
def test_the_copy_does_not_steal_the_exit_trap(path):
    """These scripts spend EXIT on `colab stop`, and bash keeps one handler."""
    text = path.read_text()
    if "colab stop" not in text:
        pytest.skip(f"{path.name} sets no session trap")
    assert "trap 'rm -f \"$CHAIN_REEXEC\"' EXIT" not in text


def test_the_reference_detector_does_not_read_a_lowercase_local_as_an_env_var():
    """`$_self` is not a reference to `$_`. Pinned, because it reported one."""
    assert REF.findall('cat "$0" > "$_self" && chmod +x "$_self"') == []
    assert REF.findall('echo "$GPU and ${BRANCH}"') == ["GPU", "BRANCH"]


# ---------------------------------------------------------------------------
# What a chain installs has to cover what the trainer imports. Fourth time a
# hand-kept list has lagged the thing it was supposed to track: `chain_serve.sh`
# learned to train, and its dependency line was never brought in line with the two
# chains that always did — so a run reached `SFTTrainer` and died on
# `ModuleNotFoundError: No module named 'trl'` after twenty minutes of boot
# **[ran]** 2026-09-16. The failure was even documented in a comment two lines
# above the list, recorded as *do not train in a serving session* rather than as
# *the list is short*.
# ---------------------------------------------------------------------------

#: Third-party modules the trainer imports that arrive with vLLM or with Colab, so
#: a chain does not have to install them. Anything else it imports, it must.
BUNDLED = {"torch", "transformers", "numpy"}

TRAINER = pathlib.Path("training/s4_train.py")


def trainer_imports() -> set[str]:
    """Top-level third-party modules `s4_train` imports, at any indentation."""
    body = TRAINER.read_text()
    found = set()
    for m in re.finditer(r"^\s*(?:from|import)\s+([a-zA-Z_][\w]*)", body, re.M):
        name = m.group(1)
        if name in ("training", "__future__"):
            continue
        if name in sys.stdlib_module_names:
            continue
        found.add(name)
    return found


def test_the_trainer_still_imports_what_we_think():
    needed = trainer_imports() - BUNDLED
    assert "trl" in needed and "peft" in needed and "datasets" in needed


#: What `trl` brings with it, from its own published requirements: accelerate,
#: datasets, transformers and peft **[read]** PyPI 2026-09-16. A chain that installs
#: trl therefore does not have to name those, and demanding it would fail the two
#: chains that have trained correctly for weeks.
TRANSITIVE = {"trl": {"accelerate", "datasets", "peft", "transformers"}}


INSTALL = re.compile(r"(?:pip -q install|colab install(?:\s+-s\s+\S+)?)([^\n\"']*)")


def install_commands(body: str) -> str:
    """Only the package names, never the prose around them.

    THE FILE IS THE WRONG THING TO SEARCH, AND SEARCHING IT WAS THIS CHECK'S OWN
    FIRST BUG. `chain_serve.sh` carries two comments about the P26 failure, both of
    which contain the word `trl` — so a substring test over the whole script found
    the dependency in the very prose explaining that it was missing. Three guards in
    this repository have now fired on text describing the absence they check for
    **[ran]**; this is the fourth, caught by a test written to break it on purpose.
    """
    return " ".join(m.group(1) for m in INSTALL.finditer(body))


def _installs_python_packages(body: str) -> bool:
    """A chain that only reaches for apt is not a chain that trains.

    `chain_ollama.sh` installs `curl` and `zstd` to fetch a model server. Asking it
    for `peft` would be asking the wrong script.
    """
    return bool(install_commands(body).strip())


def test_every_chain_that_can_train_installs_what_the_trainer_imports():
    needed = trainer_imports() - BUNDLED
    missing = {}
    for chain in CHAINS:
        body = chain.read_text()
        if not _installs_python_packages(body):
            continue
        installed = install_commands(body)
        covered = set()
        for pkg, brings in TRANSITIVE.items():
            if pkg in installed:
                covered |= brings
        absent = sorted(n for n in needed - covered if n not in installed)
        if absent:
            missing[chain.name] = absent
    assert not missing, (
        "these chains can train and do not install what the trainer imports, so a "
        "run dies at the import after paying for its boot:\n"
        + "\n".join(f"  {k}: {v}" for k, v in sorted(missing.items())))


def test_removing_trl_from_a_chain_is_caught():
    """The check has to fail on the thing that actually happened.

    `chain_serve.sh` learned to train and kept a dependency line that predated it,
    so a run died on `No module named 'trl'` after twenty minutes of boot.
    """
    needed = trainer_imports() - BUNDLED
    body = pathlib.Path("training/harness/chain_serve.sh").read_text()
    broken = install_commands(body.replace("peft trl datasets", "peft datasets"))
    covered = set()
    for pkg, brings in TRANSITIVE.items():
        if pkg in broken:
            covered |= brings
    assert sorted(n for n in needed - covered if n not in broken) == ["trl"]
    # and the word IS in the file, in the comments explaining the failure — which
    # is exactly why the file is the wrong thing to search.
    assert "trl" in body.replace("peft trl datasets", "peft datasets")



def test_the_chain_brings_a_runner_s_adapters_home():
    """P64 attempt 1 [ran]: a released member's weights stayed on the card."""
    from pathlib import Path
    chain = Path("training/harness/chain_serve.sh").read_text()
    assert "adapters_out.tgz" in chain
    assert "adapters_out.tgz" in Path("training/harness/pool_second.py").read_text()
    assert "results/*/adapters_out.tgz" in Path(".gitignore").read_text()


def test_the_pack_counter_survives_a_results_file_with_nothing_packed(tmp_path):
    """M1 attempt 2 [ran] 2026-09-19: `PACKS=$(grep … | grep … | tail -1)` under
    `set -euo pipefail` exits 1 when the key is not there yet — on the first poll of every
    run — and the chain's EXIT trap stopped an A100 that had just begun to train. The line
    is lifted from the script and run under the script's own shell options, because a syntax
    check cannot see an exit status."""
    import re
    import subprocess
    from pathlib import Path

    src = Path("training/harness/chain_serve.sh").read_text()
    opts = re.search(r"^set -[a-z]+ ?[a-z]*$", src, re.M).group(0)
    line = next(l.strip() for l in src.splitlines() if l.strip().startswith("PACKS=$("))
    for body, want in ((None, ""), ('{"arms": {}}', ""), ('{\n "packed": 2,\n "x": 1}', "2")):
        f = tmp_path / "r.json"
        if body is None:
            f.unlink(missing_ok=True) if hasattr(f, "unlink") and f.exists() else None
        else:
            f.write_text(body.replace("\\n", "\n"))
        r = subprocess.run(["bash", "-c", f'{opts}\nLOCAL="{f}"\n{line}\necho "[$PACKS]"'],
                           capture_output=True, text=True)
        assert r.returncode == 0 and r.stdout.strip() == f"[{want}]", (body, r.returncode, r.stdout, r.stderr)


def test_the_partial_results_carried_into_a_new_session_are_valid_json_without_the_marker(tmp_path):
    """A session lives sixty minutes [ran] 2026-09-19, so a long run is several sessions and the
    runner resumes from its results file. The marker of the LAST session's end has to come out on
    the way in — and a `sed` that deletes the last key of a JSON object leaves a trailing comma."""
    import json
    import re
    import subprocess
    from pathlib import Path

    src = Path("training/harness/chain_serve.sh").read_text()
    line = next(l.strip() for l in src.splitlines() if "d.pop(\"trained_only\"" in l)
    local, out = tmp_path / "r.json", tmp_path / "o.json"
    local.write_text(json.dumps({"arms": {"a": 1}, "packed": 1, "trained_only": "2026-09-19T12:50:00"}, indent=1))
    cmd = line.replace('"$LOCAL"', str(local)).replace("/tmp/_resume.json", str(out))
    assert subprocess.run(["bash", "-c", cmd]).returncode == 0
    assert json.loads(out.read_text()) == {"arms": {"a": 1}, "packed": 1}


def test_the_peek_sees_a_training_step_bar_that_tqdm_redraws_in_place(tmp_path):
    """The trainer prints no loss line, so the step bar is the only sign of life — and tqdm
    redraws it with a carriage return, which makes a whole training one line to `grep`.
    An abort rule keyed to `loss` fired on a healthy 114-step run [ran] M7 arm 0c."""
    import subprocess
    src = pathlib.Path("training/harness/chain_serve.sh").read_text()
    assert "tr '\\\\r' '\\\\n'" in src, "the peek must split tqdm's carriage returns before it greps"
    assert " [0-9]+/[0-9]+ \\\\[[0-9:]+<" in src
    pat = r" [0-9]+/[0-9]+ \[[0-9:]+<"          # what the shell receives once Python has read the line above
    log = tmp_path / "run.log"
    log.write_bytes(b"noise\n" + b"\r".join(f" {i}/114 [0{i % 10}:00<40:00, 23.1s/it]".encode() for i in (1, 2, 48)) + b"\n")
    out = subprocess.run(["bash", "-c", f"grep -E '{pat}' <(tr '\\r' '\\n' < {log}) | tail -1"],
                         capture_output=True, text=True).stdout
    assert "48/114" in out
