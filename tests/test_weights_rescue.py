"""`grep -c` prints its zero and exits 1, and that cost nine minutes of training.

The rescue added on 2026-09-14 exists to fetch an adapter tarball before a Colab
session is stopped. On 2026-09-15 it silently did not run, and the fluids expert
went with the session. The reason was not the rescue's logic but its arithmetic:

    $(tar tzf f | grep -c safetensors || echo 0)

On an empty archive `grep -c` prints "0" **and** exits 1, so `|| echo 0` fires too
and the expression is "0\\n0" — which is not equal to "0", so the guard read false
and skipped itself.
"""

import subprocess
import tarfile
from pathlib import Path

import pytest

CHAIN = Path("training/harness/chain_separate.sh")


def _weights_in(path) -> str:
    """Run the helper exactly as the chain defines it."""
    src = CHAIN.read_text()
    line = next(l for l in src.splitlines() if l.startswith("weights_in ()"))
    return subprocess.run(["bash", "-c", f'{line}\nweights_in "{path}"'],
                          capture_output=True, text=True).stdout.strip()


def test_the_buggy_form_really_does_produce_two_zeros():
    """Pinned, because the fix is only obvious once you have seen this."""
    r = subprocess.run(["bash", "-c",
                        'printf "x\\n" > /tmp/_p.txt; '
                        'echo "[$(grep -c zzz /tmp/_p.txt || echo 0)]"'],
                       capture_output=True, text=True)
    assert r.stdout.strip() == "[0\n0]"


def test_an_empty_tarball_counts_zero_not_zero_zero(tmp_path):
    empty = tmp_path / "adapters.tgz"
    with tarfile.open(empty, "w:gz"):
        pass
    assert _weights_in(empty) == "0"


def test_a_missing_tarball_counts_zero(tmp_path):
    assert _weights_in(tmp_path / "nothing.tgz") in ("0", "")


def test_a_tarball_with_weights_counts_them(tmp_path):
    d = tmp_path / "adapters" / "fluids-full"
    d.mkdir(parents=True)
    (d / "adapter_model.safetensors").write_bytes(b"0" * 64)
    tgz = tmp_path / "adapters.tgz"
    with tarfile.open(tgz, "w:gz") as t:
        t.add(tmp_path / "adapters", arcname="adapters")
    assert _weights_in(tgz) == "1"


def _code(path: Path) -> str:
    """The script with its comment lines removed.

    THIRD TIME TODAY A GUARD OF MINE FIRED ON PROSE EXPLAINING AN ABSENCE. The
    email corpus check refused the word `automated` inside an automated email's
    body; the domain-free check refused `fluid` inside a comment saying "no fluid
    names"; and this one refused the broken idiom inside the comment that documents
    it. A guard that reads source has to read the code.
    """
    return "\n".join(l for l in path.read_text().splitlines()
                      if not l.lstrip().startswith("#"))


def test_the_chain_no_longer_counts_with_the_broken_idiom():
    code = _code(CHAIN)
    assert "grep -c safetensors || echo 0" not in code
    assert code.count("weights_in ()") == 1, "the helper must have one definition"


def test_the_guard_reads_code_and_not_the_comment_that_explains_it():
    """Pinned: the chain deliberately quotes the broken idiom in a comment."""
    assert "grep -c safetensors || echo 0" in CHAIN.read_text()
    assert "grep -c safetensors || echo 0" not in _code(CHAIN)


def test_the_rescue_packs_every_adapter_not_one_by_name():
    """A pack script naming `adapters/kernel-email` produced a 45-byte tarball in a
    session that had trained `adapters/fluids-full`."""
    code = _code(CHAIN)
    assert "tar czf adapters.tgz adapters" in code
    assert "adapters/kernel-email" not in code
