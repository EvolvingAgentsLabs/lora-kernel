"""Training data for the expert adapters — generated, never borrowed from the seal.

WHERE THE DATA COMES FROM. `../verified-runtime` ships the generator that made the
sealed benchmark, parameterised by seed and by split. This calls it with a
DIFFERENT SEED into this repository's own directory, so an adapter can be trained
on hundreds of cases while the 50 held-out and 20 delta cases stay untouched and
unseen.

WHAT THE DELTA CLINIC IS FOR, AND WHY IT IS NOT IN THE TRAINING SET. The benchmark
plants three unpublished rules, and `delta` **inverts** one of them. It appears in
no training split by design. An adapter that memorises "anticoagulant implies
medication reconciliation" scores well everywhere except delta — which is exactly
the false promotion this project has to be able to detect in an expert before
promoting it. Training on delta would destroy the only generalisation probe the
suite has.

THE LEAK CHECK IS NOT OPTIONAL. A training prompt identical to a held-out prompt
turns the evaluation into a memory test and every number after it is void. This
refuses to write if it finds one. A channel nobody watches is a channel nobody
notices.

    python3 -m training.build_dataset --n-train 600 --n-val 100
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from alpha import cases as suite

OUT = Path("training/data")
# `cases.load` expects a checkout root and appends `benchmarks/clinical_learning`,
# and the generator writes its splits into that same directory. One layout, so
# the generated corpus is read by exactly the loader the sealed one is read by.
CHECKOUT = OUT / "root"
BENCH = CHECKOUT / "benchmarks" / "clinical_learning"


def _generator(root: Path):
    import contextlib
    import os
    vr = suite.DEFAULT_ROOT
    if str(vr) not in sys.path:
        sys.path.insert(0, str(vr))

    @contextlib.contextmanager
    def _in(d):
        prev = os.getcwd()
        os.chdir(d)
        try:
            yield
        finally:
            os.chdir(prev)
    return _in, vr


def generate(n_train: int, n_val: int, seed: int) -> None:
    _in, vr = _generator(BENCH)
    target = BENCH.resolve()
    with _in(vr):
        from domains.clinical_learning.generate import generate as gen
        gen(seed=seed, root=target,
            splits={"train": (n_train, ["alpha", "beta", "gamma"], False),
                    "val": (n_val, ["alpha", "beta", "gamma"], False),
                    # The generalisation probe, kept out of training on purpose:
                    # `delta` inverts one of the unpublished rules, so an adapter
                    # that memorised the rule scores well on `val` and fails here.
                    # That gap IS the false-promotion number.
                    "val_delta": (n_val // 2, ["delta"], False)})


def to_messages(case) -> dict:
    """One training example: the canonical prompt in, the correct action out.

    The completion is the action the verifier accepts, in the compact form —
    formatting is a constant the kernel adapter owns, not something a domain
    expert should be spending capacity on.
    """
    answer = json.dumps(
        {"kind": "submit_missing_documents",
         "arguments": {"missing": sorted(case.truth)}},
        separators=(", ", ": "))
    return {
        "case_id": case.case_id, "clinic": case.region,
        "messages": [
            {"role": "system", "content": suite.SYSTEM},
            {"role": "user", "content": case.prompt},
            {"role": "assistant", "content": answer},
        ],
    }


def leak_check(rows: list[dict]) -> list[str]:
    sealed = {c.prompt for split in ("held_out", "held_out_delta")
              for c in suite.load(split)}
    return [r["case_id"] for r in rows if r["messages"][1]["content"] in sealed]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-train", type=int, default=600)
    ap.add_argument("--n-val", type=int, default=120,
                    help="val is this many; val_delta is half as many")
    ap.add_argument("--seed", type=int, default=20260907,
                    help="deliberately not the benchmark's 20260901")
    args = ap.parse_args()

    if CHECKOUT.exists():
        shutil.rmtree(CHECKOUT)
    OUT.mkdir(parents=True, exist_ok=True)
    generate(args.n_train, args.n_val, args.seed)

    written = {}
    for split in ("train", "val", "val_delta"):
        cs = suite.load(split, root=CHECKOUT, prompt="canonical")
        rows = [to_messages(c) for c in cs]
        leaks = leak_check(rows)
        if leaks:
            print(f"LEAK: {len(leaks)} training prompts are identical to sealed "
                  f"cases ({leaks[:3]}...). Nothing written.", file=sys.stderr)
            return 2
        (OUT / f"{split}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows) + "\n")
        written[split] = len(rows)
        by_clinic: dict[str, list] = {}
        for r in rows:
            by_clinic.setdefault(r["clinic"], []).append(r)
        for clinic, rs in sorted(by_clinic.items()):
            (OUT / f"{split}.{clinic}.jsonl").write_text(
                "\n".join(json.dumps(r) for r in rs) + "\n")
            written[f"{split}.{clinic}"] = len(rs)

    print(json.dumps({"seed": args.seed, "written": written,
                      "leak_check": "passed — no training prompt matches a "
                                    "sealed held-out prompt"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
