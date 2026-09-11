#!/usr/bin/env bash
# The experiment queue, in the order the work is meant to happen.
#
#   training/harness/run_queue.sh
#
# P13 (sequential activation) runs first and STAYS first: it is retried up to
# three times and the queue only moves on once its results file says `finished`.
# Without that check a dropped websocket during provisioning ended the chain,
# `set -e` propagated, and the experiment meant to be first silently became last
# [ran] 2026-09-10.
#
# Everything resumes at case granularity, so a reclaimed session costs the cases
# in flight and never an arm. Safe to stop and re-run at any time.
# P13 first and it stays first: each experiment gets its own retries, and a
# failure in one does not silently promote the next.
cd /Users/agustinazwiener/evolvingagents/lora-kernel
SP="${SP:-/tmp/lora-kernel-logs}"; mkdir -p "$SP"

# CAPACITY IS NOT AN ERROR TO RETRY IMMEDIATELY. Colab answered `Service
# Unavailable` on the L4 assignment, and a loop with no backoff burns every
# attempt against a capacity outage in two minutes [ran] 2026-09-10. So the
# attempts are spaced, and they walk down a list of cards.
#
# T4 IS LAST AND ON PURPOSE. It has no bf16, and `is_bf16_supported()` returns
# True on it anyway because it counts emulation — that pairing produced a 0/60
# that read exactly like the step's own falsification condition. The precision
# check keys on compute capability now, so a T4 run is correct but slower, and
# it is a fallback rather than a choice.
# THE QUEUE AS IT STANDS: C then A, in the order the work was prioritised.
#
#   P14 (C)  where does the expert's region actually end
#   P15 (A)  is a learned protocol worth its weights when the call is not a copy
#   P18      the tripwire, with P16's cut fixed and two unseen families
#
# Each waits for the previous to finish rather than for its process to exit, so a
# failure does not silently promote the next experiment — that already happened
# once and turned the run meant to be first into the last [ran] 2026-09-10.

finished () {  # $1 = results file
  python3 -c "
import json,sys,pathlib
p=pathlib.Path('$1')
sys.exit(0 if p.exists() and 'finished' in json.loads(p.read_text()) else 1)" 2>/dev/null
}

for attempt in 1 2 3; do
  finished results/P14-held-out-20260910/sequential_results_heldout.json && break
  echo "=== P14 attempt $attempt" >> "$SP/p14.log"
  GPU=L4 BRANCH=tournament MODULE=training.harness.sequential \
  RUN_DIR=results/P14-held-out-20260910 RESULTS_NAME=sequential_results_heldout.json \
  ARGS="--n-eval 20 --held-out" \
  training/harness/chain_separate.sh 2 >> "$SP/p14.log" 2>&1
  sleep 60
done

for attempt in 1 2 3; do
  finished results/P15-multitool-20260910/multitool_results.json && break
  echo "=== P15 attempt $attempt" >> "$SP/p15.log"
  GPU=L4 BRANCH=tournament MODULE=training.harness.multitool_run \
  RUN_DIR=results/P15-multitool-20260910 RESULTS_NAME=multitool_results.json \
  ARGS="--n-eval 30" \
  training/harness/chain_separate.sh 3 >> "$SP/p15.log" 2>&1
  sleep 60
done
for attempt in 1 2 3; do
  finished results/P18-confirm-20260910/sequential_results_confirm.json && break
  echo "=== P18 attempt $attempt" >> "$SP/p18.log"
  GPU=L4 BRANCH=tournament MODULE=training.harness.sequential \
  RUN_DIR=results/P18-confirm-20260910 RESULTS_NAME=sequential_results_confirm.json \
  ARGS="--n-eval 20 --confirm" \
  training/harness/chain_separate.sh 2 >> "$SP/p18.log" 2>&1
  sleep 60
done
exit 0
