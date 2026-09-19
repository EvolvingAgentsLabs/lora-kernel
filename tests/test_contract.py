"""The pool contract, and the check that keeps a declaration honest.

The band is the field P45 forced into existence: `fluids-full` was trained only on
6-to-9-step chains, and served a two-step problem it over-solves on 18 of 18 cases
rather than simplifying **[ran]**. A band nobody verifies is worse than no band,
because a caller would act on it — so the corpora are re-read here.
"""

import json
import pathlib
import re

import pytest

from training.harness import contract
from training.harness.train_pool import POOL

CALL = re.compile(r"<(calc|lookup|convert|thread_history|sender_stats|message)>")


def _corpus_band(path: str) -> tuple[int, int]:
    counts = []
    for line in pathlib.Path(path).open():
        if not line.strip():
            continue
        row = json.loads(line)
        text = "".join(m["content"] for m in row["messages"]
                       if m["role"] == "assistant")
        counts.append(len(CALL.findall(text)))
    assert counts, f"{path} has no examples"
    return min(counts), max(counts)


@pytest.mark.parametrize("path", sorted(POOL))
def test_every_declared_band_matches_the_corpus_it_names(path):
    """A band is read off the corpus, never asserted.

    Doing this rather than trusting the first draft caught three of five wrong:
    `kernel-mt` declared 6-9 and is 2-4, `kernel-email` is 1-1 exactly, and
    `domain-mt` calls nothing in 600 of 600 **[ran]** 2026-09-15.
    """
    record = POOL[path]
    corpus = pathlib.Path(record["corpus"])
    if not corpus.exists():
        pytest.skip(f"{corpus} is not checked in")
    lo, hi = _corpus_band(str(corpus))
    assert (record["band"]["min_steps"], record["band"]["max_steps"]) == (lo, hi), (
        f"{path} declares {record['band']} but {corpus} contains {lo}-{hi} steps")


def test_the_pool_validates_at_import():
    assert contract.validate_pool(POOL) == POOL


def test_a_member_without_a_band_is_refused():
    with pytest.raises(contract.ContractError, match="band"):
        contract.validate("adapters/x", {"corpus": "c.jsonl",
                                         "output_contract": {"kind": "text"}})


def test_a_zero_step_band_is_legal_because_one_adapter_never_calls_anything():
    # `domain-mt` is the physics corpus with the protocol removed; refusing 0 would
    # make the one adapter that never uses a tool undeclarable.
    r = contract.text("c.jsonl", contract.band(0, 0))
    assert contract.validate("adapters/x", r)["band"]["max_steps"] == 0
    assert contract.accepts(r, 0) and not contract.accepts(r, 1)


def test_a_backwards_band_is_refused():
    with pytest.raises(contract.ContractError, match="not a range"):
        contract.band(4, 2)


def test_accepts_is_the_question_p45_made_answerable():
    # The retired fluids member was trained on 6-to-9-step chains only and over-solved
    # 18 of 18 cases below that band [ran] P45 (tag v0.1-foundations). The band is what
    # lets a router refuse such a member a two-step problem.
    deep_only = {"band": contract.band(6, 9)}
    assert not contract.accepts(deep_only, 2), "a two-step problem is outside its band"
    assert contract.accepts(deep_only, 7)


def test_a_typed_member_without_token_ids_is_refused():
    with pytest.raises(contract.ContractError, match="value_tokens"):
        contract.validate("adapters/t", {
            "corpus": "c.jsonl", "band": contract.band(0, 0),
            "output_contract": {"kind": "typed", "type": "enum",
                                "values": ["yes", "no"], "value_tokens": []}})


def test_two_typed_values_sharing_a_token_are_refused():
    with pytest.raises(contract.ContractError, match="share a token"):
        contract.validate("adapters/t", contract.typed(
            "c.jsonl", contract.band(0, 0), ["yes", "no"], [9693, 9693]))


def test_an_unknown_output_kind_is_refused():
    with pytest.raises(contract.ContractError, match="not one of"):
        contract.validate("adapters/x", {"corpus": "c.jsonl",
                                         "band": contract.band(0, 0),
                                         "output_contract": {"kind": "logits"}})


def test_a_typed_record_round_trips():
    r = contract.typed("c.jsonl", contract.band(0, 0), ["yes", "no"], [9693, 2152])
    assert contract.validate("adapters/t", r)["output_contract"]["values"] == ["yes", "no"]
