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

for i in $(seq 1 "$SESSIONS"); do
  # NOTHING LEFT TO DO IS NOT A REASON TO RENT A CARD. chain_separate.sh spent two
  # whole sessions retraining adapters for a finished experiment before this check
  # existed [ran] 2026-09-10.
  # A FILE IS NOT A RESULT. The first run wrote four headroom.json files in five
  # minutes, each 0/60 with every response empty, and this check declared the work
  # done [ran] 2026-09-12. A run where nothing parsed is a broken run.
  missing=0
  for m in $MODELS; do
    f="$RUN_DIR/$(echo "$m" | tr ':.' '--')/headroom.json"
    [ -f "$f" ] || { missing=1; continue; }
    python3 -c "
import json,sys
a=next(iter(json.load(open(sys.argv[1]))['arms'].values()))
sys.exit(1 if a['unparsed'] >= a['n'] else 0)" "$f" || missing=1
  done
  [ "$missing" = "0" ] && { echo "=== every candidate is on disk"; break; }

  S="olm$(date +%H%M%S)"
  echo "=== session $i of $SESSIONS · $S · $GPU"
  tmo 600 colab new --gpu "$GPU" -s "$S" >/dev/null
  trap 'colab stop -s "$S" >/dev/null 2>&1 || true' EXIT

  # EACH STEP REPORTS, BECAUSE THE CHAINED VERSION HID WHICH ONE FAILED. The
  # install was piped to /dev/null and `&&`-chained, so a failed install silently
  # skipped `ollama serve` and the only line that came back was the git HEAD —
  # which read like a healthy boot [ran] 2026-09-12.
  cat > /tmp/_oboot.py <<PY
import subprocess

def step(name, cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()
    print(f"{name}: rc={r.returncode} {tail[-1] if tail else ''}"[:160])

step("clone", "rm -rf /content/lora-kernel && cd /content && git clone -q -b $BRANCH "
              "https://github.com/EvolvingAgentsLabs/lora-kernel.git && "
              "cd lora-kernel && git log --oneline -1")
step("install", "curl -fsSL https://ollama.com/install.sh | sh 2>&1 | tail -2")
# setsid, so the server is not a child of the cell that started it.
step("serve", "setsid nohup ollama serve > /content/ollama.log 2>&1 < /dev/null & "
              "sleep 12; tail -2 /content/ollama.log")
PY
  # THE CHECK HAS TO PROVE THE SERVER ANSWERS, NOT THAT A BINARY EXISTS. The first
  # version verified the git checkout and took `head -1` of the output, so
  # `ollama --version` was never even read — and four candidates ran to completion
  # against a server that was not there, each producing 60 empty responses and a
  # tidy `0/60` that looked exactly like a model failing the suite [ran] 2026-09-12.
  # A generation that comes back with text is the only proof that counts.
  cat > /tmp/_ocheck.py <<'PY'
import subprocess
r = subprocess.run(
    "cd /content/lora-kernel && git log --oneline -1 && "
    "(ollama pull qwen3.5:2b 2>&1 | tail -1) && "
    "(ollama run qwen3.5:2b 'say OK' 2>&1 | tail -1)",
    shell=True, capture_output=True, text=True)
lines = [l for l in r.stdout.splitlines() if l.strip()]
print(" | ".join(lines) if len(lines) >= 3 else "OLLAMA NOT SERVING")
PY
  HEAD=""
  for try in 1 2 3; do
    tmo 600 colab exec -s "$S" -f /tmp/_oboot.py >/dev/null 2>&1 || true
    HEAD=$(tmo 600 colab exec -s "$S" -f /tmp/_ocheck.py 2>/dev/null | grep -vE "^\[colab\]|^$" | head -1 || true)
    case "$HEAD" in
      ""|*"NO CLONE"*|*"NOT SERVING"*) echo "    boot attempt $try did not take: ${HEAD:-silence}" ;;
      *) break ;;
    esac
  done
  case "$HEAD" in
    ""|*"NO CLONE"*|*"NOT SERVING"*)
      echo "    GIVING UP: no checkout, or ollama is not answering. Running the"
      echo "    candidates against a dead server produces 60 empty answers per model"
      echo "    and a 0/60 that reads exactly like a result."
      tmo 300 colab stop -s "$S" >/dev/null 2>&1; exit 1 ;;
  esac
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
  ollama pull "\$m" 2>&1 | tail -1
  python -u -m training.physics.headroom --small "ollama:\$m" --large "" \\
    --n 60 --seed 515151 --contract shared --rtol 0.02 --max-tokens 6000 \\
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
