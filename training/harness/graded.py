"""Experts graded by construction: nested subsets of one corpus.

WHY GRADED AND NOT DIFFERENT. The architecture's central claim is that acceptance
against a larger target **orders experts the way verified quality orders them** —
and it has never been tested, because this project has never had two experts that
differ in quality on the same input. Every suite it built produced either one expert
at 1.000 or one that fails; language experts on code would be told apart by twelve
keywords **[ran]** P1/S3, and a pool of far-apart domains never meets in one problem.

So the experts are made to differ **by construction**: the same corpus, the same
base, the same hyperparameters, and only the amount of data changes. `g75` has seen
75 examples, `g200` two hundred, `email-full` all 598. If verified quality then
orders them — and `tests/test_accept_rank.py` gates on the scorer resolving that
order before any acceptance is bought — there is, for the first time, an ordering
for α to agree or disagree with.

NESTED, NOT INDEPENDENT. One shuffle, seeded, and each grade is a prefix of it, so
`g75 ⊂ g200 ⊂ full`. A grade that saw different examples rather than fewer would
confound *how much* with *which*.

    python3 -m training.harness.graded          # writes the subset files
"""

from __future__ import annotations

import json
import random
from pathlib import Path

FULL = Path("training/harness/data_ef/train.jsonl")
SIZES = (75, 200)
SEED = 0


def nested_subsets(rows: list[dict], sizes=SIZES, seed: int = SEED) -> dict[int, list[dict]]:
    order = list(range(len(rows)))
    random.Random(seed).shuffle(order)
    return {k: [rows[i] for i in sorted(order[:k])] for k in sizes}


def path_for(size: int) -> Path:
    return FULL.with_name(f"train_g{size}.jsonl")


def write(rows: list[dict] | None = None) -> dict[int, Path]:
    rows = rows or [json.loads(l) for l in FULL.read_text().splitlines() if l.strip()]
    out = {}
    for size, sub in nested_subsets(rows).items():
        # THE SAME BALANCE RULE THE FULL CORPUS ENFORCES. A 75-row draw that came
        # out 80% one answer would teach that answer, and the grade would then
        # differ from the others in *what* it learned rather than *how much*.
        share = sum(r["truth"] for r in sub) / len(sub)
        assert 0.3 <= share <= 0.7, f"g{size} is {share:.0%} important — too lopsided"
        p = path_for(size)
        p.write_text("\n".join(json.dumps(r) for r in sub) + "\n")
        out[size] = p
    return out


if __name__ == "__main__":
    for size, p in write().items():
        print(f"g{size}: {p}")
