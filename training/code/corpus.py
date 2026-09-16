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
        completion = source[len(prefix):]
        # THE COMPLETION HAS TO CARRY SOMETHING THIS INSTANCE DREW. Otherwise the
        # tail is the same text for every program of the family, and an adapter that
        # memorises one tail scores 1.000 on held-out cases without computing
        # anything — which is exactly what P53 measured, 180 of 180 **[ran]**.
        if not any(v in completion for v in program.get("varies", [])):
            continue
        out.append({
            "family": program["family"], "region": language, "depth": depth,
            "prefix": prefix, "completion": completion,
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

    train_all = build(args.programs, TRAIN_SEED, args.language, args.cuts)
    held_all = build(args.eval_programs, EVAL_SEED, args.language, args.cuts)

    # DEDUPLICATED ON THE COMPLETION AS WELL AS THE PROMPT. P53's prompts were all
    # distinct and every one of its 180 held-out **completions** was already in the
    # training set, so the adapter scored 1.000 by reproducing one memorised tail
    # **[ran]**. A distinct prompt is not a distinct question when the answer is the
    # same text.
    train_prompts = {c["prompt"] for c in train_all}
    train_completions = {c["completion"] for c in train_all}
    held = [c for c in held_all
            if c["prompt"] not in train_prompts
            and c["completion"] not in train_completions]
    held_prompts = {c["prompt"] for c in held}
    train = [c for c in train_all if c["prompt"] not in held_prompts]
    dropped = len(held_all) - len(held)

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
          f"{dropped} held-out cases dropped for repeating a training prompt "
          f"or completion", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
