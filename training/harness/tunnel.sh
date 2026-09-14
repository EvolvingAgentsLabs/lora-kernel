#!/usr/bin/env bash
# The pool, the translation and a public URL — for pointing a real agent at it.
#
#   RUN THIS INSIDE A COLAB SESSION, not here.
#
# WHY A KEY IS NOT OPTIONAL. A tunnel turns a localhost proxy into a public inference
# endpoint. An open one is somebody else's free GPU, and the URL is guessable enough
# that "nobody knows it" is not a control. One is generated if none is given.
set -euo pipefail
BASE="${BASE:-Qwen/Qwen2.5-3B-Instruct}"
KEY="${KEY:-$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')}"
LOG="${LOG:-/content/traffic.jsonl}"

cd /content/lora-kernel
[ -f adapters.tgz ] && tar xzf adapters.tgz

nohup vllm serve "$BASE" --enable-lora --max-lora-rank 16 --max-loras 2 \
  --dtype bfloat16 --lora-modules kernel=adapters/kernel-mt domain=adapters/domain-mt \
  > vllm.log 2>&1 &

for _ in $(seq 1 180); do
  curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 5
done
curl -sf http://127.0.0.1:8000/health >/dev/null || { echo "vllm no levantó"; tail -20 vllm.log; exit 1; }
echo "=== vllm arriba"

nohup python -u -m training.harness.openai_proxy \
  --upstream http://127.0.0.1:8000 --port 8001 --api-key "$KEY" --log "$LOG" \
  > proxy.log 2>&1 &
sleep 4

# A quick tunnel needs no account and no token. It is ephemeral, which is the right
# lifetime for a measurement session.
if ! command -v cloudflared >/dev/null; then
  curl -sL -o /usr/local/bin/cloudflared \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
  chmod +x /usr/local/bin/cloudflared
fi
nohup cloudflared tunnel --url http://127.0.0.1:8001 --no-autoupdate > tunnel.log 2>&1 &

for _ in $(seq 1 60); do
  URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" tunnel.log | head -1 || true)
  [ -n "$URL" ] && break
  sleep 3
done
[ -z "${URL:-}" ] && { echo "el túnel no publicó una URL"; tail -20 tunnel.log; exit 1; }

cat <<EOF

=== listo

  base URL   $URL/v1
  api key    $KEY
  models     kernel · domain · $BASE
  traffic    $LOG   (for training.harness.null_arm)

Point the agent at that base URL with that key. The key is not optional: the URL is
public while this session lives.
EOF
tail -f proxy.log
