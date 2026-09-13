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
BASE="${BASE:-Qwen/Qwen2.5-3B-Instruct}"
SESSIONS="${SESSIONS:-2}"
LOCAL="$RUN_DIR/serve_results.json"
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

for i in $(seq 1 "$SESSIONS"); do
  if [ -f "$LOCAL" ] && grep -q '"finished"\|stopped_at_gate' "$LOCAL" 2>/dev/null; then
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
step("vllm", "pip -q install 'vllm>=0.28' 2>&1 | tail -1; vllm --version")
PY
  cat > /tmp/_vcheck.py <<'PY'
import subprocess
r = subprocess.run("cd /content/lora-kernel && git log --oneline -1 && vllm --version",
                   shell=True, capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(" | ".join(lines) if len(lines) >= 2 else "NO VLLM")
PY
  HEAD=""
  for try in 1 2 3; do
    boot=$(tmo 900 colab exec -s "$S" -f /tmp/_vboot.py 2>/dev/null | grep -vE "^\[colab\]|^$" || true)
    [ -n "$boot" ] && echo "$boot" | sed "s/^/    boot /"
    HEAD=$(tmo 300 colab exec -s "$S" -f /tmp/_vcheck.py 2>/dev/null | grep -vE "^\[colab\]|^$" | head -1 || true)
    case "$HEAD" in ""|*"NO VLLM"*) echo "    boot attempt $try did not take: ${HEAD:-silence}" ;; *) break ;; esac
  done
  case "$HEAD" in ""|*"NO VLLM"*) echo "    GIVING UP: no vllm"; tmo 300 colab stop -s "$S" >/dev/null 2>&1; exit 1 ;; esac
  echo "    $HEAD"

  [ -f "$ADAPTERS" ] && { tmo 600 colab upload -s "$S" "$ADAPTERS" /content/lora-kernel/adapters.tgz >/dev/null \
      && echo "    carried the adapters in" || echo "    WARNING: adapters did not upload"; }

  cat > /tmp/_vrun.py <<PY
import subprocess
subprocess.Popen(
    "cd /content/lora-kernel && ([ -f adapters.tgz ] && tar xzf adapters.tgz || true) && "
    # WHATEVER THE CARRIED TARBALL IS SHORT OF, gets trained here rather than inside
    # the serving run. P25's tarball came back with only kernel-mt in it.
    "python -u -m training.harness.train_pool --base $BASE >> run.log 2>&1 && "
    "(tar czf adapters.tgz adapters) && "
    "nohup python -u -m training.harness.serve_openai --base $BASE "
    "--adapter kernel=adapters/kernel-mt --adapter domain=adapters/domain-mt "
    "> run.log 2>&1 &", shell=True)
PY
  tmo 300 colab exec -s "$S" -f /tmp/_vrun.py >/dev/null 2>&1 || true

  cat > /tmp/_vpeek.py <<'PY'
import subprocess
print(subprocess.run(
    "grep -E 'serve\\]|gate\\]|passed [0-9]+|prompts/s|Traceback|Error|OutOfMemory|Killed' "
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
    tmo 300 colab download -s "$S" /content/lora-kernel/serve_results.json "$LOCAL" >/dev/null 2>&1 || true
    echo "$out" | grep -qE "prompts/s|STOPPED|Traceback|OutOfMemory|Killed|never came up" && break
    sleep 45
  done
  tmo 300 colab download -s "$S" /content/lora-kernel/serve_results.json "$LOCAL" >/dev/null 2>&1 || true
  tmo 300 colab download -s "$S" /content/lora-kernel/vllm.log "$RUN_DIR/vllm.log" >/dev/null 2>&1 || true
  tmo 300 colab stop -s "$S" >/dev/null 2>&1 || true; trap - EXIT
done
