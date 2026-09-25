"""B2 — the large half of a pair on Gemma 4: one id space with the small, and a LoRA it serves applied.

Milestone 3's two preconditions, cheapest first, in one session (results/B2-gemma4-large-gate-20260926/BRIEF.md):

    ids    `tokenizer_compat.from_files` on the small's and the large's `tokenizer.json` — a speculative pair
           verifies the drafter's ids against the target's distribution, so an id has to mean the same string to
           both (P48 [ran] found Qwen3-32B id-compatible with four extra ids a drafter can never emit)
    LoRA   `lora_matrix` with the instrument's own control (Qwen2.5-3B, applied without rekey) and the large as
           the subject: a tiny adapter trained in process (G1), then served by vLLM (G2)

If the ids do not agree the pair cannot exist on this family and the LoRA gate is not run.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from training.harness import family


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=family.LARGE, help="the large half (the chain passes --base)")
    ap.add_argument("--small", default=family.SMALL)
    ap.add_argument("--adapter", action="append", default=[], help="pool adapters (ignored)")
    ap.add_argument("--out", default="large_gate.json")
    a = ap.parse_args()
    out = Path(a.out)
    rec = {"small": a.small, "large": a.base, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    from huggingface_hub import hf_hub_download
    from training.harness.tokenizer_compat import from_files
    ids = from_files(hf_hub_download(a.small, "tokenizer.json"), hf_hub_download(a.base, "tokenizer.json"))
    rec["ids"] = ids
    out.write_text(json.dumps(rec, indent=1))
    print(f"[gate] ids {a.small} vs {a.base}: {rec['ids']['reading']}", flush=True)
    if not ids.get("usable_for_speculation"):
        rec["verdict"] = "NO PAIR: the two tokenizers do not share an id space"
    else:
        rc = subprocess.call([sys.executable, "-m", "training.harness.lora_matrix", "--control", "Qwen/Qwen2.5-3B-Instruct",
                              "--subject", a.base, "--out", "lora_matrix.json"])
        m = json.loads(Path("lora_matrix.json").read_text()) if Path("lora_matrix.json").exists() else {}
        rec["lora_matrix"] = {"exit": rc, "control_valid": m.get("control_valid"), "reading": m.get("reading"),
                              "subject": m.get("arms", {}).get("subject")}
        served = (m.get("arms", {}).get("subject", {}).get("G2") or {}).get("passed")
        rec["verdict"] = ("VOID: the control failed" if not m.get("control_valid") else
                          "PAIR POSSIBLE: one id space, and the large serves a LoRA applied" if served else
                          "NO LORA ON THE LARGE: the ids agree, the adapter is not applied when served")
    rec["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out.write_text(json.dumps(rec, indent=1))
    print(f"[gate] {rec['verdict']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
