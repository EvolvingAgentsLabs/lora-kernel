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
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()


def run(mod: str, *argv: str, env: dict | None = None) -> int:
    """A module, streamed. Nothing this run does may hide its position."""
    return subprocess.run([sys.executable, "-u", "-m", mod, *argv],
                          env={**os.environ, **(env or {})}).returncode


FOUND = "Successfully loaded LoRA weights for module"
MISSING = "No LoRA weights found for module"


def activation(tag: str) -> dict:
    """THE FAILURE, COUNTED WHERE IT HAPPENS. The served text is where C18 surfaces;
    where it happens is vLLM's activation loop, which says per module whether the
    adapter had weights for it — at DEBUG, which is why four runs never saw it
    (`lora/model_manager.py` v0.29.0 **[read]**). `serve_openai` truncates `vllm.log`
    on every serve, so it is kept under the arm's name before the next one starts."""
    src = Path("vllm.log")
    if not src.exists():
        return {"log": None}
    text = src.read_text(errors="replace")
    kept = Path(f"vllm-{tag}.log")
    kept.write_text(text)
    return {"log": kept.name, "modules_with_weights": text.count(FOUND),
            "modules_without": text.count(MISSING)}


def g1(base: str, tag: str, steps: int) -> dict:
    """Train a native adapter and make it prove, in process, that it is not a no-op."""
    out = f"adapters/tiny-{tag}"
    code = run("training.harness.tiny_adapter", "--base", base, "--out", out,
               "--steps", str(steps))
    return {"passed": code == 0, "adapter": out}


def g2(base: str, adapter: str, tag: str, debug: bool = False) -> dict:
    """Ask vLLM. `--gate-only` brings the server up, compares, and comes down."""
    dest = f"gate_{tag}.json"
    argv = ("training.harness.serve_openai", "--base", base,
            "--adapter", f"tiny={adapter}", "--gate-only", "--out", dest)
    code = run(*argv, env={"VLLM_LOGGING_LEVEL": "DEBUG"}) if debug else run(*argv)
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
    out = {"passed": verdict == "applied", "verdict": verdict, "exit": code}
    if debug:
        out["activation"] = activation(tag)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--control", default="Qwen/Qwen2.5-3B-Instruct",
                    help="the base whose answer is already known")
    # `--base` IS THE SUBJECT UNDER ANOTHER NAME. `chain_serve.sh` passes `--base`
    # to every module it runs, and a runner that rejected it would not start at all
    # — argparse would exit 2 into a log whose filter used to drop the word `error`.
    ap.add_argument("--subject", "--base", dest="subject", default="Qwen/Qwen3.5-4B")
    ap.add_argument("--steps", type=int, default=60)
    ap.add_argument("--rekey", action="store_true",
                    help="D2: if the subject's G2 fails, rename the adapter's tensors "
                         "to where vLLM looks (training/harness/rekey.py) and ask again")
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
            debug = args.rekey and role == "subject"
            arm["G2"] = (g2(base, arm["G1"]["adapter"], role, debug=True) if debug
                         else g2(base, arm["G1"]["adapter"], role))
            print(f"[matrix] {role} G2 served: {arm['G2']['verdict']} "
                  f"{arm['G2'].get('activation', '')}", flush=True)
            # THE ARM IS BOUGHT ONLY IF THERE IS A FAILURE TO EXPLAIN. If the subject
            # already serves its adapter, C18 is gone and a renaming proves nothing.
            if debug and not arm["G2"]["passed"]:
                results["arms"][role] = arm      # the failed G2 is on disk before
                persist()                        # the arm that explains it is bought
                from training.harness.rekey import rekey_adapter
                arm["rekey"] = rekey_adapter(arm["G1"]["adapter"], "adapters/tiny-rekeyed")
                print(f"[matrix] {role} rekey: {arm['rekey']}", flush=True)
                if not arm["rekey"].get("moved"):
                    # NOTHING WAS RENAMED, SO G2r WOULD ASK G2'S QUESTION AGAIN and its
                    # `not applied` would read as the falsification. The premise — PEFT
                    # wrote `model.layers.` — is what failed, not the hypothesis.
                    arm["G2r"] = {"passed": False, "verdict": "not asked: nothing to rename"}
                else:
                    arm["G2r"] = g2(base, "adapters/tiny-rekeyed", "rekeyed", debug=True)
                print(f"[matrix] {role} G2r served, renamed: {arm['G2r']['verdict']} "
                      f"{arm['G2r'].get('activation', '')}", flush=True)
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
    elif s["G1"]["passed"] and s.get("G2r", {}).get("passed"):
        # D2's row, written before the run — results/D2-rekey-20260918/BRIEF.md
        reading = ("C18 is a naming mismatch: the same weights, renamed to where vLLM "
                   "looks, are applied. Not a serving-stack limit and not a model one")
        decision = ("a Qwen3.5 adapter is servable as a pool member once its tensors "
                    "carry `language_model.`; train through the class vLLM serves, or "
                    "rekey at release")
    elif s["G1"]["passed"] and s.get("G2r", {}).get("verdict", "").startswith("not asked"):
        reading = ("VOID for D2: the adapter's names were not the ones the brief assumed, "
                   "so nothing was renamed and the hypothesis was not tested")
        decision = "read the adapter's tensor names (`rekey.before`); Qwen2.5 stays"
    elif s["G1"]["passed"] and "G2r" in s:
        reading = ("renaming was not enough: the adapter is still served as the base. "
                   "Read `activation` — if modules_with_weights > 0 the weights land "
                   "and something downstream drops them")
        decision = "Qwen2.5 stays; D2 is not closed by the name alone"
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
