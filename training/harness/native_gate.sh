#!/usr/bin/env bash
# Train a native adapter on a base, then ask whether vLLM applies it.
#
#   RUN INSIDE A COLAB SESSION.
#
# THE GATE NEEDS A NATIVE ADAPTER TO BE CONCLUSIVE. Asked with an adapter built for
# another base, `IDENTICAL TO BASE` is ambiguous between "this class does not apply
# LoRA" and "vLLM silently ignores a mismatched adapter" [ran] 2026-09-14. The second
# would be the worse finding, so it is separated rather than assumed away.
set -euo pipefail
BASE="${BASE:?set BASE}"
OUT="${OUT:-gate_native.json}"

cd /content/lora-kernel
pip -q install trl peft bitsandbytes datasets 2>&1 | tail -1 || true

python -u -m training.harness.tiny_adapter --base "$BASE" --out adapters/tiny
python -u -m training.harness.serve_openai --base "$BASE" \
    --adapter tiny=adapters/tiny --gate-only --out "$OUT"
