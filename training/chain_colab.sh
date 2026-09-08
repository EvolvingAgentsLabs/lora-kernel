#!/usr/bin/env bash
# One arm per Colab session, because the free tier does not keep one.
#
# Free Colab reclaimed three sessions inside roughly forty minutes of GPU work
# each [ran] 2026-09-08, and an arm that dies loses everything after the last
# save. So the run is chained: each session provisions, restores the partial
# results, completes ONE arm, hands the results back, and stops. The state of
# the experiment lives on this machine between sessions, not on the runtime.
#
#   training/chain_colab.sh                    # one arm on a free T4
#   training/chain_colab.sh 3                  # three arms, three sessions
#   GPU=L4 MAXARMS=0 training/chain_colab.sh   # every arm in one Pro session
#
# It is idempotent: an arm already in the results file is skipped, so running it
# more times than there are arms left costs one session start and nothing else.

set -euo pipefail

ARMS="${1:-1}"
GPU="${GPU:-T4}"          # T4 free; L4/A100 need Pro
MAXARMS="${MAXARMS:-1}"   # arms per session; 0 runs them all in one session
BASE="${BASE:-Qwen/Qwen3.5-2B}"
RUN_DIR="${RUN_DIR:-results/S4-qwen35-2b-20260908}"
LOCAL="$RUN_DIR/s4_results.json"
REMOTE=/content/lora-kernel/s4_results.json
BRANCH="${BRANCH:-main}"
ARGS="${ARGS:---batch 2 --accum 8 --epochs 2 --n-val 60 --n-delta 30 --n-region 25}"

for i in $(seq 1 "$ARMS"); do
  S="s4chain$(date +%H%M%S)"
  echo "=== arm $i of $ARMS · session $S · $GPU · base $BASE"
  colab new --gpu "$GPU" -s "$S" >/dev/null
  trap 'colab stop -s "$S" >/dev/null 2>&1 || true' EXIT
  colab install -s "$S" trl bitsandbytes "torchao>=0.16.0" >/dev/null

  cat > /tmp/_boot.py <<PY
import subprocess
print(subprocess.run("rm -rf /content/lora-kernel && cd /content && git clone -q -b $BRANCH "
                     "https://github.com/EvolvingAgentsLabs/lora-kernel.git && "
                     "cd lora-kernel && git log --oneline -1", shell=True,
                     capture_output=True, text=True).stdout)
PY
  colab exec -s "$S" -f /tmp/_boot.py | tail -2

  # The partial results ARE the experiment's state. Restore before running.
  if [ -f "$LOCAL" ]; then
    colab upload -s "$S" "$LOCAL" "$REMOTE" >/dev/null
    echo "    restored $(python3 -c "import json,sys;d=json.load(open('$LOCAL'));print([k for k in d if k.endswith(('_val','_delta'))] + list((d.get('regions') or {}).keys()))")"
  fi

  cat > /tmp/_run.py <<PY
import subprocess
subprocess.Popen("cd /content/lora-kernel && nohup python -u -m training.s4_train "
                 "--base $BASE --max-arms $MAXARMS $ARGS > s4.log 2>&1 &", shell=True)
PY
  colab exec -s "$S" -f /tmp/_run.py >/dev/null

  cat > /tmp/_peek.py <<'PY'
import subprocess
print(subprocess.run("grep -E '\\[arm\\]|\\[precision\\]|passed [0-9]+|trainable params|"
                     "Traceback|Error|OutOfMemory|Killed' /content/lora-kernel/s4.log | tail -2",
                     shell=True, capture_output=True, text=True).stdout)
PY
  # Pull after every poll, not only at the end: a session taken away between the
  # last save and the end of the loop used to lose everything the arm had done.
  for _ in $(seq 1 40); do
    out=$(colab exec -s "$S" -f /tmp/_peek.py 2>/dev/null | grep -vE "^\[colab\]|^$|Warning:" || true)
    [ -n "$out" ] && echo "    $out" | tail -2
    colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 || true
    echo "$out" | grep -qE "session done|Traceback|OutOfMemory|Killed" && break
    sleep 45
  done

  colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 \
    || echo "    WARNING: nothing came back from this session"
  colab exec -s "$S" -f /dev/stdin <<'PY' >/dev/null 2>&1 || true
import subprocess
subprocess.run("cd /content/lora-kernel && zip -qr adapters.zip adapters", shell=True)
PY
  colab download -s "$S" /content/lora-kernel/adapters.zip "$RUN_DIR/adapters-$(date +%H%M%S).zip" >/dev/null 2>&1 || true
  colab stop -s "$S" >/dev/null 2>&1 || true
  trap - EXIT

  python3 - <<PY
import json, pathlib
p = pathlib.Path("$LOCAL")
if p.exists():
    d = json.loads(p.read_text())
    for k, v in d.items():
        if isinstance(v, dict) and "accuracy" in v:
            print(f"    {k:<16}{v['passed']}/{v['n']} = {v['accuracy']:.3f}  unparseable={v['unparseable']}")
    for k, v in (d.get("regions") or {}).items():
        print(f"    region {k:<18}{v['passed']}/{v['n']} = {v['accuracy']:.3f}")
    if "finished" in d:
        print("    ALL ARMS COMPLETE")
PY
done
