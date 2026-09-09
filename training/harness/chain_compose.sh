#!/usr/bin/env bash
# The composition experiment, chained across Colab sessions.
#
# `training/chain_colab.sh` does this for S4; this does it for P8, and it carries
# one extra piece of state. The compose run trains two adapters before it can
# measure anything, so a session that dies after the training has thrown away the
# expensive half. The adapters travel with the results file: zipped and pulled at
# the end of every session, pushed back and unzipped at the start of the next.
#
#   training/harness/chain_compose.sh          # one session on a free T4
#   GPU=L4 training/harness/chain_compose.sh 2 # two Pro sessions
#
# Idempotent at case granularity: compose.py banks every scored case, so a
# reclaimed session costs the cases in flight, not the arm.

set -euo pipefail

SESSIONS="${1:-1}"
GPU="${GPU:-T4}"
BASE="${BASE:-Qwen/Qwen2.5-3B-Instruct}"
RUN_DIR="${RUN_DIR:-results/P8-harness-lora-20260909}"
BRANCH="${BRANCH:-harness-lora}"
ARGS="${ARGS:---n-eval 30 --epochs 3}"

LOCAL="$RUN_DIR/compose_results.json"
LOCAL_AD="$RUN_DIR/adapters.zip"
REMOTE=/content/lora-kernel/compose_results.json
REMOTE_AD=/content/lora-kernel/adapters.zip

for i in $(seq 1 "$SESSIONS"); do
  S="compose$(date +%H%M%S)"
  echo "=== session $i of $SESSIONS · $S · $GPU · base $BASE"
  colab new --gpu "$GPU" -s "$S" >/dev/null
  trap 'colab stop -s "$S" >/dev/null 2>&1 || true' EXIT
  colab install -s "$S" trl bitsandbytes "torchao>=0.16.0" >/dev/null

  cat > /tmp/_cboot.py <<PY
import subprocess
print(subprocess.run("rm -rf /content/lora-kernel && cd /content && git clone -q -b $BRANCH "
                     "https://github.com/EvolvingAgentsLabs/lora-kernel.git && "
                     "cd lora-kernel && git log --oneline -1", shell=True,
                     capture_output=True, text=True).stdout)
PY
  colab exec -s "$S" -f /tmp/_cboot.py | tail -2

  [ -f "$LOCAL" ] && colab upload -s "$S" "$LOCAL" "$REMOTE" >/dev/null && \
    echo "    restored $(python3 -c "import json;d=json.load(open('$LOCAL'));print([(k, v.get('scored', v['n'])) for k,v in d['arms'].items()])")"
  if [ -f "$LOCAL_AD" ]; then
    colab upload -s "$S" "$LOCAL_AD" "$REMOTE_AD" >/dev/null
    colab exec -s "$S" -f /dev/stdin <<'PY' >/dev/null
import subprocess
subprocess.run("cd /content/lora-kernel && unzip -qo adapters.zip", shell=True)
PY
    echo "    restored adapters — no retrain this session"
  fi

  cat > /tmp/_crun.py <<PY
import subprocess
subprocess.Popen("cd /content/lora-kernel && nohup python -u -m training.harness.compose "
                 "--base $BASE $ARGS > compose.log 2>&1 &", shell=True)
PY
  colab exec -s "$S" -f /tmp/_crun.py >/dev/null

  cat > /tmp/_cpeek.py <<'PY'
import subprocess
print(subprocess.run("grep -E '\\[arm\\]|\\[train\\]|\\[resume\\]|\\[corpora\\]|passed [0-9]+|"
                     "composition|Traceback|Error|OutOfMemory|Killed' "
                     "/content/lora-kernel/compose.log | tail -2",
                     shell=True, capture_output=True, text=True).stdout)
PY
  for _ in $(seq 1 120); do
    out=$(colab exec -s "$S" -f /tmp/_cpeek.py 2>/dev/null | grep -vE "^\[colab\]|^$|Warning:" || true)
    [ -n "$out" ] && echo "    $out" | tail -2
    colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 || true
    echo "$out" | grep -qE "composition |Traceback|OutOfMemory|Killed" && break
    sleep 45
  done

  # The adapters cost more than the measurement; take them home either way.
  colab exec -s "$S" -f /dev/stdin <<'PY' >/dev/null 2>&1 || true
import subprocess
subprocess.run("cd /content/lora-kernel && zip -qr adapters.zip adapters", shell=True)
PY
  colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 \
    || echo "    WARNING: nothing came back from this session"
  colab download -s "$S" "$REMOTE_AD" "$LOCAL_AD" >/dev/null 2>&1 || true
  colab stop -s "$S" >/dev/null 2>&1 || true
  trap - EXIT

  python3 - <<PY
import json, pathlib
p = pathlib.Path("$LOCAL")
if p.exists():
    d = json.loads(p.read_text())
    for k, v in d["arms"].items():
        mark = "" if v.get("complete", True) else "  (partial)"
        print(f"    {k:<26}{v['passed']}/{v.get('scored', v['n'])} "
              f"calls={v['tool_calls']}{mark}")
    if "finished" in d:
        print("    ALL ARMS COMPLETE")
PY
done
