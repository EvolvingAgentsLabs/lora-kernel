"""The corpus and the held-out set for step zero: does the adapter beat the base?

STEP ZERO IS THE SMALLEST THING THAT SHOWS THE IDEA WORKS OR DOES NOT. One language,
one adapter, one question: **does a base model with the right LoRA complete these
programs better than the base alone?** If no, nothing downstream is worth buying —
not the pool, not acceptance, not ranking. If yes, all of it becomes buyable and this
is the first rung.

WHERE THE DATA COMES FROM, WHICH THE FIRST DEFINITION HAD NO ANSWER TO. `reference.py`
holds fifteen hand-written programs; fifteen programs train nothing. `families.py`
draws them instead, with the constants fixed per case, so there is as much corpus as
we want **and the expected output did not exist before the case was generated**. That
is P15's lesson: a suite whose values can be recalled is answered without doing the
work — measured at 27/30 — and only drawing them per case made the experiment
measure anything.

THE SPLIT IS BY SEED AND BY CONTENT. Training draws from one seed and evaluation from
another, and every training prompt that reproduces an evaluation prompt is dropped.
`generate_email_full` learned that the hard way: skipping the evaluation's seed was
not enough, because a different draw reproduces a case by chance **[ran]**.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from training.code.families import FAMILIES, draw
from training.code.suite import INSTRUCTION, SPEC_PREAMBLE, cut_points, prompt_for

TRAIN_SEED, EVAL_SEED = 515151, 929292


def cases_from(program: dict, language: str, cuts: int, rng: random.Random) -> list[dict]:
    """One drawn program becomes several completion cases, cut at different points."""
    source = program[language]
    out = []
    for depth, prefix, removed in cut_points(source, cuts, rng):
        out.append({
            "family": program["family"], "region": language, "depth": depth,
            "prefix": prefix, "completion": source[len(prefix):],
            "answer": program["answer"], "spec": program["spec"],
            "lines_removed": removed,
            "prompt": prompt_for(program["spec"], language, prefix),
        })
    return out


def build(n_programs: int, seed: int, language: str, cuts: int = 3,
          families=tuple(sorted(FAMILIES))) -> list[dict]:
    rng = random.Random(seed)
    cases = []
    for i in range(n_programs):
        program = draw(rng, families[i % len(families)])
        cases.extend(cases_from(program, language, cuts, rng))
    for i, c in enumerate(cases):
        c["case_id"] = f"{language[:2]}-{seed}-{i:04d}"
    return cases


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--language", default="python")
    ap.add_argument("--programs", type=int, default=200)
    ap.add_argument("--cuts", type=int, default=3)
    ap.add_argument("--eval-programs", type=int, default=60)
    ap.add_argument("--out", default="training/code/data")
    args = ap.parse_args()

    held = build(args.eval_programs, EVAL_SEED, args.language, args.cuts)
    held_prompts = {c["prompt"] for c in held}
    train = [c for c in build(args.programs, TRAIN_SEED, args.language, args.cuts)
             if c["prompt"] not in held_prompts]
    dropped = args.programs * args.cuts - len(train)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / f"train.{args.language}.jsonl").open("w") as f:
        for c in train:
            f.write(json.dumps({
                "case_id": c["case_id"], "family": c["family"], "depth": c["depth"],
                "messages": [{"role": "user", "content": c["prompt"]},
                             {"role": "assistant", "content": c["completion"]}],
            }) + "\n")
    with (out / f"eval.{args.language}.jsonl").open("w") as f:
        for c in held:
            f.write(json.dumps(c) + "\n")
    print(f"[corpus] {len(train)} training examples, {len(held)} held out, "
          f"{dropped} dropped for reproducing an evaluation prompt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
