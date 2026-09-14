"""P33 — the same three gates on two bases, one of which we already know the answer for.

WHY A CONTROL ARM EXISTS AT ALL. Four runs asked "does vLLM apply a LoRA to
Qwen3.5?" and four came back `IDENTICAL TO BASE`. None of them could separate

    the model class does not apply LoRA
    the adapter was never really trained
    my own check was wrong                <- it was, twice [ran] 2026-09-14

A negative result is only readable next to a positive one taken the same way. So
this runs the identical procedure on `Qwen2.5-3B-Instruct`, where P26 already
measured an applied adapter (base 0/60, adapter 20/60 **[ran]**), and on the
subject. If the control fails, **the run is void and says so** rather than
reporting a number about the subject.

Three gates, each conclusive on its own, cheapest first:

    G1  in-process   lora_B moved AND the output changed  (training/harness/tiny_adapter)
    G2  served       vLLM's text differs from the base    (training/harness/serve_openai)
    G3  merged       only if G2 fails — and it is NOT a pool

G3 answers a different question from G2 on purpose. Merging writes the delta into
the weights and serves an ordinary model — unsloth's own Qwen3.5 guide routes
through `save_pretrained_merged` for exactly this reason **[read]**. It works, and
it costs one full copy of the weights per expert with no swapping: the thing this
architecture exists to avoid. It is bought only to know whether a fallback exists.

    python3 -m training.harness.lora_matrix \
        --control Qwen/Qwen2.5-3B-Instruct --subject Qwen/Qwen3.5-4B \
        --out results.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()


def run(mod: str, *argv: str) -> int:
    """A module, streamed. Nothing this run does may hide its position."""
    return subprocess.run([sys.executable, "-u", "-m", mod, *argv]).returncode


def g1(base: str, tag: str, steps: int) -> dict:
    """Train a native adapter and make it prove, in process, that it is not a no-op."""
    out = f"adapters/tiny-{tag}"
    code = run("training.harness.tiny_adapter", "--base", base, "--out", out,
               "--steps", str(steps))
    return {"passed": code == 0, "adapter": out}


def g2(base: str, adapter: str, tag: str) -> dict:
    """Ask vLLM. `--gate-only` brings the server up, compares, and comes down."""
    dest = f"gate_{tag}.json"
    code = run("training.harness.serve_openai", "--base", base,
               "--adapter", f"tiny={adapter}", "--gate-only", "--out", dest)
    verdict = None
    p = Path(dest)
    if p.exists():
        try:
            verdict = json.loads(p.read_text()).get("gate_verdict")
        except json.JSONDecodeError:
            verdict = None
    # THE EXIT CODE IS NOT THE VERDICT. `serve_openai` exits 0 on a clean run whose
    # gate said "not applied" — reading the code alone would report every subject as
    # a pass. The file is the answer; the code only says whether it was produced.
    return {"passed": verdict == "applied", "verdict": verdict, "exit": code}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--control", default="Qwen/Qwen2.5-3B-Instruct",
                    help="the base whose answer is already known")
    # `--base` IS THE SUBJECT UNDER ANOTHER NAME. `chain_serve.sh` passes `--base`
    # to every module it runs, and a runner that rejected it would not start at all
    # — argparse would exit 2 into a log whose filter used to drop the word `error`.
    ap.add_argument("--subject", "--base", dest="subject", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--out", default="lora_matrix.json")
    args = ap.parse_args()

    results = {"control_base": args.control, "subject_base": args.subject, "arms": {}}
    dest = Path(args.out)

    def persist():
        # EVERY RESULT AS IT LANDS. A report written only at the end makes an abort
        # cost the whole run, and this run holds a GPU while it thinks.
        dest.write_text(json.dumps(results, indent=2) + "\n")

    for role, base in (("control", args.control), ("subject", args.subject)):
        t0 = time.time()
        print(f"\n[matrix] ===== {role}: {base} =====", flush=True)
        arm = {"base": base}
        arm["G1"] = g1(base, role, args.steps)
        print(f"[matrix] {role} G1 in-process: "
              + ("passed" if arm["G1"]["passed"] else "FAILED"), flush=True)
        if arm["G1"]["passed"]:
            arm["G2"] = g2(base, arm["G1"]["adapter"], role)
            print(f"[matrix] {role} G2 served: {arm['G2']['verdict']}", flush=True)
        else:
            # ASKING G2 AFTER G1 FAILED IS THE MISTAKE THIS FILE EXISTS TO STOP. A
            # gate fed a no-op adapter answers about the adapter and reads as an
            # answer about the server.
            arm["G2"] = {"passed": False, "verdict": "not asked: G1 failed"}
            print(f"[matrix] {role} G2 skipped — a no-op adapter cannot ask a "
                  "serving gate anything", flush=True)
        arm["seconds"] = round(time.time() - t0)
        results["arms"][role] = arm
        persist()

    c, s = results["arms"]["control"], results["arms"]["subject"]
    control_ok = c["G1"]["passed"] and c["G2"]["passed"]

    # THE VERDICT TABLE WAS WRITTEN BEFORE THE RUN — results/P33-lora-matrix-20260914/BRIEF.md
    if not control_ok:
        reading = ("VOID: the procedure failed on a base where it is known to work. "
                   "Nothing here is a fact about " + args.subject)
        decision = "fix the harness; no model was measured"
    elif s["G1"]["passed"] and s["G2"]["passed"]:
        reading = "the subject serves LoRA through vLLM"
        decision = "Qwen3.5 is usable; whether to pay for retraining is a separate call"
    elif s["G1"]["passed"]:
        reading = ("the adapter trains and changes the output in process, and vLLM "
                   "serves the base anyway — a serving-stack limit, not a model one")
        decision = "Qwen2.5 for the end-to-end; G3 says whether merging is a fallback"
    else:
        reading = "the adapter cannot be trained this way on this architecture"
        decision = "Qwen2.5 for the end-to-end"

    results["control_valid"] = control_ok
    results["reading"] = reading
    results["decision"] = decision
    persist()
    print(f"\n[matrix] control valid: {control_ok}")
    print(f"[matrix] reading: {reading}")
    print(f"[matrix] decision: {decision}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
