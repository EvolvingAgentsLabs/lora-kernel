#!/usr/bin/env bash
# P9 across Colab sessions. Same shape as chain_compose.sh, different runner.
set -euo pipefail

# BASH READS A SCRIPT INCREMENTALLY, BY BYTE OFFSET. Editing this file while it is
# running moves the ground under the running instance: on 2026-09-14 a patch landed
# mid-loop and the live chain died with `line 184: syntax error near unexpected
# token 'done'`, after its run had finished but before its trap could stop the
# session — which is where that afternoon's orphaned Colab sessions came from [ran].
#
# Telling the next person not to edit a running script is a rule they have to
# remember. Running from a copy makes it impossible instead.
if [ -z "${CHAIN_REEXEC:-}" ]; then
  _self="$(mktemp -t chain)" || exit 1
  cat "$0" > "$_self" && chmod +x "$_self" || exit 1
  CHAIN_REEXEC="$_self" exec "$_self" "$@"
fi
# THE COPY IS DELIBERATELY NOT TRAPPED FOR CLEANUP. Bash keeps one handler per
# signal, and these scripts already spend their EXIT trap on `colab stop` — which
# is worth more than a few kilobytes in /tmp. Leaving the copy behind is the
# cheaper of the two failures.
SESSIONS="${1:-1}"; GPU="${GPU:-L4}"
BASE="${BASE:-Qwen/Qwen2.5-3B-Instruct}"
RUN_DIR="${RUN_DIR:-results/P9-shared-contract-20260909}"
BRANCH="${BRANCH:-shared-contract}"
# `:-` SUBSTITUTES ON AN EMPTY STRING, NOT ONLY ON AN UNSET ONE. Passing ARGS=""
# to run a module that takes no arguments handed it `--n-eval 30 --epochs 3`
# instead, and train_pool died on argparse in the first second of two sessions
# that then looked busy for seventy-seven minutes each [ran] 2026-09-13.
ARGS="${ARGS---n-eval 30 --epochs 3}"
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
  # The watchdog is disowned so that killing it does not print `Killed: 9` into
  # the run log on every single bounded call — a log nobody reads is a log that
  # hides the line that mattered.
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
# HOW MANY TRAINED ADAPTERS A TARBALL ACTUALLY CARRIES.
#
# `grep -c` PRINTS ITS ZERO **AND** EXITS 1, so the obvious
#     $(tar tzf f | grep -c safetensors || echo 0)
# yields "0\n0" on an empty archive — which is not equal to "0", so the guard that
# asked `= "0"` read false and skipped the rescue it exists for. That is exactly
# how a 45-byte tarball reached disk and nine minutes of L4 training went with the
# session [ran] 2026-09-15. One helper, one `|| true`, one place to get it wrong.
weights_in () { tar tzf "$1" 2>/dev/null | grep -c safetensors 2>/dev/null || true; }

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

  # THE ADAPTERS ARE TRAINED ONCE, NOT ONCE PER SESSION. A reclaimed card used to
  # cost forty minutes of retraining before it could score a single case, and this
  # experiment paid that twice [ran] 2026-09-12. The weights are a few tens of
  # megabytes; carrying them is strictly cheaper than rebuilding them.
  ADAPTERS="$RUN_DIR/adapters.tgz"
  [ -f "$ADAPTERS" ] && { upload_big "$S" "$ADAPTERS" /content/lora-kernel/adapters.tgz \
                          || echo "    WARNING: adapters did not upload"; }

  cat > /tmp/_srun.py <<PY
import subprocess
# Unpack whatever was carried in, then start a watcher that packs the adapters up
# the moment they exist — so the next session inherits them even if this one is
# reclaimed mid-scoring, which is exactly how the last two were lost.
subprocess.Popen(
    "cd /content/lora-kernel && "
    "([ -f adapters.tgz ] && tar xzf adapters.tgz || true) && "
    # A DIRECTORY IS NOT A TRAINED ADAPTER. The first version of this watcher
    # waited for 'adapters/domain-mt' to EXIST and fired the moment trl created
    # it, shipping back a 106 MB tarball whose domain adapter was an empty
    # directory [ran] 2026-09-12. The runner skips training when the directory is
    # present, so that tarball would have scored an untrained adapter in silence.
    # The trigger is the weights file, and only the weights files are packed.
    "(nohup bash -c 'while [ ! -f adapters/domain-mt/adapter_model.safetensors ] "
    "|| [ ! -f adapters/kernel-mt/adapter_model.safetensors ]; do sleep 20; done; "
    "sleep 10; tar czf adapters.tgz adapters' >/dev/null 2>&1 &) && "
    "nohup python -u -m $MODULE --base $BASE $ARGS > run.log 2>&1 &", shell=True)
PY
  tmo 180 colab exec -s "$S" -f /tmp/_srun.py >/dev/null 2>&1 || true

  cat > /tmp/_speek.py <<'PY'
import subprocess
print(subprocess.run("grep -E '\[(serve|gate|tiny|native|matrix|run|arm|resume|cost|domain|P24|sweep|depth|fluids|sim|pool|judge|conf|shim|tunnel|3p|read|skip|train|corpora)\]|passed [0-9]+|"
                     "composition |Traceback|[Ee]rror|OutOfMemory|Killed|\\[pool\\]' "
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
    # A STALE LOCAL COPY MUST NOT BLOCK THE FRESH ONE. This was guarded by "do we
    # already have it", and we did — a one-adapter tarball copied in by hand — so
    # the two-adapter one the session had just built was never fetched, and the
    # session took it with it when it died [ran] 2026-09-13. Fetch, then keep
    # whichever carries more weights.
    if tmo 300 colab download -s "$S" /content/lora-kernel/adapters.tgz \
         "$ADAPTERS.new" >/dev/null 2>&1 && [ -s "$ADAPTERS.new" ]; then
      a=$(weights_in "$ADAPTERS"); b=$(weights_in "$ADAPTERS.new")
      a=${a:-0}; b=${b:-0}
      if [ "$b" -ge "$a" ]; then mv "$ADAPTERS.new" "$ADAPTERS"
        echo "    fetched the adapters ($b with weights)"
      else rm -f "$ADAPTERS.new"; fi
    fi
    echo "$out" | grep -qE "composition |Sequential:|The kernel adapter reproduced|\[pool\] complete|STOPPED|Traceback|OutOfMemory|Killed" && break
    sleep 45
  done
  tmo 180 colab download -s "$S" "$REMOTE" "$LOCAL" >/dev/null 2>&1 || echo "    WARNING: nothing came back"

  # ONE LAST REACH FOR THE WEIGHTS, BECAUSE THE LOOP AND THE TARBALL RACE. The tar
  # is built in the background after a sleep, and the loop breaks the moment it
  # sees `[pool] complete` — so on the last iteration the archive may not exist
  # yet, and stopping the session here would take nine minutes of training with it.
  # That is not hypothetical: it happened on 2026-09-14, by a different route, and
  # the retraining cost more than this retry ever will [ran].
  have=$(weights_in "$ADAPTERS"); have=${have:-0}
  if [ ! -s "$ADAPTERS" ] || [ "$have" -eq 0 ]; then
    echo "    no weights yet — packing and fetching before the session goes"
    cat > /tmp/_repack.py <<'PYPACK'
import subprocess
print(subprocess.run("cd /content/lora-kernel && rm -f adapters.tgz && "
                     "tar czf adapters.tgz adapters && ls -l adapters.tgz",
                     shell=True, capture_output=True, text=True).stdout.strip()[-120:])
PYPACK
    tmo 300 colab exec -s "$S" -f /tmp/_repack.py >/dev/null 2>&1 || true
    if tmo 600 colab download -s "$S" /content/lora-kernel/adapters.tgz \
         "$ADAPTERS.new" >/dev/null 2>&1 && [ -s "$ADAPTERS.new" ]; then
      mv "$ADAPTERS.new" "$ADAPTERS"
      echo "    fetched the adapters on the way out"
    else
      echo "    WARNING: the weights did not come back and the session is closing"
    fi
  fi
  colab stop -s "$S" >/dev/null 2>&1 || true; trap - EXIT

  python3 - <<PY
import json, pathlib
p = pathlib.Path("$LOCAL")
if p.exists():
    d = json.loads(p.read_text())
    # NOT EVERY RUNNER WRITES ARMS. train_pool writes a list of adapters, and this
    # block raised KeyError on it — under set -e that ended the chain before the
    # final download, losing the weights the session had just finished training.
    for k, v in (d.get("arms") or {}).items():
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
