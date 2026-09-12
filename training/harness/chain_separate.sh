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


# EVERY CALL TO THE SESSION IS BOUNDED. On 2026-09-12 a single `colab exec` peek
# hung for **75 minutes** with no timeout, and the loop could not tell: the silence
# counter only advances when a call RETURNS empty, so a call that never returns
# advances nothing. Four earlier versions of this failure were about a channel that
# answered wrongly; this one is about a channel that does not answer at all, and it
# is invisible to every guard written for the other four.
#
# macOS ships no coreutils `timeout`, so this is the portable one.
tmo () {  # tmo SECONDS cmd...
  local secs=$1; shift
  "$@" & local p=$!
  ( sleep "$secs"; kill -9 "$p" 2>/dev/null ) >/dev/null 2>&1 & local w=$!
  wait "$p" 2>/dev/null; local rc=$?
  kill -9 "$w" 2>/dev/null
  return $rc
}

for i in $(seq 1 "$SESSIONS"); do
  # A FINISHED RUN DOES NOT NEED ANOTHER SESSION. The loop used to spend its whole
  # allowance regardless, so a completed experiment provisioned a fresh L4 and
  # retrained both adapters for forty minutes before discovering there was nothing
  # to do — twice, and both times the next experiment waited behind it [ran].
  if [ -f "$LOCAL" ] && grep -q '"finished"' "$LOCAL" 2>/dev/null; then
    echo "=== $RESULTS_NAME already says finished — no further sessions"
    break
  fi
  S="sep$(date +%H%M%S)"
  echo "=== session $i of $SESSIONS · $S · $GPU · base $BASE"
  tmo 600 colab new --gpu "$GPU" -s "$S" >/dev/null
  trap 'colab stop -s "$S" >/dev/null 2>&1 || true' EXIT
  # THE PROVISIONING STEP IS NOT ALLOWED TO END THE RUN EITHER. A dropped
  # websocket during `install` raised RuntimeError("Connection was lost."),
  # `set -e` ended the chain, and the queue behind it moved on to the next
  # experiment — so the run that was meant to be first silently became last
  # [ran] 2026-09-10. Same shape as the clone: retry, then verify.
  for try in 1 2 3; do
    tmo 600 colab install -s "$S" trl bitsandbytes "torchao>=0.16.0" >/dev/null 2>&1 && break
    echo "    install attempt $try did not take"
  done

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
    tmo 180 colab exec -s "$S" -f /tmp/_sboot.py >/dev/null 2>&1 || true
    HEAD=$(tmo 180 colab exec -s "$S" -f /tmp/_scheck.py 2>/dev/null | grep -vE "^\[colab\]|^$" | head -1 || true)
    case "$HEAD" in ""|*"NO CLONE"*) echo "    clone attempt $try did not take" ;; *) break ;; esac
  done
  case "$HEAD" in ""|*"NO CLONE"*) echo "    giving up: no checkout"; colab stop -s "$S" >/dev/null 2>&1; exit 1 ;; esac
  echo "    $HEAD"

  [ -f "$LOCAL" ] && { tmo 180 colab upload -s "$S" "$LOCAL" "$REMOTE" >/dev/null && echo "    restored partial results" \
                       || echo "    WARNING: results did not upload"; }

  cat > /tmp/_srun.py <<PY
import subprocess
subprocess.Popen("cd /content/lora-kernel && nohup python -u -m $MODULE "
                 "--base $BASE $ARGS > run.log 2>&1 &", shell=True)
PY
  tmo 180 colab exec -s "$S" -f /tmp/_srun.py >/dev/null 2>&1 || true

  cat > /tmp/_speek.py <<'PY'
import subprocess
print(subprocess.run("grep -E '\\[arm\\]|\\[train\\]|\\[gate\\]|\\[corpora\\]|passed [0-9]+|"
                     "composition |Traceback|Error|OutOfMemory|Killed' "
                     "/content/lora-kernel/run.log | tail -2",
                     shell=True, capture_output=True, text=True).stdout)
PY
  # TOLERATING A FAILURE IS NOT DETECTING ONE. Three times a session became
  # unaddressable — its name pruned from the CLI's local registry while the VM
  # kept running — and because every call here is written `|| true`, the loop
  # polled a channel that no longer existed for up to 105 minutes while the log
  # repeated its last line [ran] 2026-09-10. Silence is now counted, and a session
  # that has stopped answering ends the attempt instead of consuming its window.
  printf 'print("ALIVE")\n' > /tmp/_alive.py
  QUIET=0
  for _ in $(seq 1 140); do
    out=$(tmo 180 colab exec -s "$S" -f /tmp/_speek.py 2>/dev/null | grep -vE "^\[colab\]|^$|Warning:" || true)
    if [ -n "$out" ]; then
      echo "    $out" | tail -2
      QUIET=0
    else
      QUIET=$((QUIET + 1))
      # A DEAD CHANNEL DOES NOT ALWAYS DEAD-LIST. The previous version required the
      # session to vanish from `colab sessions` before giving up, and a session that
      # is still listed but mute sailed straight past it — five hours against a
      # channel that answered nothing [ran] 2026-09-11, the fourth time this shape
      # of failure has cost a run. So the channel is probed directly, with a command
      # that cannot fail for any reason except the channel being gone.
      if [ "$QUIET" -ge 6 ]; then
        ALIVE=$(tmo 180 colab exec -s "$S" -f /tmp/_alive.py 2>/dev/null | grep -c ALIVE || true)
        if [ "$ALIVE" = "0" ]; then
          echo "    session $S is not answering a trivial command — giving up on it"
          break
        fi
        QUIET=0
      fi
    fi
    tmo 180 colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 || true
    echo "$out" | grep -qE "composition |Sequential:|The kernel adapter reproduced|STOPPED|Traceback|OutOfMemory|Killed" && break
    sleep 45
  done
  tmo 180 colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 || echo "    WARNING: nothing came back"
  colab stop -s "$S" >/dev/null 2>&1 || true; trap - EXIT

  python3 - <<PY
import json, pathlib
p = pathlib.Path("$LOCAL")
if p.exists():
    d = json.loads(p.read_text())
    for k, v in d["arms"].items():
        mark = "" if v.get("complete", True) else "  (partial)"
        extra = (f"repaired={v['repaired_passed']} calls={v['tool_calls']}"
                 if 'repaired_passed' in v else
                 f"tools={v.get('tool_values_matched')}/{v.get('tool_values_wanted')} "
                 f"queries={v.get('queries')}")
        print(f"    {k:<40}{v['passed']}/{v.get('scored', v['n'])} {extra}{mark}")
    if d.get("stopped_at_gate"): print("    STOPPED AT THE GATE")
    elif "finished" in d: print("    ALL ARMS COMPLETE")
PY
done
