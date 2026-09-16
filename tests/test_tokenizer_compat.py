"""P4's first step: whether a drafter and a target share an id space.

The plan asserted this and marked it [read]. These are the real shapes, measured
2026-09-16 from the published tokenizers **[ran]**.
"""

from training.harness.tokenizer_compat import compare, reading


def tok(vocab, added=()):
    return {"model": {"vocab": vocab, "merges": ["a b"]},
            "added_tokens": [{"id": i, "content": c} for i, c in added]}


def test_an_identical_tokenizer_needs_nothing_handled():
    """Every Qwen2.5-Instruct size hashes the same — 3B through 72B [ran]."""
    v = {"a": 0, "b": 1}
    out = compare(tok(v, [(9, "<|im_end|>")]), tok(v, [(9, "<|im_end|>")]))
    assert out["usable_for_speculation"]
    assert out["guaranteed_rejection_ids"] == []
    assert "nothing to handle" in reading(out)


def test_the_qwen3_shape_is_usable_but_carries_guaranteed_rejections():
    """Same 151,643-entry map, no collisions, four extra special ids [ran]."""
    v = {"a": 0, "b": 1}
    out = compare(tok(v, [(9, "<|im_end|>")]),
                  tok(v, [(9, "<|im_end|>"), (151667, "<think>"),
                          (151668, "</think>")]))
    assert out["usable_for_speculation"] is True
    assert out["guaranteed_rejection_ids"] == [151667, 151668]
    r = reading(out)
    assert "thinking target rejects" in r and "C7" in r


def test_an_id_meaning_two_different_things_disqualifies_the_pair():
    """The silent failure: a drafted id accepted as a string the drafter did not mean."""
    v = {"a": 0}
    out = compare(tok(v, [(7, "<|pad|>")]), tok(v, [(7, "<|mask|>")]))
    assert out["usable_for_speculation"] is False
    assert out["id_collisions"] == {7: ("<|pad|>", "<|mask|>")}
    assert "two different things" in reading(out)


def test_differing_vocabularies_are_refused():
    out = compare(tok({"a": 0}), tok({"a": 1}))
    assert out["usable_for_speculation"] is False
    assert "disagree" in reading(out)


def test_both_vocabulary_sizes_are_reported_not_just_the_drafter_s():
    """A 248k-entry target printing the drafter's 151k is how a pair gets misread."""
    out = compare(tok({"a": 0}), tok({"a": 0, "b": 1, "c": 2}))
    assert out["drafter_vocab"] == 1
    assert out["target_vocab"] == 3
    assert "vocab_size" not in out


def test_merges_may_differ_without_disqualifying_the_pair():
    """`merges` govern text -> ids, which happens once; speculation lives in id space."""
    v = {"a": 0, "b": 1}
    a, b = tok(v), tok(v)
    b["model"]["merges"] = ["b a"]
    out = compare(a, b)
    assert out["merges_identical"] is False
    assert out["usable_for_speculation"] is True
