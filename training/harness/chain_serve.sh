#!/usr/bin/env bash
# P26 on a rented card: install vLLM, serve the pool, run the three arms.
#
#   GPU=A100 training/harness/chain_serve.sh
#
# THE ADAPTERS ARE CARRIED IN, NOT RETRAINED. This step measures a serving stack,
# not a training one, and retraining inside it would put forty minutes and a second
# source of variance into a question about HTTP.
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
GPU="${GPU:-A100}"
BRANCH="${BRANCH:-handbook}"
RUN_DIR="${RUN_DIR:-results/P26-openai-server-20260913}"
MODULE="${MODULE:-training.harness.serve_openai}"
MARGS="${MARGS:---adapter kernel=adapters/kernel-mt --adapter domain=adapters/domain-mt}"
RESULTS_NAME="${RESULTS_NAME:-serve_results.json}"
BASE="${BASE:-Qwen/Qwen2.5-3B-Instruct}"
SESSIONS="${SESSIONS:-2}"
# THE TWO OPTIONAL SWITCHES, DEFAULTED HERE RATHER THAN AT THEIR USE SITES.
# `set -u` turns a bare $TRAINDEPS inside a heredoc into a dead chain, and it
# died at line 69 with the reason printed as the heredoc's line number rather
# than the reference's [ran] 2026-09-14. Same family as the ${ARGS:-} bug
# recorded in chain_separate.sh, which cost two sessions.
TRAINDEPS="${TRAINDEPS:-}"
SKIP_ADAPTERS="${SKIP_ADAPTERS:-}"
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

# A REJECTED ACCELERATOR IS NOT A FAILED COMMAND. When the account has no units left the backend
# answers "Backend rejected accelerator 'L4'. You may not have quota or entitlement…" and
# `colab new` still exits 0 — so the chain walked on with no session, polling nothing, and had to
# be killed by hand [ran] 2026-09-20. Read what it said, not only how it exited, and stop before
# the EXIT trap exists: there is no session to stop, and nothing may be left behind.
open_session () {  # open_session SECONDS GPU NAME
  local out rc=0
  out=$(tmo "$1" colab new --gpu "$2" -s "$3" 2>&1) || rc=$?
  if [ "$rc" -ne 0 ] || printf '%s' "$out" | grep -qiE 'rejected accelerator|quota or entitlement'; then
    echo "NO SESSION: the backend gave no $2 (rc=$rc) — quota or entitlement, not an outage; nothing was started. A T4 is not a substitute."
    printf '%s\n' "$out" | tail -2
    return 3
  fi
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
  open_session 900 "$GPU" "$S" || exit 3
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
# raised on import, so vllm never starts [ran] 2026-09-13. Neither is needed to
# serve a text model, so they go before vllm arrives rather than being pinned
# around.
step("clear", "pip -q uninstall -y torchaudio torchvision 2>&1 | tail -1; echo cleared")
step("vllm", "pip -q install 'vllm>=0.28' 2>&1 | tail -1")
# PEFT AND DATASETS ONLY WHEN THE STEP TRAINS. native_gate trains a tiny adapter
# before serving it; every other module here only serves. P26 learned what putting
# training into a serving session costs: an import error for trl, after vLLM had
# already installed, in a session that had no reason to carry it.
# (No backticks in this heredoc: it is unquoted so BRANCH interpolates, a leading
#  hash comments nothing here, and bash runs whatever looks like a substitution.
#  Four times now, so tests/test_chain_scripts.py fails the build instead.)
# torchao IS PINNED HERE FOR THE SAME REASON chain_separate.sh pins it: Colab ships
# 0.10.0, transformers refuses anything under 0.16.0, and the refusal arrives as an
# ImportError in the first second of the run. That fix has been in the training chain
# for days and was not carried across when this one learned to train [ran] 2026-09-14.
step("train deps", "[ -z '${TRAINDEPS:-}' ] || pip -q install peft trl datasets accelerate bitsandbytes 'torchao>=0.16.0' 2>&1 | tail -1; echo ok")
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
  # THE PARTIAL RESULTS GO IN WITH THE WEIGHTS. A session lives sixty minutes [ran] 2026-09-19, so
  # a run longer than that is several sessions, and a runner resumes from its own results file —
  # which a new VM does not have unless it is put there. `"trained_only"` is a marker of the LAST
  # session's end, not of this one's, and is taken out on the way in.
  if [ -f "$LOCAL" ] && ! grep -q '"finished"' "$LOCAL" 2>/dev/null; then
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d.pop("trained_only",None); json.dump(d,open(sys.argv[2],"w"),indent=1)' "$LOCAL" /tmp/_resume.json
    tmo 300 colab upload -s "$S" /tmp/_resume.json "/content/lora-kernel/$RESULTS_NAME" >/dev/null 2>&1 \
      && echo "    carried the partial results in" || echo "    could not carry the partial results in"
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
    # EVERY RUNNER'S PREFIX, NOT THE ONES THIS CHAIN STARTED WITH. triage_run
    # prints `[run]` and `[arm]`; neither was here, so a 150-case scoring run
    # showed as silence for its whole length and could not have been stopped
    # early [ran] 2026-09-14. Fifth time a log held the answer and a filter
    # kept it out, so tests/test_chain_scripts.py now checks the two agree.
    "grep -E '(serve|gate|tiny|native|matrix|run|arm|resume|cost|domain|P24|sweep|depth|fluids|sim|pool|judge|conf|shim|tunnel|3p|read|skip|train|loss|corpora|draft|desk|zero|code|rank|substrate|release|attr|sim|awq|tiny|precision|kb|route|live|radar)\\]|"
    "passed [0-9]+|clears the gate|prompts/s|Traceback|[Ee]rror|OutOfMemory|Killed|"
    # THE TRAINER'S ONLY SIGN OF LIFE IS ITS STEP BAR. `loss]` above has never matched: this
    # harness's Trainer prints no loss line at all — zero in M1's logs, zero in arm 0c's 114 steps
    # [ran] 2026-09-19 — so an abort rule keyed to it fires on a healthy run. tqdm redraws with a
    # carriage return, which makes 45 minutes of training ONE line to grep: split it first.
    " [0-9]+/[0-9]+ \\[[0-9:]+<' "
    "<(tr '\\r' '\\n' < /content/lora-kernel/run.log) | tail -3", shell=True, executable='/bin/bash',
    capture_output=True, text=True).stdout)
PY
  printf 'print("ALIVE")\n' > /tmp/_valive.py
  QUIET=0
  DEAF=0
  HOME_PACKS=0
  for _ in $(seq 1 120); do
    out=$(tmo 300 colab exec -s "$S" -f /tmp/_vpeek.py 2>/dev/null | grep -vE "^\[colab\]|^$" || true)
    if [ -n "$out" ]; then echo "$out" | sed "s/^/    /" | tail -3; QUIET=0; else
      QUIET=$((QUIET + 1))
      if [ "$QUIET" -ge 6 ]; then
        A=$(tmo 300 colab exec -s "$S" -f /tmp/_valive.py 2>/dev/null | grep -c ALIVE || true)
        # ONE SILENT PROBE IS NOT A DEAD SESSION. An expired `colab exec` is not a failed
        # command (CLAUDE.md §3), and giving up here *stops the session*: M1's first
        # attempt trained a member for fifty minutes in silence, one probe went
        # unanswered, and the chain ended a run whose second training had just begun
        # [ran] 2026-09-19. Three in a row, a minute apart, before a card is given up.
        if [ "$A" = "0" ]; then
          DEAF=$((DEAF + 1))
          echo "    $S did not answer a probe ($DEAF of 3)"
          [ "$DEAF" -ge 3 ] && { echo "    $S is not answering — giving up on it"; break; }
          sleep 60; continue
        fi
        DEAF=0
        QUIET=0
      fi
    fi
    tmo 300 colab download -s "$S" /content/lora-kernel/$RESULTS_NAME "$LOCAL" >/dev/null 2>&1 || true
    # WEIGHTS COME HOME WHEN THEY EXIST, NOT WHEN THE RUN ENDS. A runner that trains more
    # than one adapter says so in its results file (`"packed": n`) each time it repacks
    # `adapters_out.tgz`; fetched only at the end, fifty minutes of training died with
    # the session that held it [ran] 2026-09-19. A checkpoint nobody downloads is a
    # checkpoint nobody has — and a dead session gives nothing back.
    # `|| true` IS THE LINE. Under `set -euo pipefail` a grep that finds nothing exits 1 and
    # takes the chain with it — and the EXIT trap then stops the card. Attempt 2 of M1 died
    # on its first poll exactly so, before the key this looks for could exist [ran]
    # 2026-09-19. `bash -n` cannot see it; tests/test_chain_scripts.py runs this line.
    PACKS=$(grep -o '"packed": *[0-9]*' "$LOCAL" 2>/dev/null | grep -o '[0-9]*$' | tail -1 || true)
    if [ -n "${PACKS:-}" ] && [ "$PACKS" -gt "$HOME_PACKS" ]; then
      tmo 900 colab download -s "$S" /content/lora-kernel/adapters_out.tgz "$RUN_DIR/adapters_out.tgz" >/dev/null 2>&1 \
        && { HOME_PACKS=$PACKS; echo "    adapters home: $PACKS packed"; } || true
    fi
    # THE WATCH LOOP HAS TO KNOW EVERY WAY A RUN ENDS, not the ways the first
    # runner ended. triage_run finishes by printing its arm table and nothing here
    # matched it, so a completed 150-case run held an L4 for the loop's full 120
    # iterations — ninety minutes of a card for a result already on disk
    # [ran] 2026-09-14. The results file is the authority: if the runner wrote its
    # completion marker, the run is over whatever the log looks like.
    if [ -f "$LOCAL" ] && grep -q '"finished"\|"decision"\|stopped_at_gate\|"trained_only"' "$LOCAL" 2>/dev/null; then
      echo "    the runner wrote its result — done"; break
    fi
    echo "$out" | grep -qE "prompts/s|decision:|clears the gate|STOPPED|Traceback|OutOfMemory|Killed|never came up" && break
    sleep 45
  done
  tmo 300 colab download -s "$S" /content/lora-kernel/$RESULTS_NAME "$LOCAL" >/dev/null 2>&1 || true
  tmo 300 colab download -s "$S" /content/lora-kernel/vllm.log "$RUN_DIR/vllm.log" >/dev/null 2>&1 || true
  # WEIGHTS A RUNNER PRODUCED COME HOME. P64 attempt 1 trained and released a member
  # and this chain stopped the session with the adapter still on it [ran] 2026-09-18;
  # a runner that trains packs `adapters_out.tgz` and it is fetched here.
  tmo 600 colab download -s "$S" /content/lora-kernel/adapters_out.tgz "$RUN_DIR/adapters_out.tgz" >/dev/null 2>&1 || true
  # THE PARTIAL ARMS, NOT ONLY THE FINISHED RESULT. P47 died at 260 of 475 with a
  # checkpoint on the VM that nobody fetched, so the next attempt had nothing to
  # resume from and paid for those 260 again [ran] 2026-09-16. A checkpoint nobody
  # downloads is a checkpoint nobody has.
  for _arm in arm_base arm_expert arm_tools arm_email-full arm_fluids-full; do
    tmo 120 colab download -s "$S" "/content/lora-kernel/$_arm.json"         "$RUN_DIR/$_arm.json" >/dev/null 2>&1 || true
  done
  tmo 300 colab stop -s "$S" >/dev/null 2>&1 || true; trap - EXIT
done
