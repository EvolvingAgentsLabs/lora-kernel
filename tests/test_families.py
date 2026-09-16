"""Drawn programs: three languages agree, and with an oracle written separately.

`reference.py`'s fifteen hand-written programs are an evaluation set, not a corpus —
fifteen programs train nothing, so **step zero could not be run on them at all**. And
a hand-written `crc32` with the standard polynomial is in every model's training data,
which is P42's ceiling. Drawing the constants per case fixes both: there is as much
corpus as we want, and the expected output did not exist before the case did.
"""

import random
import shutil
import sys

import pytest

from training.code.families import FAMILIES, LANGUAGES, draw
from training.code.suite import RunError, run_source

HAVE = {"python": sys.executable, "javascript": shutil.which("node"),
        "c": shutil.which("gcc")}
DRAWN = [draw(random.Random(s), f)
         for s in range(6) for f in sorted(FAMILIES)]


@pytest.mark.parametrize("program", DRAWN,
                         ids=[f"{p['family']}-{i}" for i, p in enumerate(DRAWN)])
def test_three_languages_agree_with_an_oracle_written_separately(program):
    """The oracle is computed in the generator, not by running an implementation.

    So three implementations agreeing with it is three independent checks rather
    than one implementation agreeing with itself.
    """
    for lang in LANGUAGES:
        if not HAVE[lang]:
            pytest.skip(f"{lang} toolchain absent")
        assert run_source(program[lang], lang) == program["answer"], lang


def test_the_constants_actually_vary():
    """A family that draws the same program every time is a hand-written program."""
    rng = random.Random(1)
    answers = {draw(rng, "crc")["answer"] for _ in range(20)}
    assert len(answers) >= 15, "crc is not drawing distinct programs"
    shifts = {draw(rng, "xorshift")["spec"] for _ in range(20)}
    assert len(shifts) >= 4, "xorshift is not drawing distinct shift amounts"


def test_the_answer_is_never_in_the_program_text():
    """Otherwise the completion transcribes a number instead of computing it."""
    rng = random.Random(3)
    for _ in range(20):
        p = draw(rng)
        for lang in LANGUAGES:
            assert p["answer"].split()[0] not in p[lang], (p["family"], lang)


def test_the_spec_names_the_constants_the_completion_needs():
    rng = random.Random(5)
    crc = draw(rng, "crc")
    assert "polynomial 0x" in crc["spec"] and "final xor" in crc["spec"]
    xs = draw(rng, "xorshift")
    assert "shifts" in xs["spec"]


def test_a_broken_completion_is_reported_rather_than_scored_as_wrong_output():
    if not HAVE["python"]:
        pytest.skip("python absent")
    with pytest.raises(RunError):
        run_source("def f(:\n", "python")
