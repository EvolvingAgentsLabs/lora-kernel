"""Train a native adapter on this base, then ask the gate. One command for a chain.

`chain_serve.sh` runs one module; this is that module. It exists because the gate is
only conclusive with a native adapter — asked with one built for another base, its
`IDENTICAL TO BASE` cannot be told apart from vLLM silently ignoring a mismatch
**[ran]** 2026-09-14.
"""

from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--out", default="gate_native.json")
    ap.add_argument("--steps", type=int, default=60)
    args, _ = ap.parse_known_args()

    print(f"[native] training a tiny adapter on {args.base}", flush=True)
    r = subprocess.run([sys.executable, "-u", "-m", "training.harness.tiny_adapter",
                        "--base", args.base, "--out", "adapters/tiny",
                        "--steps", str(args.steps)])
    if r.returncode != 0:
        print("[native] the adapter did not train; the gate would measure nothing",
              flush=True)
        return 1
    print("[native] asking the gate with it", flush=True)
    return subprocess.run([sys.executable, "-u", "-m",
                           "training.harness.serve_openai", "--base", args.base,
                           "--adapter", "tiny=adapters/tiny", "--gate-only",
                           "--out", args.out]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
