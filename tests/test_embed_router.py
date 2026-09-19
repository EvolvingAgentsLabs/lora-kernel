"""Milestone 2, arm 2: the decision rule of the embedding router — never a model, in tests.

THE MATHEMATICS THESE GUARD (docs/FOUNDATIONS.md §8.5): s_m(x) the mean cosine to the k nearest
corpus requests; served by argmax iff s ≥ τ_m, τ the 1st percentile held out; otherwise out."""

import subprocess
import sys

from training.harness import embed_router as er


def _router():
    corpora = {"alpha": [f"please triage message number {i} is this important" for i in range(60)],
               "beta": [f"on what date did you commit in thread number {i}" for i in range(60)]}
    return er.EmbedRouter(corpora, er.HashingEncoder())


def test_a_request_from_a_corpus_is_served_by_its_member():
    r = _router()
    assert r.decide_many(["please triage message number 999 is this important"]) == ["alpha"]
    assert r.decide_many(["on what date did you commit in thread number 999"]) == ["beta"]


def test_text_from_no_corpus_goes_out():
    assert _router().decide_many(["write a haiku about autumn rain in lisbon"]) == ["out"]


def test_the_stand_in_encoder_is_the_same_in_every_process():
    """`hash()` is randomised per process; an encoder built on it fails one run in five."""
    code = ("from training.harness.embed_router import HashingEncoder as H;"
            "print(sum(H().encode(['is this important'])[0][:64]))")
    seen = {subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                           env={"PYTHONHASHSEED": str(s), "PATH": "/usr/bin:/bin"}).stdout for s in (0, 1, 7)}
    assert len(seen) == 1 and "" not in seen


def test_the_verdict_names_the_wall_arm_1_hit():
    base = {k: {"n": n, "misrouted_to_local": 0, "lost_local": 0, "abstained": n, "local_right_member": 0}
            for k, n in (("C", 14), ("D", 76), ("E", 120), ("C2", 8), ("E2", 120))}
    ok = {**base, "A": {"n": 715, "misrouted_to_local": 0, "lost_local": 3, "local_right_member": 712},
          "F": {"n": 120, "misrouted_to_local": 0, "lost_local": 2, "local_right_member": 118},
          "B": {"n": 240, "misrouted_to_local": 0, "lost_local": 100, "local_right_member": 140}}
    assert er.verdict(ok)["passes"] is True
    wall = {**ok, "F": {"n": 120, "misrouted_to_local": 0, "lost_local": 120, "local_right_member": 0}}
    assert er.verdict(wall)["reading"].startswith("SAFE AND LOSES")
    leaky = {**ok, "E2": {"n": 120, "misrouted_to_local": 90, "lost_local": 0, "abstained": 30, "local_right_member": 0}}
    assert er.verdict(leaky)["reading"].startswith("NOT SAFE")
