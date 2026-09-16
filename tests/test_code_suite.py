"""The code-completion suite: its references run, and its oracle reconstructs itself.

WHY THIS PREDICATE. C9 measured that layout dominates agreement — identical answers
scored 0.00 across formats **[ran]**. A code prefix has already fixed the layout, so
what is left to predict is the algorithm. And the difficulty is where the
implementation is cut, which comes from the code rather than from us — the answer to
the report's finding that a generated suite cannot hold a difficulty nobody thought of.
"""

import shutil
import subprocess
import sys

import pytest

from training.code.reference import ALGORITHMS, LANGUAGES, REFERENCE
from training.code.suite import (
    DEPTHS,
    generate,
    run_source,
    strip_fences,
    truncate,
    verify,
)
from training.suite_gates import inspect

NEEDS = {"python": sys.executable, "javascript": "node", "c": "gcc"}
HAVE = {lang: (exe if lang == "python" else shutil.which(exe))
        for lang, exe in NEEDS.items()}


def _tail(case):
    src = REFERENCE[(case["algorithm"], case["region"])][0]
    return src[len(case["prefix"]):]


def test_every_pair_has_a_reference():
    assert set(REFERENCE) == {(a, l) for a in ALGORITHMS for l in LANGUAGES}


@pytest.mark.parametrize("algorithm", sorted(ALGORITHMS))
def test_all_three_languages_agree_on_the_answer(algorithm):
    """What makes the verifier EXACT rather than a tolerance.

    Three independent implementations printing the same string is a much stronger
    check than one implementation printing something. `base32` additionally
    reproduces the published RFC 4648 vectors, so one of the five is checked against
    something outside this repository.
    """
    outs = {}
    for lang in LANGUAGES:
        if not HAVE[lang]:
            pytest.skip(f"{lang} toolchain absent")
        outs[lang] = run_source(REFERENCE[(algorithm, lang)][0], lang)
    assert len(set(outs.values())) == 1, outs


def test_base32_matches_the_published_rfc_vectors():
    if not HAVE["python"]:
        pytest.skip("python absent")
    got = run_source(REFERENCE[("base32", "python")][0], "python")
    assert got == "- MY====== MZXQ==== MZXW6=== MZXW6YQ= MZXW6YTB MZXW6YTBOI======"


@pytest.mark.parametrize("case", generate(), ids=lambda c: c["case_id"])
def test_the_oracle_completion_reconstructs_the_reference(case):
    """A suite whose own answer does not verify is broken before a model sees it."""
    if not HAVE[case["region"]]:
        pytest.skip(f"{case['region']} toolchain absent")
    r = verify(case, _tail(case))
    assert r["correct"], f"{case['case_id']}: {r['why']}"


def test_the_grid_is_full_and_depth_spans_every_language():
    cases = generate()
    assert len(cases) == len(ALGORITHMS) * len(LANGUAGES) * len(DEPTHS)
    for lang in LANGUAGES:
        assert {c["depth"] for c in cases if c["region"] == lang} == set(DEPTHS)


def test_deeper_cuts_remove_more():
    for algorithm in ALGORITHMS:
        for lang in LANGUAGES:
            src = REFERENCE[(algorithm, lang)][0]
            cuts = [truncate(src, d)[1] for d in sorted(DEPTHS)]
            assert cuts == sorted(cuts), (algorithm, lang, cuts)
            assert cuts[-1] > cuts[0]


def test_the_prefix_never_contains_the_expected_output():
    """Otherwise the model transcribes a number instead of computing it."""
    if not HAVE["python"]:
        pytest.skip("python absent")
    for case in generate(languages=("python",)):
        from training.code.suite import expected
        want = expected(case["algorithm"], "python")
        assert want not in case["prefix"], case["case_id"]


def test_fences_are_stripped_because_refusing_them_would_measure_phrasing():
    body = "print(1)\n"
    assert strip_fences(f"```python\n{body}```") == "print(1)"
    assert strip_fences(body) == "print(1)"


def test_a_completion_that_does_not_run_is_incorrect_and_says_why():
    if not HAVE["python"]:
        pytest.skip("python absent")
    case = generate(languages=("python",), algorithms=("crc32",), depths=(4,))[0]
    r = verify(case, "this is not python\n")
    assert r["correct"] is False and r["why"]


def test_the_suite_passes_its_gates_with_one_declared_waiver():
    cases = generate()
    rep = inspect("code", cases, region_of=lambda c: c["region"],
                  prompt_of=lambda c: c["prompt"], depth_of=lambda c: c["depth"],
                  answer_of=_tail,
                  waive={"region_not_in_the_prompt":
                         "ranking, not routing — the language is the code"})
    assert rep.usable is True
    assert rep.waived == ["region_not_in_the_prompt"], (
        "a second waiver means a gate is being ignored by habit")


def test_the_copy_gate_replaces_the_tool_gate_rather_than_sitting_beside_it():
    """Exactly one of the two applies, chosen by the task's shape."""
    cases = generate()
    rep = inspect("code", cases, region_of=lambda c: c["region"],
                  prompt_of=lambda c: c["prompt"], depth_of=lambda c: c["depth"],
                  answer_of=_tail,
                  waive={"region_not_in_the_prompt": "ranking"})
    names = [f.gate for f in rep.findings]
    assert "the_answer_is_not_a_copy" in names
    assert "asking_is_a_decision" not in names
