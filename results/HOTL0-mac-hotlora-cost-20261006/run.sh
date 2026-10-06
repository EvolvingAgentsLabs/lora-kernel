#!/bin/bash
cd /Users/agustinazwiener/evolvingagents/lora-kernel-hotl0
mem() { echo "[hotl0] $1 · $(memory_pressure | tail -1) · $(sysctl -n vm.swapusage)"; }
export HF_HUB_OFFLINE=1
mem "H0 start"; /private/tmp/claude-501/-Users-agustinazwiener-evolvingagents/23be4e8a-4173-40ef-9732-d2937dc03cec/scratchpad/mlx073/bin/python -u -m examples.mac.mlx_spec_lora --sets general --block-sizes 2,3 --out results/HOTL0-mac-hotlora-cost-20261006/h0_bare.json
mem "H1 start"; /private/tmp/claude-501/-Users-agustinazwiener-evolvingagents/23be4e8a-4173-40ef-9732-d2937dc03cec/scratchpad/mlx073/bin/python -u -m examples.mac.mlx_spec_lora --adapter wiki12b=$HOME/lora-kernel-adapters/B3-gemma4-12b-wiki-s0/x/adapters/wiki12b-walks-s0 --sets general --block-sizes 2,3 --out results/HOTL0-mac-hotlora-cost-20261006/h1_wrapped.json
mem "end"; echo "[hotl0] done"
