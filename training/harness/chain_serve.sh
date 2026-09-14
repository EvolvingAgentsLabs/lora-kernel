#!/usr/bin/env bash
# P26 on a rented card: install vLLM, serve the pool, run the three arms.
#
#   GPU=A100 training/harness/chain_serve.sh
#
# THE ADAPTERS ARE CARRIED IN, NOT RETRAINED. This step measures a serving stack,
# not a training one, and retraining inside it would put forty minutes and a second
# source of variance into a question about HTTP.
set -euo pipefail
GPU="${GPU:-A100}"
BRANCH="${BRANCH:-handbook}"
RUN_DIR="${RUN_DIR:-results/P26-openai-server-20260913}"
MODULE="${MODULE:-training.harness.serve_openai}"
MARGS="${MARGS:---adapter kernel=adapters/kernel-mt --adapter domain=adapters/domain-mt}"
RESULTS_NAME="${RESULTS_NAME:-serve_results.json}"
BASE="${BASE:-Qwen/Qwen2.5-3B-Instruct}"
SESSIONS="${SESSIONS:-2}"
LOCAL="$RUN_DIR/$RESULTS_NAME"
ADAPTERS="$RUN_DIR/adapters.tgz"

tmo () {
  local secs=$1; shift
  "$@" & local p=$!
  { ( sleep "$secs"; kill -9 "$p" 2>/dev/null ) >/dev/null 2>&1 & } 2>/dev/null
  local w=$!
  disown "$w" 2>/dev/null || true
  wait "$p" 2>/dev/null; local rc=$?
  kill -9 "$w" 2>/dev/null
  return $rc
}

# COLAB'S UPLOAD ENDPOINT REFUSES A LARGE FILE WITH A 500, NOT A TIMEOUT. Measured
# 2026-09-13 against a live session: 4, 16, 32, 48 and 64 MB all upload; 80 MB
# fails in 1.5 seconds with `500 Internal Server Error`. The adapter tarball is
# 106 MB, so the cache added to save forty minutes of retraining never once worked
# — and raising the timeout, the obvious first guess, would never have helped.
# Chunked, reassembled on the far side.
upload_big () {  # upload_big SESSION LOCAL REMOTE
  local S="$1" src="$2" dst="$3"
  local dir; dir=$(mktemp -d)
  split -b 48m "$src" "$dir/part_"
  local n=0
  for f in "$dir"/part_*; do
    tmo 600 colab upload -s "$S" "$f" "/content/_up_$(basename "$f")" >/dev/null 2>&1 || {
      echo "    chunk $(basename "$f") did not upload"; rm -rf "$dir"; return 1; }
    n=$((n + 1))
  done
  rm -rf "$dir"
  cat > /tmp/_join.py <<PYJOIN
import glob, subprocess
parts = sorted(glob.glob("/content/_up_part_*"))
print(subprocess.run("cat " + " ".join(parts) + " > $dst && rm -f /content/_up_part_*"
                     " && ls -l $dst", shell=True, capture_output=True,
                     text=True).stdout.strip()[:120])
PYJOIN
  tmo 300 colab exec -s "$S" -f /tmp/_join.py >/dev/null 2>&1 || return 1
  echo "    carried the adapters in ($n chunks)"
}

for i in $(seq 1 "$SESSIONS"); do
  if [ -f "$LOCAL" ] && grep -q '"finished"\|stopped_at_gate\|"decision"' "$LOCAL" 2>/dev/null; then
    echo "=== already decided — no further sessions"; break
  fi
  S="srv$(date +%H%M%S)"
  echo "=== session $i of $SESSIONS · $S · $GPU"
  tmo 900 colab new --gpu "$GPU" -s "$S" >/dev/null
  trap 'colab stop -s "$S" >/dev/null 2>&1 || true' EXIT

  cat > /tmp/_vboot.py <<PY
import subprocess

def step(name, cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()
    print(f"{name}: rc={r.returncode} {tail[-1] if tail else ''}"[:170])

step("clone", "rm -rf /content/lora-kernel && cd /content && git clone -q -b $BRANCH "
              "https://github.com/EvolvingAgentsLabs/lora-kernel.git && "
              "cd lora-kernel && git log --oneline -1")
# COLAB SHIPS torchaudio AND torchvision BUILT AGAINST ITS OWN CUDA, and pip
# resolving vllm's torch leaves them behind pointing at a different one:
#   RuntimeError: PyTorch has CUDA version 13.0 whereas TorchAudio has CUDA ...
# raised on `import`, so vllm never starts [ran] 2026-09-13. Neither is needed to
# serve a text model, so they go before vllm arrives rather than being pinned
# around.
step("clear", "pip -q uninstall -y torchaudio torchvision 2>&1 | tail -1; echo cleared")
step("vllm", "pip -q install 'vllm>=0.28' 2>&1 | tail -1")
# PEFT AND DATASETS ONLY WHEN THE STEP TRAINS. native_gate trains a tiny adapter
# before serving it; every other module here only serves. P26 learned what putting
# training into a serving session costs: an import error for trl, after vLLM had
# already installed, in a session that had no reason to carry it.
# (No backticks in this heredoc — it is unquoted so BRANCH interpolates, and bash
#  runs anything in here that looks like a substitution. Third time today.)
# torchao IS PINNED HERE FOR THE SAME REASON chain_separate.sh pins it: Colab ships
# 0.10.0, transformers refuses anything under 0.16.0, and the refusal arrives as an
# ImportError in the first second of the run. That fix has been in the training chain
# for days and was not carried across when this one learned to train [ran] 2026-09-14.
step("train deps", "[ -z '$TRAINDEPS' ] || pip -q install peft datasets accelerate 'torchao>=0.16.0' 2>&1 | tail -1; echo ok")
step("check", "python -c 'import vllm; print(vllm.__version__)' 2>&1 | tail -1")
PY
  cat > /tmp/_vcheck.py <<'PY'
import subprocess
r = subprocess.run("cd /content/lora-kernel && git log --oneline -1 && "
                   "python -c 'import vllm; print(vllm.__version__)'",
                   shell=True, capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(" | ".join(lines) if len(lines) >= 2 else "NO VLLM")
PY
  HEAD=""
  for try in 1 2 3; do
    # Installing vLLM ran past 900s once and the check then found nothing, which
    # reads as `silence` rather than as a timeout [ran] 2026-09-13.
    boot=$(tmo 1800 colab exec -s "$S" -f /tmp/_vboot.py 2>/dev/null | grep -vE "^\[colab\]|^$" || true)
    [ -n "$boot" ] && echo "$boot" | sed "s/^/    boot /"
    HEAD=$(tmo 300 colab exec -s "$S" -f /tmp/_vcheck.py 2>/dev/null | grep -vE "^\[colab\]|^$" | head -1 || true)
    case "$HEAD" in ""|*"NO VLLM"*) echo "    boot attempt $try did not take: ${HEAD:-silence}" ;; *) break ;; esac
  done
  case "$HEAD" in ""|*"NO VLLM"*) echo "    GIVING UP: no vllm"; tmo 300 colab stop -s "$S" >/dev/null 2>&1; exit 1 ;; esac
  echo "    $HEAD"

  # TRAINING HAPPENS ELSEWHERE. This brief says retraining inside a serving run puts
  # forty minutes and a second source of variance into a question about HTTP, and
  # the first attempt proved the smaller version of that: the serving session has no
  # `trl`, because it has no reason to [ran] 2026-09-13. The adapters are built by
  # chain_separate.sh with MODULE=training.harness.train_pool and carried in here.
  # A RUN THAT TRAINS ITS OWN ADAPTER HAS NOTHING TO CARRY IN. native_gate and
  # lora_matrix build one on the VM, and refusing to start them for want of a
  # tarball they never read cost two launches [ran] 2026-09-14.
  if [ -n "${SKIP_ADAPTERS:-}" ]; then
    echo "    this module trains its own adapter — nothing to carry in"
  elif [ ! -f "$ADAPTERS" ]; then
    echo "    NO ADAPTERS. Build them first:"
    echo "      MODULE=training.harness.train_pool RESULTS_NAME=pool.json \\"
    echo "      RUN_DIR=$RUN_DIR ARGS= training/harness/chain_separate.sh 2"
    exit 1
  fi
  if [ -z "${SKIP_ADAPTERS:-}" ]; then
    upload_big "$S" "$ADAPTERS" /content/lora-kernel/adapters.tgz \
        || { echo "    adapters did not upload"; exit 1; }
  fi

  cat > /tmp/_vrun.py <<PY
import subprocess
subprocess.Popen(
    "cd /content/lora-kernel && ([ -f adapters.tgz ] && tar xzf adapters.tgz || true) && "
    # --out is passed so the runner writes the name the chain will ask for. Two
    # pool-cost runs came home empty because those two names disagreed.
    "nohup python -u -m $MODULE --base $BASE $MARGS --out $RESULTS_NAME "
    "> run.log 2>&1 &", shell=True)
PY
  tmo 300 colab exec -s "$S" -f /tmp/_vrun.py >/dev/null 2>&1 || true

  cat > /tmp/_vpeek.py <<'PY'
import subprocess
print(subprocess.run(
    "grep -E 'serve\\]|gate\\]|tiny\\]|native\\]|matrix\\]|passed [0-9]+|prompts/s|Traceback|[Ee]rror|OutOfMemory|Killed' "
    "/content/lora-kernel/run.log | tail -3", shell=True,
    capture_output=True, text=True).stdout)
PY
  printf 'print("ALIVE")\n' > /tmp/_valive.py
  QUIET=0
  for _ in $(seq 1 120); do
    out=$(tmo 300 colab exec -s "$S" -f /tmp/_vpeek.py 2>/dev/null | grep -vE "^\[colab\]|^$" || true)
    if [ -n "$out" ]; then echo "$out" | sed "s/^/    /" | tail -3; QUIET=0; else
      QUIET=$((QUIET + 1))
      if [ "$QUIET" -ge 6 ]; then
        A=$(tmo 300 colab exec -s "$S" -f /tmp/_valive.py 2>/dev/null | grep -c ALIVE || true)
        [ "$A" = "0" ] && { echo "    $S is not answering — giving up on it"; break; }
        QUIET=0
      fi
    fi
    tmo 300 colab download -s "$S" /content/lora-kernel/$RESULTS_NAME "$LOCAL" >/dev/null 2>&1 || true
    echo "$out" | grep -qE "prompts/s|decision:|STOPPED|Traceback|OutOfMemory|Killed|never came up" && break
    sleep 45
  done
  tmo 300 colab download -s "$S" /content/lora-kernel/$RESULTS_NAME "$LOCAL" >/dev/null 2>&1 || true
  tmo 300 colab download -s "$S" /content/lora-kernel/vllm.log "$RUN_DIR/vllm.log" >/dev/null 2>&1 || true
  tmo 300 colab stop -s "$S" >/dev/null 2>&1 || true; trap - EXIT
done
