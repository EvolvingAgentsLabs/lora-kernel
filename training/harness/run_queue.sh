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
for attempt in 1 2 3 4 5 6; do
  case $attempt in
    1|4) CARD=L4 ;;
    2|5) CARD=A100 ;;
    *)   CARD=T4 ;;
  esac
  echo "=== P13 attempt $attempt on $CARD" >> "$SP/p13.log"
  GPU=$CARD BRANCH=delegation-variants MODULE=training.harness.sequential \
  RUN_DIR=results/P13-sequential-20260910 RESULTS_NAME=sequential_results.json \
  ARGS="--n-eval 30" \
  training/harness/chain_separate.sh 2 >> "$SP/p13.log" 2>&1
  python3 -c "
import json,sys,pathlib
p=pathlib.Path('results/P13-sequential-20260910/sequential_results.json')
sys.exit(0 if p.exists() and 'finished' in json.loads(p.read_text()) else 1)" && break
  echo "    attempt $attempt did not finish; waiting before the next card" >> "$SP/p13.log"
  sleep 300
done

GPU=L4 BRANCH=delegation-variants RUN_DIR=results/P12-formula-corpus-20260909 \
RESULTS_NAME=separate_results-formula.json \
ARGS="--n-eval 30 --epochs 3 --tag formula --domain-corpus training/physics/data_formula/train.jsonl" \
training/harness/chain_separate.sh 2 >> "$SP/p12.log" 2>&1
