"""Session 1 of 4 — let the base and the target say where the difficulty is.

WHY THIS RUNS BEFORE ANYTHING IS TRAINED. `training/suite_gates.py` has seven gates
and **four of them need a model**: a suite's ceiling is a property of the suite *and*
the model together, and no amount of reading a generator reveals it. Those four are
the ones that voided runs — P42's base already at 0.815, P45's floor of six steps,
P49's saturated `team`, P46's information ceiling.

AND IT ANSWERS THE DEEPEST FINDING IN THE REPORT, which no gate can:

> *A generated suite cannot contain a difficulty its author did not think of.*

The answer is not a check — it is to stop choosing the difficulty. The suite is
generated wide, across the **full region x depth grid**, and the band that gets kept
is the one where the **base model** is neither on the floor nor at the ceiling.

THE STOPPING RULE, WRITTEN BEFORE THE RUN AND NOT NEGOTIABLE AFTERWARDS. The band is
`0.15 <= base accuracy <= 0.70`, chosen **once**, from this run, and never revisited
whatever a later treatment scores. Choosing it twice would be the instrument looking
for a result, which this repository counts and stops at three.

TWO ARMS, SEQUENTIALLY, THE BASE FIRST. The base is what decides the band; the target
is what acceptance will later be measured against, and a cell the target also fails
is a cell where nothing can be learned about ranking.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from training.email.desk import generate
from training.harness.desk_sim import run, summarise

OUT = Path("desk_profile.json")

#: Pre-registered. Cells outside this band are guards, not evidence.
BAND_LOW, BAND_HIGH = 0.15, 0.70
#: A cell the target cannot do either is a broken cell, not a hard one.
TARGET_FLOOR = 0.40


def _wait(url: str, minutes: int, proc=None) -> bool:
    for _ in range(minutes * 12):
        if proc is not None and proc.poll() is not None:
            return False
        try:
            urllib.request.urlopen(url, timeout=5)
            return True
        except Exception:
            time.sleep(5)
    return False


def band(base: dict, target: dict) -> dict:
    """Which cells of the grid are worth measuring a treatment on, and why not."""
    cells = base.get("by_cell") or {}
    tcells = target.get("by_cell") or {}
    keep, why = [], {}
    for cell, row in sorted(cells.items()):
        b = row["rate"]
        t = (tcells.get(cell) or {}).get("rate")
        if b > BAND_HIGH:
            why[cell] = f"base at the ceiling ({b:.3f}) — no treatment can move it"
        elif b < BAND_LOW:
            why[cell] = f"base on the floor ({b:.3f}) — every arm fails and it reads "
            why[cell] += "as the approach not working"
        elif t is not None and t < TARGET_FLOOR:
            why[cell] = (f"the target fails it too ({t:.3f}) — nothing can be learned "
                         "about ranking here")
        else:
            keep.append(cell)
    return {
        "band": [BAND_LOW, BAND_HIGH], "target_floor": TARGET_FLOOR,
        "kept": keep, "dropped": why,
        "kept_regions": sorted({c.split("@")[0] for c in keep}),
        # The suite is only usable if the kept cells still span regions AND depths —
        # otherwise the grid has collapsed back into the diagonal every previous
        # suite had.
        "kept_depths": sorted({c.split("@")[1] for c in keep}),
        "usable": len({c.split("@")[0] for c in keep}) >= 2
                  and len({c.split("@")[1] for c in keep}) >= 2,
    }


#: NATIVE TOOL CALLING, NOT THE TAG SURFACE. vLLM refuses `tool_choice: auto`
#: without these two flags and returns **HTTP 400 on every request** — P51's first
#: attempt scored 240 of 240 cases as errors and printed `correct 0 calls 0 refused
#: 0`, which reads exactly like a floor result **[ran]** 2026-09-16.
#:
#: And the flags are the right fix rather than the proxy, which is the other path
#: this repository has. The proxy renders tools as **tags in the prompt**, a surface
#: our older adapters were trained on — but P51 profiles **stock** models, and making
#: them speak a protocol they never saw would measure the protocol instead of the
#: task. This whole line uses the tool API the models actually know.
TOOL_FLAGS = ["--enable-auto-tool-choice", "--tool-call-parser", "hermes"]


def serve(model: str, port: int, extra: list[str]) -> subprocess.Popen:
    cmd = ["vllm", "serve", model, "--port", str(port), *extra]
    print(f"[desk] {' '.join(cmd)}", flush=True)
    return subprocess.Popen(cmd, stdout=open(f"vllm-{port}.log", "w"),
                            stderr=subprocess.STDOUT)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="Qwen/Qwen2.5-3B-Instruct")
    ap.add_argument("--target", default="Qwen/Qwen2.5-32B-Instruct-AWQ")
    ap.add_argument("--n", type=int, default=240)
    ap.add_argument("--seed", type=int, default=424242)
    ap.add_argument("--max-turns", type=int, default=8)
    ap.add_argument("--max-tokens", type=int, default=250)
    ap.add_argument("--max-model-len", type=int, default=8192)
    ap.add_argument("--tool-parser", default="hermes",
                    help="vLLM's parser for this family's tool-call format")
    ap.add_argument("--extra", nargs="*", default=[],
                    help="further flags passed straight to `vllm serve`")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    TOOL_FLAGS[-1] = args.tool_parser
    if args.out:
        globals()["OUT"] = Path(args.out)

    cases = generate(args.n, args.seed)["cases"]
    results = {"base": args.base, "target": args.target, "n": args.n,
               "seed": args.seed, "band": [BAND_LOW, BAND_HIGH], "arms": {}}
    OUT.write_text(json.dumps(results, indent=2))

    for arm, model in (("base", args.base), ("target", args.target)):
        p = serve(model, 8000, ["--max-model-len", str(args.max_model_len),
                                "--gpu-memory-utilization", "0.90",
                                *TOOL_FLAGS, *args.extra])
        try:
            if not _wait("http://127.0.0.1:8000/health", 25, p):
                results["arms"][arm] = {"status": "never came up"}
                OUT.write_text(json.dumps(results, indent=2))
                return 1
            print(f"[desk] {arm} up", flush=True)
            recs = run("http://127.0.0.1:8000/v1", None, model, cases,
                       args.max_turns, args.max_tokens, Path(f"arm_{arm}.json"))
            results["arms"][arm] = {**summarise(recs), "records": recs}
            OUT.write_text(json.dumps(results, indent=2))
        finally:
            p.terminate()
            try:
                p.wait(timeout=60)
            except subprocess.TimeoutExpired:
                p.kill()

    results["verdict"] = band(results["arms"].get("base", {}),
                              results["arms"].get("target", {}))
    v = results["verdict"]
    print(f"\n{'cell':22}{'base':>8}{'target':>8}")
    b = results["arms"].get("base", {}).get("by_cell", {})
    t = results["arms"].get("target", {}).get("by_cell", {})
    for cell in sorted(set(b) | set(t)):
        mark = "keep" if cell in v["kept"] else "drop"
        print(f"{cell:22}{b.get(cell, {}).get('rate', float('nan')):>8.3f}"
              f"{t.get(cell, {}).get('rate', float('nan')):>8.3f}  {mark}")
    print(f"\nkept {len(v['kept'])} cells over regions {v['kept_regions']} "
          f"and depths {v['kept_depths']} — usable: {v['usable']}")
    for cell, reason in sorted(v["dropped"].items()):
        print(f"  dropped {cell:20} {reason}")
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    OUT.write_text(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
