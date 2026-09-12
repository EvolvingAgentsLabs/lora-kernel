#!/usr/bin/env bash
# P23's candidates, on Colab instead of the user's own GPU.
#
#   GPU=L4 training/harness/chain_ollama.sh
#
# WHY OLLAMA AND NOT TRANSFORMERS. The candidate ladder has to be comparable to
# `qwen3.5:4b`'s published 14/30, and that number came out of ollama — its
# quantisation, its chat template, its sampling defaults. Running the other
# candidates through a different stack would put the loader inside the ordering
# test, which is exactly the confound S2 exists to avoid. So the same server runs,
# on a rented card instead of a local one.
#
# AND ALL FOUR CANDIDATES ARE RE-RUN, the 4b included. Mac ollama and Linux ollama
# are not the same build, and reusing one number from one machine beside three from
# another is the same confound wearing a smaller coat.
set -euo pipefail
GPU="${GPU:-L4}"
BRANCH="${BRANCH:-handbook}"
RUN_DIR="${RUN_DIR:-results/P23-ranking-20260912}"
MODELS="${MODELS:-qwen3.5:2b qwen3.5:4b qwen3.5:9b gemma4:12b}"
SESSIONS="${SESSIONS:-2}"


# EVERY CALL TO THE SESSION IS BOUNDED — see chain_separate.sh. One `colab exec`
# hung for 75 minutes with no timeout and the silence counter could not see it,
# because that counter only advances when a call RETURNS [ran] 2026-09-12.
tmo () {  # tmo SECONDS cmd...  — macOS ships no coreutils `timeout`
  local secs=$1; shift
  "$@" & local p=$!
  ( sleep "$secs"; kill -9 "$p" 2>/dev/null ) >/dev/null 2>&1 & local w=$!
  wait "$p" 2>/dev/null; local rc=$?
  kill -9 "$w" 2>/dev/null
  return $rc
}

for i in $(seq 1 "$SESSIONS"); do
  # NOTHING LEFT TO DO IS NOT A REASON TO RENT A CARD. chain_separate.sh spent two
  # whole sessions retraining adapters for a finished experiment before this check
  # existed [ran] 2026-09-10.
  missing=0
  for m in $MODELS; do
    [ -f "$RUN_DIR/$(echo "$m" | tr ':.' '--')/headroom.json" ] || missing=1
  done
  [ "$missing" = "0" ] && { echo "=== every candidate is on disk"; break; }

  S="olm$(date +%H%M%S)"
  echo "=== session $i of $SESSIONS · $S · $GPU"
  tmo 600 colab new --gpu "$GPU" -s "$S" >/dev/null
  trap 'colab stop -s "$S" >/dev/null 2>&1 || true' EXIT

  cat > /tmp/_oboot.py <<PY
import subprocess
print(subprocess.run(
    "rm -rf /content/lora-kernel && cd /content && git clone -q -b $BRANCH "
    "https://github.com/EvolvingAgentsLabs/lora-kernel.git && "
    "(curl -fsSL https://ollama.com/install.sh | sh >/dev/null 2>&1) && "
    "(nohup ollama serve > /content/ollama.log 2>&1 &) && sleep 8 && "
    "cd lora-kernel && git log --oneline -1", shell=True,
    capture_output=True, text=True).stdout)
PY
  cat > /tmp/_ocheck.py <<'PY'
import subprocess
print(subprocess.run("cd /content/lora-kernel && git log --oneline -1 && "
                     "ollama --version", shell=True,
                     capture_output=True, text=True).stdout.strip() or "NO CLONE")
PY
  HEAD=""
  for try in 1 2 3; do
    tmo 180 colab exec -s "$S" -f /tmp/_oboot.py >/dev/null 2>&1 || true
    HEAD=$(tmo 180 colab exec -s "$S" -f /tmp/_ocheck.py 2>/dev/null | grep -vE "^\[colab\]|^$" | head -1 || true)
    case "$HEAD" in ""|*"NO CLONE"*) echo "    boot attempt $try did not take" ;; *) break ;; esac
  done
  case "$HEAD" in ""|*"NO CLONE"*) echo "    giving up: no checkout"; colab stop -s "$S" >/dev/null 2>&1; exit 1 ;; esac
  echo "    $HEAD"

  # WHAT IS ALREADY DOWNLOADED DOES NOT GET RE-RUN. Each candidate writes its own
  # directory, so a reclaimed session costs one model and never the ladder.
  RUNS=""
  for m in $MODELS; do
    d="$RUN_DIR/$(echo "$m" | tr ':.' '--')"
    [ -f "$d/headroom.json" ] && continue
    RUNS="$RUNS $m"
  done
  echo "    still to run:$RUNS"

  cat > /tmp/_orun.py <<PY
import subprocess
script = '''
cd /content/lora-kernel
for m in$RUNS; do
  d="$RUN_DIR/\$(echo \$m | tr ':.' '--')"
  echo "=== \$m"
  ollama pull "\$m" >/dev/null 2>&1
  python -u -m training.physics.headroom --small "ollama:\$m" --large "" \\
    --n 30 --seed 515151 --contract shared --rtol 0.02 --max-tokens 6000 \\
    --run-dir "\$d"
done
echo "=== P23 CANDIDATES DONE"
'''
open("/content/p23.sh", "w").write(script)
subprocess.Popen("cd /content && nohup bash p23.sh > p23.log 2>&1 &", shell=True)
PY
  tmo 180 colab exec -s "$S" -f /tmp/_orun.py >/dev/null 2>&1 || true

  cat > /tmp/_opeek.py <<'PY'
import subprocess
print(subprocess.run("tail -3 /content/p23.log", shell=True,
                     capture_output=True, text=True).stdout)
PY
  cat > /tmp/_opull.py <<PY
import base64, glob, json, subprocess
out = {}
for f in glob.glob("$RUN_DIR/*/headroom.json", root_dir="/content/lora-kernel"):
    out[f] = open("/content/lora-kernel/" + f).read()
print("RESULTS " + base64.b64encode(json.dumps(out).encode()).decode())
PY
  printf 'print("ALIVE")\n' > /tmp/_oalive.py
  QUIET=0
  for _ in $(seq 1 120); do
    out=$(tmo 180 colab exec -s "$S" -f /tmp/_opeek.py 2>/dev/null | grep -vE "^\[colab\]|^$" || true)
    if [ -n "$out" ]; then echo "    $out" | tail -2; QUIET=0; else
      QUIET=$((QUIET + 1))
      # A SESSION THAT IS STILL LISTED CAN STILL BE MUTE — five hours were spent
      # polling one [ran] 2026-09-11. The channel is probed directly.
      if [ "$QUIET" -ge 6 ]; then
        ALIVE=$(tmo 180 colab exec -s "$S" -f /tmp/_oalive.py 2>/dev/null | grep -c ALIVE || true)
        [ "$ALIVE" = "0" ] && { echo "    $S is not answering — giving up on it"; break; }
        QUIET=0
      fi
    fi
    blob=$(tmo 180 colab exec -s "$S" -f /tmp/_opull.py 2>/dev/null | grep "^RESULTS " | cut -d' ' -f2- || true)
    if [ -n "$blob" ]; then
      BLOB="$blob" python3 - <<'PY'
import base64, json, os, pathlib
for f, body in json.loads(base64.b64decode(os.environ["BLOB"])).items():
    p = pathlib.Path(f); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(body)
    d = json.loads(body)
    for k, v in d["arms"].items():
        print(f"    got {k} {v['passed']}/{v['n']}")
PY
    fi
    echo "$out" | grep -qE "CANDIDATES DONE|Traceback|OutOfMemory|Killed" && break
    sleep 45
  done
  colab stop -s "$S" >/dev/null 2>&1 || true; trap - EXIT
done
