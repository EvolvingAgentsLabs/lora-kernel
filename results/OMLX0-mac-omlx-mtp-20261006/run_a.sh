#!/bin/bash
cd /Users/agustinazwiener/evolvingagents/lora-kernel-omlx0
HF_HUB_OFFLINE=1 /private/tmp/claude-501/-Users-agustinazwiener-evolvingagents/23be4e8a-4173-40ef-9732-d2937dc03cec/scratchpad/mlx073/bin/python -u -m examples.mac.mlx_spec_lora --sets general --block-sizes 2,3,4 --out results/OMLX0-mac-omlx-mtp-20261006/a0_mlxvlm073.json
HF_HUB_OFFLINE=1 /private/tmp/claude-501/-Users-agustinazwiener-evolvingagents/23be4e8a-4173-40ef-9732-d2937dc03cec/scratchpad/mlx076/bin/python -u -m examples.mac.mlx_spec_lora --sets general --block-sizes 2,3,4 --out results/OMLX0-mac-omlx-mtp-20261006/a1_mlxvlm076.json
echo "[omlx0] A done"
