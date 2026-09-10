#!/usr/bin/env bash
# P9 across Colab sessions. Same shape as chain_compose.sh, different runner.
set -euo pipefail
SESSIONS="${1:-1}"; GPU="${GPU:-L4}"
BASE="${BASE:-Qwen/Qwen2.5-3B-Instruct}"
RUN_DIR="${RUN_DIR:-results/P9-shared-contract-20260909}"
BRANCH="${BRANCH:-shared-contract}"
ARGS="${ARGS:---n-eval 30 --epochs 3}"
MODULE="${MODULE:-training.harness.separate}"
RESULTS_NAME="${RESULTS_NAME:-separate_results.json}"
LOCAL="$RUN_DIR/$RESULTS_NAME"
REMOTE=/content/lora-kernel/$RESULTS_NAME

for i in $(seq 1 "$SESSIONS"); do
  S="sep$(date +%H%M%S)"
  echo "=== session $i of $SESSIONS · $S · $GPU · base $BASE"
  colab new --gpu "$GPU" -s "$S" >/dev/null
  trap 'colab stop -s "$S" >/dev/null 2>&1 || true' EXIT
  colab install -s "$S" trl bitsandbytes "torchao>=0.16.0" >/dev/null

  cat > /tmp/_sboot.py <<PY
import subprocess
print(subprocess.run("rm -rf /content/lora-kernel && cd /content && git clone -q -b $BRANCH "
                     "https://github.com/EvolvingAgentsLabs/lora-kernel.git && "
                     "cd lora-kernel && git log --oneline -1", shell=True,
                     capture_output=True, text=True).stdout)
PY
  cat > /tmp/_scheck.py <<'PY'
import subprocess
print(subprocess.run("cd /content/lora-kernel && git log --oneline -1", shell=True,
                     capture_output=True, text=True).stdout.strip() or "NO CLONE")
PY
  # A timed-out `colab exec` is not a failed command: it killed a healthy L4 over
  # a clone that had already succeeded [ran] 2026-09-09. Retry, then verify.
  HEAD=""
  for try in 1 2 3; do
    colab exec -s "$S" -f /tmp/_sboot.py >/dev/null 2>&1 || true
    HEAD=$(colab exec -s "$S" -f /tmp/_scheck.py 2>/dev/null | grep -vE "^\[colab\]|^$" | head -1 || true)
    case "$HEAD" in ""|*"NO CLONE"*) echo "    clone attempt $try did not take" ;; *) break ;; esac
  done
  case "$HEAD" in ""|*"NO CLONE"*) echo "    giving up: no checkout"; colab stop -s "$S" >/dev/null 2>&1; exit 1 ;; esac
  echo "    $HEAD"

  [ -f "$LOCAL" ] && { colab upload -s "$S" "$LOCAL" "$REMOTE" >/dev/null && echo "    restored partial results" \
                       || echo "    WARNING: results did not upload"; }

  cat > /tmp/_srun.py <<PY
import subprocess
subprocess.Popen("cd /content/lora-kernel && nohup python -u -m $MODULE "
                 "--base $BASE $ARGS > run.log 2>&1 &", shell=True)
PY
  colab exec -s "$S" -f /tmp/_srun.py >/dev/null 2>&1 || true

  cat > /tmp/_speek.py <<'PY'
import subprocess
print(subprocess.run("grep -E '\\[arm\\]|\\[train\\]|\\[gate\\]|\\[corpora\\]|passed [0-9]+|"
                     "composition |Traceback|Error|OutOfMemory|Killed' "
                     "/content/lora-kernel/run.log | tail -2",
                     shell=True, capture_output=True, text=True).stdout)
PY
  for _ in $(seq 1 140); do
    out=$(colab exec -s "$S" -f /tmp/_speek.py 2>/dev/null | grep -vE "^\[colab\]|^$|Warning:" || true)
    [ -n "$out" ] && echo "    $out" | tail -2
    colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 || true
    echo "$out" | grep -qE "composition |Sequential:|STOPPED|Traceback|OutOfMemory|Killed" && break
    sleep 45
  done
  colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 || echo "    WARNING: nothing came back"
  colab stop -s "$S" >/dev/null 2>&1 || true; trap - EXIT

  python3 - <<PY
import json, pathlib
p = pathlib.Path("$LOCAL")
if p.exists():
    d = json.loads(p.read_text())
    for k, v in d["arms"].items():
        mark = "" if v.get("complete", True) else "  (partial)"
        print(f"    {k:<18}{v['passed']}/{v.get('scored', v['n'])} "
              f"repaired={v['repaired_passed']} calls={v['tool_calls']}{mark}")
    if d.get("stopped_at_gate"): print("    STOPPED AT THE GATE")
    elif "finished" in d: print("    ALL ARMS COMPLETE")
PY
done
