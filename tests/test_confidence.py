"""Reading a confidence off the wire, and the ways that could be wrong."""

import math

import pytest

from training.harness.confidence import confidence_from


def _out(text, tops):
    return {"choices": [{"message": {"content": text},
                         "logprobs": {"content": [{"top_logprobs": [
                             {"token": t, "logprob": math.log(p)} for t, p in tops]}]}}]}


def test_the_confidence_is_in_the_answer_given_not_in_the_larger_class():
    """A router thresholds on *this answer*, so a confident NOT IMPORTANT must read
    as confident — not as 0.2 because the other class is small."""
    said, conf, _ = confidence_from(_out("NOT IMPORTANT", [("NOT", 0.9), ("IMP", 0.1)]))
    assert said is False and conf == pytest.approx(0.9, abs=1e-6)


def test_an_important_verdict_reads_its_own_mass():
    said, conf, _ = confidence_from(_out("IMPORTANT", [("IMP", 0.7), ("NOT", 0.3)]))
    assert said is True and conf == pytest.approx(0.7, abs=1e-6)


def test_mass_is_summed_over_every_spelling_of_the_same_decision():
    """Tokenisers split these differently; missing a variant silently shrinks the
    denominator and inflates the confidence."""
    said, conf, _ = confidence_from(
        _out("NOT IMPORTANT", [("NOT", 0.5), (" NOT", 0.3), ("IMP", 0.2)]))
    assert conf == pytest.approx(0.8, abs=1e-6)


def test_a_reply_with_no_logprobs_yields_no_confidence_rather_than_a_guess():
    out = {"choices": [{"message": {"content": "NOT IMPORTANT"}}]}
    said, conf, _ = confidence_from(out)
    assert said is False and conf is None


def test_an_unparseable_verdict_is_not_scored_as_wrong():
    """A model that said nothing has not answered incorrectly, and adding the two
    is how a broken channel reads as a bad model."""
    said, conf, _ = confidence_from(_out("hmm", [("hm", 0.9), ("IMP", 0.1)]))
    assert said is None


def test_no_recognised_token_yields_no_confidence():
    said, conf, _ = confidence_from(_out("IMPORTANT", [("xyz", 0.6), ("qqq", 0.4)]))
    assert conf is None


def test_not_important_is_read_as_not_rather_than_as_important():
    """`IMPORTANT` is a substring of `NOT IMPORTANT`; checking the wrong one first
    inverts every negative verdict in the suite."""
    said, _, _ = confidence_from(_out("NOT IMPORTANT", [("NOT", 0.9), ("IMP", 0.1)]))
    assert said is False
