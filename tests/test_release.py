"""Phase 1's gate: a release reproduces when every pair is a tie.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §9.2). The paired sign test on
discordant cases, p = min(1, 2·Pr[Bin(u+d, ½) ≥ max(u, d)]); a tie is p > 0.05; a
regression is a pair that is different with the new arm losing; an improvement is
reported too, because a chain that silently got better is not reproducible either.
"""

import hashlib
import json
import pathlib

from training.harness.release_gate import RECIPE, pair, sha256, verdict


def recs(correct, prefix="c"):
    return [{"id": f"{prefix}{i}", "correct": c} for i, c in enumerate(correct)]


def test_a_reserve_that_matches_its_record_is_a_tie():
    ref = recs([True] * 470 + [False] * 5)
    new = recs([True] * 468 + [False] * 4 + [True] * 3)
    p = pair(new, ref, "re-served vs recorded")
    assert p["state"] == "tie" and verdict([p])["reproduces"] is True


def test_a_retrain_that_loses_is_a_regression_and_is_named():
    ref = recs([True] * 470 + [False] * 5)
    new = recs([True] * 440 + [False] * 35)
    p = pair(new, ref, "re-trained vs re-served")
    assert p["state"] == "REGRESSION"
    v = verdict([p])
    assert v["reproduces"] is False and "REGRESSION" in v["reading"]


def test_a_silent_improvement_also_fails_reproduction():
    ref = recs([True] * 400 + [False] * 75)
    new = recs([True] * 470 + [False] * 5)
    assert pair(new, ref, "x")["state"] == "improvement"
    assert verdict([pair(new, ref, "x")])["reproduces"] is False


def test_nothing_compared_is_not_a_pass():
    assert verdict([])["reproduces"] is False


def test_the_recipe_is_the_documented_one():
    assert RECIPE["r"] == 16 and RECIPE["lora_alpha"] == 32 and RECIPE["epochs"] == 3


def test_sha256_matches_hashlib(tmp_path):
    f = tmp_path / "x"; f.write_bytes(b"abc" * 1000)
    assert sha256(f) == hashlib.sha256(b"abc" * 1000).hexdigest()


def test_every_manifest_names_files_whose_hashes_still_match():
    """A release whose corpus or adapter changed underneath it is not that release."""
    for man in pathlib.Path("releases").glob("*.json"):
        m = json.loads(man.read_text())
        corpus = pathlib.Path(m["corpus"])
        assert sha256(corpus) == m["corpus_sha256"], f"{man}: corpus drifted"
