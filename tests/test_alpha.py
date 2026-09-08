"""The instrument is asked to lie on purpose.

An instrument that cannot be made to fail on demand is not yet understood. Each
test below is one of the ways this measurement could produce a clean, wrong
number, pinned so it cannot come back quietly.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alpha.cases import content_offset, parse_answer, payload, verify  # noqa: E402
from alpha.measure import lcp  # noqa: E402


# -- the acceptance arithmetic --------------------------------------------------

def test_identical_candidate_accepts_everything():
    """A candidate that IS the target must score 1.0, or the metric is broken."""
    want = 'ents": ["cbct", "med'
    assert lcp(want, want) == len(want)


def test_pure_noise_accepts_nothing():
    assert lcp("qqqq", "abcd") == 0


def test_alpha_is_a_prefix_not_an_overlap():
    """Speculative decoding stops at the FIRST rejection. A draft that agrees
    everywhere except position 1 accepts one character, not five."""
    assert lcp("a_cdef", "abcdef") == 1


def test_empty_draft_is_zero_not_a_crash():
    assert lcp("", "abcd") == 0






# -- the failure the FIRST S0 run actually produced ------------------------------

PRETTY = '```json\n{\n  "kind": "x",\n  "arguments": {\n    "missing": [\n      "cbct"\n    ]\n  }\n}\n```'
FENCED = '```json\n{"kind": "submit_missing_documents", "arguments": {"missing": ["cbct"]}}\n```'
PLAIN = '{"kind": "submit_missing_documents", "arguments": {"missing": ["cbct"]}}'
COMPACT = '{"kind":"submit_missing_documents","arguments":{"missing":["cbct"]}}'


def test_a_markdown_fence_is_not_a_disagreement():
    """Run 1 scored α = 0.00 between two identical answers because one was
    fenced. A metric that moves while the capability does not is deleted, not
    loosened — so the payload is compared, each side from its own marker."""
    assert lcp(FENCED, PLAIN) == 0
    assert payload(FENCED) == payload(PLAIN)


def test_whitespace_formatting_is_not_a_disagreement():
    assert payload(COMPACT) == payload(PLAIN)


def test_the_shared_preamble_is_not_measured():
    """Three models produced the same WRONG answer and scored α = 1.00 on the
    format alone. The payload of a different answer must not."""
    other = '{"kind": "submit_missing_documents", "arguments": {"missing": ["x"]}}'
    assert lcp(PLAIN, other) > 40          # the raw streams agree on the boilerplate
    assert lcp(payload(PLAIN), payload(other)) == 1   # '"' only — they disagree at once


def test_an_absent_format_is_none_not_zero():
    """A model that did not produce the declared shape has no payload. Scoring it
    as 0.0 would invent a disagreement; scoring it as 1.0 would invent an
    agreement. It is excluded and counted."""
    assert content_offset("I cannot help with that.") is None
    assert payload("no json here") is None


def test_an_empty_payload_is_an_answer_not_an_absence():
    """"Nothing is missing" is a real answer. Two models that both say it agree."""
    empty = '{"kind": "submit_missing_documents", "arguments": {"missing": []}}'
    assert payload(empty) == ""
    assert payload(empty) is not None


# -- the promotion criterion, decided in EXPERIMENT_PLAN.md §11 ------------------

def test_agreement_ignores_item_order():
    """Two models that named the same two documents agree, whatever order they
    listed them in. Character agreement cannot see this and never could."""
    from alpha.report import semantic
    a = '{"arguments": {"missing": ["cbct", "medical_history"]}}'
    b = '{"arguments": {"missing": ["medical_history", "cbct"]}}'
    assert semantic(a, b) == (True, 1.0)


def test_agreement_ignores_layout():
    """The failure that forced this criterion: a correct compact answer scored
    0.00 against an indented target while an indented copy scored 1.00."""
    from alpha.report import semantic
    assert semantic(COMPACT, PRETTY)[0] is True


def test_agreement_is_not_verification():
    """Two models can agree perfectly and both be wrong. Agreement is measured
    against the TARGET, never against the truth — collapsing the two would make
    the criterion score itself."""
    from alpha.report import semantic
    wrong_a = '{"arguments": {"missing": ["insurance_card"]}}'
    wrong_b = '{"arguments": {"missing": ["insurance_card"]}}'
    assert semantic(wrong_a, wrong_b) == (True, 1.0)
    assert not verify(wrong_a, frozenset({"cbct"}))["passed"]


def test_partial_agreement_is_graded_not_binary():
    from alpha.report import semantic
    a = '{"arguments": {"missing": ["cbct"]}}'
    b = '{"arguments": {"missing": ["cbct", "medical_history"]}}'
    same, f1 = semantic(a, b)
    assert same is False and 0.6 < f1 < 0.7


def test_an_unparseable_side_is_excluded_not_scored():
    from alpha.report import semantic
    assert semantic("I cannot help", PLAIN) is None
    assert semantic(PLAIN, "I cannot help") is None


def test_both_empty_is_agreement():
    from alpha.report import semantic
    e = '{"arguments": {"missing": []}}'
    assert semantic(e, e) == (True, 1.0)


# -- the verifier ----------------------------------------------------------------

def test_unparseable_answer_fails_and_is_recorded_as_unparseable():
    r = verify("I cannot help with that.", frozenset({"cbct"}))
    assert r["passed"] is False and r["parsed"] is False


def test_prose_around_the_json_is_tolerated_but_wrong_content_is_not():
    good = verify('Here you go: {"arguments": {"missing": ["cbct"]}} — done',
                  frozenset({"cbct"}))
    assert good["passed"] and good["parsed"]
    bad = verify('{"arguments": {"missing": ["cbct", "insurance_card"]}}',
                 frozenset({"cbct"}))
    assert not bad["passed"] and bad["extra"] == ["insurance_card"]


def test_set_equality_not_containment():
    """Reporting a superset is not a pass. A packet check that over-reports sends
    a patient away for documents they already filed."""
    assert not verify('{"arguments": {"missing": ["cbct", "x"]}}',
                      frozenset({"cbct"}))["passed"]
    assert not verify('{"arguments": {"missing": []}}',
                      frozenset({"cbct"}))["passed"]


def test_empty_truth_is_passed_only_by_an_empty_answer():
    assert verify('{"arguments": {"missing": []}}', frozenset())["passed"]
    assert not verify('{"arguments": {"missing": ["cbct"]}}', frozenset())["passed"]


def test_a_missing_key_is_a_parse_failure_not_a_silent_pass():
    assert parse_answer('{"kind": "declare_unsolved"}') is None


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\n{len(fns)} checks passed")
