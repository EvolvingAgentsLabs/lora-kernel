"""The corpus for step zero, and the split that keeps it honest."""

import json
import shutil
import sys
from pathlib import Path

import pytest

from training.code.corpus import EVAL_SEED, TRAIN_SEED, build
from training.code.suite import verify_against

HAVE_PY = bool(sys.executable)
DATA = Path("training/code/data")


def test_training_and_evaluation_come_from_different_seeds():
    assert TRAIN_SEED != EVAL_SEED


def test_no_training_prompt_reproduces_an_evaluation_prompt():
    """Skipping the evaluation's seed is not enough — a different draw can collide.

    `generate_email_full` measured exactly that: 2 of 150 evaluation listings recurred
    in a 600-example corpus **[ran]**. Here the check is on content, and the corpus
    build reports how many it dropped.
    """
    held = {c["prompt"] for c in build(40, EVAL_SEED, "python")}
    train = [c for c in build(60, TRAIN_SEED, "python") if c["prompt"] in held]
    assert not train, f"{len(train)} training prompts reproduce an evaluation prompt"


def test_every_case_carries_its_own_answer_and_a_runnable_prefix():
    for c in build(6, 11, "python"):
        assert c["answer"] and c["prefix"].strip()
        assert c["completion"], "nothing was removed"


@pytest.mark.skipif(not (DATA / "eval.python.jsonl").exists(),
                    reason="corpus not built")
def test_every_held_out_oracle_completion_verifies():
    """A suite whose own answer does not verify is broken before a model sees it."""
    if not shutil.which(sys.executable):
        pytest.skip("python absent")
    cases = [json.loads(l) for l in (DATA / "eval.python.jsonl").open()]
    assert len(cases) >= 100
    bad = [c["case_id"] for c in cases[:60]
           if not verify_against(c["prefix"], c["region"], c["answer"],
                                 c["completion"])["correct"]]
    assert not bad, bad[:5]


@pytest.mark.skipif(not (DATA / "train.python.jsonl").exists(),
                    reason="corpus not built")
def test_the_training_file_is_the_shape_the_trainer_reads():
    rows = [json.loads(l) for l in (DATA / "train.python.jsonl").open()]
    assert len(rows) >= 400
    for r in rows[:20]:
        roles = [m["role"] for m in r["messages"]]
        assert roles == ["user", "assistant"]
        assert r["messages"][1]["content"].strip()


# ---------------------------------------------------------------------------
# The check that would have voided P53 before it ran. Its prompts were all
# distinct and every one of its 180 held-out COMPLETIONS was already in the
# training set, word for word — so a +0.689 delta with p < 1e-5 measured one
# memorised tail per family **[ran]** 2026-09-16.
# ---------------------------------------------------------------------------

def test_held_out_completions_are_not_already_in_the_training_set():
    """Distinct prompts are not enough. The completion is what gets written.

    P53's constants lived in the prefix and were referenced by name, so one tail was
    correct for every instance of a family. Parameterising the constants did nothing,
    because the constants are the part that never has to be written.
    """
    held = build(40, EVAL_SEED, "python")
    train = {c["completion"] for c in build(120, TRAIN_SEED, "python")}
    repeated = [c["case_id"] for c in held if c["completion"] in train]
    share = len(repeated) / len(held)
    assert share < 0.20, (
        f"{len(repeated)} of {len(held)} held-out completions are already in the "
        "training set verbatim — the adapter can memorise the tail instead of "
        "learning the shape")


def test_two_programs_of_one_family_do_not_share_a_completion():
    """The sharpest form of the same check, and the one P53 failed outright."""
    cases = build(30, 4242, "python")
    for family in {c["family"] for c in cases}:
        same_depth = {}
        for c in (x for x in cases if x["family"] == family):
            same_depth.setdefault(c["depth"], []).append(c["completion"])
        for depth, comps in same_depth.items():
            if len(comps) < 2:
                continue
            assert len(set(comps)) > 1, (
                f"{family} at depth {depth}: every program has the same completion")


def test_held_out_skeletons_are_measured_even_though_they_are_not_novel():
    """The ceiling, asserted so it cannot be forgotten or quietly re-patched.

    P53 memorised one tail per family. P54 memorised one skeleton per (family, cut) —
    197 completions, 6 skeletons. Adding names and loop forms raised the shape space
    to about 60, and 720 training examples cover every shape twelve times over, so
    **204 of 204** held-out skeletons are still in training **[ran]** 2026-09-16.

    This test does not demand novelty, because the generator cannot provide it: for a
    held-out shape to be unseen the structural space must exceed the training set,
    which needs roughly ten structural dimensions of four choices each. It records
    the number instead, so a future change that claims to fix it has to move it.
    """
    import re
    held = build(40, EVAL_SEED, "python")
    train_sk = {re.sub(r"0x[0-9A-Fa-f]+|\b\d+\b", "N", c["completion"])
                for c in build(120, TRAIN_SEED, "python")}
    seen = sum(re.sub(r"0x[0-9A-Fa-f]+|\b\d+\b", "N", c["completion"]) in train_sk
               for c in held)
    # Recorded, not aspirational. If a change makes this drop, the docstring is stale.
    assert seen == len(held), (
        f"held-out skeleton novelty changed: {len(held) - seen} of {len(held)} are "
        "now unseen — update docs/analysis/generated-code-ceiling.md")


def test_structural_variety_at_least_broke_the_six_skeleton_collapse():
    """Not a fix, but not nothing: 6 shapes became about 60."""
    import re
    held = build(90, EVAL_SEED, "python")
    sk = {re.sub(r"0x[0-9A-Fa-f]+|\b\d+\b", "N", c["completion"]) for c in held}
    assert len(sk) > 20, f"only {len(sk)} distinct skeletons; P54 had 6"
